"""POST /api/v1/generate — SSE 流式生成带货文案"""
import json
import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import GenerateRequest
from app.services import text_service, audit_service
from app.config import settings
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["文案生成"])


def sse_event(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate")
async def generate(
    payload: GenerateRequest,
    user_id: int = Depends(get_current_user)  # ✅ JWT 认证
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

            # 4. 记录成功审计日志
            await audit_service.log_generate_call(
                user_id=user_id,
                model_name=settings.DEEPSEEK_MODEL,
                input_summary=f"{payload.brand} {payload.model}",
                raw_response="".join(full_text),
                start_time=start_time,
                success=True,
            )

        except Exception as e:
            logger.error(f"❌ 流式生成失败: {e}")

            # 发送错误事件
            yield sse_event({
                "type": "error",
                "status": "error",
                "code": "GENERATION_ERROR",
                "message": str(e)
            })

            # 记录失败审计日志
            await audit_service.log_generate_call(
                user_id=user_id,
                model_name=settings.DEEPSEEK_MODEL,
                input_summary=f"{payload.brand} {payload.model}",
                raw_response="".join(full_text),
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