"""POST /api/v1/extract — 图片上传 + Qwen-VL-Max 视觉识别"""
import os
import uuid
import json
import time
import base64
import logging

from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
import aiofiles

from app.config import settings
from app.models.schemas import ExtractResponse, ExtractResult
from app.services import vision_service, audit_service
from app.llm.qwen_vl_client import QwenVLClient, EXTRACT_SYSTEM_PROMPT
from app.utils.file_validator import validate_upload_file

# 导入双模型比对相关模块
from app.ml.yolo_detector import YOLODetector
from app.ml.data_collector import DataCollector
from app.utils.preprocess import get_preprocessor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["视觉识别"])

# ============================================================
# 全局单例
# ============================================================
_yolo_detector = None
_data_collector = None


def get_yolo_detector():
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLODetector()
    return _yolo_detector


def get_data_collector():
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector


# ============================================================
# 提取接口
# ============================================================

@router.post("/extract", response_model=ExtractResponse)
async def extract(
    request: Request,
    image: UploadFile = File(...),
    user_id: int = Form(default=1),
):
    """上传图片并提取商品特征"""
    start_time = time.time()

    # ============================================================
    # ✅ 1. 文件上传校验
    # ============================================================
    try:
        file_content, safe_filename = await validate_upload_file(
            file=image,
            max_size=settings.MAX_UPLOAD_SIZE,
            check_content=True
        )
        content = file_content
    except HTTPException as e:
        await image.seek(0)
        raise e
    except Exception as e:
        await image.seek(0)
        raise HTTPException(status_code=400, detail=f"文件验证失败: {str(e)}")

    # ============================================================
    # 2. 保存图片到本地
    # ============================================================
    ext = os.path.splitext(safe_filename or "image.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    image_url = f"/static/uploads/{filename}"

    from PIL import Image
    import io
    pil_image = Image.open(io.BytesIO(content))

    # ============================================================
    # 3. 图片预处理
    # ============================================================
    preprocessor = get_preprocessor(target_size=448)
    preprocess_result = preprocessor.process(pil_image)
    
    if not preprocess_result['success']:
        logger.warning(f"预处理警告: {preprocess_result['message']}")
        processed_image = pil_image
    else:
        processed_image = preprocess_result['denoised']
        logger.info(f"✅ 预处理完成: {preprocess_result['message']}")

    # ============================================================
    # 4. 调用 Qwen-VL-Max 视觉识别
    # ============================================================
    success = True
    error_msg = None
    raw_response = ""
    qwen_label = "unknown"
    result = ExtractResult()

    try:
        # 使用预处理后的图片生成 base64
        import io
        buf = io.BytesIO()
        processed_image.save(buf, format='JPEG', quality=85)
        processed_content = buf.getvalue()
        image_b64 = base64.b64encode(processed_content).decode()
        image_data_uri = f"data:image/jpeg;base64,{image_b64}"

        client = QwenVLClient()
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            *client.build_vision_message(image_data_uri, "请识别图片中的二手商品信息"),
        ]
        raw_response = await client.chat(messages)
        result = vision_service.parse_to_extract_result(raw_response)
        qwen_label = result.category if result.category else "unknown"
        
    except Exception as e:
        success = False
        error_msg = str(e)
        result = ExtractResult()
        logger.error(f"Qwen 识别失败: {e}")

    # ============================================================
    # 5. 双模型比对 + 错误数据收集
    # ============================================================
    item_id = filename

    try:
        yolo_detector = get_yolo_detector()
        yolo_result = yolo_detector.predict(processed_image)
        
        if yolo_result['detections']:
            yolo_label = yolo_result['detections'][0]['class_name']
            yolo_conf = yolo_result['detections'][0]['confidence']
        else:
            yolo_label = 'unknown'
            yolo_conf = 0.0
        
        if (yolo_label != qwen_label and 
            qwen_label != 'unknown' and 
            yolo_label != 'unknown'):
            
            collector = get_data_collector()
            collector.collect(
                image=processed_image,
                wrong_label=yolo_label,
                correct_label=qwen_label,
                user_id=user_id,
                item_id=item_id,
                confidence=yolo_conf,
                save_to_db=True
            )
            logger.warning(f"⚠️ 模型结果不一致: YOLO={yolo_label}, Qwen={qwen_label}")
        else:
            logger.info(f"✅ 模型结果一致: {yolo_label}")
            
    except Exception as e:
        logger.error(f"双模型比对失败: {e}")

    # ============================================================
    # 6. 审计日志
    # ============================================================
    await audit_service.log_vision_call(
        user_id=user_id,
        model_name=settings.QWEN_VL_MODEL,
        input_summary=f"图片: {safe_filename} ({len(content)} bytes)",
        raw_response=raw_response,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
    )

    # ============================================================
    # 7. 返回结果
    # ============================================================
    return ExtractResponse(
        success=success,
        data=result,
        image_urls=[image_url],
        error=error_msg,
    )