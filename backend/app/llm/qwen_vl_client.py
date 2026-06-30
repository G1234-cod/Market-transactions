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
EXTRACT_SYSTEM_PROMPT = """你是一个专业的二手商品识别专家。本地轻量模型（YOLOv8）已经对图片做了初步检测，以下是它的检测结果作为参考：

{yolo_context}

你的任务：
1. 根据 YOLO 的检测结果，结合图片内容，判断 YOLO 是否识别正确（注意：YOLO 输出是英文，你是中文，请做语义级判断，比如 YOLO 的 "laptop" 对应你的 "笔记本"、"tomato" 对应 "西红柿" 就是正确的）
2. 无论如何，请重新仔细观察图片，给出你自己精确的识别结果，要精细到品牌和具体型号

严格输出以下 JSON，不要添加任何额外文字：
```json
{
    "category": "商品品类（中文）",
    "brand": "品牌（中文或英文原名）",
    "model": "具体型号",
    "condition": "成色描述",
    "condition_grade": "完整、轻微瑕疵、中度瑕疵、重度瑕疵、完全损坏 中选一个",
    "yolo_correct": true,
    "yolo_judgment": "对YOLO检测结果的评价（中文一句话，说明为什么正确或哪里错了）"
}
```

yolo_correct 的判断标准：只要 YOLO 检测到的物品种类与图片实际内容语义一致（即使名称写法不同），就是 true。如果 YOLO 完全识别错误或置信度过低，才是 false。"""
