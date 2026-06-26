"""
全链路图片处理路由：瑕疵检测 + 画框标注 + DeepSeek 定价 + 数据库保存 + 预处理
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
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
from app.db import crud
from app.utils.preprocess import get_preprocessor
from app.utils.file_validator import validate_upload_file
from app.dependencies import get_current_user
from app.services.price_service import query_price
from app.models.schemas import PriceResult  # ✅ 导入类型

logger = logging.getLogger(__name__)

router = APIRouter(tags=["图片处理"])

_detector = None
_price_client = None


def get_detector():
    global _detector
    if _detector is None:
        _detector = DefectDetector()
    return _detector


def get_price_client():
    global _price_client
    if _price_client is None:
        _price_client = DeepSeekPriceClient()
    return _price_client


@router.post("/process/image")
async def process_image(
    image: UploadFile = File(...),
    user_id: int = Depends(get_current_user),
    item_id: Optional[int] = Form(default=None),
    category: str = Form(default="手机"),
    brand: str = Form(default="Apple"),
    model: str = Form(default="iPhone 14 Pro"),
):
    """
    全链路图片处理：预处理 + 瑕疵检测 + 画框标注 + 结构化数据 + DeepSeek 定价 + 数据库保存
    """
    try:
        # ============================================================
        # 1. 文件上传校验
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
        
        pil_image = Image.open(io.BytesIO(content))

        # ============================================================
        # 2. 图片预处理
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
        # 3. 瑕疵检测
        # ============================================================
        detector = get_detector()
        result = detector.process(processed_image)

        logger.info(f"📊 result keys: {result.keys()}")
        logger.info(f"📊 defect_count: {result.get('defect_count', 0)}")

        # ============================================================
        # 4. 保存标注图
        # ============================================================
        uid = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{uid}"
        annotated_path = f"static/uploads/annotated/{base_name}.png"
        
        logger.info(f"📝 准备保存标注图: {annotated_path}")
        
        if result.get('annotated') is not None:
            save_image(result['annotated'], annotated_path)
            logger.info(f"✅ 标注图已保存: {annotated_path}")
        else:
            logger.warning("⚠️ result['annotated'] 为 None，无法保存标注图")

        # ============================================================
        # 5. 保存瑕疵数据到数据库
        # ============================================================
        if item_id:
            try:
                # 验证商品所有权
                item = await crud.get_item_by_id(item_id)
                if item is None:
                    raise HTTPException(status_code=404, detail="商品不存在")
                if item["user_id"] != user_id:
                    raise HTTPException(status_code=403, detail="无权操作此商品")

                await crud.update_item_defects(
                    item_id=item_id,
                    annotated_url=annotated_path,
                    defect_count=result['defect_count'],
                    defect_data=result.get('defects_for_ds')
                )
                logger.info(f"✅ 瑕疵数据已保存到数据库: item_id={item_id}")
            except Exception as e:
                logger.error(f"保存瑕疵数据到数据库失败: {e}")

        # ============================================================
        # 6. ✅ 服务端查询市场均价（修复 BaseModel 访问）
        # ============================================================
        market_avg_price = 5000.0  # fallback 默认值
        
        try:
            # ✅ 查询市场行情（返回 PriceResult 对象）
            price_result: PriceResult = await query_price(brand=brand, model_name=model)
            
            # ✅ 使用 . 属性访问（BaseModel 正确方式）
            if price_result and price_result.avg_price:
                market_avg_price = float(price_result.avg_price)
                logger.info(f"✅ 查询到市场均价: {market_avg_price}")
            else:
                logger.warning(f"⚠️ 未查询到 {brand} {model} 的行情数据，使用默认值")
        except Exception as e:
            logger.error(f"❌ 查询市场行情失败: {e}，使用默认值")

        # ============================================================
        # 7. DeepSeek 定价
        # ============================================================
        deepseek_data = None
        price_suggestion = None
        
        if result['defect_count'] > 0 and result.get('defects_for_ds'):
            defects_for_ds = result['defects_for_ds']
            deepseek_data = detector.get_defects_for_deepseek(defects_for_ds)
            
            product_info = {
                'category': category,
                'brand': brand,
                'model': model,
                'market_avg_price': market_avg_price,
                'user_id': user_id
            }
            
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

        # ============================================================
        # 8. 构建返回数据
        # ============================================================
        response_data = {
            'success': True,
            'data': {
                'annotated_base64': pil_to_base64(result['annotated']) if result.get('annotated') else None,
                'defects': result['defects'],
                'defect_count': result['defect_count']
            },
            'saved_files': {
                'annotated': annotated_path if result.get('annotated') else None
            },
            'preprocess_info': {
                'success': preprocess_result['success'],
                'area_ratio': preprocess_result.get('area_ratio', 0.0),
                'message': preprocess_result.get('message', '')
            },
            'file_info': {
                'original_filename': safe_filename,
                'file_size': len(content)
            },
            'market_price': market_avg_price,
            'message': f"处理完成，检测到 {result['defect_count']} 个瑕疵"
        }

        if deepseek_data:
            response_data['deepseek_data'] = deepseek_data
        
        if price_suggestion:
            response_data['price_suggestion'] = price_suggestion

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/process/health")
async def process_health():
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )