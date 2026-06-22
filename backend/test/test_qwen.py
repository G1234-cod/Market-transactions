"""测试 Qwen API Key —— 新 Key"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("DASHSCOPE_API_KEY")
print(f"Key: {key[:12]}...{key[-4:]}  (长度={len(key)})")

from openai import OpenAI

client = OpenAI(
    api_key=key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

print("\n--- 测试1: qwen-max 文本 ---")
try:
    resp = client.chat.completions.create(
        model="qwen-max",
        messages=[{"role": "user", "content": "回复 OK"}],
    )
    print(f"  PASS: {resp.choices[0].message.content}")
    print(f"  模型: {resp.model}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n--- 测试2: qwen-vl-max 视觉模型 ---")
try:
    resp = client.chat.completions.create(
        model="qwen-vl-max",
        messages=[{"role": "user", "content": '用JSON格式返回{"status":"ok"}，不要其他内容'}],
    )
    print(f"  PASS: {resp.choices[0].message.content[:80]}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n--- 测试3: qwen-plus 流式 ---")
try:
    stream = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": "用一句话介绍二手商品发布助手"}],
        stream=True,
    )
    chunks = []
    for chunk in stream:
        if chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)
    print(f"  PASS: {''.join(chunks)}")
except Exception as e:
    print(f"  FAIL: {e}")
