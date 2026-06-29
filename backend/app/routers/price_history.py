"""历史价格路由"""
from fastapi import APIRouter, Query
from typing import Optional

from app.models.schemas import PriceHistoryResponse, PricePoint
from app.services import price_service
from app.db import crud

router = APIRouter(tags=["价格历史"])


@router.get(
    "/price-history",
    response_model=PriceHistoryResponse,
    summary="获取历史价格走势",
)
async def get_price_history(
    brand: str = Query(..., description="品牌名称"),
    model: str = Query(..., description="商品型号"),
    days: int = Query(default=180, ge=30, le=365, description="查询最近天数"),
    base_price: float = Query(default=0, description="当前参考价格（来自AI识别建议价）"),
):
    """
    获取指定品牌型号过去6个月的价格走势数据，用于前端绘制价格曲线图。

    - **brand**: 品牌名称
    - **model**: 商品型号
    - **base_price**: 当前参考价格，优先使用此价格作为基准
    """
    result = await price_service.get_enriched_price_history(brand, model, days, base_price=base_price)

    price_points = [
        PricePoint(
            date=p["date"],
            price=p["price"],
            count=1,
            source=result.get("source", ""),
        )
        for p in result["price_points"]
    ]

    return PriceHistoryResponse(
        brand=brand,
        model=model,
        total_records=len(price_points),
        avg_price=result.get("avg_price", 0),
        min_price=result.get("min_price", 0),
        max_price=result.get("max_price", 0),
        price_points=price_points,
        has_estimated_data=False,
        estimate_analysis="",
        estimate_source="",
    )


@router.get(
    "/price-history/models",
    summary="获取价格历史可查的型号列表",
)
async def get_available_models(
    keyword: str = Query(default="", description="搜索关键词"),
    category: str = Query(default="", description="品类筛选"),
):
    models = await crud.get_available_price_models(keyword, category)
    return models


@router.get(
    "/price-history/categories",
    summary="获取价格历史可查的品类列表",
)
async def get_price_categories():
    from app.db.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT DISTINCT category FROM published_items
                   WHERE category IS NOT NULL
                   AND category != ''
                   AND suggested_price IS NOT NULL
                   ORDER BY category"""
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows if r[0]]


@router.get(
    "/price-history/refresh",
    summary="刷新价格数据",
)
async def refresh_price_history(
    brand: str = Query(..., description="品牌名称"),
    model: str = Query(..., description="商品型号"),
):
    history_result = await price_service.get_enriched_price_history(brand, model, days=180)

    return {
        "success": True,
        "brand": brand,
        "model": model,
        "avg_price": history_result.get("avg_price", 0),
        "min_price": history_result.get("min_price", 0),
        "max_price": history_result.get("max_price", 0),
    }
