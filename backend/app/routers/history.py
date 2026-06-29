"""GET /api/v1/history — 查询发布历史 + POST /api/v1/history/save — 保存发布记录 + 下架/发布操作 + 重新评估"""
import logging
import io
import time
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status
from PIL import Image
import httpx

from app.models.schemas import HistoryItem, GenerateSaveRequest
from app.db import crud
from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.config import get_static_url, get_base_url, settings
from app.dependencies import get_current_user_optional, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["发布历史"])


def build_image_url(image_url: str) -> str:
    """
    构建完整的图片 URL（统一处理函数）
    
    Args:
        image_url: 原始图片路径（相对路径或完整URL）
    
    Returns:
        str: 完整图片URL
    """
    if not image_url:
        return ""
    
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    
    if image_url.startswith(f"{settings.STATIC_PREFIX}/"):
        return f"{get_base_url()}{image_url}"
    
    return get_static_url(image_url)


@router.get("/history")
async def get_history(
    user_id: Optional[int] = Depends(get_current_user_optional),  # ✅ 可选认证
):
    """查询当前用户的发布记录列表"""
    if user_id is None:
        return {"items": []}
    rows = await crud.get_history(user_id)
    items = []
    for r in rows:
        img_url = build_image_url(r.get("original_image_url", ""))
        
        items.append(HistoryItem(
            id=r["id"],
            user_id=r["user_id"],
            original_image_url=img_url,
            ai_generated_title=r["ai_generated_title"],
            ai_generated_desc=r.get("ai_generated_desc"),
            suggested_price=float(r["suggested_price"]) if r.get("suggested_price") else None,
            status=r["status"],
            category=r.get("category"),
            condition=r.get("condition"),  # ✅ 使用 condition
            views=r.get("views", 0),
            created_at=str(r["created_at"]),
        ))
    return {"items": items}


@router.post("/history/save")
async def save_history(
    payload: GenerateSaveRequest,
    user_id: Optional[int] = Depends(get_current_user_optional),  # ✅ 可选认证
):
    """
    保存生成的文案到发布记录（可指定 status: published / draft）
    保存成功后自动加入以图搜图索引
    """
    # ✅ 修复：必须认证，不再静默回退到 user_id=1
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")
    final_user_id = user_id
    item_id = await crud.insert_published_item(
        user_id=final_user_id,
        image_url=payload.image_url,
        title=payload.title,
        desc=payload.desc,
        price=payload.price,
        status=payload.status,
        category=payload.category,
        brand=payload.brand,
        model=payload.model,
        condition=payload.condition,  # ✅ 使用 condition
    )
    
    # 自动加入以图搜图索引（失败不影响保存结果）
    try:
        await add_to_search_index(item_id, payload)
    except Exception as e:
        logger.error(f"自动索引失败: {e}")

    return {"id": item_id, "status": "saved"}


async def add_to_search_index(item_id: int, payload: GenerateSaveRequest):
    """
    将商品添加到以图搜图索引
    
    Args:
        item_id: 商品ID
        payload: 商品数据
    """
    try:
        img_path = payload.image_url

        if not img_path:
            logger.warning(f"⚠️ 商品 {item_id} 图片URL为空，未加入索引")
            return

        # ✅ 本地图片直接从文件系统读取，不走HTTP（避免SSRF拦截localhost）
        pil_img = None
        if img_path.startswith('/static/') or img_path.startswith('static/'):
            local_path = settings.BASE_DIR / img_path.lstrip('/')
            if local_path.exists():
                pil_img = Image.open(local_path)
                logger.info(f"📁 本地图片直接读取: {local_path}")
            else:
                logger.warning(f"⚠️ 本地图片不存在: {local_path}")

        # 兜底：HTTP下载
        if pil_img is None:
            img_url = build_image_url(img_path)
            from urllib.parse import urlparse
            parsed = urlparse(img_url)
            host = (parsed.hostname or '').lower()
            blocked = {'localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254.169.254', 'metadata.google.internal'}
            if host in blocked:
                logger.warning(f"⚠️ 跳过本地地址索引: {img_url}")
                return
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(img_url)
                response.raise_for_status()
                pil_img = Image.open(io.BytesIO(response.content))
        
        extractor = get_extractor()
        vector = extractor.extract_image(pil_img)
        
        qdrant = get_qdrant()
        qdrant.add_item(item_id, vector, {
            'title': payload.title,
            'category': payload.category or '',
            'price': float(payload.price) if payload.price else 0
        })
        logger.info(f"✅ 商品 {item_id} 已自动加入以图搜图索引")
        
    except httpx.TimeoutException:
        logger.error(f"⏱️ 商品 {item_id} 图片下载超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ 商品 {item_id} 图片下载失败 (HTTP {e.response.status_code})")
    except Exception as e:
        logger.error(f"❌ 商品 {item_id} 自动索引失败: {e}")


@router.post("/history/{item_id}/delist")
async def delist_item(
    item_id: int,
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取
):
    """
    下架商品（仅限商品所有者）
    """
    # ✅ 验证商品所有权
    item = await crud.get_item_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")
    
    await crud.update_item_status(item_id, "delisted", user_id)
    
    # 从搜索索引删除
    try:
        qdrant = get_qdrant()
        qdrant.delete_item(item_id)
        logger.info(f"🗑️ 商品 {item_id} 已从搜索索引删除")
    except Exception as e:
        logger.error(f"❌ 删除索引失败: {e}")
    
    return {"status": "delisted"}


@router.post("/history/{item_id}/publish")
async def publish_item(
    item_id: int,
    user_id: int = Depends(get_current_user),  # ✅ 从 JWT 获取
):
    """
    从草稿发布（仅限商品所有者）
    """
    # ✅ 验证商品所有权
    item = await crud.get_item_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")
    
    await crud.update_item_status(item_id, "published")
    
    # 发布时自动加入以图搜图索引（草稿时可能未索引）
    try:
        if item:
            # 构建 payload 用于索引
            payload = GenerateSaveRequest(
                user_id=item["user_id"],
                image_url=item["original_image_url"],
                title=item["ai_generated_title"],
                desc=item.get("ai_generated_desc", ""),
                price=float(item.get("suggested_price", 0)) if item.get("suggested_price") else 0,
                status=item.get("status", "published"),
                category=item.get("category"),
                brand=item.get("brand"),
                model=item.get("model"),
                condition=item.get("condition"),  # ✅ 使用 condition
            )
            await add_to_search_index(item_id, payload)
    except Exception as e:
        logger.error(f"❌ 草稿发布后索引失败: {e}")
    
    return {"status": "published"}


@router.post("/history/{item_id}/sold")
async def mark_sold_item(
    item_id: int,
    user_id: int = Depends(get_current_user),
):
    """
    标记商品为已售出（仅限商品所有者，仅限已发布状态）
    """
    item = await crud.get_item_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")
    if item["status"] != "published":
        raise HTTPException(status_code=400, detail="仅已发布商品可标记为售出")
    
    await crud.update_item_status(item_id, "sold")
    
    # 从搜索索引删除
    try:
        qdrant = get_qdrant()
        qdrant.delete_item(item_id)
        logger.info(f"✅ 商品 {item_id} 已标记为售出并从搜索索引删除")
    except Exception as e:
        logger.error(f"❌ 删除索引失败: {e}")
    
    return {"status": "sold"}


@router.post("/history/{item_id}/reevaluate")
async def reevaluate_item(
    item_id: int,
    user_id: int = Depends(get_current_user),
):
    """
    重新评估商品：使用 DeepSeek 重新生成标题、描述和价格

    会携带之前保存的瑕疵数据一起提交给 DeepSeek，
    让模型结合商品信息和瑕疵情况重新评估。
    """
    # 1. 获取商品数据
    item = await crud.get_item_full_data(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此商品")

    # 2. 获取瑕疵数据
    defect_data = None
    defect_count = item.get("defect_count", 0)
    if item.get("defect_data"):
        try:
            if isinstance(item["defect_data"], str):
                defect_data = json.loads(item["defect_data"])
            else:
                defect_data = item["defect_data"]
        except (json.JSONDecodeError, TypeError):
            defect_data = None

    # 3. 调用 DeepSeek 重新评估
    try:
        from app.llm.deepseek_client import get_deepseek_client

        deepseek = get_deepseek_client()

        # 构建 prompt
        defect_desc = ""
        if defect_data and isinstance(defect_data, list):
            defect_parts = []
            for d in defect_data:
                if isinstance(d, dict):
                    defect_parts.append(
                        f"- {d.get('type_cn', d.get('type', '瑕疵'))} "
                        f"(严重程度: {d.get('severity_label', d.get('severity', '未知'))}, "
                        f"置信度: {int(d.get('confidence', 0) * 100)}%)"
                    )
            if defect_parts:
                defect_desc = "检测到的瑕疵：\n" + "\n".join(defect_parts)

        prompt = f"""请根据以下二手商品信息，重新生成专业的商品标题、描述和建议售价。

商品信息：
- 品类：{item.get('category', '未知')}
- 品牌：{item.get('brand', '未知')}
- 型号：{item.get('model', '未知')}
- 成色：{item.get('condition', '未填写')}
- 瑕疵数量：{defect_count}
{defect_desc}

请以 JSON 格式返回，包含以下字段：
{{
    "title": "商品标题（吸引人且包含关键信息，不超过50字）",
    "description": "商品详细描述（突出卖点和瑕疵说明，不超过200字）",
    "suggested_price": 数字（单位：元，考虑瑕疵后的建议售价）,
    "selling_points": ["卖点1", "卖点2", "卖点3"]
}}

只返回 JSON，不要包含其他文字。"""

        start_time = time.time()
        # ✅ 直接 await async 方法（deepseek.chat 是 async def，无需 run_in_executor）
        response = await deepseek.chat(prompt)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(f"DeepSeek 重新评估响应: {response[:300]}")

        # 4. 解析 DeepSeek 响应
        try:
            # 尝试直接解析
            result = json.loads(response)
        except json.JSONDecodeError:
            # ✅ 修复：使用平衡括号匹配提取 JSON（支持嵌套对象）
            start = response.find('{')
            if start >= 0:
                depth = 0
                end = start
                for i in range(start, len(response)):
                    if response[i] == '{':
                        depth += 1
                    elif response[i] == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                try:
                    result = json.loads(response[start:end])
                except json.JSONDecodeError:
                    result = {
                        "title": item.get("ai_generated_title", ""),
                        "description": item.get("ai_generated_desc", ""),
                        "suggested_price": float(item.get("suggested_price", 0)) if item.get("suggested_price") else 0,
                        "selling_points": [],
                    }
            else:
                result = {
                    "title": item.get("ai_generated_title", ""),
                    "description": item.get("ai_generated_desc", ""),
                    "suggested_price": float(item.get("suggested_price", 0)) if item.get("suggested_price") else 0,
                    "selling_points": [],
                }

        # 5. 更新商品数据
        await crud.update_item_reevaluation(
            item_id=item_id,
            ai_generated_title=result.get("title", ""),
            ai_generated_desc=result.get("description", ""),
            suggested_price=float(result.get("suggested_price", 0)) if result.get("suggested_price") else None,
        )

        # 6. 记录审计日志
        await crud.insert_audit_log(
            user_id=user_id,
            action_type="reevaluate",
            model_name="DeepSeek",
            input_summary=f"重新评估商品 #{item_id}: {item.get('brand', '')} {item.get('model', '')}",
            raw_ai_response=result,
            execution_time_ms=elapsed_ms,
            status="SUCCESS",
        )

        return {
            "success": True,
            "message": "重新评估完成",
            "item_id": item_id,
            "result": {
                "title": result.get("title", ""),
                "description": result.get("description", ""),
                "suggested_price": result.get("suggested_price", 0),
                "selling_points": result.get("selling_points", []),
            },
        }

    except Exception as e:
        logger.error(f"重新评估失败: {e}")
        # 记录失败日志
        await crud.insert_audit_log(
            user_id=user_id,
            action_type="reevaluate",
            model_name="DeepSeek",
            input_summary=f"重新评估商品 #{item_id}",
            raw_ai_response=None,
            execution_time_ms=0,
            status="FAILED",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"重新评估失败: {str(e)}")