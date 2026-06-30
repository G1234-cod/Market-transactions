"""GET /api/v1/history — 查询发布历史 + POST /api/v1/history/save — 保存发布记录 + 下架/发布操作"""
import logging
import io
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status, Request
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


def build_image_url(image_url: str, request: Optional[Request] = None) -> str:
    """
    构建完整的图片 URL（统一处理函数）
    - 生产环境通过 Cloudflare Tunnel 自动获取正确域名
    - 自动剥离旧数据中硬编码的 http://localhost 前缀

    Args:
        image_url: 原始图片路径（相对路径或完整URL）
        request: FastAPI Request 对象（可选，用于获取正确的域名）

    Returns:
        str: 完整图片URL
    """
    if not image_url:
        return ""

    # ✅ 生产环境（非本地访问）：剥离旧数据中硬编码的 localhost 前缀
    if image_url.startswith("http://localhost"):
        from urllib.parse import urlparse
        is_local = True
        if request:
            host = request.headers.get("X-Forwarded-Host") or request.url.hostname or ""
            is_local = host in ("localhost", "127.0.0.1") or host.startswith("localhost:")
        if not is_local:
            image_url = image_url[len("http://localhost"):]
            # 去掉可能残留的端口号 :8000
            if image_url.startswith(":8000"):
                image_url = image_url[5:]

    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url

    base = get_base_url(request) if request else get_base_url()

    if image_url.startswith(f"{settings.STATIC_PREFIX}/"):
        return f"{base}{image_url}"

    return get_static_url(image_url, request)


@router.get("/history")
async def get_history(
    request: Request,
    user_id: Optional[int] = Depends(get_current_user_optional),  # ✅ 可选认证
):
    """查询当前用户的发布记录列表"""
    if user_id is None:
        return {"items": []}
    rows = await crud.get_history(user_id)
    items = []
    for r in rows:
        img_url = build_image_url(r.get("original_image_url", ""), request)
        
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

