"""
YOLOv8 检测 API - 独立路由 + 预处理
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io
import logging

from app.ml.yolo_detector import YOLODetector
from app.utils.preprocess import get_preprocessor  # 🆕 新增

logger = logging.getLogger(__name__)

router = APIRouter(tags=["YOLO检测"])

_detector = None


def get_detector():
    global _detector
    if _detector is None:
        _detector = YOLODetector()
    return _detector


@router.post("/yolo/detect")
async def yolo_detect(image: UploadFile = File(...)):
    """使用 YOLOv8 检测图片中的物品"""
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        # ============================================================
        # 🆕 图片预处理
        # ============================================================
        preprocessor = get_preprocessor(target_size=448)
        preprocess_result = preprocessor.process(pil_image)
        
        if not preprocess_result['success']:
            logger.warning(f"预处理警告: {preprocess_result['message']}")
            processed_image = pil_image
        else:
            processed_image = preprocess_result['denoised']
            logger.info(f"✅ 预处理完成: {preprocess_result['message']}")
        
        detector = get_detector()
        result = detector.predict(processed_image)
        
        return {
            'success': True,
            'count': result['count'],
            'detections': result['detections'],
            'annotated_image': result['annotated_base64'],
            'model': 'yolov8',
            'preprocess_info': {
                'success': preprocess_result['success'],
                'area_ratio': preprocess_result.get('area_ratio', 0.0),
                'message': preprocess_result.get('message', '')
            }
        }
        
    except Exception as e:
        logger.error(f"检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/yolo/health")
async def yolo_health():
    """健康检查"""
    try:
        detector = get_detector()
        return {
            'status': 'healthy',
            'device': detector.device,
            'model': 'yolov8'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }