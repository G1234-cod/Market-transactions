"""GET /api/v1/history — 查询发布历史 + POST /api/v1/history/save — 保存发布记录 + 下架/发布操作"""
import logging
import io
from fastapi import APIRouter, Query, Depends, HTTPException, status
from PIL import Image
import httpx

from app.models.schemas import HistoryItem, GenerateSaveRequest
from app.db import crud
from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.config import get_static_url, get_base_url, settings
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["发布历史"])


def build_image_url(image_url: str) -> str:
    """
    构建完整的图片 URL（统一处理函数）
    
    Args:
        image_url: 原始图片路径（相对路径或完整URL）
    
    Returns:
        str: 完整图片URL
    """
    if not image_url:
        return ""
    
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    
    if image_url.startswith(f"{settings.STATIC_PREFIX}/"):
        return f"{get_base_url()}{image_url}"
    
    return get_static_url(image_url)


@router.get("/history")
async def get_history(
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取，不可伪造
):
    """查询当前用户的发布记录列表"""
    rows = await crud.get_history(user_id)
    items = []
    for r in rows:
        img_url = build_image_url(r.get("original_image_url", ""))
        
        items.append(HistoryItem(
            id=r["id"],
            user_id=r["user_id"],
            original_image_url=img_url,
            ai_generated_title=r["ai_generated_title"],
            ai_generated_desc=r.get("ai_generated_desc"),
            suggested_price=float(r["suggested_price"]) if r.get("suggested_price") else None,
            status=r["status"],
            category=r.get("category"),
            condition=r.get("condition"),  # ✅ 使用 condition
            views=r.get("views", 0),
            created_at=str(r["created_at"]),
        ))
    return {"items": items}


@router.post("/history/save")
async def save_history(
    payload: GenerateSaveRequest,
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取，不可伪造
):
    """
    保存生成的文案到发布记录（可指定 status: published / draft）
    保存成功后自动加入以图搜图索引
    """
    # ✅ 使用从 JWT 获取的 user_id，忽略客户端传入的
    item_id = await crud.insert_published_item(
        user_id=user_id,  # ✅ 来自认证，不可伪造
        image_url=payload.image_url,
        title=payload.title,
        desc=payload.desc,
        price=payload.price,
        status=payload.status,
        category=payload.category,
        brand=payload.brand,
        model=payload.model,
        condition=payload.condition,  # ✅ 使用 condition
    )
    
    # 自动加入以图搜图索引（失败不影响保存结果）
    try:
        await add_to_search_index(item_id, payload)
    except Exception as e:
        logger.error(f"自动索引失败: {e}")

    return {"id": item_id, "status": "saved"}


async def add_to_search_index(item_id: int, payload: GenerateSaveRequest):
    """
    将商品添加到以图搜图索引
    
    Args:
        item_id: 商品ID
        payload: 商品数据
    """
    try:
        img_url = build_image_url(payload.image_url)
        
        if not img_url:
            logger.warning(f"⚠️ 商品 {item_id} 图片URL为空，未加入索引")
            return
        
        logger.info(f"📥 下载图片: {img_url}")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(img_url)
            response.raise_for_status()
            content = response.content
        
        pil_img = Image.open(io.BytesIO(content))
        
        extractor = get_extractor()
        vector = extractor.extract_image(pil_img)
        
        qdrant = get_qdrant()
        qdrant.add_item(item_id, vector, {
            'title': payload.title,
            'category': payload.category or '',
            'price': float(payload.price) if payload.price else 0
        })
        logger.info(f"✅ 商品 {item_id} 已自动加入以图搜图索引")
        
    except httpx.TimeoutException:
        logger.error(f"⏱️ 商品 {item_id} 图片下载超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ 商品 {item_id} 图片下载失败 (HTTP {e.response.status_code})")
    except Exception as e:
        logger.error(f"❌ 商品 {item_id} 自动索引失败: {e}")


@router.post("/history/{item_id}/delist")
async def delist_item(
    item_id: int,
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取
):
    """
    下架商品（仅限商品所有者）
    """
    # ✅ 验证商品所有权
    item = await crud.get_item_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")
    
    await crud.update_item_status(item_id, "delisted")
    
    # 从搜索索引删除
    try:
        qdrant = get_qdrant()
        qdrant.delete_item(item_id)
        logger.info(f"🗑️ 商品 {item_id} 已从搜索索引删除")
    except Exception as e:
        logger.error(f"❌ 删除索引失败: {e}")
    
    return {"status": "delisted"}


@router.post("/history/{item_id}/publish")
async def publish_item(
    item_id: int,
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取
):
    """
    从草稿发布（仅限商品所有者）
    """
    # ✅ 验证商品所有权
    item = await crud.get_item_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")
    
    await crud.update_item_status(item_id, "published")
    
    # 发布时自动加入以图搜图索引（草稿时可能未索引）
    try:
        if item:
            # 构建 payload 用于索引
            payload = GenerateSaveRequest(
                user_id=item["user_id"],
                image_url=item["original_image_url"],
                title=item["ai_generated_title"],
                desc=item.get("ai_generated_desc", ""),
                price=float(item.get("suggested_price", 0)) if item.get("suggested_price") else 0,
                status=item.get("status", "published"),
                category=item.get("category"),
                brand=item.get("brand"),
                model=item.get("model"),
                condition=item.get("condition"),  # ✅ 使用 condition
            )
            await add_to_search_index(item_id, payload)
    except Exception as e:
        logger.error(f"❌ 草稿发布后索引失败: {e}")
    
    return {"status": "published"}