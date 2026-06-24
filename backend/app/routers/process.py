from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
import uuid
import os
import logging
from datetime import datetime

from app.ml.defect_detector_yolo import DefectDetector
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
    """
    全链路图片处理：瑕疵检测 + 画框标注 + 结构化数据
    
    返回：
        - annotated_base64: 标注图（不同形状+颜色代表不同程度，程度不显示给用户）
        - defects: 前端展示的瑕疵列表（不含程度）
        - defects_for_ds: DeepSeek 定价用的数据（含程度）
        - defect_count: 瑕疵总数
        - severity_summary: 程度统计（供内部使用）
    """
    try:
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        detector = get_detector()
        result = detector.process(pil_image)

        uid = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{uid}"

        # 保存标注图
        annotated_path = f"static/uploads/annotated/{base_name}.png"
        save_image(result['annotated'], annotated_path)

        # 生成 DeepSeek 定价数据
        deepseek_data = None
        if result['defect_count'] > 0 and result.get('defects_for_ds'):
            deepseek_data = detector.get_defects_for_deepseek(result['defects_for_ds'])

        # 构建返回数据
        response_data = {
            'success': True,
            'data': {
                'annotated_base64': pil_to_base64(result['annotated']),
                'defects': result['defects'],              # 前端展示（不含程度）
                'defect_count': result['defect_count']
            },
            'saved_files': {
                'annotated': annotated_path
            },
            'message': f"处理完成，检测到 {result['defect_count']} 个瑕疵"
        }

        # 如果有瑕疵，附加 DeepSeek 数据（供后续调用）
        if deepseek_data:
            response_data['deepseek_data'] = deepseek_data

        return response_data

    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/process/health")
async def process_health():
    """健康检查"""
    try:
        detector = get_detector()
        model_status = 'loaded' if detector.model else 'no_model'
        return {
            'status': 'healthy',
            'model_status': model_status,
            'model': 'yolo_defect',
            'device': detector.device
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }