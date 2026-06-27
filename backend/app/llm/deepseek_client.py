"""DeepSeek 客户端 —— 对接 DeepSeek 官方 API（兼容 OpenAI SDK）"""
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.llm.base import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=60.0,  # ✅ 设置超时，防止请求无限挂起
        )
        self._model = settings.DEEPSEEK_MODEL

    async def chat(self, messages: list[dict], **kwargs) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
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
