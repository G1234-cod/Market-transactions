"""GET /api/v1/history — 查询发布历史 + POST /api/v1/history/save — 保存发布记录 + 下架/发布操作"""
from fastapi import APIRouter, Query

from app.models.schemas import HistoryItem, GenerateSaveRequest
from app.db import crud

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
    """保存生成的文案到发布记录（可指定 status: published / draft）"""
    item_id = await crud.insert_published_item(
        user_id=payload.user_id,
        image_url=payload.image_url,
        title=payload.title,
        desc=payload.desc,
        price=payload.price,
        status=payload.status,
    )
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
