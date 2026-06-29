"""POST /api/v1/generate — SSE 流式生成带货文案"""
import json
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import GenerateRequest
from app.services import text_service, audit_service
from app.config import settings
from app.dependencies import get_current_user_optional
from app.middleware.rate_limit import create_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["文案生成"])


def sse_event(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate")
async def generate(
    payload: GenerateRequest,
    user_id: Optional[int] = Depends(get_current_user_optional),  # ✅ 可选认证
    rate: None = Depends(create_rate_limit(20, 60)),  # DeepSeek: 20次/分钟
):
    """SSE 流式生成商品带货文案

    接收用户确认后的商品信息 + 行情数据，调用 DeepSeek-V4-Pro 流式生成。
    前端以 EventSource / fetch ReadableStream 方式接收。

    响应格式:
        正常流:
            data: {"type": "start", "status": "started", "message": "开始生成文案..."}
            data: {"type": "content", "content": "这是一台..."}
            data: {"type": "done", "status": "success", "message": "生成完成"}

        异常:
            data: {"type": "error", "status": "error", "code": "GENERATION_ERROR", "message": "错误描述"}
    """
    start_time = time.time()
    full_text = []

    async def event_stream():
        try:
            # 1. 发送开始事件
            yield sse_event({
                "type": "start",
                "status": "started",
                "message": "开始生成文案..."
            })

            # 2. 流式生成内容
            async for token in text_service.generate_text_stream(
                category=payload.category,
                brand=payload.brand,
                model_name=payload.model,
                condition=payload.condition,
                avg_price=payload.avg_price,
                low_price=payload.low_price,
                high_price=payload.high_price,
            ):
                full_text.append(token)
                yield sse_event({
                    "type": "content",
                    "content": token
                })

            # 3. 发送完成事件
            yield sse_event({
                "type": "done",
                "status": "success",
                "message": "文案生成完成"
            })

            # 4. 记录成功审计日志（✅ 修复：失败不影响 SSE 流）
            full_response = "".join(full_text)
            logged_response = full_response[:2000] + ("...(truncated)" if len(full_response) > 2000 else "")
            try:
                await audit_service.log_generate_call(
                    user_id=user_id,
                    model_name=settings.DEEPSEEK_MODEL,
                    input_summary=f"{payload.brand} {payload.model}",
                    raw_response=logged_response,
                    start_time=start_time,
                    success=True,
                )
            except Exception as audit_err:
                logger.warning(f"审计日志写入失败（不影响主流程）: {audit_err}")

        except Exception as e:
            logger.error(f"❌ 流式生成失败: {e}")

            # 发送错误事件
            yield sse_event({
                "type": "error",
                "status": "error",
                "code": "GENERATION_ERROR",
                "message": "文案生成失败，请重试"  # ✅ 修复：不暴露内部错误详情
            })

            # 记录失败审计日志（截断过长内容）
            full_response = "".join(full_text)
            logged_response = full_response[:2000] + ("...(truncated)" if len(full_response) > 2000 else "")
            await audit_service.log_generate_call(
                user_id=user_id,
                model_name=settings.DEEPSEEK_MODEL,
                input_summary=f"{payload.brand} {payload.model}",
                raw_response=logged_response,
                start_time=start_time,
                success=False,
                error_msg=str(e),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )