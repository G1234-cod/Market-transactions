"""价格查询路由"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.models.schemas import PriceResult, PriceDetailResult
from app.services import price_service
from app.dependencies import get_current_user_optional

router = APIRouter(tags=["行情查询"])


@router.get("/price", response_model=PriceResult)
async def get_price(
    brand: str = Query(..., description="品牌"),
    model: str = Query(..., description="型号"),
    user_id: Optional[int] = Depends(get_current_user_optional),
):
    """
    根据品牌+型号查询二手市场行情价格区间（快速估算）
    """
    result = await price_service.query_price(brand, model)
    
    if user_id:
        from app.db import crud
        await crud.insert_audit_log(
            user_id=user_id,
            action_type="price_query",
            model_name="market_prices",
            input_summary=f"{brand} {model}",
            raw_ai_response=None,
            execution_time_ms=0,
            status="SUCCESS",
        )
    
    return result


@router.get("/price/detail", response_model=PriceDetailResult)
async def get_price_detail(
    brand: str = Query(..., description="品牌"),
    model: str = Query(..., description="型号"),
    category: str = Query("", description="品类"),
    user_id: Optional[int] = Depends(get_current_user_optional),
):
    """
    查询价格详情（触发爬虫，获取实时数据和历史价格）
    
    用户点击"查看历史详情"时调用此接口
    """
    result = await price_service.query_price_detail(brand, model, category)
    
    if user_id:
        from app.db import crud
        await crud.insert_audit_log(
            user_id=user_id,
            action_type="price_detail",
            model_name="crawler",
            input_summary=f"{brand} {model}",
            raw_ai_response=None,
            execution_time_ms=0,
            status="SUCCESS",
        )
    
    return result