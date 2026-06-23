"""POST /api/v1/damage - 损伤检测"""
import os
import uuid
import json
import time

from fastapi import APIRouter, UploadFile, File, Form, Request
import aiofiles

from app.config import settings
from app.models.schemas import (
    DamageDetectionResponse,
    DamageDetectionResult,
    DamageRegion,
    DAMAGE_COLORS
)
from app.services import image_processor, damage_detector

router = APIRouter(tags=["损伤检测"])


@router.post("/damage", response_model=DamageDetectionResponse)
async def detect_damage(
    request: Request,
    images: list[UploadFile] = File(...),
    user_id: int = Form(default=1),
):
    """对上传的图片进行损伤检测

    流程：
    1. 保存原图到 static/uploads/
    2. 对每张图进行预处理（去噪、增强、锐化、尺寸归一化）
    3. YOLO检测损伤区域
    4. 在原图上标注损伤（多边形）
    5. 返回检测结果和标注图URL
    """
    start_time = time.time()
    results = []
    error_msg = None

    try:
        for image in images:
            # 1. 保存原图
            ext = os.path.splitext(image.filename or "image.jpg")[1] or ".jpg"
            original_filename = f"{uuid.uuid4().hex}{ext}"
            original_filepath = os.path.join(settings.UPLOAD_DIR, original_filename)

            content = await image.read()
            async with aiofiles.open(original_filepath, "wb") as f:
                await f.write(content)

            original_url = f"/static/uploads/{original_filename}"

            # 2. 预处理图片
            processed_path, scale_x, scale_y = image_processor.preprocess_image(
                original_filepath,
                settings.UPLOAD_DIR
            )

            # 3. 获取原图尺寸（用于坐标转换）
            orig_w, orig_h = image_processor.get_image_dimensions(original_filepath)

            # 4. YOLO损伤检测（在原图上标注）
            annotated_url, regions = damage_detector.detector.detect(
                processed_image_path=processed_path,
                original_image_path=original_filepath,
                scale_x=scale_x,
                scale_y=scale_y,
                output_dir=settings.UPLOAD_DIR
            )

            # 5. 构建结果
            result = DamageDetectionResult(
                image_url=original_url,
                annotated_image_url=annotated_url,
                regions=regions,
                total_regions=len(regions)
            )
            results.append(result)

            # 6. 保存到数据库
            await _save_detection_record(
                original_url=original_url,
                annotated_url=annotated_url,
                regions=regions,
                user_id=user_id
            )

            # 7. 清理预处理生成的临时文件
            if os.path.exists(processed_path):
                os.remove(processed_path)

    except Exception as e:
        error_msg = str(e)

    return DamageDetectionResponse(
        success=error_msg is None,
        data=results if results else None,
        error=error_msg
    )


async def _save_detection_record(
    original_url: str,
    annotated_url: str,
    regions: list[DamageRegion],
    user_id: int
):
    """保存检测记录到数据库"""
    from app.db.connection import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            has_damage = 1 if len(regions) > 0 else 0

            # 插入检测记录
            await cursor.execute(
                """
                INSERT INTO damage_detections
                (original_image_url, annotated_image_url, total_regions, has_damage)
                VALUES (%s, %s, %s, %s)
                """,
                (original_url, annotated_url, len(regions), has_damage)
            )
            detection_id = cursor.lastrowid

            # 插入损伤区域详情
            for region in regions:
                await cursor.execute(
                    """
                    INSERT INTO damage_regions
                    (detection_id, damage_type, confidence, polygon_coords)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        detection_id,
                        region.damage_type,
                        region.confidence,
                        json.dumps(region.polygon, ensure_ascii=False)
                    )
                )

            await conn.commit()


@router.get("/damage/types")
async def get_damage_types():
    """获取支持的损伤类型及其颜色"""
    return {
        "types": [
            {"id": "scratch", "name": "划痕", "color": list(DAMAGE_COLORS["scratch"])},
            {"id": "dent", "name": "凹陷", "color": list(DAMAGE_COLORS["dent"])},
            {"id": "crack", "name": "裂纹", "color": list(DAMAGE_COLORS["crack"])},
            {"id": "stain", "name": "污渍", "color": list(DAMAGE_COLORS["stain"])},
            {"id": "other", "name": "其他", "color": list(DAMAGE_COLORS["other"])},
        ]
    }
