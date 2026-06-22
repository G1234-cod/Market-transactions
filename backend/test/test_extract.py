"""端到端测试：上传图片 → Qwen-VL-Max 识别 → 打印结果"""
import requests
import json
from pathlib import Path

# 用项目中已有的一张图片
image_paths = list(Path("e:/Market-transactions/backend/static/uploads").glob("*.*"))
if not image_paths:
    print("没有测试图片，请先通过网页上传一张！")
    exit(1)

image_path = image_paths[0]
print(f"测试图片: {image_path.name}\n")

with open(image_path, "rb") as f:
    resp = requests.post(
        "http://localhost:8000/api/v1/extract",
        files={"image": (image_path.name, f, "image/jpeg")},
        data={"user_id": "1"},
    )

result = resp.json()
print(f"success: {result['success']}")
print(f"data: {json.dumps(result['data'], ensure_ascii=False, indent=2)}")
if result.get("error"):
    print(f"error: {result['error']}")
print(f"image_url: {result['image_urls'][0]}")
