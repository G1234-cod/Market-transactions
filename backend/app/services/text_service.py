"""
文案生成服务 —— 拼装 Prompt → 调 DeepSeek-V4-Pro 流式生成
"""
import asyncio
import logging
from typing import AsyncIterator, Optional

from app.llm.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

# 二手车带货专家 System Prompt
SYSTEM_PROMPT = """你是一位经验丰富的二手商品带货专家，擅长撰写在闲鱼、转转等平台的吸睛商品文案。

## 你的任务
根据用户提供的商品信息，生成一份完整的高质量二手商品发布内容。

## 输出格式（严格遵守）
1. **商品标题**（一行，20字以内，包含品牌型号+核心卖点）
2. **商品描述**（分段，300-500字，包含：成色说明、使用感受、适合人群、出手原因）

## 风格要求
- 语气真诚、接地气，像真人卖家而非机器
- 适当使用 emoji 增强可读性
- 突出商品亮点，但不过度夸大
- 不要在输出中给出具体建议售价"""


def build_user_prompt(
    category: str,
    brand: str,
    model_name: str,
    condition: str,
    avg_price: Optional[float] = None,
    low_price: Optional[float] = None,
    high_price: Optional[float] = None,
) -> str:
    """
    拼装 User Prompt
    
    Args:
        category: 品类
        brand: 品牌
        model_name: 型号
        condition: 成色
        avg_price: 市场均价
        low_price: 市场最低价
        high_price: 市场最高价
    
    Returns:
        str: 完整的 User Prompt
    """
    parts = [
        "请为以下二手商品生成发布内容：",
        f"- 品类：{category}",
        f"- 品牌：{brand}",
        f"- 型号：{model_name}",
        f"- 成色：{condition}",
    ]
    if avg_price is not None and low_price is not None and high_price is not None:
        parts.append(f"- 市场行情：均价 ¥{avg_price:.0f}，区间 ¥{low_price:.0f} ~ ¥{high_price:.0f}")
    else:
        parts.append("- 市场行情：暂无参考数据，请根据经验合理定价")
    return "\n".join(parts)


# ============================================================
# ✅ DeepSeek 客户端单例
# ============================================================

_client: Optional[DeepSeekClient] = None
_client_lock = asyncio.Lock()


async def get_deepseek_client() -> DeepSeekClient:
    """获取 DeepSeek 客户端单例（线程安全）"""
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:  # 双重检查
                logger.info("🔄 初始化 DeepSeek 客户端（单例）...")
                _client = DeepSeekClient()
    return _client


# ============================================================
# 流式生成
# ============================================================

async def generate_text_stream(
    category: str,
    brand: str,
    model_name: str,
    condition: str,
    avg_price: Optional[float] = None,
    low_price: Optional[float] = None,
    high_price: Optional[float] = None,
) -> AsyncIterator[str]:
    """
    流式生成带货文案
    
    Args:
        category: 品类
        brand: 品牌
        model_name: 型号
        condition: 成色
        avg_price: 市场均价
        low_price: 市场最低价
        high_price: 市场最高价
    
    Yields:
        str: 文本片段
    
    Raises:
        Exception: 生成失败时抛出
    """
    try:
        # ✅ 使用单例客户端（async 安全）
        client = await get_deepseek_client()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(
                category, brand, model_name, condition,
                avg_price, low_price, high_price
            )},
        ]
        async for token in client.chat_stream(messages):
            yield token

    except Exception as e:
        logger.error(f"❌ 文案生成服务失败: {e}")
        # 重新抛出，让路由层处理
        raise