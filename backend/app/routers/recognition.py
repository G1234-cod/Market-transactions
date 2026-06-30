"""
视觉大模型识别路由 —— Qwen-VL独立识别 + YOLO旁路校验 + DeepSeek文案定价

核心逻辑：
1. 视觉大模型(Qwen-VL)完全独立运行——它看到什么就是什么，不受任何预设类别限制
2. YOLO仅在旁路运行，用于内部数据统计和模型训练，不影响最终结果
3. 最终返回的 category/brand/model/condition 100%来自视觉大模型
4. 非80类商品的后台数据自动存入训练集，供YOLO模型迭代
5. DeepSeek根据视觉大模型结果生成AI建议售价和推荐文案
"""
import os
import uuid
import json
import time
import base64
import logging
import asyncio
import threading
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Request, HTTPException, Depends
import aiofiles

from app.config import settings
from app.models.schemas import ExtractResult, ExtractResponse
from app.services import vision_service, audit_service
from app.llm.qwen_vl_client import QwenVLClient, EXTRACT_SYSTEM_PROMPT
from app.llm.deepseek_client import DeepSeekClient
from app.ml.yolo_detector import YOLODetector
from app.ml.defect_detector_yolo import DefectDetector
from app.ml.data_collector import DataCollector
from app.utils.file_validator import validate_upload_file
from app.utils.preprocess import get_preprocessor
from app.utils.image_utils import pil_to_base64, save_image
from app.constants.categories import (
    PRESET_CATEGORIES,
    is_preset_category,
    is_preset_model,
    match_preset,
    get_all_categories,
)
from app.db import crud
from app.dependencies import get_current_user_optional
from app.middleware.rate_limit import create_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["双模型识别"])

# ✅ 品类兜底价格（当市场和DeepSeek都无法给出价格时使用）
_CATEGORY_FALLBACK_PRICES = {
    '手机': 1500, '笔记本': 3000, '平板': 1200, '耳机': 300, '手表': 800,
    '相机': 2000, '外设': 200, '游戏机': 1000, '家电': 500, '家具': 600,
    '键盘': 200, '鼠标': 100, '显示器': 800, '音箱': 300, '无人机': 1500,
}


def _estimate_price(category: str) -> float:
    """根据品类估算兜底价格"""
    for key, price in _CATEGORY_FALLBACK_PRICES.items():
        if key in str(category):
            return float(price)
    return 500.0  # 完全未知品类给500

# ============================================================
# 全局单例（线程安全）
# ============================================================
_yolo_detector = None
_defect_detector = None
_qwen_client = None
_deepseek_client = None
_data_collector = None
_yolo_lock = threading.Lock()
_defect_lock = threading.Lock()
_qwen_lock = threading.Lock()
_ds_lock = threading.Lock()
_collector_lock = threading.Lock()


def get_yolo_detector():
    global _yolo_detector
    if _yolo_detector is not None:
        return _yolo_detector
    with _yolo_lock:
        if _yolo_detector is not None:
            return _yolo_detector
        _yolo_detector = YOLODetector()
        return _yolo_detector


def get_defect_detector():
    global _defect_detector
    if _defect_detector is not None:
        return _defect_detector
    with _defect_lock:
        if _defect_detector is not None:
            return _defect_detector
        _defect_detector = DefectDetector()
        return _defect_detector


def get_qwen_client():
    global _qwen_client
    if _qwen_client is not None:
        return _qwen_client
    with _qwen_lock:
        if _qwen_client is not None:
            return _qwen_client
        _qwen_client = QwenVLClient()
        return _qwen_client


def get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is not None:
        return _deepseek_client
    with _ds_lock:
        if _deepseek_client is not None:
            return _deepseek_client
        _deepseek_client = DeepSeekClient()
        return _deepseek_client


def get_data_collector():
    global _data_collector
    if _data_collector is not None:
        return _data_collector
    with _collector_lock:
        if _data_collector is not None:
            return _data_collector
        _data_collector = DataCollector()
        return _data_collector


# ============================================================
# DeepSeek 文案生成 Prompt
# ============================================================
DEEPSEEK_GENERATE_PROMPT = """你是一个专业的二手商品文案专家。请根据以下信息生成商品描述和AI建议售价。

## 商品信息
类别：{category}
品牌：{brand}
型号：{model}
成色描述：{condition}

## 瑕疵检测结果
{defects_info}

## 整体成色程度
{condition_grade}

## 市场参考价格
市场均价：{market_avg_price}元

## 输出要求
严格输出以下 JSON 格式，不要添加任何额外说明文字：
```json
{{
    "title": "吸引人的商品标题（30字以内）",
    "description": "详细的商品描述，突出卖点和成色，200字左右",
    "suggested_price": "AI建议售价（数字，单位元）",
    "price_reasoning": "定价理由（说明品类、品牌、型号、成色、瑕疵程度如何影响定价）",
    "selling_points": ["卖点1", "卖点2", "卖点3"]
}}
```

## 定价规则
- 完整（无瑕疵）：按市场均价上浮 5-10%
- 轻微瑕疵：按市场均价定价
- 中度瑕疵：按市场均价下调 10-20%
- 重度瑕疵：按市场均价下调 20-40%
- 完全损坏：残值定价，不超过市场均价的 10%
- 同时考虑品牌溢价、型号热门程度、成色描述的细节"""


# ============================================================
# 双模型协同识别接口
# ============================================================
@router.post("/recognize")
async def recognize(
    request: Request,
    image: UploadFile = File(...),
    user_id: Optional[int] = Depends(get_current_user_optional),
    rate: None = Depends(create_rate_limit(5, 60)),
):
    """
    双模型协同识别：自研模型 + 阿里云Qwen-VL + DeepSeek
    
    流程：
    1. 文件校验和保存
    2. 图片预处理
    3. 并行执行：自研模型识别 + Qwen-VL识别 + 瑕疵检测
    4. 结果比对和融合
    5. DeepSeek生成文案和定价
    6. 返回最终结果
    """
    start_time = time.time()
    result_id = uuid.uuid4().hex[:8]
    logger.info(f"🚀 开始双模型识别 [{result_id}]: user_id={user_id}, filename={image.filename}")

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

    # ============================================================
    # 2. 保存图片到本地
    # ============================================================
    from PIL import Image
    import io

    pil_image = Image.open(io.BytesIO(content))
    ext = os.path.splitext(safe_filename or "image.jpg")[1] or ".jpg"
    filename = f"{result_id}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    image_url = f"{settings.STATIC_PREFIX}/uploads/{filename}"
    logger.info(f"📁 图片已保存: {image_url}")

    # ============================================================
    # 3. 图片预处理
    # ============================================================
    preprocessor = get_preprocessor(target_size=448)
    preprocess_result = preprocessor.process(pil_image)

    if not preprocess_result['success']:
        logger.warning(f"预处理警告: {preprocess_result['message']}")
        # ✅ 即使预处理失败也强制缩放到 448，确保 Qwen-VL 不会因图片过大而超时
        processed_image = preprocessor.resize(pil_image)
    else:
        processed_image = preprocess_result['denoised']
        logger.info(f"✅ 预处理完成")

    # ============================================================
    # 4. 并行推理检测
    # ============================================================
    async def run_yolo():
        """自研YOLO模型识别"""
        try:
            detector = get_yolo_detector()
            result = detector.predict(processed_image)
            raw_detections = result['detections']  # 原始检测列表，供上下文构建
            
            if result['detections']:
                detection = result['detections'][0]
                return {
                    'success': True,
                    'category': detection['class_name'],
                    'model': detection['class_name'],
                    'confidence': detection['confidence'],
                    'annotated_base64': result['annotated_base64'],
                    '_detections_raw': raw_detections,  # 供 Qwen 上下文使用
                }
            else:
                return {
                    'success': True,
                    'category': 'unknown',
                    'model': '',
                    'confidence': 0.0,
                    'annotated_base64': result['annotated_base64'],
                    '_detections_raw': [],
                }
        except Exception as e:
            logger.error(f"❌ YOLO识别失败: {e}")
            return {
                'success': False,
                'category': 'unknown',
                'model': '',
                'confidence': 0.0,
                'error': str(e),
                '_detections_raw': [],
            }

    async def run_qwen_with_context(yolo_result):
        """阿里云Qwen-VL识别（附带YOLO检测结果作为上下文）"""
        try:
            # 构建 YOLO 上下文文本
            yolo_detector = get_yolo_detector()
            yolo_detections = yolo_result.get('_detections_raw', [])
            yolo_ctx = yolo_detector.format_context(yolo_detections) if yolo_detections else "YOLO 模型未检测到任何物品。"

            # 替换 System Prompt 中的上下文占位
            system_prompt = EXTRACT_SYSTEM_PROMPT.replace("{yolo_context}", yolo_ctx)
            logger.info(f"📋 YOLO上下文: {yolo_ctx}")

            # ✅ 确保图片尺寸可控：最大 1024px，JPEG 质量 75
            img_for_qwen = processed_image.copy()
            w, h = img_for_qwen.size
            max_dim = max(w, h)
            if max_dim > 1024:
                ratio = 1024 / max_dim
                img_for_qwen = img_for_qwen.resize((int(w*ratio), int(h*ratio)), Image.Resampling.LANCZOS)
            if img_for_qwen.mode in ('RGBA', 'P'):
                img_for_qwen = img_for_qwen.convert('RGB')

            buf = io.BytesIO()
            img_for_qwen.save(buf, format='JPEG', quality=75)
            img_bytes = buf.getvalue()
            logger.info(f"📸 Qwen-VL 输入图片: {img_for_qwen.size}, {len(img_bytes)} bytes")

            image_b64 = base64.b64encode(img_bytes).decode()
            image_data_uri = f"data:image/jpeg;base64,{image_b64}"

            client = get_qwen_client()
            messages = [
                {"role": "system", "content": system_prompt},
                *client.build_vision_message(image_data_uri, "请根据YOLO的检测结果和图片内容，进行精确识别"),
            ]
            raw_response = await client.chat(messages)
            logger.info(f"📡 Qwen-VL 响应: {len(raw_response)}字符")
            result = vision_service.parse_to_extract_result(raw_response)
            logger.info(f"✅ Qwen-VL: category={result.category}, brand={result.brand}, model={result.model}, yolo_correct={result.yolo_correct}")

            return {
                'success': True,
                'category': result.category,
                'brand': result.brand,
                'model': result.model,
                'condition': result.condition,
                'condition_grade': result.condition_grade,
                'yolo_correct': result.yolo_correct,
                'yolo_judgment': result.yolo_judgment,
                'raw_response': raw_response,
            }
        except Exception as e:
            import traceback
            logger.error(f"❌ Qwen-VL调用失败: {e}")
            logger.error(f"   堆栈: {traceback.format_exc()}")
            logger.error(f"   API_KEY已配置: {bool(settings.DASHSCOPE_API_KEY)}")
            return {
                'success': False,
                'category': '',
                'brand': '',
                'model': '',
                'condition': '',
                'condition_grade': '',
                'yolo_correct': None,
                'yolo_judgment': '',
                'error': str(e),
                'raw_response': '',
            }

    async def run_defect():
        """自研瑕疵检测模型"""
        try:
            detector = get_defect_detector()
            result = detector.process(processed_image)
            return {
                'success': True,
                'defects': result['defects'],
                'defect_count': result['defect_count'],
                'annotated': result.get('annotated'),
                'defects_for_ds': result.get('defects_for_ds'),
            }
        except Exception as e:
            logger.error(f"❌ 瑕疵检测失败: {e}")
            return {
                'success': False,
                'defects': [],
                'defect_count': 0,
                'error': str(e),
            }

    # 第一阶段：YOLO 和缺陷检测并行执行
    yolo_result, defect_result = await asyncio.gather(
        run_yolo(),
        run_defect(),
    )

    # 第二阶段：将 YOLO 结果作为上下文，喂给 Qwen-VL 进行语义级裁决
    qwen_result = await run_qwen_with_context(yolo_result)

    logger.info(f"⏱️ 推理完成 [{result_id}]: "
                f"YOLO={'success' if yolo_result['success'] else 'failed'}, "
                f"Qwen={'success' if qwen_result['success'] else 'failed'}, "
                f"Defect={'success' if defect_result['success'] else 'failed'}")

    # ============================================================
    # 5. 双重校验与容错机制（R1+R2）
    # ============================================================
    yolo_category = yolo_result.get('category', 'unknown')
    qwen_category = qwen_result.get('category', '')
    qwen_brand = qwen_result.get('brand', '')
    qwen_model = qwen_result.get('model', '')
    qwen_condition = qwen_result.get('condition', '')
    qwen_condition_grade = qwen_result.get('condition_grade', '')  # 视觉大模型判定的成色程度

    # ✅ 视觉大模型结果校验
    if not qwen_result['success']:
        logger.error(f"❌ [视觉大模型] 调用失败 [{result_id}]")
        raise HTTPException(status_code=422, detail="视觉大模型调用失败，请稍后重试")

    blocked = {'未知', 'unknown', '其他', 'other', '无法识别', 'unrecognized', '未分类', 'uncategorized', ''}
    if not qwen_category or qwen_category.strip().lower() in {c.lower() for c in blocked}:
        logger.error(f"❌ [视觉大模型] category无效 [{result_id}]: '{qwen_category}'")
        raise HTTPException(status_code=422, detail="视觉大模型未能识别商品品类，请重新上传更清晰的图片")

    # ✅ 两模型同时判定结果
    from app.constants.categories import get_all_categories, get_models_by_category
    qwen_in_preset = is_preset_category(qwen_category) or is_preset_model(qwen_model, qwen_category)

    if qwen_in_preset:
        # ✅ 是80类：标准化到80类名称
        matched = match_preset(qwen_model, qwen_category)
        final_category = matched.get('category', qwen_category)
        logger.info(f"📋 [80类] [{result_id}]: {final_category} / {qwen_brand} / {qwen_model}")
    else:
        # ✅ 不是80类：视觉大模型独立判定，它是什么就是什么
        # 不做任何错题记录——品类不在预设范围不是错误，只有模型判断冲突才是
        final_category = qwen_category
        logger.info(f"📋 [视觉大模型] [{result_id}]: {final_category} / {qwen_brand} / {qwen_model}")

    final_brand = qwen_brand
    final_model = qwen_model
    final_condition = qwen_condition

    # ✅ 由 Qwen 语义判断 YOLO 是否正确（不再做字符串比对）
    qwen_yolo_correct = qwen_result.get('yolo_correct', None)
    qwen_yolo_judgment = qwen_result.get('yolo_judgment', '')

    disagreement_recorded = False
    if yolo_result['success'] and qwen_result['success']:
        if qwen_yolo_correct is False:
            # Qwen 判定 YOLO 检测错误 → 存入错题集 + 差异记录
            logger.warning(f"⚠️ [Qwen判定YOLO错误] [{result_id}]: "
                          f"YOLO={yolo_category} vs Qwen={qwen_category}, "
                          f"评价: {qwen_yolo_judgment}")

            # 1. 存入错题集（图片 + 标签）
            try:
                collector = get_data_collector()
                collector.collect(
                    image=processed_image,
                    wrong_label=yolo_category if yolo_category != 'unknown' else 'unknown_preset',
                    correct_label=qwen_category,
                    user_id=user_id or 0,
                    item_id=None,
                    confidence=yolo_result.get('confidence', 0.0),
                    save_to_db=True,
                )
                logger.info(f"✅ [错题集] 冲突数据已存入 [{result_id}]")
            except Exception as e:
                logger.error(f"❌ [错题集] 存入失败: {e}")

            # 2. 存入数据库差异记录
            try:
                await crud.insert_model_disagreement(
                    image_url=image_url,
                    yolo_category=yolo_category,
                    yolo_model=yolo_result.get('model', ''),
                    qwen_category=qwen_category,
                    qwen_model=qwen_model,
                    qwen_brand=qwen_brand,
                    user_id=user_id,
                    item_id=None,
                    confidence=yolo_result.get('confidence', 0.0),
                )
                disagreement_recorded = True
                logger.info(f"✅ [数据库] 差异记录已保存 [{result_id}]")
            except Exception as e:
                logger.error(f"❌ [数据库] 差异记录保存失败: {e}")
        else:
            logger.info(f"✅ [Qwen判定YOLO正确] [{result_id}]: {qwen_yolo_judgment}")


    # ============================================================
    # 6. 保存瑕疵标注图
    # ============================================================
    annotated_url = None
    annotated_base64 = None

    if defect_result['success'] and defect_result.get('annotated'):
        annotated_filename = f"{result_id}_annotated.png"
        annotated_path = os.path.join(settings.UPLOAD_DIR, 'annotated', annotated_filename)
        save_image(defect_result['annotated'], annotated_path)
        annotated_url = f"{settings.STATIC_PREFIX}/uploads/annotated/{annotated_filename}"
        annotated_base64 = pil_to_base64(defect_result['annotated'])
        logger.info(f"📝 瑕疵标注图已保存: {annotated_url}")

    # ============================================================
    # 7. 查询市场均价
    # ============================================================
    market_avg_price = 0.0
    price_result = None

    if final_brand and final_model:
        try:
            price_result = await crud.query_price(brand=final_brand, model=final_model)
            if price_result:
                market_avg_price = float(price_result.get('avg_price', 0))
                logger.info(f"💰 查询到市场均价: {market_avg_price}")
            else:
                logger.warning(f"⚠️ 未查询到 {final_brand} {final_model} 的行情数据")
        except Exception as e:
            logger.error(f"❌ 查询市场行情失败: {e}")

    # ============================================================
    # 8. DeepSeek 生成文案和定价
    # ============================================================
    deepseek_result = None

    if final_category and (final_brand or final_model):
        try:
            # 构建瑕疵信息（含5级成色程度）
            defects_info = ""
            if defect_result['success'] and defect_result['defects']:
                defects_info = "\n".join([
                    f"- {d['type_cn']}: 置信度{d['confidence']:.2f}"
                    for d in defect_result['defects'][:5]
                ])
            else:
                defects_info = "无明显瑕疵"

            # ✅ 5级成色程度 —— 视觉大模型判定优先
            condition_grade_label = qwen_condition_grade or defect_result.get('condition_grade', {}).get('grade_label', '未知')
            condition_grade_str = f"整体成色程度：{condition_grade_label}"

            # ✅ 市场均价：如果没有数据，让DeepSeek自己估算
            if market_avg_price > 0:
                market_price_str = f"市场均价：{market_avg_price}元"
            else:
                market_price_str = "市场均价：暂无数据，请根据品类、品牌、型号和成色自行估算合理二手价格"

            # ✅ 修复：使用 safe replace 替代 .format()，避免用户数据中的 {} 导致崩溃
            prompt = (DEEPSEEK_GENERATE_PROMPT
                .replace("{category}", str(final_category))
                .replace("{brand}", str(final_brand))
                .replace("{model}", str(final_model))
                .replace("{condition}", str(final_condition or "未知"))
                .replace("{defects_info}", str(defects_info))
                .replace("{condition_grade}", condition_grade_str)
                .replace("{market_avg_price}", market_price_str))

            client = get_deepseek_client()
            messages = [
                {"role": "system", "content": "你是一个专业的二手商品文案生成专家。"},
                {"role": "user", "content": prompt},
            ]
            raw_response = await client.chat(messages)

            # 解析DeepSeek响应（包含AI建议售价供确认页展示，但文案生成不含售价）
            try:
                data = vision_service._parse_json_from_text(raw_response)
                suggested_price = float(data.get('suggested_price', 0))
                # ✅ AI价格绝不能为0 —— 兜底用市场价或品类估算
                if suggested_price <= 0:
                    suggested_price = market_avg_price if market_avg_price > 0 else _estimate_price(final_category)
                deepseek_result = {
                    'success': True,
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'suggested_price': suggested_price,
                    'price_reasoning': data.get('price_reasoning', ''),
                    'selling_points': data.get('selling_points', []),
                    'raw_response': raw_response,
                }
                logger.info(f"✅ DeepSeek生成完成 [{result_id}]: "
                           f"AI建议价={deepseek_result['suggested_price']}")
            except (json.JSONDecodeError, AttributeError):
                fallback_price = market_avg_price if market_avg_price > 0 else _estimate_price(final_category)
                deepseek_result = {
                    'success': True,
                    'title': '',
                    'description': raw_response[:500],
                    'suggested_price': fallback_price,
                    'price_reasoning': '',
                    'selling_points': [],
                    'raw_response': raw_response,
                }
                logger.warning(f"⚠️ DeepSeek响应解析失败，使用兜底价格: {fallback_price}")

        except Exception as e:
            logger.error(f"❌ DeepSeek调用失败: {e}")
            fallback_price = market_avg_price if market_avg_price > 0 else _estimate_price(final_category)
            deepseek_result = {
                'success': False,
                'error': str(e),
                'suggested_price': fallback_price,
            }

    # ============================================================
    # 9. 构建返回结果
    # ============================================================
    # ✅ 成色程度：优先用视觉大模型判定，兜底用瑕疵检测计算
    if qwen_condition_grade:
        condition_grade = {
            'grade': -1,
            'grade_label': qwen_condition_grade,
            'defect_count': defect_result.get('defect_count', 0),
            'severity_summary': defect_result.get('severity_summary', {}),
            'source': 'qwen-vl',
        }
    elif defect_result.get('condition_grade'):
        condition_grade = defect_result['condition_grade']
        condition_grade['source'] = 'defect_detector'
    else:
        condition_grade = {}

    response_data = {
        'success': True,
        'result_id': result_id,
        'final_result': {
            'category': final_category,
            'brand': final_brand,
            'model': final_model,
            'condition': final_condition,
        },
        'model_disagreement': {
            'has_disagreement': disagreement_recorded,
            'yolo_category': yolo_category,
            'qwen_category': qwen_category,
            'yolo_confidence': yolo_result.get('confidence', 0.0),
            'yolo_correct': qwen_yolo_correct,
            'yolo_judgment': qwen_yolo_judgment,
        },
        'is_preset': qwen_in_preset,
        'defect_result': {
            'success': defect_result['success'],
            'defect_count': defect_result['defect_count'],
            'defects': defect_result.get('defects', []),
            'annotated_url': annotated_url,
            'annotated_base64': annotated_base64,
            'condition_grade': condition_grade,
        },
        'market_price': {
            'avg_price': market_avg_price,
            'matched': price_result is not None,
        },
        'image_urls': [image_url],
        'message': f"{'80类' if qwen_in_preset else '视觉大模型判定'}: {final_category}",
    }

    if deepseek_result:
        response_data['deepseek'] = deepseek_result

    # ============================================================
    # 10. 审计日志
    # ============================================================
    try:
        execution_time_ms = int((time.time() - start_time) * 1000)
        await audit_service.log_vision_call(
            user_id=user_id,
            model_name=f"dual_model(yolo+qwen)",
            input_summary=f"图片: {safe_filename} ({len(content)} bytes)",
            raw_response=json.dumps({
                'yolo': yolo_result,
                'qwen': qwen_result,
                'final': response_data['final_result'],
            }),
            start_time=start_time,
            success=True,
            error_msg=None,
        )
        logger.info(f"✅ 双模型识别完成 [{result_id}]: {execution_time_ms}ms")
    except Exception as e:
        logger.error(f"❌ 审计日志记录失败: {e}")

    return response_data


# ============================================================
# 预设类别查询接口
# ============================================================
@router.get("/recognize/categories")
async def get_categories():
    """获取平台预设的所有商品类别"""
    return {
        'success': True,
        'categories': get_all_categories(),
        'total': len(get_all_categories()),
        'preset_models_count': sum(len(models) for models in PRESET_CATEGORIES.values()),
    }


# ============================================================
# 模型差异统计接口
# ============================================================
@router.get("/recognize/disagreements/stats")
async def get_disagreement_stats(
    user_id: int = Depends(get_current_user_optional),
):
    """获取模型差异统计信息（需登录）"""
    # ✅ 修复：要求登录才能查看模型差异数据
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        stats = await crud.get_model_disagreements_stats()
        return {
            'success': True,
            **stats,
        }
    except Exception as e:
        logger.error(f"获取差异统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 模型差异记录列表接口
# ============================================================
@router.get("/recognize/disagreements")
async def get_disagreements(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    user_id: int = Depends(get_current_user_optional),
):
    """获取模型差异记录列表（需登录）"""
    # ✅ 修复：要求登录才能查看模型差异数据
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        records = await crud.get_model_disagreements(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
        )
        return {
            'success': True,
            'records': records,
            'count': len(records),
        }
    except Exception as e:
        logger.error(f"获取差异记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 健康检查接口
# ============================================================
@router.get("/recognize/health")
async def recognize_health():
    """双模型识别服务健康检查"""
    try:
        yolo_detector = get_yolo_detector()
        defect_detector = get_defect_detector()
        qwen_client = get_qwen_client()
        deepseek_client = get_deepseek_client()

        # ✅ 修复：不暴露 API Key 配置状态（安全加固）
        return {
            'status': 'healthy',
            'yolo_model': yolo_detector.model_path,
            'yolo_device': yolo_detector.device,
            'defect_model': defect_detector.model_path if defect_detector.model else 'not loaded',
            'defect_device': defect_detector.device,
            'qwen_available': bool(qwen_client._api_key),
            'deepseek_available': bool(deepseek_client._client.api_key),
            'preset_categories': len(get_all_categories()),
            'preset_models': sum(len(models) for models in PRESET_CATEGORIES.values()),
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )
