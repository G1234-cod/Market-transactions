"""
爬虫基类
提供通用的请求、重试、解析功能
"""
import time
import random
import logging
import asyncio
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(self, base_url: str, timeout: int = 15, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建请求会话"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session

    def _random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """随机延迟，避免被封"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def fetch(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """
        获取页面内容（带重试机制）
        
        Args:
            url: 目标URL
            params: 请求参数
            
        Returns:
            str: HTML内容，失败返回None
        """
        self._random_delay()
        
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                resp.encoding = 'utf-8'
                return resp.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"获取失败 (尝试 {attempt+1}/{self.max_retries+1}): {url}, {e}")
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.info(f"等待 {wait}s 后重试...")
                    time.sleep(wait)
        
        logger.error(f"获取最终失败: {url}")
        return None

    def fetch_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        获取JSON数据（带重试机制）
        
        Args:
            url: 目标URL
            params: 请求参数
            
        Returns:
            Dict: JSON数据，失败返回None
        """
        self._random_delay()
        
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"获取JSON失败 (尝试 {attempt+1}/{self.max_retries+1}): {url}, {e}")
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    time.sleep(wait)
        
        logger.error(f"获取JSON最终失败: {url}")
        return None

    def resolve_url(self, relative_url: str) -> str:
        """将相对URL转换为绝对URL"""
        return urljoin(self.base_url, relative_url)

    @abstractmethod
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索商品
        
        Args:
            keyword: 搜索关键词（品牌+型号）
            
        Returns:
            List[Dict]: 商品列表
        """
        pass

    @abstractmethod
    def get_price_range(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        从商品列表中计算价格区间
        
        Args:
            items: 商品列表
            
        Returns:
            Dict: {'low': 最低价, 'avg': 均价, 'high': 最高价}
        """
        pass

    def crawl(self, keyword: str) -> Dict[str, Any]:
        """
        执行完整爬取流程
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            Dict: 爬取结果
        """
        logger.info(f"开始爬取: {keyword}")
        
        try:
            items = self.search(keyword)
            
            if not items:
                logger.warning(f"未找到商品: {keyword}")
                return {
                    'success': False,
                    'message': '未找到商品',
                    'items': [],
                    'price_range': {}
                }
            
            price_range = self.get_price_range(items)
            
            result = {
                'success': True,
                'message': '爬取成功',
                'items': items[:20],
                'price_range': price_range,
                'source': self.__class__.__name__,
                'total_found': len(items)
            }
            
            logger.info(f"爬取完成: {keyword}, 找到 {len(items)} 个商品")
            return result
            
        except Exception as e:
            logger.error(f"爬取失败: {keyword}, {e}")
            return {
                'success': False,
                'message': str(e),
                'items': [],
                'price_range': {}
            }


class CrawlerManager:
    """爬虫管理器"""

    def __init__(self, crawlers: List[BaseCrawler] = None):
        self.crawlers = crawlers or []

    def add_crawler(self, crawler: BaseCrawler):
        """添加爬虫"""
        self.crawlers.append(crawler)

    def crawl_all(self, keyword: str) -> List[Dict[str, Any]]:
        """
        并行爬取所有爬虫
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Dict]: 所有爬虫的结果
        """
        results = []
        for crawler in self.crawlers:
            try:
                result = crawler.crawl(keyword)
                results.append(result)
            except Exception as e:
                logger.error(f"爬虫 {crawler.__class__.__name__} 执行失败: {e}")
                results.append({
                    'success': False,
                    'message': str(e),
                    'source': crawler.__class__.__name__
                })
        return results

    def merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个爬虫结果
        
        Args:
            results: 多个爬虫结果
            
        Returns:
            Dict: 合并后的结果
        """
        all_items = []
        all_price_ranges = []
        
        for result in results:
            if result.get('success'):
                all_items.extend(result.get('items', []))
                price_range = result.get('price_range', {})
                if price_range:
                    all_price_ranges.append(price_range)
        
        if not all_items:
            return {
                'success': False,
                'message': '所有爬虫均未找到数据',
                'items': [],
                'price_range': {}
            }
        
        prices = []
        for item in all_items:
            price = item.get('price')
            if price:
                try:
                    prices.append(float(price))
                except (ValueError, TypeError):
                    continue
        
        if prices:
            price_range = {
                'low': min(prices),
                'avg': sum(prices) / len(prices),
                'high': max(prices)
            }
        elif all_price_ranges:
            price_range = {
                'low': min(r['low'] for r in all_price_ranges),
                'avg': sum(r['avg'] for r in all_price_ranges) / len(all_price_ranges),
                'high': max(r['high'] for r in all_price_ranges)
            }
        else:
            price_range = {}
        
        return {
            'success': True,
            'message': '合并成功',
            'items': all_items[:30],
            'price_range': price_range,
            'total_found': len(all_items),
            'sources': [r.get('source') for r in results if r.get('success')]
        }