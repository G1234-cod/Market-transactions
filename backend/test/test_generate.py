"""手动测试流式生成接口 —— python test_generate.py"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json

url = "http://localhost:8000/api/v1/generate"
payload = {
    "user_id": 1,
    "category": "手机",
    "brand": "Apple",
    "model": "iPhone 13",
    "condition": "9成新，屏幕有细微划痕，电池健康度85%",
    "avg_price": 3200,
    "low_price": 2800,
    "high_price": 3800,
}

print("=== SSE 流式生成测试 ===\n")
print(f"发送请求: {payload['brand']} {payload['model']} (成色: {payload['condition']})")
print(f"行情参考: ¥{payload['low_price']} ~ ¥{payload['high_price']}\n")
print("--- 开始生成 ---\n")

with requests.post(url, json=payload, stream=True) as resp:
    for line in resp.iter_lines():
        if line and line.startswith(b"data: "):
            data = json.loads(line[6:])
            if "content" in data:
                print(data["content"], end="", flush=True)
            elif "done" in data:
                print("\n\n--- 生成完成 ---")
            elif "error" in data:
                print(f"\n错误: {data['error']}")
