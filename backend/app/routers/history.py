"""GET /api/v1/history — 查询发布历史 + POST /api/v1/history/save — 保存发布记录 + 下架/发布操作"""
import logging
import requests
from PIL import Image
import io
from fastapi import APIRouter, Query

from app.models.schemas import HistoryItem, GenerateSaveRequest
from app.db import crud
from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant

logger = logging.getLogger(__name__)

router = APIRouter(tags=["发布历史"])


@router.get("/history")
async def get_history(user_id: int = Query(default=1)):
    """查询当前用户的发布记录列表"""
    rows = await crud.get_history(user_id)
    items = []
    for r in rows:
        items.append(HistoryItem(
            id=r["id"],
            user_id=r["user_id"],
            original_image_url=r["original_image_url"],
            ai_generated_title=r["ai_generated_title"],
            ai_generated_desc=r.get("ai_generated_desc"),
            suggested_price=float(r["suggested_price"]) if r.get("suggested_price") else None,
            status=r["status"],
            created_at=str(r["created_at"]),
        ))
    return {"items": items}


@router.post("/history/save")
async def save_history(payload: GenerateSaveRequest):
    """
    保存生成的文案到发布记录（可指定 status: published / draft）
    保存成功后自动加入以图搜图索引
    """
    # 1. 保存商品到 MySQL
    item_id = await crud.insert_published_item(
        user_id=payload.user_id,
        image_url=payload.image_url,
        title=payload.title,
        desc=payload.desc,
        price=payload.price,
        status=payload.status,
    )
    
    # 2. 🆕 自动加入以图搜图索引
    try:
        img_url = payload.image_url
        if img_url.startswith('/static/'):
            img_url = f"http://localhost:8000{img_url}"
        
        resp = requests.get(img_url, timeout=10)
        if resp.status_code == 200:
            pil_img = Image.open(io.BytesIO(resp.content))
            
            extractor = get_extractor()
            vector = extractor.extract_image(pil_img)
            
            qdrant = get_qdrant()
            qdrant.add_item(item_id, vector, {
                'title': payload.title,
                'category': getattr(payload, 'category', ''),
                'price': float(payload.price) if payload.price else 0
            })
            logger.info(f"✅ 商品 {item_id} 已自动加入以图搜图索引")
        else:
            logger.warning(f"⚠️ 商品 {item_id} 图片下载失败，未加入索引")
            
    except Exception as e:
        logger.error(f"自动索引失败: {e}")
        # 不影响主流程

    return {"id": item_id, "status": "saved"}


@router.post("/history/{item_id}/delist")
async def delist_item(item_id: int):
    """下架商品"""
    await crud.update_item_status(item_id, "delisted")
    return {"status": "delisted"}


@router.post("/history/{item_id}/publish")
async def publish_item(item_id: int):
    """从草稿发布"""
    await crud.update_item_status(item_id, "published")
    return {"status": "published"}