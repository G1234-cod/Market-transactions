"""查价引擎 —— 三层匹配策略"""
from app.models.schemas import PriceResult
from app.db import crud


async def query_price(brand: str, model_name: str) -> PriceResult:
    """查询行情，返回 PriceResult"""
    row = await crud.query_price(brand, model_name)

    if row:
        return PriceResult(
            category=row["category"],
            brand=row["brand"],
            model=row["model"],
            avg_price=float(row["avg_price"]),
            low_price=float(row["low_price"]),
            high_price=float(row["high_price"]),
            matched=True,
            note="数据库匹配成功",
        )

    return PriceResult(
        brand=brand,
        model=model_name,
        matched=False,
        note="暂无该型号的市场行情数据，建议根据经验定价",
    )
