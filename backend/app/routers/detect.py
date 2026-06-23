"""
YOLOv8 检测 API - 独立路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
import io
import logging

from app.ml.yolo_detector import YOLODetector

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
        
        detector = get_detector()
        result = detector.predict(pil_image)
        
        return {
            'success': True,
            'count': result['count'],
            'detections': result['detections'],
            'annotated_image': result['annotated_base64'],
            'model': 'yolov8'
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