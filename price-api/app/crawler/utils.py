"""
爬虫工具函数
"""
import re
import random
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def extract_price(text: str) -> Optional[float]:
    """
    从文本中提取价格
    
    Args:
        text: 包含价格的文本
        
    Returns:
        float: 价格，提取失败返回None
    """
    if not text:
        return None
    
    patterns = [
        r'¥\s*(\d+\.?\d*)',
        r'￥\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*元',
        r'(\d+\.?\d*)\s*RMB',
        r'(\d+\.?\d*)\s*CNY',
        r'价格\s*[:：]\s*(\d+\.?\d*)',
        r'(\d+\.?\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def clean_title(title: str) -> str:
    """
    清理商品标题
    
    Args:
        title: 原始标题
        
    Returns:
        str: 清理后的标题
    """
    if not title:
        return ""
    
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()
    
    return title


def is_valid_price(price: float) -> bool:
    """
    判断价格是否有效
    
    Args:
        price: 价格
        
    Returns:
        bool: 是否有效
    """
    return price is not None and price > 0 and price < 1000000


def calculate_price_range(prices: List[float]) -> Dict[str, float]:
    """
    计算价格区间
    
    Args:
        prices: 价格列表
        
    Returns:
        Dict: 价格区间
    """
    valid_prices = [p for p in prices if is_valid_price(p)]
    
    if not valid_prices:
        return {}
    
    return {
        'low': min(valid_prices),
        'avg': sum(valid_prices) / len(valid_prices),
        'high': max(valid_prices)
    }


def format_keyword(brand: str, model: str) -> str:
    """
    格式化搜索关键词
    
    Args:
        brand: 品牌
        model: 型号
        
    Returns:
        str: 格式化后的关键词
    """
    parts = []
    if brand:
        parts.append(brand.strip())
    if model:
        parts.append(model.strip())
    
    return ' '.join(parts)


def is_cache_valid(crawled_at: Optional[datetime], ttl_hours: int = 24) -> bool:
    """
    判断缓存是否有效
    
    Args:
        crawled_at: 爬取时间
        ttl_hours: TTL时长（小时）
        
    Returns:
        bool: 缓存是否有效
    """
    if crawled_at is None:
        return False
    
    now = datetime.now()
    delta = now - crawled_at
    
    return delta < timedelta(hours=ttl_hours)


def get_random_user_agent(user_agents: List[str]) -> str:
    """
    获取随机User-Agent
    
    Args:
        user_agents: User-Agent列表
        
    Returns:
        str: 随机User-Agent
    """
    return random.choice(user_agents)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        str: 截断后的文本
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    解析日期时间字符串
    
    Args:
        date_str: 日期时间字符串
        
    Returns:
        datetime: 解析后的日期时间，失败返回None
    """
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d',
        '%m-%d %H:%M',
        '%m/%d/%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None