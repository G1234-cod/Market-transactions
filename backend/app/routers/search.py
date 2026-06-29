"""
以图搜图 + 以文搜图 API
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from PIL import Image
import io
import json
import logging
import httpx

from app.ml.clip_extractor import get_extractor
from app.ml.qdrant_client import get_qdrant
from app.db import crud
from app.db.connection import get_pool
from app.config import get_static_url, get_base_url
from app.dependencies import get_current_user, get_current_user_optional
from app.utils.file_validator import validate_upload_file
from app.config import settings
import re

logger = logging.getLogger(__name__)

router = APIRouter(tags=["以图搜图"])

# ✅ 搜索参数限制
MAX_TOP_K = 100
DEFAULT_TOP_K = 10


def build_image_url(image_url: str) -> str:
    """构建完整的图片 URL"""
    if not image_url:
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    if image_url.startswith(f"{settings.STATIC_PREFIX}/"):
        return f"{get_base_url()}{image_url}"
    return get_static_url(image_url)


# ✅ SSRF 防护：验证 URL 是否安全
import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    'localhost', '127.0.0.1', '0.0.0.0', '::1',
    '169.254.169.254',  # AWS metadata
    'metadata.google.internal',  # GCP metadata
}

def _is_safe_url(url: str) -> bool:
    """检查 URL 是否可安全访问（防 SSRF）"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        # 阻止已知敏感主机名
        if hostname.lower() in _BLOCKED_HOSTS:
            return False
        # 阻止私有/内部 IP 范围
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast:
                return False
        except ValueError:
            pass  # 非 IP 地址（域名），DNS 解析由 httpx 处理
        return True
    except Exception:
        return False


@router.post("/search/image")
async def search_by_image(
    image: UploadFile = File(...),
    top_k: int = Form(10, ge=1, le=MAX_TOP_K),  # ✅ 添加范围验证
    filter_category: str = Form(default=""),
    user_id: int = Depends(get_current_user_optional),
):
    """
    以图搜图：上传图片，返回相似商品列表

    Args:
        top_k: 返回结果数量 (1-100)
    """
    try:
        # ✅ 文件上传校验（修复：之前缺少验证）
        try:
            content, safe_filename = await validate_upload_file(
                file=image,
                max_size=settings.MAX_UPLOAD_SIZE,
                check_content=True
            )
        except HTTPException:
            await image.seek(0)
            raise
        except Exception as e:
            await image.seek(0)
            raise HTTPException(status_code=400, detail=f"文件验证失败: {str(e)}")

        pil_image = Image.open(io.BytesIO(content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        qdrant = get_qdrant()
        results = qdrant.search(
            vector=vector,
            top_k=top_k,
            filter_category=filter_category if filter_category else None,
            score_threshold=0.7,
        )

        # ✅ 批量查询商品详情（避免 N+1 查询）
        result_ids = [r["id"] for r in results]
        items_map = await crud.get_items_by_ids(result_ids)

        items = []
        for r in results:
            item_id = r["id"]
            score = r["score"]
            item = items_map.get(item_id)

            if item and item.get('status') == 'published':
                img_url = build_image_url(item.get("original_image_url", ""))
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': img_url,
                    'category': item.get('category'),
                    'similarity': round(score, 4)
                })

        return {
            'success': True,
            'results': items,
            'count': len(items)
        }

    except Exception as e:
        logger.error(f"以图搜图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/text")
async def search_by_text(
    text: str = Form(..., description="商品描述文本"),
    top_k: int = Form(10, ge=1, le=MAX_TOP_K),  # ✅ 添加范围验证
    category: Optional[str] = Form(None, description="筛选品类（可选）"),
    user_id: int = Depends(get_current_user_optional),
):
    """
    以文搜图：输入文字描述，返回匹配的商品列表
    
    Args:
        top_k: 返回结果数量 (1-100)
    """
    try:
        # 1. 提取文本特征向量
        extractor = get_extractor()
        vector = extractor.extract_text(text)

        # 2. Qdrant 检索
        qdrant = get_qdrant()
        results = qdrant.search(
            vector=vector,
            top_k=top_k,
            filter_category=category if category else None,
        )

        # 3. 查询商品详情（批量查询，避免 N+1）
        items = []
        result_ids = [r["id"] for r in results]
        items_map = await crud.get_items_by_ids(result_ids)

        for r in results:
            item_id = r["id"]
            score = r["score"]
            item = items_map.get(item_id)

            if item and item.get('status') == 'published':
                img_url = build_image_url(item.get("original_image_url", ""))
                items.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', '未命名商品'),
                    'price': float(item['suggested_price']) if item['suggested_price'] else None,
                    'image_url': img_url,
                    'category': item.get('category'),
                    'similarity': round(score, 4)
                })

        return {
            'success': True,
            'results': items,
            'count': len(items)
        }

    except Exception as e:
        logger.error(f"以文搜图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/index")
async def add_to_index(
    item_id: int = Form(...),
    image_url: str = Form(...),
    title: str = Form(""),
    category: str = Form(""),
    user_id: int = Depends(get_current_user),
):
    """商品上架时加入索引"""
    try:
        full_url = build_image_url(image_url)
        if not full_url:
            raise HTTPException(status_code=400, detail="无效的图片URL")

        # ✅ SSRF 防护：验证目标 URL 安全
        if not _is_safe_url(full_url):
            raise HTTPException(status_code=400, detail="不允许访问的图片URL")

        # 使用 httpx.AsyncClient 异步下载
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(full_url)
            response.raise_for_status()
            content = response.content

        pil_image = Image.open(io.BytesIO(content))

        extractor = get_extractor()
        vector = extractor.extract_image(pil_image)

        payload = {
            'title': title,
            'category': category,
        }
        qdrant = get_qdrant()
        qdrant.add_item(item_id, vector, payload)

        return {
            'success': True,
            'item_id': item_id,
            'message': '已加入索引'
        }

    except httpx.TimeoutException:
        logger.error(f"⏱️ 图片下载超时: {image_url}")
        raise HTTPException(status_code=408, detail="图片下载超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ 图片下载失败 (HTTP {e.response.status_code}): {image_url}")
        raise HTTPException(status_code=400, detail=f"图片下载失败: HTTP {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加入索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/stats")
async def search_stats():
    """获取索引统计信息"""
    try:
        qdrant = get_qdrant()
        return {
            'total_items': qdrant.count(),
            'collection': qdrant.collection_name,
            'vector_size': qdrant.vector_size,
            'host': qdrant.host,
            'port': qdrant.port
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/by-filter")
async def search_by_filter(
    category: Optional[str] = Form(None, description="品类筛选"),
    brand: Optional[str] = Form(None, description="品牌筛选"),
    model: Optional[str] = Form(None, description="型号关键词"),
    page: int = Form(1, ge=1, description="页码"),
    page_size: int = Form(20, ge=1, le=100, description="每页数量"),
):
    """
    按类别、品牌、型号直接搜索商品（数据库查询，非向量搜索）

    支持级联筛选：品类 → 品牌 → 型号
    """
    try:
        items, total = await crud.search_items_by_filter(
            category=category,
            brand=brand,
            model=model,
            status="published",
            page=page,
            page_size=page_size,
        )

        # 构建返回结果
        results = []
        for item in items:
            img_url = build_image_url(item.get("original_image_url", ""))
            results.append({
                'id': item['id'],
                'title': item.get('ai_generated_title', '未命名商品'),
                'desc': item.get('ai_generated_desc', ''),
                'price': float(item['suggested_price']) if item['suggested_price'] else None,
                'image_url': img_url,
                'category': item.get('category'),
                'brand': item.get('brand'),
                'model': item.get('model'),
                'condition': item.get('condition'),
                'username': item.get('username'),
                'views': item.get('views', 0),
                'created_at': str(item.get('created_at', '')),
            })

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            'success': True,
            'results': results,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        }

    except Exception as e:
        logger.error(f"按条件搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/categories-brands")
async def get_categories_and_brands(
    category: Optional[str] = None,
):
    """
    获取品类列表及对应品牌（用于级联选择器）

    Args:
        category: 指定品类时，返回该品类下的品牌；否则返回所有品类
    """
    try:
        if category:
            brands = await crud.get_brands_by_category(category)
            return {
                'success': True,
                'category': category,
                'brands': brands,
            }
        else:
            categories = await crud.get_categories()
            return {
                'success': True,
                'categories': categories,
            }
    except Exception as e:
        logger.error(f"获取品类品牌失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/available-models")
async def get_available_models(
    category: Optional[str] = None,
    brand: Optional[str] = None,
):
    """
    获取可搜索的型号列表（用于级联选择器）

    Args:
        category: 品类筛选
        brand: 品牌筛选
    """
    try:
        models = await crud.get_available_models_by_category_brand(category, brand)
        return {
            'success': True,
            'models': models,
        }
    except Exception as e:
        logger.error(f"获取型号列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/health")
async def search_health():
    """健康检查"""
    try:
        extractor = get_extractor()
        qdrant = get_qdrant()
        return {
            "status": "healthy",
            "clip_model": extractor.model_name,
            "clip_device": extractor.device,
            "clip_pretrained": extractor.pretrained,
            "qdrant_collection": qdrant.collection_name,
            "qdrant_count": qdrant.count()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )


# ============================================================
# DeepSeek 语义搜索 —— 模糊匹配+同义词+语义理解
# ============================================================
@router.post("/search/semantic")
async def search_semantic(
    text: str = Form(..., description="搜索关键词"),
    top_k: int = Form(10, ge=1, le=50),
    user_id: int = Depends(get_current_user_optional),
):
    """
    DeepSeek 语义搜索：用自然语言描述找商品

    支持模糊匹配：搜"电风扇"可以找到标注为"风扇"的商品
    """
    try:
        # 1. 获取所有已发布商品
        import aiomysql
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT p.id, p.ai_generated_title, p.ai_generated_desc, p.category,
                              p.brand, p.model, p.suggested_price, p.original_image_url,
                              u.username
                       FROM published_items p
                       JOIN users u ON p.user_id = u.id
                       WHERE p.status = 'published'
                       ORDER BY p.created_at DESC
                       LIMIT 200"""
                )
                all_items = await cur.fetchall()

        if not all_items:
            return {'success': True, 'results': [], 'count': 0, 'message': '暂无已发布商品'}

        # 2. 用 DeepSeek 进行语义匹配（按品类/品牌/型号匹配，不用标题）
        item_list = "\n".join([
            f"ID:{item['id']} | 品类:{item.get('category','')} | 品牌:{item.get('brand','')} | 型号:{item.get('model','')}"
            for item in all_items
        ])

        from app.llm.deepseek_client import DeepSeekClient
        ds = DeepSeekClient()
        prompt = f"""用户想找："{text}"

在售商品：
{item_list}

找出匹配的商品（最多{top_k}个）。注意：
- 品类、品牌、型号任意一个匹配即可
- 模糊匹配：搜"风扇"要匹配到"电风扇""落地扇"；搜"苹果"匹配"Apple"；搜"耳机"匹配"蓝牙耳机""无线耳机"
- 只要有关联就给分，不要严格精确匹配

返回JSON数组：
```json
[{{"id": 1, "score": 0.9, "reason": "品类匹配"}}]
```"""

        raw = await ds.chat([{"role": "user", "content": prompt}])

        # 3. 解析 DeepSeek 响应
        try:
            text_part = raw
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            if m:
                text_part = m.group(1)
            start = text_part.find('[')
            if start >= 0:
                depth = 0
                for i in range(start, len(text_part)):
                    if text_part[i] == '[': depth += 1
                    elif text_part[i] == ']':
                        depth -= 1
                        if depth == 0:
                            text_part = text_part[start:i+1]
                            break
            matches = json.loads(text_part)
        except Exception:
            # 兜底：关键词匹配
            matches = []
            query_lower = text.lower()
            for item in all_items:
                title = (item.get('ai_generated_title') or '').lower()
                cat = (item.get('category') or '').lower()
                brand = (item.get('brand') or '').lower()
                model = (item.get('model') or '').lower()
                if query_lower in title or query_lower in cat or query_lower in f"{brand} {model}":
                    matches.append({"id": item['id'], "score": 0.7})

        # 4. 构建返回结果
        item_map = {i['id']: i for i in all_items}
        results = []
        for m in matches[:top_k]:
            item = item_map.get(m['id'])
            if item:
                results.append({
                    'id': item['id'],
                    'title': item.get('ai_generated_title', ''),
                    'price': float(item['suggested_price']) if item.get('suggested_price') else None,
                    'image_url': item.get('original_image_url', ''),
                    'category': item.get('category', ''),
                    'brand': item.get('brand', ''),
                    'model': item.get('model', ''),
                    'username': item.get('username', ''),
                    'score': m.get('score', 0.5),
                    'reason': m.get('reason', ''),
                })

        return {
            'success': True,
            'results': results,
            'count': len(results),
            'query': text,
        }

    except Exception as e:
        logger.error(f"语义搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))