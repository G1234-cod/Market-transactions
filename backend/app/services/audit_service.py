"""审计日志服务 —— 记录每次 LLM 调用的全链路信息"""
import time
from app.db import crud


async def log_vision_call(
    user_id: int,
    model_name: str,
    input_summary: str | None,
    raw_response: dict | str | None,
    start_time: float,
    success: bool,
    error_msg: str | None = None,
):
    """记录视觉识别调用"""
    elapsed = int((time.time() - start_time) * 1000)
    await crud.insert_audit_log(
        user_id=user_id,
        action_type="vision_extract",
        model_name=model_name,
        input_summary=input_summary,
        raw_ai_response=raw_response,
        execution_time_ms=elapsed,
        status="SUCCESS" if success else "FAILED",
        error_message=error_msg,
    )


async def log_generate_call(
    user_id: int,
    model_name: str,
    input_summary: str | None,
    raw_response: str | None,
    start_time: float,
    success: bool,
    error_msg: str | None = None,
):
    """记录文案生成调用"""
    elapsed = int((time.time() - start_time) * 1000)
    await crud.insert_audit_log(
        user_id=user_id,
        action_type="text_generate",
        model_name=model_name,
        input_summary=input_summary,
        raw_ai_response=raw_response,
        execution_time_ms=elapsed,
        status="SUCCESS" if success else "FAILED",
        error_message=error_msg,
    )
