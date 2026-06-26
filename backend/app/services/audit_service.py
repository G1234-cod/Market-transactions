"""审计日志服务 —— 记录每次 LLM 调用的全链路信息"""
import time
from typing import Optional, Union
from app.db import crud


# ============================================================
# ✅ 抽取公共逻辑
# ============================================================

async def _log_call(
    action_type: str,
    user_id: int,
    model_name: str,
    input_summary: Optional[str],
    raw_response: Union[dict, str, None],
    start_time: float,
    success: bool,
    error_msg: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
) -> None:
    """
    统一的审计日志记录函数
    
    Args:
        action_type: 操作类型 (vision_extract/text_generate/price_query)
        user_id: 用户ID
        model_name: 模型名称
        input_summary: 输入摘要
        raw_response: 原始响应（dict 或字符串）
        start_time: 开始时间戳
        success: 是否成功
        error_msg: 错误信息（可选）
        execution_time_ms: 执行时间（毫秒，可选，不传则自动计算）
    """
    if execution_time_ms is None:
        execution_time_ms = int((time.time() - start_time) * 1000)
    
    await crud.insert_audit_log(
        user_id=user_id,
        action_type=action_type,
        model_name=model_name,
        input_summary=input_summary,
        raw_ai_response=raw_response,
        execution_time_ms=execution_time_ms,
        status="SUCCESS" if success else "FAILED",
        error_message=error_msg if not success else None,
    )


# ============================================================
# 公共接口
# ============================================================

async def log_vision_call(
    user_id: int,
    model_name: str,
    input_summary: Optional[str],
    raw_response: Union[dict, str, None],
    start_time: float,
    success: bool,
    error_msg: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
) -> None:
    """
    记录视觉识别调用
    
    Args:
        user_id: 用户ID
        model_name: 模型名称
        input_summary: 输入摘要
        raw_response: 原始响应（dict 或 JSON 字符串）
        start_time: 开始时间戳
        success: 是否成功
        error_msg: 错误信息（可选）
        execution_time_ms: 执行时间（毫秒，可选）
    """
    await _log_call(
        action_type="vision_extract",
        user_id=user_id,
        model_name=model_name,
        input_summary=input_summary,
        raw_response=raw_response,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
        execution_time_ms=execution_time_ms,
    )


async def log_generate_call(
    user_id: int,
    model_name: str,
    input_summary: Optional[str],
    raw_response: Union[str, dict, None],
    start_time: float,
    success: bool,
    error_msg: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
) -> None:
    """
    记录文案生成调用
    
    Args:
        user_id: 用户ID
        model_name: 模型名称
        input_summary: 输入摘要
        raw_response: 原始响应（字符串或 dict）
        start_time: 开始时间戳
        success: 是否成功
        error_msg: 错误信息（可选）
        execution_time_ms: 执行时间（毫秒，可选）
    """
    await _log_call(
        action_type="text_generate",
        user_id=user_id,
        model_name=model_name,
        input_summary=input_summary,
        raw_response=raw_response,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
        execution_time_ms=execution_time_ms,
    )


async def log_price_query(
    user_id: int,
    brand: str,
    model: str,
    result: Optional[dict],
    start_time: float,
    success: bool,
    error_msg: Optional[str] = None,
) -> None:
    """
    记录价格查询调用
    
    Args:
        user_id: 用户ID
        brand: 品牌
        model: 型号
        result: 查询结果
        start_time: 开始时间戳
        success: 是否成功
        error_msg: 错误信息（可选）
    """
    input_summary = f"{brand} {model}"
    await _log_call(
        action_type="price_query",
        user_id=user_id,
        model_name="market_prices",
        input_summary=input_summary,
        raw_response=result,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
    )