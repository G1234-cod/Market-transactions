"""GET /api/v1/market — 商城商品列表（全用户已发布商品）"""
import math
from fastapi import APIRouter, Query, Request
from typing import Optional

from app.models.schemas import MarketItem, MarketListResponse
from app.db import crud
from app.config import get_static_url, get_base_url, settings

router = APIRouter(tags=["商城"])


@router.get(
    "/market",
    response_model=MarketListResponse,
    summary="商城商品列表（分页+排序+多维筛选）",
)
async def get_market(
    request: Request,
    keyword: str = Query(default="", description="搜索关键词（匹配标题和描述）"),
    category: str = Query(default="", description="品类筛选：手机/笔记本/平板/外设/耳机/手表"),
    condition: str = Query(default="", description="成色筛选（模糊匹配，如 95新）"),
    price_min: Optional[float] = Query(default=None, ge=0, description="最低价（≥0）"),
    price_max: Optional[float] = Query(default=None, ge=0, description="最高价（≥0）"),
    sort_by: str = Query(default="created_at", description="排序字段: created_at（时间）/ price（价格）"),
    sort_order: str = Query(default="desc", description="排序方向: asc（升序）/ desc（降序），默认 desc"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量，1-100"),
):
    """
    商城商品列表（全用户已发布商品）

    支持多维筛选：
    - **keyword**: 关键词搜索（匹配标题和描述）
    - **category**: 品类筛选（如 手机）
    - **condition**: 成色筛选（模糊匹配，如 95新）
    - **price_min / price_max**: 价格区间筛选
    - **sort_by**: created_at（按时间排序）/ price（按价格排序）
    - **sort_order**: asc（升序）/ desc（降序），默认 desc
    - **page / page_size**: 分页参数，默认每页 20 条
    """
    rows, total = await crud.get_market_items(
        keyword=keyword,
        category=category,
        condition=condition,
        price_min=price_min,
        price_max=price_max,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    items = []
    for r in rows:
        # 处理图片 URL
        img_url = r.get("original_image_url", "")
        # ✅ 生产环境（非本地访问）：剥离旧数据中硬编码的 localhost 前缀
        if img_url.startswith("http://localhost"):
            from urllib.parse import urlparse
            host = request.headers.get("X-Forwarded-Host") or request.url.hostname or ""
            is_local = host in ("localhost", "127.0.0.1") or host.startswith("localhost:")
            if not is_local:
                img_url = img_url[len("http://localhost"):]
                if img_url.startswith(":8000"):
                    img_url = img_url[5:]
        if img_url and not img_url.startswith("http"):
            base = get_base_url(request) if request else get_base_url()
            if img_url.startswith(f"{settings.STATIC_PREFIX}/"):
                img_url = f"{base}{img_url}"
            else:
                img_url = get_static_url(img_url, request)

        items.append(MarketItem(
            id=r["id"],
            user_id=r["user_id"],
            username=r["username"],
            original_image_url=img_url,
            ai_generated_title=r["ai_generated_title"],
            ai_generated_desc=r.get("ai_generated_desc"),
            suggested_price=float(r["suggested_price"]) if r.get("suggested_price") is not None else None,
            category=r.get("category"),
            brand=r.get("brand"),
            model=r.get("model"),
            condition=r.get("condition"),
            views=r.get("views", 0),
            created_at=str(r["created_at"]),
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return MarketListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )