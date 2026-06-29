# app/utils/json_utils.py

"""
JSON 处理工具函数
安全处理 JSON 序列化，避免双编码问题
"""
import json
from typing import Any, Optional, Union


def safe_json_dumps(data: Any, ensure_ascii: bool = False) -> Optional[str]:
    """
    安全的 JSON 序列化，避免双编码
    
    Args:
        data: 要序列化的数据
        ensure_ascii: 是否转义非 ASCII 字符
    
    Returns:
        Optional[str]: JSON 字符串，如果 data 为 None 则返回 None
    
    Examples:
        >>> safe_json_dumps({"key": "value"})
        '{"key": "value"}'
        
        >>> safe_json_dumps('{"key": "value"}')
        '{"key": "value"}'
        
        >>> safe_json_dumps("plain text")
        '{"value": "plain text"}'
        
        >>> safe_json_dumps(None)
        None
    """
    if data is None:
        return None
    
    # 如果已经是 JSON 字符串，直接返回（避免双编码）
    if isinstance(data, str):
        # 检查是否是有效的 JSON
        stripped = data.strip()
        if (stripped.startswith('{') and stripped.endswith('}')) or \
           (stripped.startswith('[') and stripped.endswith(']')):
            try:
                json.loads(stripped)
                # 是有效的 JSON，直接返回
                return stripped
            except json.JSONDecodeError:
                pass
        
        # 不是有效的 JSON，包装成 JSON
        return json.dumps({"value": data}, ensure_ascii=ensure_ascii)
    
    # dict 或 list，直接序列化
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=ensure_ascii)
    
    # 其他类型，尝试序列化
    try:
        return json.dumps(data, ensure_ascii=ensure_ascii)
    except TypeError:
        return json.dumps({"value": str(data)}, ensure_ascii=ensure_ascii)


def safe_json_loads(data: Optional[str]) -> Any:
    """
    安全的反序列化 JSON
    
    Args:
        data: JSON 字符串
    
    Returns:
        Any: 解析后的数据，如果解析失败返回原字符串
    
    Examples:
        >>> safe_json_loads('{"key": "value"}')
        {'key': 'value'}
        
        >>> safe_json_loads('plain text')
        'plain text'
        
        >>> safe_json_loads(None)
        None
    """
    if data is None:
        return None
    
    if not isinstance(data, str):
        return data
    
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data


def is_valid_json(data: str) -> bool:
    """
    检查字符串是否是有效的 JSON
    
    Args:
        data: 要检查的字符串
    
    Returns:
        bool: 是否是有效的 JSON
    """
    if not isinstance(data, str):
        return False
    
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


def json_to_dict(data: Any) -> Optional[dict]:
    """
    安全地将数据转换为 dict
    
    Args:
        data: 字典、JSON 字符串或其他类型
    
    Returns:
        Optional[dict]: 转换后的字典，失败返回 None
    """
    if data is None:
        return None
    
    if isinstance(data, dict):
        return data
    
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
            return {"data": parsed}
        except json.JSONDecodeError:
            return {"raw": data}
    
    return {"value": str(data)}