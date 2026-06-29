"""
OneBound 淘宝 API 爬虫
免费注册: https://open.onebound.cn
抓取淘宝商品价格作为二手估价参考基准
"""
import re
import logging
from typing import Dict, Any, List
from .base_crawler import BaseCrawler
from .utils import calculate_price_range

logger = logging.getLogger(__name__)

BASE_URL = "https://api-gw.onebound.cn/taobao/item_search"


class OneBoundCrawler(BaseCrawler):
    """OneBound 淘宝搜索爬虫"""

    def __init__(self, api_key: str, api_secret: str, timeout: int = 30, max_retries: int = 3):
        super().__init__(base_url=BASE_URL, timeout=timeout, max_retries=max_retries)
        self.api_key = api_key
        self.api_secret = api_secret

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        通过 OneBound API 搜索淘宝商品
        """
        params = {
            "key": self.api_key,
            "secret": self.api_secret,
            "q": keyword,
            "page": 1,
            "cache": "yes",
        }

        logger.info(f"OneBound 淘宝搜索: {keyword}")
        data = self.fetch_json(BASE_URL, params=params)

        if not data:
            logger.warning(f"OneBound 返回空数据: {keyword}")
            return []

        if data.get("error") or data.get("error_code"):
            logger.warning(f"OneBound API 错误: {data.get('error', data.get('reason', data))}")
            return []

        # 解析淘宝返回的商品列表
        items = []
        raw_items = data.get("items", {}).get("item", [])

        for item in raw_items:
            title = item.get("title", "")
            price = self._parse_price(item.get("price"))

            if not title or not price or price <= 0:
                continue

            items.append({
                "title": title.strip(),
                "price": price,
                "detail_url": item.get("detail_url", ""),
                "num_iid": item.get("num_iid", ""),
                "pic_url": item.get("pic_url", ""),
                "sales": item.get("sales", ""),
                "shop": item.get("nick", ""),
                "source": "Taobao(OneBound)",
            })

        logger.info(f"OneBound 搜索完成: {keyword}, 找到 {len(items)} 个商品")
        return items

    @staticmethod
    def _parse_price(price_val) -> float:
        """解析价格"""
        if price_val is None:
            return None
        if isinstance(price_val, (int, float)):
            return float(price_val)
        if isinstance(price_val, str):
            match = re.search(r"(\d+\.?\d*)", price_val)
            if match:
                return float(match.group(1))
        return None

    def get_price_range(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        prices = [i["price"] for i in items if i.get("price") and i["price"] > 0]
        return calculate_price_range(prices) if prices else {}
