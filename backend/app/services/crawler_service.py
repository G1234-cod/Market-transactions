"""
爬虫管理器 —— 多数据源异步爬取市场价格

采用工厂模式 + 策略模式:
- 当前接入 OneBound（万邦）API 抓取淘宝等电商平台数据
- 后续可扩展京东、转转等数据源
- 使用 ThreadPoolExecutor 异步执行，不阻塞 Web 服务
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

# 线程池：最多 4 个并发爬虫线程
_crawler_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crawler")


class OneBoundCrawler:
    """
    OneBound（万邦）API 爬虫

    通过淘宝关键词搜索，抓取商品的最低/最高/平均价格。
    文档: https://api.onebound.cn
    """

    def __init__(self):
        self.api_key = settings.ONEBOUND_API_KEY
        self.api_secret = settings.ONEBOUND_API_SECRET
        self.base_url = settings.ONEBOUND_BASE_URL

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _sign(self, params: dict) -> str:
        """生成 OneBound API 签名"""
        sorted_keys = sorted(params.keys())
        raw = "".join(f"{k}{params[k]}" for k in sorted_keys)
        raw = f"{self.api_secret}{raw}{self.api_secret}"
        return hashlib.md5(raw.encode()).hexdigest().upper()

    async def search_price(
        self,
        keyword: str,
        category: str = "手机",
        page: int = 1,
        page_size: int = 40,
    ) -> dict:
        """
        搜索商品价格

        Args:
            keyword: 搜索关键词（如 "iPhone 13"）
            category: 品类
            page: 页码
            page_size: 每页数量

        Returns:
            dict: {
                "success": True/False,
                "avg_price": float,   # 均价
                "low_price": float,   # 最低价
                "high_price": float,  # 最高价
                "total_count": int,   # 搜索结果总数
                "items": [...],       # 商品列表
                "source": "onebound",
                "error": str | None,
            }
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "OneBound API 未配置（缺少 ONEBOUND_API_KEY / ONEBOUND_API_SECRET）",
                "source": "onebound",
            }

        params = {
            "key": self.api_key,
            "secret": self.api_secret,
            "q": keyword,
            "page": str(page),
            "page_size": str(page_size),
            "sort": "price-asc",  # 按价格升序
        }
        sign = self._sign(params)
        params["sign"] = sign

        url = f"{self.base_url}/item_search/?{urlencode(params)}"

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"OneBound API 返回 HTTP {resp.status}")
                        return {
                            "success": False,
                            "error": f"OneBound API HTTP {resp.status}",
                            "source": "onebound",
                        }

                    data = await resp.json()

            # 解析 OneBound 返回结果
            return self._parse_response(data, keyword)

        except asyncio.TimeoutError:
            logger.warning(f"OneBound API 超时: {keyword}")
            return {"success": False, "error": "API 请求超时", "source": "onebound"}
        except Exception as e:
            logger.error(f"OneBound API 异常: {e}")
            return {"success": False, "error": str(e), "source": "onebound"}

    def _parse_response(self, data: dict, keyword: str) -> dict:
        """解析 OneBound API 返回数据"""
        items = data.get("items", {}).get("item", [])
        if not items:
            return {
                "success": False,
                "error": f"OneBound 未找到 '{keyword}' 的搜索结果",
                "source": "onebound",
            }

        prices = []
        parsed_items = []

        for item in items[:100]:  # 取前100条
            try:
                price_str = item.get("price", "0")
                # 处理价格格式: "2999.00" 或 "2999.00-3999.00"
                if "-" in str(price_str):
                    parts = str(price_str).split("-")
                    price = (float(parts[0]) + float(parts[1])) / 2
                else:
                    price = float(price_str)

                if price > 0:
                    prices.append(price)
                    parsed_items.append({
                        "title": item.get("title", ""),
                        "price": price,
                        "sales": int(item.get("sales", 0)),
                        "shop": item.get("nick", ""),
                    })
            except (ValueError, TypeError):
                continue

        if not prices:
            return {
                "success": False,
                "error": f"OneBound 无法解析 '{keyword}' 的价格数据",
                "source": "onebound",
            }

        prices.sort()
        n = len(prices)

        # 去除极端值（最低5%和最高5%）
        trim_start = max(0, int(n * 0.05))
        trim_end = max(0, int(n * 0.05))
        trimmed = prices[trim_start : n - trim_end] if n - trim_end > trim_start else prices

        return {
            "success": True,
            "avg_price": round(sum(trimmed) / len(trimmed), 2),
            "low_price": round(trimmed[0], 2),
            "high_price": round(trimmed[-1], 2),
            "total_count": data.get("total_results", n),
            "items": parsed_items[:20],
            "source": "onebound",
            "keyword": keyword,
        }


class CrawlerManager:
    """
    爬虫管理器 —— 工厂模式

    解耦爬虫实现，后续可添加新的 Crawler 实现类:
        - JDCrawler（京东）
        - ZhuanZhuanCrawler（转转）
        - XianyuCrawler（闲鱼）
    """

    def __init__(self):
        self._crawlers = [
            OneBoundCrawler(),
        ]

    @property
    def is_any_configured(self) -> bool:
        return any(c.is_configured for c in self._crawlers)

    async def crawl_price(
        self,
        brand: str,
        model_name: str,
        category: str = "手机",
    ) -> dict:
        """
        并发调用所有爬虫获取价格数据，取最优结果

        Args:
            brand: 品牌
            model_name: 型号
            category: 品类

        Returns:
            dict: 聚合后的价格结果
        """
        keyword = f"{brand} {model_name}"

        # 使用线程池并发执行所有爬虫
        loop = asyncio.get_running_loop()
        tasks = []
        for crawler in self._crawlers:
            tasks.append(
                loop.run_in_executor(
                    _crawler_executor,
                    lambda c=crawler: asyncio.run(c.search_price(keyword, category)),
                )
            )

        # 实际上爬虫是 async 的，直接并发调用
        results = await asyncio.gather(
            *[c.search_price(keyword, category) for c in self._crawlers],
            return_exceptions=True,
        )

        # 取第一个成功的结果
        for result in results:
            if isinstance(result, dict) and result.get("success"):
                return result

        # 全部失败时返回第一个错误
        for result in results:
            if isinstance(result, dict):
                return result

        return {
            "success": False,
            "error": "所有爬虫均未配置或请求失败",
            "source": "none",
        }


# 单例
_crawler_manager: Optional[CrawlerManager] = None


def get_crawler_manager() -> CrawlerManager:
    """获取爬虫管理器单例"""
    global _crawler_manager
    if _crawler_manager is None:
        _crawler_manager = CrawlerManager()
    return _crawler_manager
