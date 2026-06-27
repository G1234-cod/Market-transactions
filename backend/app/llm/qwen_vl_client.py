"""Qwen-VL 客户端 —— 对接阿里云百炼 Qwen-VL-Max（视觉识别）

使用方式:
    client = QwenVLClient()
    result = await client.chat(messages)          # 一次性调用
    async for token in client.chat_stream(messages):  # 流式调用
        ...

环境变量:
    DASHSCOPE_API_KEY  —— 阿里云百炼 API Key
"""
import os
from typing import AsyncIterator

from app.config import settings
from app.llm.base import BaseLLMClient


class QwenVLClient(BaseLLMClient):
    """阿里云百炼 Qwen-VL-Max 客户端，用于视觉识别 + 结构化输出"""

    def __init__(self):
        self._api_key = settings.DASHSCOPE_API_KEY
        self._model = settings.QWEN_VL_MODEL
        self._client = None  # ✅ 延迟初始化，复用连接

    # ---- 使用 OpenAI 兼容接口 ----
    def _openai_client(self):
        """✅ 复用客户端实例，避免每次请求创建新连接"""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=60.0,  # ✅ 设置超时
            )
        return self._client

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """
        一次性调用 Qwen-VL-Max。

        messages 格式（含图片）:
        [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://xxx"}},
                    {"type": "text", "text": "识别图片中的商品"}
                ]
            }
        ]

        纯文本格式:
        [
            {"role": "user", "content": "你好"}
        ]
        """
        client = self._openai_client()
        resp = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            **kwargs,
        )
        if resp.choices:
            return resp.choices[0].message.content or ""
        return ""

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """流式调用 Qwen-VL-Max，逐 token 返回"""
        client = self._openai_client()
        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # ---- DashScope 原生 SDK 接口（备选） ----
    @staticmethod
    def chat_native(messages: list[dict], **kwargs) -> str:
        """使用 DashScope 原生 SDK 调用（同步，适合简单场景）"""
        import dashscope

        resp = dashscope.MultiModalConversation.call(
            model="qwen-vl-max",
            api_key=settings.DASHSCOPE_API_KEY,
            messages=messages,
            **kwargs,
        )
        if resp.status_code == 200:
            return resp.output.choices[0].message.content[0]["text"]
        raise RuntimeError(f"Qwen-VL 调用失败: [{resp.status_code}] {resp.message}")

    @staticmethod
    def build_vision_message(image_url: str, prompt: str) -> list[dict]:
        """构建含图片的 message（OpenAI 兼容格式）"""
        return [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ]
        }]

    @staticmethod
    def build_dashscope_message(image_url: str, prompt: str) -> list[dict]:
        """构建含图片的 message（DashScope 原生格式）"""
        return [{
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": prompt},
            ]
        }]


# ---- 结构化识别的 System Prompt ----
EXTRACT_SYSTEM_PROMPT = """你是一个专业的二手商品鉴定专家。请根据上传的图片，识别其中的物品信息。

## 输出要求
严格输出以下 JSON 格式，不要添加任何额外说明文字：
```json
{
    "category": "品类（如：手机、笔记本、平板、外设、耳机）",
    "brand": "品牌（如：Apple、罗技、华为）",
    "model": "具体型号（如：iPhone 13、G610）",
    "condition": "成色描述（如：9成新，屏幕有细微划痕，电池健康度85%）"
}
```

## 注意事项
- 如果图片中无法识别到商品，所有字段留空字符串
- model 字段尽量精确到具体型号
- condition 字段描述物品外观状态，包括划痕、磕碰、配件情况等"""
