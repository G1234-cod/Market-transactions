"""
爬虫模块
提供商品价格爬取功能
"""
from .base_crawler import BaseCrawler, CrawlerManager
from .onebound_crawler import OneBoundCrawler
from .utils import format_keyword, is_cache_valid
from .config import *


def create_crawler_manager() -> CrawlerManager:
    """
    创建爬虫管理器
    
    Returns:
        CrawlerManager: 爬虫管理器
    """
    manager = CrawlerManager()
    
    if 'onebound' in ENABLED_CRAWLERS:
        api_key = ONEBOUND_API_KEY
        api_secret = ONEBOUND_API_SECRET
        if not api_key or not api_secret:
            import logging
            logging.getLogger(__name__).warning(
                "ONEBOUND_API_KEY 或 ONEBOUND_API_SECRET 未配置，请在 .env 中设置。"
                "免费注册: https://open.onebound.cn"
            )
        else:
            manager.add_crawler(OneBoundCrawler(api_key=api_key, api_secret=api_secret))
    
    return manager


__all__ = [
    'BaseCrawler',
    'CrawlerManager',
    'OneBoundCrawler',
    'create_crawler_manager',
    'format_keyword',
    'is_cache_valid',
]