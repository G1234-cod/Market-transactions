"""GET /api/v1/market — 商城商品列表（全用户已发布商品）"""
from fastapi import APIRouter, Query

from app.models.schemas import MarketItem
from app.db import crud
from app.config import get_static_url, get_base_url, settings

router = APIRouter(tags=["商城"])


@router.get("/market")
async def get_market(
    keyword: str = Query(default="", description="搜索关键词"),
    category: str = Query(default="", description="品类筛选"),
):
    """查询所有用户已发布的商品，支持关键词搜索和品类筛选"""
    rows = await crud.get_market_items(keyword=keyword, category=category)
    items = []
    for r in rows:
        # 处理图片 URL
        img_url = r.get("original_image_url", "")
        if img_url and not img_url.startswith("http"):
            if img_url.startswith(f"{settings.STATIC_PREFIX}/"):
                img_url = f"{get_base_url()}{img_url}"
            else:
                img_url = get_static_url(img_url)
        
        items.append(MarketItem(
            id=r["id"],
            user_id=r["user_id"],
            username=r["username"],
            original_image_url=img_url,
            ai_generated_title=r["ai_generated_title"],
            ai_generated_desc=r.get("ai_generated_desc"),
            suggested_price=float(r["suggested_price"]) if r.get("suggested_price") is not None else None,
            category=r.get("category"),
            condition=r.get("condition"),  # ✅ 添加 condition 字段
            views=r.get("views", 0),
            likes=r.get("likes", 0),
            created_at=str(r["created_at"]),
        ))
    return {"items": items}