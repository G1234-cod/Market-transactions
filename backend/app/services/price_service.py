"""
查价引擎 —— 三层匹配策略

1. 第一层：数据库缓存 (Cache)
   - 检查24小时内是否有人查过同款商品
   - 命中缓存 → 毫秒级返回，省去爬虫费用

2. 第二层：实时爬虫 (Crawler)
   - 缓存未命中或过期 → 触发爬虫模块
   - 通过 OneBound API 实时抓取全网最低价/最高价/均价
   - 落库更新缓存 + 记录历史快照

3. 第三层：AI 历史数据推算 (AI Estimator)
   - 历史记录不足时 → 调用 DeepSeek 推算过去6个月价格走势
   - 基于"二手电子产品每月贬值 3%-8%"的市场规律
"""
import logging
from datetime import datetime

from app.models.schemas import PriceResult
from app.db import crud
from app.config import settings

logger = logging.getLogger(__name__)


async def query_price(brand: str, model_name: str) -> PriceResult:
    """
    查询行情 —— 三层匹配策略入口

    流程:
    1. 检查数据库缓存（24h 内）
    2. 缓存过期/不存在 → 爬虫实时抓取
    3. 爬虫失败/未配置 → 回退到已有的数据库记录
    """
    cache_ttl = settings.CRAWL_CACHE_TTL

    # ============================================================
    # 第一层：数据库缓存
    # ============================================================
    cached = await crud.get_cached_price(brand, model_name, ttl_seconds=cache_ttl)
    if cached:
        logger.info(f"✅ 缓存命中: {brand} {model_name} (缓存 {cached['age_hours']} 小时)")
        return PriceResult(
            category=cached.get("category", ""),
            brand=brand,
            model=model_name,
            avg_price=cached["avg_price"],
            low_price=cached["low_price"],
            high_price=cached["high_price"],
            matched=True,
            note=f"缓存命中（{cached['age_hours']}小时前更新，来源: {cached.get('data_source', 'cache')}）",
        )

    # ============================================================
    # 第二层：实时爬虫
    # ============================================================
    logger.info(f"🔍 缓存未命中，触发爬虫: {brand} {model_name}")
    crawl_result = None
    try:
        from app.services.crawler_service import get_crawler_manager
        crawler = get_crawler_manager()
        if crawler.is_any_configured:
            crawl_result = await crawler.crawl_price(brand, model_name)
    except Exception as e:
        logger.warning(f"⚠️ 爬虫调用异常: {e}")

    if crawl_result and crawl_result.get("success"):
        # 爬取成功 → 落库
        await crud.save_crawl_result(
            brand=brand,
            model=model_name,
            avg_price=crawl_result["avg_price"],
            low_price=crawl_result["low_price"],
            high_price=crawl_result["high_price"],
            data_source=crawl_result.get("source", "onebound"),
        )
        logger.info(
            f"✅ 爬虫成功: {brand} {model_name} "
            f"均价={crawl_result['avg_price']}, "
            f"区间={crawl_result['low_price']}-{crawl_result['high_price']}"
        )
        return PriceResult(
            brand=brand,
            model=model_name,
            avg_price=crawl_result["avg_price"],
            low_price=crawl_result["low_price"],
            high_price=crawl_result["high_price"],
            matched=True,
            note=f"实时抓取成功（来源: {crawl_result.get('source', 'onebound')}）",
        )

    # ============================================================
    # 第三层：回退到原数据库（过期缓存或旧数据）
    # ============================================================
    logger.info(f"📦 爬虫未命中/未配置，回退到数据库: {brand} {model_name}")
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
            note="数据库匹配成功（可能数据较旧，建议稍后刷新）",
        )

    return PriceResult(
        brand=brand,
        model=model_name,
        matched=False,
        note="暂无该型号的市场行情数据，建议根据经验定价",
    )


async def get_enriched_price_history(
    brand: str,
    model: str,
    days: int = 180,
    base_price: float = 0,
) -> dict:
    """
    获取价格历史数据

    流程:
    1. 优先使用前端传入的 base_price（AI识别建议价）
    2. 其次从 market_prices / published_items 获取参考价
    3. 生成过去6个月的价格走势数据

    Returns:
        dict: {
            "brand", "model", "avg_price", "min_price", "max_price",
            "price_points": [...], "trend": str, "source": str,
        }
    """
    # Step 1: 确定基准价格
    if base_price > 0:
        # 优先使用前端传入的 AI 识别建议价
        base_avg = base_price
        base_low = round(base_avg * 0.85)
        base_high = round(base_avg * 1.15)
    else:
        # 其次从数据库获取
        current_price = await crud.get_market_price_for_estimate(brand, model)
        if current_price:
            base_avg = current_price["avg_price"]
            base_low = current_price["low_price"]
            base_high = current_price["high_price"]
        else:
            # 最后：从 published_items 取该品牌型号的均价
            stats = await crud.get_price_stats(brand, model)
            if stats and stats.get("avg", 0) > 0:
                base_avg = stats["avg"]
                base_low = stats["min"]
                base_high = stats["max"]
            else:
                # 完全没有数据，无法估算
                return {
                    "brand": brand,
                    "model": model,
                    "avg_price": 0,
                    "min_price": 0,
                    "max_price": 0,
                    "price_points": [],
                    "trend": "",
                    "source": "",
                }

    # Step 2: 生成价格走势
    from app.services.history_estimator import get_history_estimator
    estimator = get_history_estimator()
    estimate_result = await estimator.estimate_history(
        brand=brand,
        model_name=model,
        current_avg_price=base_avg,
        current_low_price=base_low,
        current_high_price=base_high,
    )

    price_points = estimate_result.get("price_points", [])

    # Step 3: 落库保存
    try:
        await crud.delete_old_estimated_history(brand, model)
        for point in price_points:
            await crud.save_price_history_point(
                brand=brand,
                model=model,
                price=point["price"],
                price_type="avg",
                source=estimate_result.get("source", "deepseek"),
                recorded_at=point["date"],
            )
    except Exception as e:
        logger.warning(f"Failed to save history: {e}")

    return {
        "brand": brand,
        "model": model,
        "avg_price": estimate_result.get("avg_price", base_avg),
        "min_price": estimate_result.get("min_price", base_low),
        "max_price": estimate_result.get("max_price", base_high),
        "price_points": price_points,
        "trend": estimate_result.get("trend", ""),
        "source": estimate_result.get("source", "deepseek"),
    }
