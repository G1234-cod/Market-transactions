"""POST /api/v1/extract — 图片上传 + Qwen-VL-Max 视觉识别"""
import os
import uuid
import json
import time
import base64
import logging

from fastapi import APIRouter, UploadFile, File, Form, Request
import aiofiles

from app.config import settings
from app.models.schemas import ExtractResponse, ExtractResult
from app.services import vision_service, audit_service
from app.llm.qwen_vl_client import QwenVLClient, EXTRACT_SYSTEM_PROMPT

# 🆕 导入双模型比对相关模块
from app.ml.yolo_detector import YOLODetector
from app.ml.data_collector import DataCollector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["视觉识别"])

# ============================================================
# 🆕 全局单例（只在启动时加载一次）
# ============================================================
_yolo_detector = None
_data_collector = None


def get_yolo_detector():
    """获取 YOLO 检测器单例"""
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLODetector()
    return _yolo_detector


def get_data_collector():
    """获取数据收集器单例"""
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
    """上传图片并提取商品特征

    流程：
    1. 保存图片到 static/uploads/
    2. 调 Qwen-VL-Max 识别 → 解析 JSON
    3. 🆕 双模型比对 + 错误数据收集
    4. 返回品类/品牌/型号/成色
    """
    start_time = time.time()

    # ============================================================
    # 1. 保存图片到本地
    # ============================================================
    ext = os.path.splitext(image.filename or "image.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    content = await image.read()
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    image_url = f"/static/uploads/{filename}"

    # 保存 PIL 图片供后续使用
    from PIL import Image
    import io
    pil_image = Image.open(io.BytesIO(content))

    # ============================================================
    # 2. 调用 Qwen-VL-Max 视觉识别
    # ============================================================
    success = True
    error_msg = None
    raw_response = ""
    qwen_label = "unknown"
    result = ExtractResult()

    try:
        image_b64 = base64.b64encode(content).decode()
        image_data_uri = f"data:image/{ext.lstrip('.')};base64,{image_b64}"

        client = QwenVLClient()
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            *client.build_vision_message(image_data_uri, "请识别图片中的二手商品信息"),
        ]
        raw_response = await client.chat(messages)
        result = vision_service.parse_to_extract_result(raw_response)
        
        # 提取 Qwen 的分类标签（用于比对）
        qwen_label = result.category if result.category else "unknown"
        
    except Exception as e:
        success = False
        error_msg = str(e)
        result = ExtractResult()
        logger.error(f"Qwen 识别失败: {e}")

    # ============================================================
    # 3. 🆕 双模型比对 + 错误数据收集
    # ============================================================
    # 注意：item_id 在保存图片时还没有，可以用文件名作为标识
    # 如果后续有商品 ID，可以传入真实的 item_id
    item_id = filename  # 暂时用文件名作为标识

    try:
        # 3.1 调用本地 YOLO 模型
        yolo_detector = get_yolo_detector()
        yolo_result = yolo_detector.predict(pil_image)
        
        # 提取 YOLO 的标签
        if yolo_result['detections']:
            yolo_label = yolo_result['detections'][0]['class_name']
            yolo_conf = yolo_result['detections'][0]['confidence']
        else:
            yolo_label = 'unknown'
            yolo_conf = 0.0
        
        # 3.2 比对结果
        if (yolo_label != qwen_label and 
            qwen_label != 'unknown' and 
            yolo_label != 'unknown'):
            
            # 不一致 → 收集错误数据
            collector = get_data_collector()
            collector.collect(
                image=pil_image,
                wrong_label=yolo_label,
                correct_label=qwen_label,
                user_id=user_id,
                item_id=item_id,
                confidence=yolo_conf
            )
            logger.warning(f"⚠️ 模型结果不一致: YOLO={yolo_label}, Qwen={qwen_label}")
        else:
            logger.info(f"✅ 模型结果一致: {yolo_label}")
            
    except Exception as e:
        logger.error(f"双模型比对失败: {e}")
        # 比对失败不影响主流程

    # ============================================================
    # 4. 审计日志（异步写入，不影响响应）
    # ============================================================
    await audit_service.log_vision_call(
        user_id=user_id,
        model_name=settings.QWEN_VL_MODEL,
        input_summary=f"图片: {image.filename} ({len(content)} bytes)",
        raw_response=raw_response,
        start_time=start_time,
        success=success,
        error_msg=error_msg,
    )

    # ============================================================
    # 5. 返回结果
    # ============================================================
    return ExtractResponse(
        success=success,
        data=result,
        image_urls=[image_url],
        error=error_msg,
    )