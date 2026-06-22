"""POST /api/v1/extract — 图片上传 + Qwen-VL-Max 视觉识别"""
import os
import uuid
import json
import time
import base64

from fastapi import APIRouter, UploadFile, File, Form, Request
import aiofiles

from app.config import settings
from app.models.schemas import ExtractResponse, ExtractResult
from app.services import vision_service, audit_service
from app.llm.qwen_vl_client import QwenVLClient, EXTRACT_SYSTEM_PROMPT

router = APIRouter(tags=["视觉识别"])


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    request: Request,
    image: UploadFile = File(...),
    user_id: int = Form(default=1),
):
    """上传图片并提取商品特征

    流程：
    1. 保存图片到 static/uploads/
    2. 调 Qwen-VL-Max 识别 → 解析 JSON
    3. 返回品类/品牌/型号/成色
    """
    start_time = time.time()

    # 1. 保存图片到本地
    ext = os.path.splitext(image.filename or "image.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    content = await image.read()
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    image_url = f"/static/uploads/{filename}"

    # 2. 读取图片生成 base64（直接用 data URI 传给 Qwen-VL，避免依赖外部可访问 URL）
    image_b64 = base64.b64encode(content).decode()
    image_data_uri = f"data:image/{ext.lstrip('.')};base64,{image_b64}"

    # 3. 调用 Qwen-VL-Max 视觉识别
    success = True
    error_msg = None
    raw_response = ""

    try:
        client = QwenVLClient()
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            *client.build_vision_message(image_data_uri, "请识别图片中的二手商品信息"),
        ]
        raw_response = await client.chat(messages)
        result = vision_service.parse_to_extract_result(raw_response)
    except Exception as e:
        success = False
        error_msg = str(e)
        result = ExtractResult()

    # 4. 审计日志（异步写入，不影响响应）
    await audit_service.log_vision_call(
        user_id=user_id,
        model_name=settings.QWEN_VL_MODEL,
        input_summary=f"图片: {image.filename} ({len(content)} bytes)",
        raw_response=raw_response,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
    )

    return ExtractResponse(
        success=success,
        data=result,
        image_urls=[image_url],
        error=error_msg,
    )
