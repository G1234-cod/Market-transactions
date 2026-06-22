"""测试 DeepSeek API 连接与流式输出"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI


def get_client():
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )


def test_chat_simple():
    """测试基础对话"""
    client = get_client()
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "回复 OK"}],
    )
    content = resp.choices[0].message.content
    print(f"  PASS: 基础对话 → {content}")


def test_chat_stream():
    """测试流式输出"""
    client = get_client()
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "用一句话介绍二手商品发布助手"}],
        stream=True,
    )
    chunks = []
    for chunk in stream:
        if chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)
    full = "".join(chunks)
    print(f"  PASS: 流式输出 → {full}")


def test_chat_chinese():
    """测试中文输出"""
    client = get_client()
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "请用中文回答：你好，请介绍你自己"}],
    )
    content = resp.choices[0].message.content
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in content)
    print(f"  PASS: 中文输出 ({'含中文' if has_chinese else '无中文'}) → {content[:80]}...")


# ============================================================
# 直接运行：python test_deepseek.py
# ============================================================
if __name__ == "__main__":
    print("=== DeepSeek API 连通性测试 ===\n")
    test_chat_simple()
    test_chat_stream()
    test_chat_chinese()
    print("\n=== 全部测试完成 ===")
