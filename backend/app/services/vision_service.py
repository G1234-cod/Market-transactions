"""视觉识别服务 —— 待接入 Qwen-VL-Max 后启用"""
import json
import re

from app.models.schemas import ExtractResult


def _parse_json_from_text(text: str) -> dict:
    """从 LLM 文本中提取 JSON（多层容错，支持嵌套对象）"""
    # 1. 直接从 Markdown 代码块提取
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1)
    # 2. ✅ 修复：使用平衡括号匹配提取 JSON（支持嵌套对象）
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    text = text[start:i+1]
                    break
    # 3. 解析
    return json.loads(text)


def parse_to_extract_result(raw_response: str) -> ExtractResult:
    """两层防护：json.loads + Pydantic 校验"""
    try:
        data = _parse_json_from_text(raw_response)
    except (json.JSONDecodeError, AttributeError):
        data = {}
    return ExtractResult(
        category=data.get("category", ""),
        brand=data.get("brand", ""),
        model=data.get("model", ""),
        condition=data.get("condition", ""),
        condition_grade=data.get("condition_grade", ""),
    )
