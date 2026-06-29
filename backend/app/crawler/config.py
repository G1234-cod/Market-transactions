"""
爬虫配置
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CACHE_TTL_HOURS = 24

REQUEST_DELAY_MIN = 1.0
REQUEST_DELAY_MAX = 3.0

MAX_RETRIES = 3

TIMEOUT = 15

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

ENABLED_CRAWLERS = ['onebound']

# OneBound API 配置（免费注册: https://open.onebound.cn）
# 在 .env 中配置 ONEBOUND_API_KEY 和 ONEBOUND_API_SECRET
ONEBOUND_API_KEY = os.getenv("ONEBOUND_API_KEY", "")
ONEBOUND_API_SECRET = os.getenv("ONEBOUND_API_SECRET", "")
ONEBOUND_BASE_URL = "https://api-gw.onebound.cn/goodfish/item_search"

MAX_ITEMS_PER_CRAWLER = 30

MAX_TOTAL_ITEMS = 50