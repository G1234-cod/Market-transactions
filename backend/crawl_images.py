"""
二手商品图片爬虫工具

使用方法:
1. 安装依赖: pip install requests beautifulsoup4
2. 运行: python crawl_images.py --query "二手手机 划痕" --count 100

注意: 请遵守目标网站的robots.txt规则
"""
import os
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time


def crawl_images(query, count, output_dir="dataset/crawl"):
    """爬取图片"""
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 使用百度图片搜索
    base_url = "https://image.baidu.com"
    search_url = f"{base_url}/search/index?tn=baiduimage&word={query}&pn="
    
    downloaded = 0
    page = 0
    
    while downloaded < count:
        try:
            url = search_url + str(page * 30)
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            img_tags = soup.find_all("img", class_="main_img img-hover")
            
            if not img_tags:
                print("没有找到更多图片")
                break
            
            for img_tag in img_tags:
                if downloaded >= count:
                    break
                
                try:
                    img_url = img_tag.get("src") or img_tag.get("data-src")
                    if not img_url:
                        continue
                    
                    if not img_url.startswith("http"):
                        img_url = urljoin(base_url, img_url)
                    
                    # 下载图片
                    img_response = requests.get(img_url, headers=headers, timeout=10)
                    img_response.raise_for_status()
                    
                    # 保存图片
                    filename = f"{query}_{downloaded:04d}.jpg"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)
                    
                    downloaded += 1
                    print(f"下载: {downloaded}/{count} - {filename}")
                    time.sleep(0.5)  # 避免请求过快
                    
                except Exception as e:
                    print(f"下载失败: {str(e)}")
            
            page += 1
            
        except Exception as e:
            print(f"页面请求失败: {str(e)}")
            break
    
    print(f"\n完成！共下载 {downloaded} 张图片")


def main():
    parser = argparse.ArgumentParser(description="二手商品图片爬虫")
    parser.add_argument("--query", type=str, required=True, help="搜索关键词")
    parser.add_argument("--count", type=int, default=100, help="下载数量")
    parser.add_argument("--output", type=str, default="dataset/crawl", help="输出目录")
    args = parser.parse_args()
    
    crawl_images(args.query, args.count, args.output)


if __name__ == "__main__":
    main()