"""文案生成服务 —— 拼装 Prompt → 调 DeepSeek-V4-Pro 流式生成"""
import time
from typing import AsyncIterator

from app.llm.deepseek_client import DeepSeekClient

# 二手车带货专家 System Prompt
SYSTEM_PROMPT = """你是一位经验丰富的二手商品带货专家，擅长撰写在闲鱼、转转等平台的吸睛商品文案。

## 你的任务
根据用户提供的商品信息，生成一份完整的高质量二手商品发布内容。

## 输出格式（严格遵守）
1. **商品标题**（一行，20字以内，包含品牌型号+核心卖点）
2. **商品描述**（分段，300-500字，包含：成色说明、使用感受、适合人群、出手原因）
3. **建议售价**（单独一行，格式：💰 建议售价：¥XXX）

## 风格要求
- 语气真诚、接地气，像真人卖家而非机器
- 适当使用 emoji 增强可读性
- 突出商品亮点，但不过度夸大
- 如有价格参考区间，给出合理建议价"""


def build_user_prompt(
    category: str, brand: str, model_name: str, condition: str,
    avg_price: float | None, low_price: float | None, high_price: float | None,
) -> str:
    """拼装 User Prompt"""
    parts = [
        "请为以下二手商品生成发布内容：",
        f"- 品类：{category}",
        f"- 品牌：{brand}",
        f"- 型号：{model_name}",
        f"- 成色：{condition}",
    ]
    if avg_price and low_price and high_price:
        parts.append(f"- 市场行情：均价 ¥{avg_price:.0f}，区间 ¥{low_price:.0f} ~ ¥{high_price:.0f}")
    else:
        parts.append("- 市场行情：暂无参考数据，请根据经验合理定价")
    return "\n".join(parts)


async def generate_text_stream(
    category: str, brand: str, model_name: str, condition: str,
    avg_price: float | None = None,
    low_price: float | None = None,
    high_price: float | None = None,
) -> AsyncIterator[str]:
    """流式生成带货文案"""
    client = DeepSeekClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(category, brand, model_name, condition, avg_price, low_price, high_price)},
    ]
    async for token in client.chat_stream(messages):
        yield token
