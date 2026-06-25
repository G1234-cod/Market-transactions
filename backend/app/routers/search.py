"""
以图搜图 + 以文搜图 API
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
import logging

from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.db import crud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["以图搜图"])


@router.post("/search/image")
async def search_by_image(
    image: UploadFile = File(...),
    top_k: int = Form(10)
):
    """
    以图搜图：上传图片，返回相似商品列表
    """
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        qdrant = get_qdrant()
        results = qdrant.search(vector, top_k)

        items = []
        for item_id, score, payload in results:
            item = await crud.get_item_by_id(item_id)
            if item and item.get('status') == 'published':
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': item['original_image_url'],
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
    top_k: int = Form(10, description="返回结果数量"),
    category: str = Form(None, description="筛选品类（可选）")
):
    """
    以文搜图：输入文字描述，返回匹配的商品列表
    
    示例：
    - 搜索 "红色手机" → 返回匹配的商品
    - 搜索 "iPhone 13" → 返回 iPhone 13 相关商品
    - 搜索 "笔记本" → 返回所有笔记本
    """
    try:
        # 1. 提取文本特征向量
        extractor = get_extractor()
        vector = extractor.extract_text(text)

        # 2. 构建过滤条件
        filter_condition = None
        if category:
            filter_condition = {'category': category}

        # 3. Qdrant 检索
        qdrant = get_qdrant()
        results = qdrant.search(vector, top_k, filter_condition)

        # 4. 查询商品详情
        items = []
        for item_id, score, payload in results:
            item = await crud.get_item_by_id(item_id)
            if item and item.get('status') == 'published':
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': item['original_image_url'],
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
    category: str = Form("")
):
    """商品上架时加入索引"""
    try:
        import requests
        response = requests.get(image_url, timeout=10)
        pil_image = Image.open(io.BytesIO(response.content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        payload = {'item_id': item_id, 'title': title, 'category': category}
        qdrant = get_qdrant()
        qdrant.add_item(item_id, vector, payload)

        return {'success': True, 'item_id': item_id, 'message': '已加入索引'}

    except Exception as e:
        logger.error(f"加入索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/stats")
async def search_stats():
    """获取索引统计信息"""
    qdrant = get_qdrant()
    return {
        'total_items': qdrant.count(),
        'collection': qdrant.COLLECTION_NAME,
        'vector_size': qdrant.VECTOR_SIZE
    }