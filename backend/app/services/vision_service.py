"""视觉识别服务 —— 待接入 Qwen-VL-Max 后启用"""
import json
import re

from app.models.schemas import ExtractResult


def _parse_json_from_text(text: str) -> dict:
    """从 LLM 文本中提取 JSON（多层容错）"""
    # 1. 直接从 Markdown 代码块提取
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1)
    # 2. 从文本中找第一个 { 到最后 }
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    # 3. 解析
    return json.loads(text)


def parse_to_extract_result(raw_response: str) -> ExtractResult:
    """两层防护：json.loads + Pydantic 校验"""
    data = _parse_json_from_text(raw_response)
    return ExtractResult(
        category=data.get("category", ""),
        brand=data.get("brand", ""),
        model=data.get("model", ""),
        condition=data.get("condition", ""),
    )
