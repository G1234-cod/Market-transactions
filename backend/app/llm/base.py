"""LLM 客户端抽象基类 —— 策略模式，便于切换模型"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMClient(ABC):
    """所有 LLM 客户端必须实现的接口"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """同步（一次性）调用 LLM，返回完整文本"""
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """流式调用 LLM，逐 token 返回文本"""
        ...
