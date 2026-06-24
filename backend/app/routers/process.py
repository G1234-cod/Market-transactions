from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
import uuid
import os
import logging
from datetime import datetime

from app.ml.defect_detector import DefectDetector
from app.utils.image_utils import pil_to_base64, save_image

logger = logging.getLogger(__name__)

router = APIRouter(tags=["图片处理"])

_detector = None

def get_detector():
    global _detector
    if _detector is None:
        _detector = DefectDetector()
    return _detector


@router.post("/process/image")
async def process_image(
    image: UploadFile = File(...),
    user_id: int = Form(default=1)
):
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        detector = get_detector()
        result = detector.process(pil_image)

        uid = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{uid}"

        bg_path = f"static/uploads/bg_removed/{base_name}.png"
        annotated_path = f"static/uploads/annotated/{base_name}.png"

        save_image(result['bg_removed'], bg_path)
        save_image(result['annotated'], annotated_path)

        return {
            'success': True,
            'data': {
                'bg_removed_base64': pil_to_base64(result['bg_removed']),
                'annotated_base64': pil_to_base64(result['annotated']),
                'defects': result['defects'],
                'defect_count': result['defect_count']
            },
            'saved_files': {
                'bg_removed': bg_path,
                'annotated': annotated_path
            },
            'message': f"处理完成，检测到 {result['defect_count']} 个瑕疵"
        }

    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/process/health")
async def process_health():
    try:
        detector = get_detector()
        return {
            'status': 'healthy',
            'modules': ['rembg', 'opencv']
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }