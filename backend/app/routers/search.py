"""
以图搜图 + 以文搜图 API
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from PIL import Image
import io
import logging
import httpx

from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.db import crud
from app.config import get_static_url, get_base_url
from app.dependencies import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(tags=["以图搜图"])

# ✅ 搜索参数限制
MAX_TOP_K = 100
DEFAULT_TOP_K = 10


def build_image_url(image_url: str) -> str:
    """构建完整的图片 URL"""
    if not image_url:
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    if image_url.startswith("/static/"):
        return f"{get_base_url()}{image_url}"
    return get_static_url(image_url)


@router.post("/search/image")
async def search_by_image(
    image: UploadFile = File(...),
    top_k: int = Form(10, ge=1, le=MAX_TOP_K),  # ✅ 添加范围验证
    filter_category: str = Form(default=""),
    user_id: int = Depends(get_current_user),
):
    """
    以图搜图：上传图片，返回相似商品列表
    
    Args:
        top_k: 返回结果数量 (1-100)
    """
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        qdrant = get_qdrant()
        results = qdrant.search(
            vector=vector,
            top_k=top_k,
            filter_category=filter_category if filter_category else None,
        )

        items = []
        for r in results:
            item_id = r["id"]
            score = r["score"]
            payload = r["payload"] or {}

            item = await crud.get_item_by_id(item_id)
            if item and item.get('status') == 'published':
                img_url = build_image_url(item.get("original_image_url", ""))
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': img_url,
                    'category': item.get('category'),
                    'similarity': round(score, 4)
                })

        return {
            'success': True,
            'results': items,
            'count': len(items)
        }

    except Exception as e:
        logger.error(f"以图搜图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/text")
async def search_by_text(
    text: str = Form(..., description="商品描述文本"),
    top_k: int = Form(10, ge=1, le=MAX_TOP_K),  # ✅ 添加范围验证
    category: Optional[str] = Form(None, description="筛选品类（可选）"),
    user_id: int = Depends(get_current_user),
):
    """
    以文搜图：输入文字描述，返回匹配的商品列表
    
    Args:
        top_k: 返回结果数量 (1-100)
    """
    try:
        # 1. 提取文本特征向量
        extractor = get_extractor()
        vector = extractor.extract_text(text)

        # 2. Qdrant 检索
        qdrant = get_qdrant()
        results = qdrant.search(
            vector=vector,
            top_k=top_k,
            filter_category=category if category else None,
        )

        # 3. 查询商品详情
        items = []
        for r in results:
            item_id = r["id"]
            score = r["score"]
            payload = r["payload"] or {}

            item = await crud.get_item_by_id(item_id)
            if item and item.get('status') == 'published':
                img_url = build_image_url(item.get("original_image_url", ""))
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': img_url,
                    'category': item.get('category'),
                    'similarity': round(score, 4)
                })

        return {
            'success': True,
            'results': items,
            'count': len(items)
        }

    except Exception as e:
        logger.error(f"以文搜图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/index")
async def add_to_index(
    item_id: int = Form(...),
    image_url: str = Form(...),
    title: str = Form(""),
    category: str = Form(""),
    user_id: int = Depends(get_current_user),
):
    """商品上架时加入索引"""
    try:
        full_url = build_image_url(image_url)
        if not full_url:
            raise HTTPException(status_code=400, detail="无效的图片URL")

        # 使用 httpx.AsyncClient 异步下载
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(full_url)
            response.raise_for_status()
            content = response.content

        pil_image = Image.open(io.BytesIO(content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        payload = {
            'title': title,
            'category': category,
        }
        qdrant = get_qdrant()
        qdrant.add_item(item_id, vector, payload)

        return {
            'success': True,
            'item_id': item_id,
            'message': '已加入索引'
        }

    except httpx.TimeoutException:
        logger.error(f"⏱️ 图片下载超时: {image_url}")
        raise HTTPException(status_code=408, detail="图片下载超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ 图片下载失败 (HTTP {e.response.status_code}): {image_url}")
        raise HTTPException(status_code=400, detail=f"图片下载失败: HTTP {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加入索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/stats")
async def search_stats():
    """获取索引统计信息"""
    try:
        qdrant = get_qdrant()
        return {
            'total_items': qdrant.count(),
            'collection': qdrant.collection_name,
            'vector_size': qdrant.vector_size,
            'host': qdrant.host,
            'port': qdrant.port
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/health")
async def search_health():
    """健康检查"""
    try:
        extractor = get_extractor()
        qdrant = get_qdrant()
        return {
            "status": "healthy",
            "clip_model": extractor.model_name,
            "clip_device": extractor.device,
            "clip_pretrained": extractor.pretrained,
            "qdrant_collection": qdrant.collection_name,
            "qdrant_count": qdrant.count()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )