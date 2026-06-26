"""GET /api/v1/price — 查询市场行情"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.models.schemas import PriceResult
from app.services import price_service
from app.dependencies import get_current_user_optional

router = APIRouter(tags=["行情查询"])


@router.get("/price", response_model=PriceResult)
async def get_price(
    brand: str = Query(..., description="品牌"),
    model: str = Query(..., description="型号"),
    user_id: Optional[int] = Depends(get_current_user_optional),  # ✅ 可选认证
):
    """
    根据品牌+型号查询二手市场行情价格区间
    """
    result = await price_service.query_price(brand, model)
    
    # 如果已登录，记录审计日志（可选）
    if user_id:
        from app.db import crud
        import time
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