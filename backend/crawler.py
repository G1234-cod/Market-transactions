"""
爬虫脚本 - 从二手交易平台采集公开数据
注意：遵守 robots.txt，仅采集公开数据
"""
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 配置 ==========
OUTPUT_DIR = "data/crawler_data"
DELAY_MIN = 1  # 最小请求间隔（秒）
DELAY_MAX = 3  # 最大请求间隔（秒）
# =========================


class Crawler:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.labels_dir = self.output_dir / "labels"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch(self, url):
        """获取页面"""
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"获取失败 {url}: {e}")
            return None
    
    def parse_items(self, html):
        """解析商品列表（根据目标网站定制）"""
        # 示例：解析闲鱼或转转的列表页
        # 实际需要根据目标网站结构调整
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        # 示例选择器（需要根据实际网站修改）
        for item in soup.select('.item-class'):
            title = item.select_one('.title-class')
            price = item.select_one('.price-class')
            img = item.select_one('img')
            if title and img:
                items.append({
                    'title': title.text.strip(),
                    'price': price.text.strip() if price else '',
                    'image_url': img.get('src')
                })
        return items
    
    def download_image(self, url, filename):
        """下载图片"""
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                path = self.images_dir / filename
                with open(path, 'wb') as f:
                    f.write(resp.content)
                return str(path)
        except Exception as e:
            logger.error(f"下载失败 {url}: {e}")
        return None
    
    def run(self, start_url, max_pages=5):
        """运行爬虫"""
        logger.info(f"🚀 开始爬取: {start_url}")
        for page in range(1, max_pages + 1):
            url = f"{start_url}?page={page}"
            html = self.fetch(url)
            if not html:
                continue
            
            items = self.parse_items(html)
            logger.info(f"第 {page} 页，找到 {len(items)} 个商品")
            
            for i, item in enumerate(items):
                filename = f"crawled_{page}_{i}.jpg"
                self.download_image(item['image_url'], filename)
                
                # 保存标签
                label_path = self.labels_dir / f"{Path(filename).stem}.txt"
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write(f"商品名称：{item.get('title', '')}\n")
                    f.write(f"价格：{item.get('price', '')}\n")
                    f.write(f"来源：{start_url}\n")


if __name__ == '__main__':
    # 示例：爬取某平台（需要替换成实际 URL）
    # 注意遵守 robots.txt
    crawler = Crawler()
    # crawler.run("https://example.com/items")
    print("⚠️ 请先配置目标网站 URL 和解析规则")