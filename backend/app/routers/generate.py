"""POST /api/v1/generate — SSE 流式生成带货文案"""
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import GenerateRequest
from app.services import text_service, audit_service
from app.config import settings

router = APIRouter(tags=["文案生成"])


@router.post("/generate")
async def generate(payload: GenerateRequest):
    """SSE 流式生成商品带货文案

    接收用户确认后的商品信息 + 行情数据，调用 DeepSeek-V4-Pro 流式生成。
    前端以 EventSource / fetch ReadableStream 方式接收。
    """
    start_time = time.time()
    full_text = []

    async def event_stream():
        nonlocal full_text
        try:
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
                yield f"data: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"

            # 流结束，发送完成信号 + 建议价
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            await audit_service.log_generate_call(
                user_id=payload.user_id,
                model_name=settings.DEEPSEEK_MODEL,
                input_summary=f"{payload.brand} {payload.model}",
                raw_response="".join(full_text),
                start_time=start_time,
                success=False,
                error_msg=str(e),
            )
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        else:
            await audit_service.log_generate_call(
                user_id=payload.user_id,
                model_name=settings.DEEPSEEK_MODEL,
                input_summary=f"{payload.brand} {payload.model}",
                raw_response="".join(full_text),
                start_time=start_time,
                success=True,
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
