"""
全链路图片处理路由：瑕疵检测 + 画框标注 + DeepSeek 定价
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
import uuid
import os
import logging
from datetime import datetime

from app.ml.defect_detector_yolo import DefectDetector
from app.utils.image_utils import pil_to_base64, save_image
from app.llm.deepseek_price_client import DeepSeekPriceClient
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["图片处理"])

_detector = None
_price_client = None


def get_detector():
    """获取瑕疵检测器（单例）"""
    global _detector
    if _detector is None:
        _detector = DefectDetector()
    return _detector


def get_price_client():
    """获取 DeepSeek 定价客户端（单例）"""
    global _price_client
    if _price_client is None:
        _price_client = DeepSeekPriceClient()
    return _price_client


@router.post("/process/image")
async def process_image(
    image: UploadFile = File(...),
    user_id: int = Form(default=1),
    category: str = Form(default="手机"),
    brand: str = Form(default="Apple"),
    model: str = Form(default="iPhone 14 Pro"),
    market_avg_price: float = Form(default=5000)
):
    """
    全链路图片处理：瑕疵检测 + 画框标注 + 结构化数据 + DeepSeek 定价
    
    返回：
        - annotated_base64: 标注图
        - defects: 前端展示的瑕疵列表（不含程度）
        - defect_count: 瑕疵总数
        - deepseek_data: 供 DeepSeek 定价用的数据
        - price_suggestion: DeepSeek 定价建议
    """
    try:
        # 1. 读取图片
        content = await image.read()
        pil_image = Image.open(io.BytesIO(content))

        # 2. 瑕疵检测
        detector = get_detector()
        result = detector.process(pil_image)

        # 3. 保存标注图
        uid = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{uid}"
        annotated_path = f"static/uploads/annotated/{base_name}.png"
        save_image(result['annotated'], annotated_path)

        # 4. 生成 DeepSeek 定价数据
        deepseek_data = None
        price_suggestion = None
        
        if result['defect_count'] > 0 and result.get('defects_for_ds'):
            # 构建 DeepSeek 输入数据
            defects_for_ds = result['defects_for_ds']
            deepseek_data = detector.get_defects_for_deepseek(defects_for_ds)
            
            # 构建商品信息
            product_info = {
                'category': category,
                'brand': brand,
                'model': model,
                'market_avg_price': market_avg_price,
                'user_id': user_id
            }
            
            # 调用 DeepSeek 定价
            try:
                price_client = get_price_client()
                price_suggestion = await price_client.get_price_suggestion(
                    product_info=product_info,
                    defects_data=deepseek_data
                )
                logger.info(f"✅ DeepSeek 定价完成: {price_suggestion.get('estimated_price', 'N/A')}")
            except Exception as e:
                logger.error(f"DeepSeek 定价调用失败: {e}")
                price_suggestion = {
                    'success': False,
                    'error': str(e),
                    'suggestion': '定价服务暂时不可用'
                }

        # 5. 构建返回数据
        response_data = {
            'success': True,
            'data': {
                'annotated_base64': pil_to_base64(result['annotated']),
                'defects': result['defects'],           # 前端展示（不含程度）
                'defect_count': result['defect_count']
            },
            'saved_files': {
                'annotated': annotated_path
            },
            'message': f"处理完成，检测到 {result['defect_count']} 个瑕疵"
        }

        # 附加 DeepSeek 数据
        if deepseek_data:
            response_data['deepseek_data'] = deepseek_data
        
        if price_suggestion:
            response_data['price_suggestion'] = price_suggestion

        return response_data

    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/process/health")
async def process_health():
    """健康检查"""
    try:
        detector = get_detector()
        price_client = get_price_client()
        
        model_status = 'loaded' if detector.model else 'no_model'
        deepseek_status = 'configured' if price_client.api_key else 'missing_api_key'
        
        return {
            'status': 'healthy',
            'model_status': model_status,
            'model': 'yolo_defect',
            'device': detector.device,
            'deepseek_status': deepseek_status
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }