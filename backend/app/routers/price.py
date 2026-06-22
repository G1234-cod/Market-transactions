"""GET /api/v1/price — 查询市场行情"""
from fastapi import APIRouter, Query

from app.models.schemas import PriceResult
from app.services import price_service

router = APIRouter(tags=["行情查询"])


@router.get("/price", response_model=PriceResult)
async def get_price(
    brand: str = Query(..., description="品牌"),
    model: str = Query(..., description="型号"),
):
    """根据品牌+型号查询二手市场行情价格区间"""
    return await price_service.query_price(brand, model)
