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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    for i, item in enumerate(items):
        try:
            print(f"  [{i+1}/{len(items)}] 索引商品 {item['id']}...", end=" ")
            
            image_url = item.get('original_image_url')
            if not image_url:
                print("❌ 无图片URL")
                failed += 1
                continue
            
            if image_url.startswith('/static/'):
                image_url = f"http://localhost:8000{image_url}"
            
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                print("❌ 图片下载失败")
                failed += 1
                continue
            
            pil_image = Image.open(io.BytesIO(response.content))
            vector = extractor.extract_image(pil_image)
            
            payload = {
                'title': item.get('ai_generated_title', ''),
                'category': item.get('category', ''),
                'price': float(item.get('suggested_price', 0)) if item.get('suggested_price') else 0
            }
            
            qdrant.add_item(item['id'], vector, payload)
            indexed += 1
            print("✅")
            
        except Exception as e:
            print(f"❌ {e}")
            failed += 1
            continue

    print(f"\n✅ 索引完成: {indexed}/{len(items)} 个商品")
    print(f"❌ 失败: {failed} 个")
    print(f"📊 Qdrant 总数: {qdrant.count()}")


async def clear_index():
    """清空索引"""
    print("=" * 70)
    print("⚠️ 清空索引")
    print("=" * 70)
    
    confirm = input("确认清空所有索引数据？(y/n): ")
    if confirm.lower() == 'y':
        qdrant = get_qdrant()
        qdrant.clear()
        print("✅ 索引已清空")
    else:
        print("❌ 已取消")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='索引所有商品')
    parser.add_argument('--clear', action='store_true', help='清空索引')
    
    args = parser.parse_args()
    
    if args.clear:
        asyncio.run(clear_index())
    else:
        asyncio.run(index_all_items())