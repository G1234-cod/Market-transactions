"""
批量索引已有商品到 Qdrant（以图搜图）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from PIL import Image
import io
import logging

from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.db import crud
from app.config import get_base_url, get_static_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_image_url(image_url: str) -> str:
    """
    构建完整的图片URL（解决硬编码 localhost 问题）
    
    Args:
        image_url: 原始图片路径（可能是相对路径或完整URL）
    
    Returns:
        str: 完整的图片URL
    """
    if not image_url:
        return ""
    
    # 已经是完整URL
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    
    # 以 /static/ 开头
    if image_url.startswith("/static/"):
        return f"{get_base_url()}{image_url}"
    
    # 使用静态文件工具函数
    return get_static_url(image_url)


async def index_all_items():
    """索引所有已发布的商品"""
    print("=" * 70)
    print("🚀 批量索引商品到 Qdrant")
    print("=" * 70)

    # 1. 检查 Qdrant 是否运行
    try:
        import requests as req
        resp = req.get("http://localhost:6333/healthz", timeout=3)
        if resp.status_code != 200:
            print("❌ Qdrant 未正常运行")
            print("   请先启动: docker run -d -p 6333:6333 qdrant/qdrant")
            return
    except:
        print("❌ Qdrant 未正常运行")
        print("   请先启动: docker run -d -p 6333:6333 qdrant/qdrant")
        return

    print("✅ Qdrant 连接正常")
    print(f"📌 服务器地址: {get_base_url()}")

    # 2. 获取所有已发布商品
    print("\n📊 获取商品列表...")
    items = await crud.get_market_items()
    
    if not items:
        print("⚠️ 没有已发布的商品")
        print("   请先发布一些商品，再运行此脚本")
        return

    print(f"✅ 找到 {len(items)} 个已发布商品")

    # 3. 初始化
    extractor = get_extractor()
    qdrant = get_qdrant()

    # 4. 逐个索引
    indexed = 0
    failed = 0
    skipped = 0
    
    for i, item in enumerate(items):
        try:
            print(f"  [{i+1}/{len(items)}] 索引商品 {item['id']}...", end=" ")
            
            image_url = item.get('original_image_url')
            if not image_url:
                print("❌ 无图片URL")
                failed += 1
                continue
            
            # ✅ 动态构建完整URL
            full_url = build_image_url(image_url)
            if not full_url:
                print("❌ 无法构建图片URL")
                failed += 1
                continue
            
            # 下载图片
            response = requests.get(full_url, timeout=15)
            if response.status_code != 200:
                print(f"❌ 图片下载失败 (HTTP {response.status_code})")
                failed += 1
                continue
            
            pil_image = Image.open(io.BytesIO(response.content))
            vector = extractor.extract_image(pil_image)
            
            payload = {
                'title': item.get('ai_generated_title', ''),
                'category': item.get('category', ''),
                'price': float(item.get('suggested_price', 0)) if item.get('suggested_price') else 0,
                'status': item.get('status', 'published')
            }
            
            qdrant.add_item(item['id'], vector, payload)
            indexed += 1
            print("✅")
            
        except requests.exceptions.Timeout:
            print("❌ 下载超时")
            failed += 1
            continue
        except requests.exceptions.ConnectionError:
            print("❌ 连接失败")
            failed += 1
            continue
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            failed += 1
            continue

    print("\n" + "=" * 70)
    print("📊 索引结果")
    print("=" * 70)
    print(f"  ✅ 成功: {indexed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  📦 总计: {len(items)}")
    print(f"  📊 Qdrant 总数: {qdrant.count()}")
    print("=" * 70)


async def index_single_item(item_id: int):
    """
    索引单个商品
    
    Args:
        item_id: 商品ID
    """
    print(f"🔍 索引商品 {item_id}...")
    
    # 获取商品详情
    item = await crud.get_item_by_id(item_id)
    if not item:
        print(f"❌ 商品 {item_id} 不存在")
        return False
    
    try:
        image_url = item.get('original_image_url')
        if not image_url:
            print("❌ 无图片URL")
            return False
        
        full_url = build_image_url(image_url)
        if not full_url:
            print("❌ 无法构建图片URL")
            return False
        
        response = requests.get(full_url, timeout=15)
        if response.status_code != 200:
            print(f"❌ 图片下载失败 (HTTP {response.status_code})")
            return False
        
        pil_image = Image.open(io.BytesIO(response.content))
        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)
        
        qdrant = get_qdrant()
        payload = {
            'title': item.get('ai_generated_title', ''),
            'category': item.get('category', ''),
            'price': float(item.get('suggested_price', 0)) if item.get('suggested_price') else 0,
            'status': item.get('status', 'published')
        }
        
        qdrant.add_item(item_id, vector, payload)
        print(f"✅ 商品 {item_id} 索引成功")
        return True
        
    except Exception as e:
        print(f"❌ 索引失败: {e}")
        return False


async def clear_index():
    """清空索引"""
    print("=" * 70)
    print("⚠️  清空索引")
    print("=" * 70)
    
    confirm = input("确认清空所有索引数据？(y/n): ")
    if confirm.lower() == 'y':
        qdrant = get_qdrant()
        qdrant.clear()
        print("✅ 索引已清空")
    else:
        print("❌ 已取消")


async def show_stats():
    """显示索引统计信息"""
    print("=" * 70)
    print("📊 Qdrant 索引统计")
    print("=" * 70)
    
    try:
        qdrant = get_qdrant()
        count = qdrant.count()
        print(f"  向量总数: {count}")
        
        # 获取集合信息
        info = qdrant.get_collection_info()
        if info:
            print(f"  向量维度: {info.get('vector_size', 'N/A')}")
            print(f"  距离类型: {info.get('distance', 'N/A')}")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
    
    print("=" * 70)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Qdrant 以图搜图索引管理')
    parser.add_argument('--all', action='store_true', help='索引所有商品')
    parser.add_argument('--id', type=int, help='索引指定ID的商品')
    parser.add_argument('--clear', action='store_true', help='清空索引')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.clear:
        asyncio.run(clear_index())
    elif args.stats:
        asyncio.run(show_stats())
    elif args.id:
        asyncio.run(index_single_item(args.id))
    else:
        asyncio.run(index_all_items())