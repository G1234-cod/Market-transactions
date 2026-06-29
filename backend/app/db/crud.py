"""数据库 CRUD 操作"""
import json
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any

import aiomysql

from app.db.connection import get_pool
from app.utils.json_utils import safe_json_dumps


# ============================================================
# users — 用户管理
# ============================================================

import hashlib
import os


def _hash_password(password: str) -> str:
    """PBKDF2 哈希密码"""
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored: str) -> bool:
    """验证密码"""
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return h.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


async def register_user(username: str, password: str) -> tuple[bool, int | None, str]:
    """注册用户。返回 (success, user_id, message)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if await cur.fetchone():
                return False, None, "用户名已被占用"
            pw_hash = _hash_password(password)
            await cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, pw_hash),
            )
            return True, cur.lastrowid, "注册成功"


async def get_user_by_id(user_id: int) -> dict | None:
    """根据ID获取用户信息"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, username, created_at FROM users WHERE id = %s",
                (user_id,)
            )
            return await cur.fetchone()


async def authenticate_user(username: str, password: str) -> tuple[bool, int | None, str]:
    """登录鉴权。返回 (success, user_id, message)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, password_hash FROM users WHERE username=%s",
                (username,),
            )
            row = await cur.fetchone()
            if not row:
                return False, None, "用户不存在"
            if not _verify_password(password, row["password_hash"]):
                return False, None, "密码错误"
            await cur.execute(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (row["id"],)
            )
            return True, row["id"], "登录成功"


# ============================================================
# market_prices — 行情查询
# ============================================================

async def query_price(brand: str, model: str) -> dict | None:
    """三层匹配策略查询行情"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT category, brand, model, avg_price, low_price, high_price, crawled_at "
                "FROM market_prices WHERE brand=%s AND model=%s",
                (brand, model),
            )
            row = await cur.fetchone()
            if row:
                return row

            await cur.execute(
                "SELECT category, brand, model, avg_price, low_price, high_price, crawled_at "
                "FROM market_prices WHERE brand=%s",
                (brand,),
            )
            rows = await cur.fetchall()
            best, best_score = None, 0
            for r in rows:
                score = SequenceMatcher(None, model.lower(), r["model"].lower()).ratio()
                if score > best_score:
                    best_score, best = score, r
            if best and best_score > 0.7:
                return best
            return None


async def upsert_price(
    brand: str, 
    model: str, 
    avg_price: float, 
    low_price: float, 
    high_price: float,
    category: str = "",
    data_source: str = ""
) -> bool:
    """
    更新或插入价格数据（缓存）
    
    Args:
        brand: 品牌
        model: 型号
        avg_price: 均价
        low_price: 最低价
        high_price: 最高价
        category: 品类
        data_source: 数据来源
        
    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO market_prices 
                   (category, brand, model, avg_price, low_price, high_price, 
                    price_unit, data_source, crawled_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                   ON DUPLICATE KEY UPDATE 
                   avg_price = VALUES(avg_price),
                   low_price = VALUES(low_price),
                   high_price = VALUES(high_price),
                   category = COALESCE(VALUES(category), category),
                   data_source = VALUES(data_source),
                   crawled_at = NOW()""",
                (category, brand, model, avg_price, low_price, high_price, 
                 'CNY', data_source)
            )
            await conn.commit()
            return True


async def insert_price_history(
    brand: str,
    model: str,
    avg_price: float,
    low_price: float,
    high_price: float,
    source: str = ""
) -> int:
    """
    插入价格历史记录
    
    Args:
        brand: 品牌
        model: 型号
        avg_price: 均价
        low_price: 最低价
        high_price: 最高价
        source: 数据来源
        
    Returns:
        int: 记录ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO price_history 
                   (brand, model, price, low_price, high_price, price_type, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (brand, model, avg_price, low_price, high_price, 'avg', source)
            )
            await conn.commit()
            return cur.lastrowid


async def get_price_history(brand: str, model: str, limit: int = 50) -> list[dict]:
    """
    获取价格历史记录
    
    Args:
        brand: 品牌
        model: 型号
        limit: 返回数量
        
    Returns:
        list[dict]: 历史记录列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT price, low_price, high_price, source, recorded_at
                   FROM price_history 
                   WHERE brand = %s AND model = %s
                   ORDER BY recorded_at DESC
                   LIMIT %s""",
                (brand, model, limit)
            )
            return await cur.fetchall()


# ============================================================
# published_items — 发布记录
# ============================================================

async def insert_published_item(
    user_id: int,
    image_url: str,
    title: str,
    desc: str,
    price: float,
    status: str = "published",
    category: str = None,
    brand: str = None,
    model: str = None,
    condition: str = None,
) -> int:
    """
    插入发布记录
    
    Args:
        user_id: 用户ID
        image_url: 图片URL
        title: 标题
        desc: 描述
        price: 价格
        status: 状态 (published/draft)
        category: 品类
        brand: 品牌
        model: 型号
        condition: 成色
    
    Returns:
        int: 商品ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO published_items 
                   (user_id, original_image_url, ai_generated_title, 
                    ai_generated_desc, suggested_price, status, category, 
                    brand, model, `condition`) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, image_url, title, desc, price, status, 
                 category, brand, model, condition)
            )
            return cur.lastrowid


async def update_item_status(item_id: int, status: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE published_items SET status=%s WHERE id=%s",
                (status, item_id),
            )


async def get_history(user_id: int) -> list[dict]:
    """获取用户发布历史（含 views）"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, user_id, original_image_url, ai_generated_title,
                          ai_generated_desc, suggested_price, status, category,
                          brand, model, `condition`, views, created_at
                   FROM published_items 
                   WHERE user_id = %s 
                   ORDER BY created_at DESC LIMIT 50""",
                (user_id,)
            )
            return await cur.fetchall()


# 排序字段白名单（防止 SQL 注入）
_MARKET_SORT_COLUMNS = {
    "created_at": "p.created_at",
    "price": "p.suggested_price",
}


async def get_market_items(
    keyword: str = "",
    category: str = "",
    condition: str = "",
    price_min: float = None,
    price_max: float = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    获取商城商品列表（分页 + 排序 + 多维筛选）

    Returns:
        tuple[list[dict], int]: (商品列表, 总条数)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # ============================================================
            # 构建 WHERE 子句
            # ============================================================
            where_parts = ["p.status = 'published'"]
            params: list = []

            if keyword:
                where_parts.append(
                    "(p.ai_generated_title LIKE %s OR p.ai_generated_desc LIKE %s)"
                )
                kw = f"%{keyword}%"
                params.extend([kw, kw])

            if category:
                where_parts.append("p.category = %s")
                params.append(category)

            if condition:
                where_parts.append("p.`condition` LIKE %s")
                params.append(f"%{condition}%")

            if price_min is not None:
                where_parts.append("p.suggested_price >= %s")
                params.append(price_min)

            if price_max is not None:
                where_parts.append("p.suggested_price <= %s")
                params.append(price_max)

            where_clause = " AND ".join(where_parts)

            # ============================================================
            # COUNT 查询
            # ============================================================
            count_sql = (
                "SELECT COUNT(*) AS total FROM published_items p "
                "JOIN users u ON p.user_id = u.id "
                f"WHERE {where_clause}"
            )
            await cur.execute(count_sql, params)
            total_row = await cur.fetchone()
            total = total_row["total"] if total_row else 0

            # ============================================================
            # 排序（白名单映射防注入）
            # ============================================================
            sort_col = _MARKET_SORT_COLUMNS.get(sort_by, "p.created_at")
            order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

            # 价格排序时：NULL 值排最后
            if sort_by == "price":
                null_pos = "DESC" if order_dir == "ASC" else "ASC"
                order_clause = (
                    f"ORDER BY CASE WHEN p.suggested_price IS NULL THEN 1 ELSE 0 END {null_pos}, "
                    f"{sort_col} {order_dir}"
                )
            else:
                order_clause = f"ORDER BY {sort_col} {order_dir}"

            # ============================================================
            # 数据查询（分页）
            # ============================================================
            offset = (page - 1) * page_size
            data_sql = (
                "SELECT p.id, p.user_id, u.username, p.original_image_url, "
                "p.ai_generated_title, p.ai_generated_desc, p.suggested_price, "
                "p.category, p.brand, p.model, p.`condition`, "
                "p.views, p.created_at "
                "FROM published_items p "
                "JOIN users u ON p.user_id = u.id "
                f"WHERE {where_clause} "
                f"{order_clause} "
                "LIMIT %s OFFSET %s"
            )
            await cur.execute(data_sql, params + [page_size, offset])
            items = await cur.fetchall()

            return items, total


# ============================================================
# published_items — 瑕疵数据更新
# ============================================================

async def update_item_defects(
    item_id: int,
    bg_removed_url: str = None,
    annotated_url: str = None,
    defect_count: int = 0,
    defect_data: list = None
):
    """
    更新商品的瑕疵信息
    
    Args:
        item_id: 商品ID
        bg_removed_url: 去背景图URL
        annotated_url: 标注图URL
        defect_count: 瑕疵数量
        defect_data: 瑕疵详细数据列表（含程度信息）
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # ✅ 使用 safe_json_dumps 替代直接 json.dumps
            defect_json = safe_json_dumps(defect_data)
            
            await cur.execute(
                """UPDATE published_items 
                   SET bg_removed_url = COALESCE(%s, bg_removed_url),
                       annotated_url = COALESCE(%s, annotated_url),
                       defect_count = %s,
                       defect_data = %s,
                       updated_at = NOW()
                   WHERE id = %s""",
                (bg_removed_url, annotated_url, defect_count, defect_json, item_id)
            )


async def get_item_by_id(item_id: int) -> dict | None:
    """根据ID获取商品信息（含 views）"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, user_id, original_image_url, bg_removed_url, annotated_url,
                          ai_generated_title, ai_generated_desc, suggested_price,
                          category, brand, model, `condition`, status,
                          views, defect_count, defect_data, created_at
                   FROM published_items WHERE id = %s""",
                (item_id,)
            )
            return await cur.fetchone()


async def get_items_by_ids(item_ids: list[int]) -> dict[int, dict]:
    """
    批量获取商品信息（避免 N+1 查询）

    Args:
        item_ids: 商品ID列表

    Returns:
        dict[int, dict]: {item_id: item_data} 映射
    """
    if not item_ids:
        return {}

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(item_ids))
            await cur.execute(
                f"""SELECT id, user_id, original_image_url, bg_removed_url, annotated_url,
                          ai_generated_title, ai_generated_desc, suggested_price,
                          category, brand, model, `condition`, status,
                          views, defect_count, defect_data, created_at
                   FROM published_items WHERE id IN ({placeholders})""",
                item_ids
            )
            rows = await cur.fetchall()
            return {row['id']: row for row in rows}


# ============================================================
# views 更新操作
# ============================================================

async def increment_views(item_id: int) -> None:
    """增加浏览次数"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE published_items SET views = views + 1 WHERE id = %s",
                (item_id,)
            )


# ============================================================
# hard_cases — 错误数据记录（增强版，支持数据飞轮）
# ============================================================

async def insert_hard_case(
    image_url: str,
    wrong_label: str,
    correct_label: str,
    user_id: int,
    item_id: int = None,
    model_version: str = None,
    confidence: float = 0.0
) -> int:
    """
    插入错误数据到 hard_cases 表
    
    支持幂等性：如果相同 image_url + wrong_label + correct_label 已存在，更新而非插入
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 检查是否已存在（幂等性）
            await cur.execute(
                """SELECT id, retry_count FROM hard_cases 
                   WHERE image_url = %s AND wrong_label = %s AND correct_label = %s""",
                (image_url, wrong_label, correct_label)
            )
            existing = await cur.fetchone()
            
            if existing:
                # 更新已有记录（增加重试计数）
                await cur.execute(
                    """UPDATE hard_cases 
                       SET retry_count = retry_count + 1,
                           updated_at = NOW()
                       WHERE id = %s""",
                    (existing[0],)
                )
                return existing[0]
            
            # 插入新记录
            await cur.execute(
                """INSERT INTO hard_cases 
                   (image_url, wrong_label, correct_label, user_id, item_id, model_version, confidence, created_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                (image_url, wrong_label, correct_label, user_id, item_id, model_version, confidence)
            )
            return cur.lastrowid


async def get_hard_cases(
    limit: int = 100,
    offset: int = 0,
    is_fixed: bool = False,
    sort_by: str = "created_at"
) -> list[dict]:
    """
    获取错误数据列表（用于训练）
    
    Args:
        limit: 返回数量
        offset: 偏移量
        is_fixed: 是否已修复
        sort_by: 排序字段 (created_at, retry_count, confidence)
    
    Returns:
        list: 错误数据列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # ✅ 排序字段白名单映射 — 将用户输入映射到安全的列名
            # 不允许直接将 sort_by 插入 SQL，而是通过 dict 间接查找
            _SORT_COLUMNS = {
                "created_at": "created_at",
                "retry_count": "retry_count",
                "confidence": "confidence",
                "id": "id",
            }
            sort_column = _SORT_COLUMNS.get(sort_by, "created_at")

            await cur.execute(
                f"""SELECT id, image_url, wrong_label, correct_label, user_id,
                          item_id, model_version, confidence, retry_count, is_fixed,
                          created_at, updated_at, fixed_at
                   FROM hard_cases
                   WHERE is_fixed = %s
                   ORDER BY {sort_column} DESC
                   LIMIT %s OFFSET %s""",
                (1 if is_fixed else 0, limit, offset)
            )
            return await cur.fetchall()


async def get_hard_cases_by_item(item_id: int) -> list[dict]:
    """
    获取指定商品的所有错误数据
    
    Args:
        item_id: 商品ID
    
    Returns:
        list: 错误数据列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, image_url, wrong_label, correct_label, user_id, 
                          model_version, confidence, retry_count, is_fixed, created_at
                   FROM hard_cases 
                   WHERE item_id = %s
                   ORDER BY created_at DESC""",
                (item_id,)
            )
            return await cur.fetchall()


async def mark_hard_case_fixed(case_id: int) -> bool:
    """
    标记错误数据已修复（用于训练完成后）
    
    Args:
        case_id: 错误数据ID
    
    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                "UPDATE hard_cases SET is_fixed = 1, fixed_at = NOW() WHERE id = %s",
                (case_id,)
            )
            return result > 0


async def mark_hard_cases_fixed(case_ids: list[int]) -> int:
    """
    批量标记错误数据已修复
    
    Args:
        case_ids: 错误数据ID列表
    
    Returns:
        int: 更新的记录数
    """
    if not case_ids:
        return 0
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(case_ids))
            result = await cur.execute(
                f"UPDATE hard_cases SET is_fixed = 1, fixed_at = NOW() WHERE id IN ({placeholders})",
                case_ids
            )
            return result


async def delete_hard_case(case_id: int) -> bool:
    """
    删除错误数据
    
    Args:
        case_id: 错误数据ID
    
    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                "DELETE FROM hard_cases WHERE id = %s",
                (case_id,)
            )
            return result > 0


async def get_hard_cases_stats() -> dict:
    """
    获取错误数据统计信息
    
    Returns:
        dict: 统计数据
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 总数
            await cur.execute("SELECT COUNT(*) as total FROM hard_cases")
            total = await cur.fetchone()
            
            # 未修复数
            await cur.execute("SELECT COUNT(*) as unfixed FROM hard_cases WHERE is_fixed = 0")
            unfixed = await cur.fetchone()
            
            # 按错误类型分组
            await cur.execute(
                """SELECT wrong_label, COUNT(*) as count 
                   FROM hard_cases 
                   GROUP BY wrong_label 
                   ORDER BY count DESC 
                   LIMIT 20"""
            )
            by_wrong = await cur.fetchall()
            
            # 按正确类型分组
            await cur.execute(
                """SELECT correct_label, COUNT(*) as count 
                   FROM hard_cases 
                   GROUP BY correct_label 
                   ORDER BY count DESC 
                   LIMIT 20"""
            )
            by_correct = await cur.fetchall()
            
            # 按模型版本分组
            await cur.execute(
                """SELECT model_version, COUNT(*) as count 
                   FROM hard_cases 
                   WHERE model_version IS NOT NULL
                   GROUP BY model_version 
                   ORDER BY count DESC"""
            )
            by_version = await cur.fetchall()
            
            return {
                'total': total['total'] if total else 0,
                'unfixed': unfixed['unfixed'] if unfixed else 0,
                'fixed': (total['total'] if total else 0) - (unfixed['unfixed'] if unfixed else 0),
                'by_wrong_label': by_wrong,
                'by_correct_label': by_correct,
                'by_model_version': by_version
            }


# ============================================================
# ai_audit_logs — 审计日志
# ============================================================

async def insert_audit_log(
    user_id: int,
    action_type: str,
    model_name: str,
    input_summary: str | None,
    raw_ai_response: dict | str | None,
    execution_time_ms: int,
    status: str,
    error_message: str | None = None,
):
    """
    插入审计日志
    
    Args:
        raw_ai_response: 可以是 dict、JSON 字符串或 None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # ✅ 使用 safe_json_dumps 避免双编码
            raw_json = safe_json_dumps(raw_ai_response)
            
            await cur.execute(
                "INSERT INTO ai_audit_logs (user_id, action_type, model_name, input_summary, "
                "raw_ai_response, execution_time_ms, status, error_message) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, action_type, model_name, input_summary, raw_json, 
                 execution_time_ms, status, error_message),
            )


async def get_audit_logs(
    user_id: int = None,
    action_type: str = None,
    limit: int = 100,
    offset: int = 0
) -> list[dict]:
    """
    获取审计日志
    
    Args:
        user_id: 用户ID（可选）
        action_type: 操作类型（可选）
        limit: 返回数量
        offset: 偏移量
    
    Returns:
        list: 审计日志列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = "SELECT * FROM ai_audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                sql += " AND user_id = %s"
                params.append(user_id)
            
            if action_type:
                sql += " AND action_type = %s"
                params.append(action_type)
            
            sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            await cur.execute(sql, params)
            return await cur.fetchall()