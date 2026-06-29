"""查价引擎 —— 三层匹配策略 + 爬虫支持"""
import logging
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from app.models.schemas import PriceResult, PriceDetailResult, CrawledItem, PriceHistoryItem
from app.db import crud
from app.crawler import create_crawler_manager, format_keyword, is_cache_valid

logger = logging.getLogger(__name__)


CACHE_TTL_HOURS = 24


async def query_price(brand: str, model_name: str) -> PriceResult:
    """查询行情，返回 PriceResult（快速估算）"""
    row = await crud.query_price(brand, model_name)

    if row:
        return PriceResult(
            category=row.get("category", ""),
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


async def query_price_detail(brand: str, model_name: str, category: str = "") -> PriceDetailResult:
    """
    查询价格详情（触发爬虫）
    
    流程：查缓存(TTL内) → 爬取实时数据 → 返回历史价格
    
    Args:
        brand: 品牌
        model_name: 型号
        category: 品类
        
    Returns:
        PriceDetailResult: 价格详情结果
    """
    logger.info(f"查询价格详情: {brand} {model_name}")
    
    result = PriceDetailResult(
        brand=brand,
        model=model_name,
        category=category,
        current_price={"avg": 0, "low": 0, "high": 0},
        history_prices=[],
        crawled_items=[],
        note="",
    )
    
    cache_row = await crud.query_price(brand, model_name)
    
    if cache_row:
        crawled_at = cache_row.get("crawled_at")
        if crawled_at and is_cache_valid(crawled_at, CACHE_TTL_HOURS):
            logger.info("缓存命中，直接返回")
            result.current_price = {
                "avg": float(cache_row["avg_price"]),
                "low": float(cache_row["low_price"]),
                "high": float(cache_row["high_price"]),
            }
            result.category = cache_row.get("category", category)
            result.note = "数据来自缓存（24小时内）"
            
            history = await get_history_prices(brand, model_name)
            result.history_prices = history
            
            return result
        else:
            logger.info("缓存过期，触发爬取")
            result.note = "缓存已过期，正在爬取实时数据..."
    else:
        logger.info("无缓存，触发爬取")
        result.note = "无缓存数据，正在爬取实时数据..."
    
    crawl_result = await crawl_price(brand, model_name, category)
    
    if crawl_result.get("success"):
        price_range = crawl_result.get("price_range", {})
        result.current_price = {
            "avg": price_range.get("avg", 0),
            "low": price_range.get("low", 0),
            "high": price_range.get("high", 0),
        }
        result.data_source = ", ".join(crawl_result.get("sources", []))
        result.note = "实时数据爬取成功"
        
        crawled_items = crawl_result.get("items", [])
        result.crawled_items = [
            CrawledItem(
                title=item.get("title", ""),
                price=item.get("price", 0),
                url=item.get("url", ""),
                image=item.get("image", ""),
            )
            for item in crawled_items
        ]
        
        await save_crawl_result(brand, model_name, category, price_range, crawl_result.get("sources", []))
        
        history = await get_history_prices(brand, model_name)
        result.history_prices = history
        
        return result
    else:
        logger.warning(f"爬取失败: {crawl_result.get('message')}")
        
        if cache_row:
            result.current_price = {
                "avg": float(cache_row["avg_price"]),
                "low": float(cache_row["low_price"]),
                "high": float(cache_row["high_price"]),
            }
            result.category = cache_row.get("category", category)
            result.note = f"爬取失败，返回缓存数据。{crawl_result.get('message', '')}"
            
            history = await get_history_prices(brand, model_name)
            result.history_prices = history
            
            return result
        else:
            result.note = f"爬取失败，且无缓存数据。{crawl_result.get('message', '')}"
            return result


def _sync_crawl_price(brand: str, model_name: str) -> Dict[str, Any]:
    """
    同步爬取价格数据（在线程池中运行）
    
    Args:
        brand: 品牌
        model_name: 型号
        
    Returns:
        Dict: 爬取结果
    """
    try:
        keyword = format_keyword(brand, model_name)
        logger.info(f"开始爬取: {keyword}")
        
        manager = create_crawler_manager()
        results = manager.crawl_all(keyword)
        
        if not results:
            return {"success": False, "message": "无可用爬虫"}
        
        merged = manager.merge_results(results)
        
        if merged.get("success"):
            logger.info(f"爬取成功: {merged.get('price_range')}")
            return merged
        else:
            return {"success": False, "message": merged.get("message", "爬取失败")}
            
    except Exception as e:
        logger.error(f"爬取异常: {e}")
        return {"success": False, "message": str(e)}


async def crawl_price(brand: str, model_name: str, category: str = "") -> Dict[str, Any]:
    """
    异步爬取价格数据（使用线程池避免阻塞事件循环）
    
    Args:
        brand: 品牌
        model_name: 型号
        category: 品类
        
    Returns:
        Dict: 爬取结果
    """
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    
    try:
        result = await loop.run_in_executor(executor, _sync_crawl_price, brand, model_name)
        return result
    finally:
        executor.shutdown(wait=False)


async def save_crawl_result(
    brand: str,
    model_name: str,
    category: str,
    price_range: Dict[str, float],
    sources: List[str]
):
    """
    保存爬取结果到数据库
    
    Args:
        brand: 品牌
        model_name: 型号
        category: 品类
        price_range: 价格区间
        sources: 数据来源列表
    """
    try:
        avg_price = price_range.get("avg", 0)
        low_price = price_range.get("low", 0)
        high_price = price_range.get("high", 0)
        
        if avg_price <= 0:
            logger.warning("价格无效，跳过保存")
            return
        
        data_source = ", ".join(sources) if sources else "crawler"
        
        await crud.upsert_price(
            brand=brand,
            model=model_name,
            avg_price=avg_price,
            low_price=low_price,
            high_price=high_price,
            category=category,
            data_source=data_source,
        )
        
        await crud.insert_price_history(
            brand=brand,
            model=model_name,
            avg_price=avg_price,
            low_price=low_price,
            high_price=high_price,
            source=data_source,
        )
        
        logger.info(f"保存爬取结果成功: {brand} {model_name}")
        
    except Exception as e:
        logger.error(f"保存爬取结果失败: {e}")


async def get_history_prices(brand: str, model_name: str) -> List[PriceHistoryItem]:
    """
    获取价格历史记录
    
    Args:
        brand: 品牌
        model_name: 型号
        
    Returns:
        List[PriceHistoryItem]: 历史记录列表
    """
    try:
        records = await crud.get_price_history(brand, model_name, limit=50)
        
        return [
            PriceHistoryItem(
                price=float(record.get("price", 0)),
                low_price=float(record.get("low_price", 0)),
                high_price=float(record.get("high_price", 0)),
                recorded_at=str(record.get("recorded_at", "")),
                source=record.get("source", ""),
            )
            for record in records
        ]
        
    except Exception as e:
        logger.error(f"获取历史价格失败: {e}")
        return []