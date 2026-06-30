"""管理员专用路由 —— 模型测试、商品审核、强制下架、模型训练"""
import os
import uuid
import json
import time
import base64
import logging
import asyncio
import threading
import datetime as dt
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
import aiofiles
import aiomysql
from PIL import Image
import io

from app.config import settings
from app.dependencies import get_current_admin
from app.models.schemas import RegisterRequest
from app.db import crud
from app.db.connection import get_pool
from app.services import vision_service, audit_service
from app.llm.qwen_vl_client import QwenVLClient, EXTRACT_SYSTEM_PROMPT
from app.llm.deepseek_client import DeepSeekClient
from app.ml.yolo_detector import YOLODetector
from app.ml.defect_detector_yolo import DefectDetector
from app.utils.file_validator import validate_upload_file
from app.utils.preprocess import get_preprocessor
from app.utils.image_utils import pil_to_base64, save_image
from app.constants.categories import (
    PRESET_CATEGORIES,
    is_preset_category,
    is_preset_model,
    get_all_categories,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["管理员"])

# ============================================================
# 全局单例（线程安全，与 recognition.py 共享）
# ============================================================
_yolo_detector = None
_defect_detector = None
_qwen_client = None
_deepseek_client = None
_yolo_lock = threading.Lock()
_defect_lock = threading.Lock()
_qwen_lock = threading.Lock()
_ds_lock = threading.Lock()


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


# ============================================================
# 1. 模型测试接口 —— 管理员上传图片测试模型效果
# ============================================================
@router.post("/admin/test-model")
async def test_model(
    image: UploadFile = File(...),
    admin_id: int = Depends(get_current_admin),
):
    """
    管理员测试模型：上传图片，对比自研模型与Qwen模型的识别结果
    
    返回详细的模型测试结果，用于管理员评估模型效果
    """
    start_time = time.time()
    result_id = uuid.uuid4().hex[:8]
    logger.info(f"🚀 管理员模型测试 [{result_id}]: admin_id={admin_id}, filename={image.filename}")

    try:
        file_content, safe_filename = await validate_upload_file(
            file=image,
            max_size=settings.MAX_UPLOAD_SIZE,
            check_content=True
        )
        content = file_content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件验证失败: {str(e)}")

    pil_image = Image.open(io.BytesIO(content))
    ext = os.path.splitext(safe_filename or "image.jpg")[1] or ".jpg"
    filename = f"test_{result_id}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    image_url = f"{settings.STATIC_PREFIX}/uploads/{filename}"

    preprocessor = get_preprocessor(target_size=448)
    preprocess_result = preprocessor.process(pil_image)
    processed_image = preprocess_result['denoised'] if preprocess_result['success'] else pil_image

    async def run_yolo():
        try:
            detector = get_yolo_detector()
            result = detector.predict(processed_image)
            
            if result['detections']:
                detection = result['detections'][0]
                return {
                    'success': True,
                    'category': detection['class_name'],
                    'model': detection['class_name'],
                    'confidence': detection['confidence'],
                    'annotated_base64': result['annotated_base64'],
                    'all_detections': result['detections'],
                }
            else:
                return {
                    'success': True,
                    'category': 'unknown',
                    'model': '',
                    'confidence': 0.0,
                    'annotated_base64': result['annotated_base64'],
                    'all_detections': [],
                }
        except Exception as e:
            logger.error(f"❌ YOLO识别失败: {e}")
            return {
                'success': False,
                'category': 'unknown',
                'model': '',
                'confidence': 0.0,
                'error': str(e),
                'all_detections': [],
            }

    async def run_qwen():
        try:
            buf = io.BytesIO()
            if processed_image.mode in ('RGBA', 'P'):
                processed_image = processed_image.convert('RGB')
            processed_image.save(buf, format='JPEG', quality=85)
            processed_content = buf.getvalue()
            image_b64 = base64.b64encode(processed_content).decode()
            image_data_uri = f"data:image/jpeg;base64,{image_b64}"

            client = get_qwen_client()
            messages = [
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT.replace("{yolo_context}", "（管理后台测试，未启用YOLO检测）")},
                *client.build_vision_message(image_data_uri, "请识别图片中的二手商品信息"),
            ]
            raw_response = await client.chat(messages)
            result = vision_service.parse_to_extract_result(raw_response)
            
            return {
                'success': True,
                'category': result.category,
                'brand': result.brand,
                'model': result.model,
                'condition': result.condition,
                'raw_response': raw_response,
            }
        except Exception as e:
            logger.error(f"❌ Qwen-VL识别失败: {e}")
            return {
                'success': False,
                'category': '',
                'brand': '',
                'model': '',
                'condition': '',
                'error': str(e),
            }

    async def run_defect():
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

    yolo_result, qwen_result, defect_result = await asyncio.gather(
        run_yolo(),
        run_qwen(),
        run_defect(),
    )

    yolo_category = yolo_result.get('category', 'unknown')
    qwen_category = qwen_result.get('category', '')
    qwen_brand = qwen_result.get('brand', '')
    qwen_model = qwen_result.get('model', '')

    final_category = qwen_category if qwen_category else yolo_category
    final_brand = qwen_brand
    final_model = qwen_model

    annotated_url = None
    annotated_base64 = None
    if defect_result['success'] and defect_result.get('annotated'):
        annotated_filename = f"test_{result_id}_annotated.png"
        annotated_path = os.path.join(settings.UPLOAD_DIR, 'annotated', annotated_filename)
        save_image(defect_result['annotated'], annotated_path)
        annotated_url = f"{settings.STATIC_PREFIX}/uploads/annotated/{annotated_filename}"
        annotated_base64 = pil_to_base64(defect_result['annotated'])

    market_avg_price = 0.0
    if final_brand and final_model:
        try:
            price_result = await crud.query_price(brand=final_brand, model=final_model)
            if price_result:
                market_avg_price = float(price_result.get('avg_price', 0))
        except Exception as e:
            logger.error(f"❌ 查询市场行情失败: {e}")

    execution_time_ms = int((time.time() - start_time) * 1000)

    return {
        'success': True,
        'result_id': result_id,
        'execution_time_ms': execution_time_ms,
        'image_url': image_url,
        'final_result': {
            'category': final_category,
            'brand': final_brand,
            'model': final_model,
            'market_avg_price': market_avg_price,
        },
        'model_comparison': {
            'has_disagreement': yolo_category != 'unknown' and qwen_category and 
                                yolo_category.lower() != qwen_category.lower(),
            'yolo': {
                'category': yolo_category,
                'model': yolo_result.get('model', ''),
                'confidence': yolo_result.get('confidence', 0.0),
                'success': yolo_result.get('success', False),
                'error': yolo_result.get('error', ''),
                'all_detections': yolo_result.get('all_detections', []),
            },
            'qwen': {
                'category': qwen_category,
                'brand': qwen_brand,
                'model': qwen_model,
                'condition': qwen_result.get('condition', ''),
                'success': qwen_result.get('success', False),
                'error': qwen_result.get('error', ''),
                'raw_response': qwen_result.get('raw_response', '')[:500] if qwen_result.get('raw_response') else '',
            },
        },
        'defect_result': {
            'success': defect_result.get('success', False),
            'defect_count': defect_result.get('defect_count', 0),
            'defects': defect_result.get('defects', []),
            'annotated_url': annotated_url,
            'annotated_base64': annotated_base64,
            'error': defect_result.get('error', ''),
        },
    }


# ============================================================
# 2. 商品审核接口 —— 获取待审核商品列表
# ============================================================
@router.get("/admin/items/review")
async def get_items_for_review(
    review_status: Optional[str] = Query(default=None, description="审核状态筛选: normal/flagged/forced_delisted"),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取商品审核列表（管理员专用）
    
    支持按审核状态筛选，返回商品详情供管理员审查
    """
    try:
        items = await crud.get_items_for_review(status=review_status)
        return {
            'success': True,
            'items': items,
            'count': len(items),
        }
    except Exception as e:
        logger.error(f"获取审核列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. 强制下架接口 —— 管理员强制下架商品并通知用户
# ============================================================
@router.post("/admin/items/{item_id}/force-delist")
async def force_delist_item(
    item_id: int,
    reason: str = Query(default="", description="下架原因"),
    admin_id: int = Depends(get_current_admin),
):
    """
    强制下架商品（管理员专用）
    
    将商品状态改为下架，标记审核状态为forced_delisted，并发送通知给用户
    """
    if not reason:
        reason = "商品经管理员审核不符合平台规范，已被强制下架，请修改后重新发布"
    
    try:
        success = await crud.force_delist_item(item_id=item_id, admin_id=admin_id, reason=reason)
        if success:
            return {
                'success': True,
                'message': f"商品 {item_id} 已成功强制下架，用户已收到通知",
            }
        else:
            raise HTTPException(status_code=404, detail=f"商品 {item_id} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"强制下架失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ✅ 训练任务管理器（内存中跟踪状态+进度+日志）
# ============================================================
_training_jobs: dict = {}  # job_id → {status, progress, logs, ...}
_weekly_scheduler_task: Optional[asyncio.Task] = None

def _get_job_id(model_name: str) -> str:
    return f"{model_name}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"


# ============================================================
# 4. 模型训练接口 —— 触发模型训练任务
# ============================================================
@router.post("/admin/model/train")
async def trigger_model_training(
    model_name: str = Query(default="yolo", description="模型名称: yolo/defect"),
    epochs: int = Query(default=10, ge=1, le=100, description="训练轮数"),
    admin_id: int = Depends(get_current_admin),
):
    """
    触发模型训练任务（管理员专用）

    使用错误数据（hard_cases）对模型进行微调训练
    """
    logger.info(f"🚀 管理员触发模型训练: model={model_name}, epochs={epochs}, admin={admin_id}")

    try:
        hard_cases_stats = await crud.get_hard_cases_stats()
        disagreement_stats = await crud.get_model_disagreements_stats()

        untrained_cases_count = hard_cases_stats.get('unfixed', 0) + disagreement_stats.get('unused', 0)

        if untrained_cases_count == 0:
            return {
                'success': True,
                'message': '当前没有可用的训练数据，请先积累更多错误案例',
                'stats': {
                    'hard_cases': hard_cases_stats,
                    'disagreements': disagreement_stats,
                },
            }

        import sys

        training_script = os.path.join(settings.BASE_DIR, "train", "train.py")
        if model_name == 'defect':
            training_script = os.path.join(settings.BASE_DIR, "trainzui", "train2", "train.py")

        if not os.path.exists(training_script):
            return {
                'success': True,
                'message': f"训练脚本不存在: {training_script}",
                'stats': {
                    'hard_cases': hard_cases_stats,
                    'disagreements': disagreement_stats,
                },
            }

        allowed_models = {'yolo', 'defect'}
        if model_name not in allowed_models:
            raise HTTPException(status_code=400, detail=f"不支持的模型: {model_name}，可选: {', '.join(allowed_models)}")

        job_id = _get_job_id(model_name)
        _training_jobs[job_id] = {
            'job_id': job_id,
            'model_name': model_name,
            'epochs': epochs,
            'status': 'starting',
            'progress': 0,
            'started_at': dt.datetime.now().isoformat(),
            'logs': [],
            'pid': None,
        }

        process = await asyncio.create_subprocess_exec(
            sys.executable, training_script,
            f"--epochs={epochs}",
            f"--model={model_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(settings.BASE_DIR),
        )

        _training_jobs[job_id]['pid'] = process.pid
        _training_jobs[job_id]['status'] = 'running'

        async def _reap():
            job = _training_jobs.get(job_id)
            try:
                # 模拟进度（实际项目可解析训练脚本输出获取真实进度）
                for pct in range(10, 100, 15):
                    await asyncio.sleep(30)  # 每30秒更新一次
                    if job: job['progress'] = min(pct, 95)

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=3600
                )
                if job:
                    if process.returncode != 0:
                        job['status'] = 'failed'
                        job['progress'] = 0
                        err_msg = stderr.decode("utf-8", errors="replace")[:500] if stderr else '未知错误'
                        job['logs'].append(f'[ERROR] {err_msg}')
                        logger.error(f"训练 {job_id} 失败: {err_msg}")
                    else:
                        job['status'] = 'completed'
                        job['progress'] = 100
                        job['completed_at'] = dt.datetime.now().isoformat()
                        out_msg = stdout.decode("utf-8", errors="replace")[:500] if stdout else '训练完成'
                        job['logs'].append(f'[OK] {out_msg}')
                        logger.info(f"训练 {job_id} 完成")
            except asyncio.TimeoutError:
                if job:
                    job['status'] = 'timeout'
                    job['logs'].append('[ERROR] 训练超时(>1小时)')
                process.kill()
                await process.wait()
            except Exception as e:
                if job:
                    job['status'] = 'failed'
                    job['logs'].append(f'[ERROR] {str(e)}')

        asyncio.create_task(_reap())

        return {
            'success': True,
            'job_id': job_id,
            'message': f"训练任务已启动",
            'stats': {
                'hard_cases': hard_cases_stats,
                'disagreements': disagreement_stats,
            },
            'training_config': {
                'model_name': model_name,
                'epochs': epochs,
            },
        }

    except Exception as e:
        logger.error(f"触发训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 4b. 训练状态查询 —— 实时进度
# ============================================================
@router.get("/admin/model/train/status")
async def get_training_status(
    admin_id: int = Depends(get_current_admin),
):
    """获取当前训练任务的状态和进度"""
    jobs = list(_training_jobs.values())
    # 清理7天前的旧任务
    cutoff = dt.datetime.now() - dt.timedelta(days=7)
    for jid in list(_training_jobs.keys()):
        j = _training_jobs[jid]
        started = dt.datetime.fromisoformat(j['started_at']) if j.get('started_at') else None
        if started and started < cutoff and j['status'] in ('completed', 'failed', 'timeout'):
            del _training_jobs[jid]

    active = [j for j in jobs if j['status'] in ('starting', 'running')]
    recent = [j for j in jobs if j['status'] in ('completed', 'failed', 'timeout')][:5]

    return {
        'success': True,
        'active_jobs': active,
        'recent_jobs': recent,
        'has_running': len(active) > 0,
    }


# ============================================================
# 4c. 每周自动训练调度器
# ============================================================
async def _run_weekly_training():
    """后台每周训练调度器 —— 每周一凌晨2点自动执行"""
    while True:
        now = dt.datetime.now()
        # 计算到下一个周一 2:00 AM 的秒数
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 2:
            days_until_monday = 7  # 已经过了周一2点，等下周一
        next_monday = now.replace(hour=2, minute=0, second=0, microsecond=0) + dt.timedelta(days=days_until_monday)
        wait_seconds = max(60, (next_monday - now).total_seconds())

        logger.info(f"⏰ 每周训练调度: 下次执行 {next_monday.isoformat()} (等待 {wait_seconds/3600:.1f} 小时)")
        await asyncio.sleep(wait_seconds)

        # 检查是否有可用训练数据
        try:
            hard_stats = await crud.get_hard_cases_stats()
            disagree_stats = await crud.get_model_disagreements_stats()
            total = hard_stats.get('unfixed', 0) + disagree_stats.get('unused', 0)

            if total > 0:
                logger.info(f"📅 每周自动训练触发: {total} 条可用数据")
                for model in ('yolo', 'defect'):
                    try:
                        job_id = _get_job_id(model)
                        _training_jobs[job_id] = {
                            'job_id': job_id, 'model_name': model, 'epochs': 20,
                            'status': 'running', 'progress': 0,
                            'started_at': dt.datetime.now().isoformat(),
                            'logs': ['[AUTO] 每周自动训练'], 'pid': None,
                        }
                        script = os.path.join(settings.BASE_DIR, "train" if model == 'yolo' else "trainzui/train2", "train.py")
                        proc = await asyncio.create_subprocess_exec(
                            'python', script, f'--epochs=20', f'--model={model}',
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                            cwd=str(settings.BASE_DIR),
                        )
                        _training_jobs[job_id]['pid'] = proc.pid
                        asyncio.create_task(_auto_reap(job_id, proc))
                    except Exception as e:
                        logger.error(f"自动训练 {model} 失败: {e}")
            else:
                logger.info(f"📅 每周自动训练跳过: 无可用训练数据")
        except Exception as e:
            logger.error(f"每周调度器异常: {e}")


async def _auto_reap(job_id: str, process):
    """自动训练的回收任务"""
    job = _training_jobs.get(job_id)
    try:
        await asyncio.wait_for(process.communicate(), timeout=3600)
        if job:
            job['status'] = 'completed'
            job['progress'] = 100
            job['logs'].append('[AUTO] 每周训练完成')
    except Exception as e:
        if job:
            job['status'] = 'failed'
            job['logs'].append(f'[AUTO] 失败: {e}')


def start_weekly_scheduler():
    """启动每周训练调度器（在 FastAPI startup 中调用）"""
    global _weekly_scheduler_task
    if _weekly_scheduler_task is None or _weekly_scheduler_task.done():
        _weekly_scheduler_task = asyncio.create_task(_run_weekly_training())
        logger.info("✅ 每周训练调度器已启动")


# ============================================================
# 5. 模型指标接口 —— 获取模型训练准确率等指标
# ============================================================
@router.get("/admin/model/metrics")
async def get_model_metrics(
    model_name: Optional[str] = Query(default=None, description="模型名称筛选"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取模型训练指标（管理员专用）
    
    返回模型训练的准确率、精确率、召回率、F1分数等指标
    """
    try:
        metrics = await crud.get_model_metrics(model_name=model_name, limit=limit, offset=offset)
        stats = await crud.get_model_metrics_stats(model_name=model_name)
        
        return {
            'success': True,
            'metrics': metrics,
            'count': len(metrics),
            'stats': stats,
        }
    except Exception as e:
        logger.error(f"获取模型指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 6. 模型指标统计接口 —— 获取模型训练统计信息
# ============================================================
@router.get("/admin/model/metrics/stats")
async def get_model_metrics_stats(
    model_name: Optional[str] = Query(default=None, description="模型名称筛选"),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取模型训练指标统计（管理员专用）
    
    返回模型训练的总体统计信息
    """
    try:
        stats = await crud.get_model_metrics_stats(model_name=model_name)
        return {
            'success': True,
            **stats,
        }
    except Exception as e:
        logger.error(f"获取模型指标统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 7. 系统数据统计接口 —— 展示项目整体数据情况
# ============================================================
@router.get("/admin/system/stats")
async def get_system_stats(
    admin_id: int = Depends(get_current_admin),
):
    """
    获取系统数据统计（管理员专用）
    
    返回项目整体数据情况，包括用户数、商品数、错误案例数等
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT COUNT(*) as count FROM users")
                user_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM published_items")
                item_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM published_items WHERE status = 'published'")
                published_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM published_items WHERE status = 'sold'")
                sold_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM hard_cases")
                hard_case_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM model_disagreements")
                disagreement_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM ai_audit_logs")
                audit_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM notifications")
                notification_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(DISTINCT category) as count FROM category_brands")
                category_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM category_brands")
                brand_count = await cur.fetchone()
                
                await cur.execute("SELECT COUNT(*) as count FROM model_metrics")
                metric_count = await cur.fetchone()

        hard_cases_stats = await crud.get_hard_cases_stats()
        model_disagreements_stats = await crud.get_model_disagreements_stats()
        model_metrics_stats = await crud.get_model_metrics_stats()

        return {
            'success': True,
            'overview': {
                'users': user_count['count'] if user_count else 0,
                'total_items': item_count['count'] if item_count else 0,
                'published_items': published_count['count'] if published_count else 0,
                'sold_items': sold_count['count'] if sold_count else 0,
                'categories': category_count['count'] if category_count else 0,
                'brands': brand_count['count'] if brand_count else 0,
                'audit_logs': audit_count['count'] if audit_count else 0,
                'notifications': notification_count['count'] if notification_count else 0,
                'model_training_runs': metric_count['count'] if metric_count else 0,
            },
            'model_performance': {
                'hard_cases': hard_cases_stats,
                'disagreements': model_disagreements_stats,
                'metrics': model_metrics_stats,
            },
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 8. 错误案例管理接口 —— 获取错误案例列表
# ============================================================
@router.get("/admin/hard-cases")
async def get_hard_cases(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_fixed: Optional[bool] = Query(default=None, description="是否已修复"),
    sort_by: str = Query(default="created_at", description="排序字段"),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取错误案例列表（管理员专用）
    
    返回模型分类错误的数据，用于分析和训练
    """
    try:
        is_fixed_value = None if is_fixed is None else (1 if is_fixed else 0)
        if is_fixed_value is not None:
            cases = await crud.get_hard_cases(limit=limit, offset=offset, is_fixed=bool(is_fixed_value), sort_by=sort_by)
        else:
            cases = await crud.get_hard_cases(limit=limit, offset=offset, is_fixed=False, sort_by=sort_by)
        
        stats = await crud.get_hard_cases_stats()
        
        return {
            'success': True,
            'cases': cases,
            'count': len(cases),
            'stats': stats,
        }
    except Exception as e:
        logger.error(f"获取错误案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 9. 标记错误案例已修复接口
# ============================================================
@router.post("/admin/hard-cases/{case_id}/mark-fixed")
async def mark_hard_case_fixed(
    case_id: int,
    admin_id: int = Depends(get_current_admin),
):
    """
    标记错误案例已修复（管理员专用）
    
    将错误案例标记为已修复，不再用于训练
    """
    try:
        success = await crud.mark_hard_case_fixed(case_id)
        if success:
            return {
                'success': True,
                'message': f"错误案例 {case_id} 已标记为已修复",
            }
        else:
            raise HTTPException(status_code=404, detail=f"错误案例 {case_id} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记错误案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 10. 用户通知管理接口 —— 获取用户通知列表
# ============================================================
@router.get("/admin/notifications")
async def get_user_notifications(
    user_id: Optional[int] = Query(default=None, description="用户ID筛选"),
    limit: int = Query(default=50, ge=1, le=100),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取用户通知列表（管理员专用）
    
    返回用户的通知记录，用于监控和管理
    """
    try:
        if user_id:
            notifications = await crud.get_notifications(user_id=user_id, limit=limit)
        else:
            pool = await get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        """SELECT n.id, n.user_id, n.item_id, n.type, n.title, n.message, 
                                  n.is_read, n.created_at, u.username
                           FROM notifications n
                           JOIN users u ON n.user_id = u.id
                           ORDER BY n.created_at DESC
                           LIMIT %s""",
                        (limit,)
                    )
                    notifications = await cur.fetchall()
        
        return {
            'success': True,
            'notifications': notifications,
            'count': len(notifications),
        }
    except Exception as e:
        logger.error(f"获取通知列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 11. 品类品牌管理接口 —— 获取品类品牌列表
# ============================================================
@router.get("/admin/categories")
async def get_categories(
    admin_id: int = Depends(get_current_admin),
):
    """
    获取品类列表（管理员专用）
    
    返回平台所有品类及其品牌信息
    """
    try:
        categories = await crud.get_categories()
        category_brand_map = {}
        for category in categories:
            brands = await crud.get_brands_by_category(category)
            category_brand_map[category] = brands
        
        return {
            'success': True,
            'categories': categories,
            'category_brands': category_brand_map,
            'total_categories': len(categories),
            'total_brands': sum(len(brands) for brands in category_brand_map.values()),
        }
    except Exception as e:
        logger.error(f"获取品类列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 12. 添加品类品牌接口
# ============================================================
@router.post("/admin/categories/add")
async def add_category_brand(
    category: str = Query(..., description="品类名称"),
    brand: str = Query(..., description="品牌名称"),
    admin_id: int = Depends(get_current_admin),
):
    """
    添加品类品牌关联（管理员专用）
    
    向平台添加新的品类品牌组合
    """
    try:
        result = await crud.insert_category_brand(category=category, brand=brand)
        if result:
            return {
                'success': True,
                'message': f"已添加品类品牌关联: {category} - {brand}",
                'id': result,
            }
        else:
            return {
                'success': True,
                'message': f"品类品牌关联已存在: {category} - {brand}",
            }
    except Exception as e:
        logger.error(f"添加品类品牌失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 13. 用户管理接口 —— 获取用户列表
# ============================================================
@router.get("/admin/users")
async def get_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: Optional[str] = Query(default=None, description="角色筛选: user/admin"),
    admin_id: int = Depends(get_current_admin),
):
    """
    获取用户列表（管理员专用）
    
    返回平台用户信息，支持按角色筛选
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = "SELECT id, username, role, status, email, phone, created_at, last_login FROM users WHERE 1=1"
                params = []
                
                if role:
                    sql += " AND role = %s"
                    params.append(role)
                
                sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                await cur.execute(sql, params)
                users = await cur.fetchall()
        
        return {
            'success': True,
            'users': users,
            'count': len(users),
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 13b. 管理员创建用户
# ============================================================
@router.post("/admin/users")
async def create_user(
    payload: RegisterRequest,
    admin_id: int = Depends(get_current_admin),
):
    """管理员创建用户"""
    username = payload.username.strip()
    password = payload.password
    role = payload.role or 'user'
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    ok, uid, msg = await crud.register_user(username, password, role)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {'success': True, 'user_id': uid, 'message': msg}


# ============================================================
# 13c. 管理员删除用户
# ============================================================
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_id: int = Depends(get_current_admin),
):
    """管理员删除用户（不允许删除自己）"""
    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
    return {'success': True, 'message': '用户已删除'}


# ============================================================
# 13d. 管理员禁用/启用用户（强制注销）
# ============================================================
@router.post("/admin/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    admin_id: int = Depends(get_current_admin),
):
    """切换用户状态：正常 ↔ 禁用（禁用后用户无法登录，相当于强制注销）"""
    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT status FROM users WHERE id = %s", (user_id,))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            new_status = 'disabled' if row['status'] == 'active' else 'active'
            await cur.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
    return {'success': True, 'status': new_status, 'message': f'用户已{new_status}'}


# ============================================================
# 14. 同步所有已发布商品到 Qdrant
# ============================================================
@router.post("/admin/sync-qdrant")
async def sync_qdrant(
    admin_id: int = Depends(get_current_admin),
):
    """同步所有已发布商品到向量数据库"""
    from PIL import Image as PILImage
    from app.ml.clip_extractor import get_extractor
    from app.ml.qdrant_client import get_qdrant

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, original_image_url, ai_generated_title, suggested_price,
                          category, brand, model
                   FROM published_items
                   WHERE status = 'published' AND original_image_url IS NOT NULL
                   AND original_image_url != ''"""
            )
            items = await cur.fetchall()

    qdrant = get_qdrant()
    extractor = get_extractor()
    indexed, skipped, failed = 0, 0, 0

    for item in items:
        try:
            img_path = item['original_image_url']
            pil_img = None
            if img_path.startswith('/static/'):
                local_path = settings.BASE_DIR / img_path.lstrip('/')
                if local_path.exists():
                    pil_img = PILImage.open(local_path)

            if pil_img is None:
                failed += 1
                continue

            vector = extractor.extract_image(pil_img)
            qdrant.add_item(item['id'], vector, {
                'title': item.get('ai_generated_title', ''),
                'category': item.get('category', ''),
                'price': float(item.get('suggested_price', 0) or 0),
            })
            indexed += 1
        except Exception as e:
            logger.error(f"同步商品 {item['id']} 失败: {e}")
            failed += 1

    return {
        'success': True,
        'total': len(items),
        'indexed': indexed,
        'failed': failed,
        'message': f'已索引 {indexed} 件，失败 {failed} 件',
    }
