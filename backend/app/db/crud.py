"""数据库 CRUD 操作"""
import json
import logging
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any

import aiomysql

from app.db.connection import get_pool
from app.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)


# ============================================================
# users — 用户管理
# ============================================================

import hashlib
import os


# ✅ 修复：OWASP 2026 PBKDF2-SHA256 至少 600,000 次迭代
_PBKDF2_ITERATIONS = 600_000
# 保留旧迭代数用于兼容旧密码
_OLD_ITERATIONS = 100_000

def _hash_password(password: str) -> str:
    """PBKDF2 哈希密码"""
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return salt.hex() + ":" + h.hex()


def _verify_password(password: str, stored: str) -> bool:
    """验证密码（兼容旧哈希：先试新迭代数，再试旧的）"""
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        # 先用新迭代数试
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
        if h.hex() == hash_hex:
            return True
        # 兼容旧数据：用旧的 10 万次迭代
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _OLD_ITERATIONS)
        return h.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


async def register_user(username: str, password: str, role: str = "user") -> tuple[bool, int | None, str]:
    """注册用户。返回 (success, user_id, message)"""
    if role not in ('user', 'admin'):
        role = 'user'
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if await cur.fetchone():
                return False, None, "用户名已被占用"
            pw_hash = _hash_password(password)
            await cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, pw_hash, role),
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


async def authenticate_user(username: str, password: str) -> tuple[bool, int | None, str, str]:
    """登录鉴权。返回 (success, user_id, message, role)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, password_hash, role, status FROM users WHERE username=%s",
                (username,),
            )
            row = await cur.fetchone()
            if not row:
                return False, None, "用户不存在", "user"
            if row.get('status') == 'disabled':
                return False, None, "账号已被禁用，请联系管理员", "user"
            if not _verify_password(password, row["password_hash"]):
                return False, None, "密码错误", "user"
            await cur.execute(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (row["id"],)
            )
            return True, row["id"], "登录成功", row.get("role", "user")


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


async def update_item_status(item_id: int, status: str, user_id: int = None):
    """更新商品状态，可选所有权验证"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if user_id is not None:
                # ✅ 修复：验证所有权
                await cur.execute(
                    "SELECT user_id FROM published_items WHERE id = %s",
                    (item_id,)
                )
                row = await cur.fetchone()
                if not row:
                    return False
                if row[0] != user_id:
                    return False
            await cur.execute(
                "UPDATE published_items SET status=%s WHERE id=%s",
                (status, item_id),
            )
            return True


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


# ============================================================
# 价格历史查询
# ============================================================

async def get_price_history(brand: str, model: str, days: int = 90) -> list[dict]:
    """
    获取指定品牌型号商品的价格历史数据
    
    从 published_items 表中提取已发布商品的价格，按日期聚合
    
    Args:
        brand: 品牌名称
        model: 商品型号
        days: 查询最近天数
    
    Returns:
        list[dict]: 价格历史数据列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 按日期聚合价格数据
            await cur.execute(
                """SELECT 
                    DATE_FORMAT(created_at, '%%Y-%%m-%%d') as date,
                    suggested_price as price,
                    COUNT(*) as count
                   FROM published_items
                   WHERE status = 'published'
                     AND brand = %s
                     AND model LIKE %s
                     AND suggested_price IS NOT NULL
                     AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                   GROUP BY DATE(created_at), suggested_price
                   ORDER BY date ASC""",
                (brand, f"%{model}%", days)
            )
            return await cur.fetchall()


async def get_price_stats(brand: str, model: str) -> dict:
    """
    获取指定品牌型号的价格统计数据
    
    Args:
        brand: 品牌名称
        model: 商品型号
    
    Returns:
        dict: 统计数据 {total, avg, min, max}
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT 
                    COUNT(*) as total,
                    AVG(suggested_price) as avg,
                    MIN(suggested_price) as min,
                    MAX(suggested_price) as max
                   FROM published_items
                   WHERE status = 'published'
                     AND brand = %s
                     AND model LIKE %s
                     AND suggested_price IS NOT NULL""",
                (brand, f"%{model}%")
            )
            row = await cur.fetchone()
            return {
                "total": row["total"] if row else 0,
                "avg": float(row["avg"]) if row and row["avg"] else 0,
                "min": float(row["min"]) if row and row["min"] else 0,
                "max": float(row["max"]) if row and row["max"] else 0,
            }


async def get_available_price_models(keyword: str = "", category: str = "") -> list[dict]:
    """
    获取有价格历史记录的型号列表
    
    Args:
        keyword: 搜索关键词
        category: 品类筛选
    
    Returns:
        list[dict]: 型号列表 [{brand, model, category, count}]
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            where_parts = [
                "status = 'published'",
                "suggested_price IS NOT NULL",
                "brand IS NOT NULL",
                "model IS NOT NULL"
            ]
            params = []
            
            if keyword:
                where_parts.append("(brand LIKE %s OR model LIKE %s)")
                kw = f"%{keyword}%"
                params.extend([kw, kw])
            
            if category:
                where_parts.append("category = %s")
                params.append(category)
            
            where_clause = " AND ".join(where_parts)
            
            await cur.execute(
                f"""SELECT brand, model, category, COUNT(*) as count
                   FROM published_items
                   WHERE {where_clause}
                   GROUP BY brand, model, category
                   ORDER BY count DESC, brand ASC
                   LIMIT 50""",
                params
            )
            return await cur.fetchall()


# ============================================================
# model_disagreements — 模型差异记录
# ============================================================

async def insert_model_disagreement(
    image_url: str,
    yolo_category: str,
    yolo_model: str,
    qwen_category: str,
    qwen_model: str,
    qwen_brand: str,
    user_id: int = None,
    item_id: int = None,
    confidence: float = 0.0,
) -> int:
    """
    记录模型识别结果差异（自研模型 vs 阿里云Qwen-VL）
    
    Args:
        image_url: 图片URL
        yolo_category: 自研模型识别的品类
        yolo_model: 自研模型识别的型号
        qwen_category: Qwen-VL识别的品类
        qwen_model: Qwen-VL识别的型号
        qwen_brand: Qwen-VL识别的品牌
        user_id: 用户ID
        item_id: 商品ID
        confidence: 自研模型置信度
    
    Returns:
        int: 记录ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO model_disagreements 
                   (image_url, yolo_category, yolo_model, 
                    qwen_category, qwen_model, qwen_brand,
                    user_id, item_id, confidence, created_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                (image_url, yolo_category, yolo_model, 
                 qwen_category, qwen_model, qwen_brand,
                 user_id, item_id, confidence)
            )
            return cur.lastrowid


async def get_model_disagreements(
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "created_at"
) -> list[dict]:
    """
    获取模型差异记录列表
    
    Args:
        limit: 返回数量
        offset: 偏移量
        sort_by: 排序字段
    
    Returns:
        list: 差异记录列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            _SORT_COLUMNS = {
                "created_at": "created_at",
                "confidence": "confidence",
                "id": "id",
            }
            sort_column = _SORT_COLUMNS.get(sort_by, "created_at")
            
            await cur.execute(
                f"""SELECT id, image_url, yolo_category, yolo_model,
                          qwen_category, qwen_model, qwen_brand,
                          user_id, item_id, confidence, is_used_for_training,
                          created_at, training_used_at
                   FROM model_disagreements
                   ORDER BY {sort_column} DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            return await cur.fetchall()


async def get_model_disagreements_stats() -> dict:
    """
    获取模型差异统计信息
    
    Returns:
        dict: 统计数据
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT COUNT(*) as total FROM model_disagreements")
            total = await cur.fetchone()
            
            await cur.execute("SELECT COUNT(*) as used FROM model_disagreements WHERE is_used_for_training = 1")
            used = await cur.fetchone()
            
            await cur.execute(
                """SELECT qwen_category, COUNT(*) as count 
                   FROM model_disagreements 
                   GROUP BY qwen_category 
                   ORDER BY count DESC 
                   LIMIT 10"""
            )
            by_category = await cur.fetchall()
            
            return {
                'total': total['total'] if total else 0,
                'used_for_training': used['used'] if used else 0,
                'unused': (total['total'] if total else 0) - (used['used'] if used else 0),
                'by_category': by_category,
            }


async def mark_disagreement_used(case_id: int) -> bool:
    """
    标记差异记录已用于训练
    
    Args:
        case_id: 记录ID
    
    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                "UPDATE model_disagreements SET is_used_for_training = 1, training_used_at = NOW() WHERE id = %s",
                (case_id,)
            )
            return result > 0


# ============================================================
# notifications — 用户通知
# ============================================================

async def insert_notification(
    user_id: int,
    item_id: int = None,
    type: str = 'system',
    title: str = '',
    message: str = ''
) -> int:
    """
    插入用户通知
    
    Args:
        user_id: 接收用户ID
        item_id: 关联商品ID
        type: 通知类型
        title: 通知标题
        message: 通知内容
    
    Returns:
        int: 通知ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO notifications 
                   (user_id, item_id, type, title, message) 
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, item_id, type, title, message)
            )
            return cur.lastrowid


async def get_notifications(user_id: int, limit: int = 50, offset: int = 0, is_read: bool = None) -> list[dict]:
    """
    获取用户通知列表
    
    Args:
        user_id: 用户ID
        limit: 返回数量
        offset: 偏移量
        is_read: 是否已读筛选（None表示全部）
    
    Returns:
        list: 通知列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            query = """SELECT id, user_id, item_id, type, title, message, is_read, created_at
                       FROM notifications
                       WHERE user_id = %s"""
            params = [user_id]
            
            if is_read is not None:
                query += " AND is_read = %s"
                params.append(1 if is_read else 0)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            await cur.execute(query, params)
            return await cur.fetchall()


async def mark_notification_read(notification_id: int, user_id: int) -> bool:
    """
    标记通知已读（✅ 必须提供 user_id 进行权限验证）

    Args:
        notification_id: 通知ID
        user_id: 用户ID（必填，用于权限验证）

    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
                (notification_id, user_id)
            )
            return result > 0


async def mark_all_notifications_read(user_id: int) -> int:
    """
    标记用户所有通知已读
    
    Args:
        user_id: 用户ID
    
    Returns:
        int: 更新数量
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                (user_id,)
            )
            return result


async def get_unread_notification_count(user_id: int) -> int:
    """
    获取用户未读通知数量
    
    Args:
        user_id: 用户ID
    
    Returns:
        int: 未读数量
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = 0",
                (user_id,)
            )
            row = await cur.fetchone()
            return row['count'] if row else 0


# ============================================================
# category_brands — 品类品牌关联
# ============================================================

async def get_categories() -> list[str]:
    """
    获取所有品类列表
    
    Returns:
        list: 品类列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT DISTINCT category FROM category_brands ORDER BY category")
            rows = await cur.fetchall()
            return [row['category'] for row in rows]


async def get_brands_by_category(category: str) -> list[str]:
    """
    获取指定品类下的品牌列表
    
    Args:
        category: 品类名称
    
    Returns:
        list: 品牌列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT brand FROM category_brands WHERE category = %s ORDER BY brand",
                (category,)
            )
            rows = await cur.fetchall()
            return [row['brand'] for row in rows]


async def insert_category_brand(category: str, brand: str) -> int | None:
    """
    插入品类品牌关联（支持幂等性）
    
    Args:
        category: 品类名称
        brand: 品牌名称
    
    Returns:
        int | None: 记录ID或None（已存在）
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(
                    "INSERT INTO category_brands (category, brand) VALUES (%s, %s)",
                    (category, brand)
                )
                return cur.lastrowid
            except aiomysql.IntegrityError:
                return None


# ============================================================
# model_metrics — 模型训练指标
# ============================================================

async def insert_model_metrics(
    model_name: str,
    training_date: str,
    accuracy: float = None,
    precision: float = None,
    recall: float = None,
    f1_score: float = None,
    training_data_count: int = None,
    epoch: int = None,
    notes: str = None
) -> int:
    """
    插入模型训练指标
    
    Args:
        model_name: 模型名称
        training_date: 训练日期
        accuracy: 准确率
        precision: 精确率
        recall: 召回率
        f1_score: F1分数
        training_data_count: 训练数据量
        epoch: 训练轮数
        notes: 备注
    
    Returns:
        int: 指标ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO model_metrics 
                   (model_name, training_date, accuracy, precision, recall, 
                    f1_score, training_data_count, epoch, notes) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (model_name, training_date, accuracy, precision, recall,
                 f1_score, training_data_count, epoch, notes)
            )
            return cur.lastrowid


async def get_model_metrics(
    model_name: str = None,
    limit: int = 50,
    offset: int = 0
) -> list[dict]:
    """
    获取模型训练指标列表
    
    Args:
        model_name: 模型名称（可选）
        limit: 返回数量
        offset: 偏移量
    
    Returns:
        list: 指标列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = "SELECT * FROM model_metrics WHERE 1=1"
            params = []
            
            if model_name:
                sql += " AND model_name = %s"
                params.append(model_name)
            
            sql += " ORDER BY training_date DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            await cur.execute(sql, params)
            return await cur.fetchall()


async def get_model_metrics_stats(model_name: str = None) -> dict:
    """
    获取模型训练指标统计
    
    Args:
        model_name: 模型名称（可选）
    
    Returns:
        dict: 统计数据
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = "SELECT COUNT(*) as total, AVG(accuracy) as avg_accuracy, AVG(f1_score) as avg_f1 FROM model_metrics WHERE 1=1"
            params = []
            
            if model_name:
                sql += " AND model_name = %s"
                params.append(model_name)
            
            await cur.execute(sql, params)
            row = await cur.fetchone()
            
            return {
                'total': row['total'] if row else 0,
                'avg_accuracy': float(row['avg_accuracy']) if row and row['avg_accuracy'] else 0,
                'avg_f1': float(row['avg_f1']) if row and row['avg_f1'] else 0,
            }


# ============================================================
# admin — 管理员操作
# ============================================================

async def get_user_role(user_id: int) -> str | None:
    """
    获取用户角色
    
    Args:
        user_id: 用户ID
    
    Returns:
        str | None: 角色或None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            row = await cur.fetchone()
            return row['role'] if row else None


async def force_delist_item(item_id: int, admin_id: int, reason: str) -> bool:
    """
    强制下架商品并记录审核状态
    
    Args:
        item_id: 商品ID
        admin_id: 管理员ID
        reason: 下架原因
    
    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:  # ✅ 修复：使用 DictCursor
            await cur.execute("SELECT user_id FROM published_items WHERE id = %s", (item_id,))
            row = await cur.fetchone()
            if not row:
                return False

            user_id = row['user_id']

            # ✅ 修复：在同一事务中执行 UPDATE + INSERT（autocommit 下尽力保证顺序）
            await cur.execute(
                """UPDATE published_items
                   SET status = 'delisted', review_status = 'forced_delisted'
                   WHERE id = %s""",
                (item_id,)
            )

            # 记录管理员操作来源
            logger.info(f"管理员 {admin_id} 强制下架商品 {item_id}（用户 {user_id}）：{reason}")

            await insert_notification(
                user_id=user_id,
                item_id=item_id,
                type='force_delisted',
                title='商品已被强制下架',
                message=reason
            )

            return True


async def get_items_for_review(status: str = None) -> list[dict]:
    """
    获取待审核商品列表

    Args:
        status: 审核状态筛选

    Returns:
        list: 商品列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            where_clause = "1=1"
            params = []

            if status:
                where_clause = "review_status = %s"
                params.append(status)

            await cur.execute(
                f"""SELECT p.id, p.user_id, u.username, p.original_image_url,
                          p.ai_generated_title, p.suggested_price,
                          p.category, p.brand, p.model, p.status, p.review_status,
                          p.created_at
                   FROM published_items p
                   JOIN users u ON p.user_id = u.id
                   WHERE {where_clause}
                   ORDER BY p.created_at DESC
                   LIMIT 50""",
                params
            )
            return await cur.fetchall()


# ============================================================
# 按类别/品牌/型号直接搜索（数据库查询，非向量搜索）
# ============================================================

async def search_items_by_filter(
    category: str = None,
    brand: str = None,
    model: str = None,
    status: str = "published",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    按类别、品牌、型号直接在数据库中搜索商品

    Args:
        category: 品类筛选
        brand: 品牌筛选
        model: 型号关键词
        status: 商品状态
        page: 页码
        page_size: 每页数量

    Returns:
        tuple[list[dict], int]: (商品列表, 总条数)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            where_parts = [f"p.status = %s"]
            params = [status]

            if category:
                where_parts.append("p.category = %s")
                params.append(category)

            if brand:
                where_parts.append("p.brand = %s")
                params.append(brand)

            if model:
                where_parts.append("p.model LIKE %s")
                params.append(f"%{model}%")

            where_clause = " AND ".join(where_parts)

            # COUNT
            count_sql = (
                "SELECT COUNT(*) AS total FROM published_items p "
                "JOIN users u ON p.user_id = u.id "
                f"WHERE {where_clause}"
            )
            await cur.execute(count_sql, params)
            total_row = await cur.fetchone()
            total = total_row["total"] if total_row else 0

            # 数据查询
            offset = (page - 1) * page_size
            data_sql = (
                "SELECT p.id, p.user_id, u.username, p.original_image_url, "
                "p.ai_generated_title, p.ai_generated_desc, p.suggested_price, "
                "p.category, p.brand, p.model, p.`condition`, "
                "p.views, p.status, p.created_at "
                "FROM published_items p "
                "JOIN users u ON p.user_id = u.id "
                f"WHERE {where_clause} "
                "ORDER BY p.created_at DESC "
                "LIMIT %s OFFSET %s"
            )
            await cur.execute(data_sql, params + [page_size, offset])
            items = await cur.fetchall()

            return items, total


# ============================================================
# 获取商品的完整数据（含瑕疵信息，供重新评估使用）
# ============================================================

async def get_item_full_data(item_id: int) -> dict | None:
    """
    获取商品的完整数据，包括瑕疵详情

    Args:
        item_id: 商品ID

    Returns:
        dict | None: 完整商品数据
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT p.*, u.username
                   FROM published_items p
                   JOIN users u ON p.user_id = u.id
                   WHERE p.id = %s""",
                (item_id,)
            )
            return await cur.fetchone()


# ============================================================
# 更新商品AI评估结果（重新评估后）
# ============================================================

async def update_item_reevaluation(
    item_id: int,
    ai_generated_title: str = None,
    ai_generated_desc: str = None,
    suggested_price: float = None,
    category: str = None,
    brand: str = None,
    model: str = None,
    condition: str = None,
    defect_count: int = None,
    defect_data: list = None,
    annotated_url: str = None,
) -> bool:
    """
    更新商品的AI重新评估结果

    Returns:
        bool: 是否成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            updates = []
            params = []

            if ai_generated_title is not None:
                updates.append("ai_generated_title = %s")
                params.append(ai_generated_title)
            if ai_generated_desc is not None:
                updates.append("ai_generated_desc = %s")
                params.append(ai_generated_desc)
            if suggested_price is not None:
                updates.append("suggested_price = %s")
                params.append(suggested_price)
            if category is not None:
                updates.append("category = %s")
                params.append(category)
            if brand is not None:
                updates.append("brand = %s")
                params.append(brand)
            if model is not None:
                updates.append("model = %s")
                params.append(model)
            if condition is not None:
                updates.append("`condition` = %s")
                params.append(condition)
            if defect_count is not None:
                updates.append("defect_count = %s")
                params.append(defect_count)
            if defect_data is not None:
                updates.append("defect_data = %s")
                params.append(safe_json_dumps(defect_data))
            if annotated_url is not None:
                updates.append("annotated_url = %s")
                params.append(annotated_url)

            if not updates:
                return False

            updates.append("updated_at = NOW()")
            params.append(item_id)

            sql = f"UPDATE published_items SET {', '.join(updates)} WHERE id = %s"
            result = await cur.execute(sql, params)
            return result > 0


# ============================================================
# 获取所有可用的型号列表（用于搜索页级联选择）
# ============================================================

async def get_available_models_by_category_brand(category: str = None, brand: str = None) -> list[dict]:
    """
    获取指定品类/品牌下的所有可用型号

    Args:
        category: 品类筛选
        brand: 品牌筛选

    Returns:
        list[dict]: 型号列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            where_parts = ["status = 'published'", "model IS NOT NULL", "model != ''"]
            params = []

            if category:
                where_parts.append("category = %s")
                params.append(category)
            if brand:
                where_parts.append("brand = %s")
                params.append(brand)

            where_clause = " AND ".join(where_parts)

            await cur.execute(
                f"""SELECT DISTINCT model, category, brand, COUNT(*) as count
                   FROM published_items
                   WHERE {where_clause}
                   GROUP BY model, category, brand
                   ORDER BY count DESC
                   LIMIT 100""",
                params
            )
            return await cur.fetchall()


# ============================================================
# 三层匹配策略 —— 爬虫缓存 & 价格历史落库
# ============================================================

async def get_cached_price(brand: str, model: str, ttl_seconds: int = 86400) -> dict | None:
    """
    第一层：检查数据库缓存（24小时内查询过的价格）

    Args:
        brand: 品牌
        model: 型号
        ttl_seconds: 缓存有效期（秒），默认 86400（24小时）

    Returns:
        dict | None: 缓存的价格数据，过期或无数据返回 None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT category, brand, model, avg_price, low_price, high_price,
                          data_source, updated_at,
                          TIMESTAMPDIFF(SECOND, updated_at, NOW()) as age_seconds
                   FROM market_prices
                   WHERE brand = %s AND model = %s AND is_active = 1""",
                (brand, model),
            )
            row = await cur.fetchone()
            if not row:
                return None

            # 检查是否在有效期内
            age = row.get("age_seconds", ttl_seconds + 1)
            if age <= ttl_seconds:
                return {
                    "category": row["category"],
                    "brand": row["brand"],
                    "model": row["model"],
                    "avg_price": float(row["avg_price"]),
                    "low_price": float(row["low_price"]),
                    "high_price": float(row["high_price"]),
                    "data_source": row.get("data_source", "cache"),
                    "from_cache": True,
                    "age_hours": round(age / 3600, 1),
                }
            return None  # 过期


async def save_crawl_result(
    brand: str,
    model: str,
    avg_price: float,
    low_price: float,
    high_price: float,
    category: str = "",
    data_source: str = "onebound",
) -> bool:
    """
    第二层：爬虫结果落库（UPSERT 到 market_prices，同时写入 price_history）

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
            # UPSERT 到 market_prices（更新缓存）
            await cur.execute(
                """INSERT INTO market_prices (category, brand, model, avg_price, low_price, high_price, data_source, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                   ON DUPLICATE KEY UPDATE
                       avg_price = VALUES(avg_price),
                       low_price = VALUES(low_price),
                       high_price = VALUES(high_price),
                       data_source = VALUES(data_source),
                       updated_at = NOW()""",
                (category, brand, model, avg_price, low_price, high_price, data_source),
            )

            # 写入 price_history（记录历史快照）
            await cur.execute(
                """INSERT INTO price_history (brand, model, price, price_type, source, recorded_at)
                   VALUES (%s, %s, %s, 'avg', %s, NOW())""",
                (brand, model, avg_price, data_source),
            )
            await cur.execute(
                """INSERT INTO price_history (brand, model, price, price_type, source, recorded_at)
                   VALUES (%s, %s, %s, 'low', %s, NOW())""",
                (brand, model, low_price, data_source),
            )
            await cur.execute(
                """INSERT INTO price_history (brand, model, price, price_type, source, recorded_at)
                   VALUES (%s, %s, %s, 'high', %s, NOW())""",
                (brand, model, high_price, data_source),
            )

            return True


async def save_price_history_point(
    brand: str,
    model: str,
    price: float,
    price_type: str = "avg",
    source: str = "ai_estimated",
    recorded_at: str = None,
) -> int:
    """
    保存单个价格历史数据点

    Args:
        brand: 品牌
        model: 型号
        price: 价格
        price_type: 价格类型 (avg/low/high)
        source: 数据来源
        recorded_at: 记录日期（ISO格式字符串，默认当前时间）

    Returns:
        int: 记录ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if recorded_at:
                await cur.execute(
                    """INSERT INTO price_history (brand, model, price, price_type, source, recorded_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (brand, model, price, price_type, source, recorded_at),
                )
            else:
                await cur.execute(
                    """INSERT INTO price_history (brand, model, price, price_type, source, recorded_at)
                       VALUES (%s, %s, %s, %s, %s, NOW())""",
                    (brand, model, price, price_type, source),
                )
            return cur.lastrowid


async def get_price_history_from_table(
    brand: str,
    model: str,
    days: int = 180,
    source: str = None,
) -> list[dict]:
    """
    从 price_history 表获取价格历史数据（按月聚合）

    Args:
        brand: 品牌
        model: 型号
        days: 查询最近天数
        source: 数据来源筛选（None=全部，'ai_estimated'=仅AI估算，'onebound'=仅爬虫）

    Returns:
        list[dict]: 按月聚合的价格历史
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            where_parts = [
                "brand = %s",
                "model LIKE %s",
                "recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)",
            ]
            params = [brand, f"%{model}%", days]

            if source:
                where_parts.append("source = %s")
                params.append(source)

            where_clause = " AND ".join(where_parts)

            await cur.execute(
                f"""SELECT
                       DATE_FORMAT(recorded_at, '%%Y-%%m') as month,
                       price_type,
                       AVG(price) as avg_price,
                       MIN(price) as min_price,
                       MAX(price) as max_price,
                       COUNT(*) as count,
                       GROUP_CONCAT(DISTINCT source) as sources
                   FROM price_history
                   WHERE {where_clause}
                   GROUP BY DATE_FORMAT(recorded_at, '%%Y-%%m'), price_type
                   ORDER BY month ASC""",
                params,
            )
            return await cur.fetchall()


async def get_price_history_daily(
    brand: str,
    model: str,
    days: int = 180,
) -> list[dict]:
    """
    从 price_history 表获取每日价格数据（用于前端图表）

    优先使用 price_history 表，数据不足时返回 published_items 的数据。
    同时标记数据来源（real / estimated / published）。

    Args:
        brand: 品牌
        model: 型号
        days: 查询最近天数

    Returns:
        list[dict]: 每日价格数据点 [{"date": "2024-01-15", "price": 3200, "count": 3, "source": "real"}, ...]
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 从 price_history 表取 avg 类型的数据
            await cur.execute(
                """SELECT
                       DATE(recorded_at) as date,
                       AVG(price) as price,
                       COUNT(*) as count,
                       GROUP_CONCAT(DISTINCT source) as sources
                   FROM price_history
                   WHERE brand = %s
                     AND model LIKE %s
                     AND price_type = 'avg'
                     AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                   GROUP BY DATE(recorded_at)
                   ORDER BY date ASC""",
                (brand, f"%{model}%", days),
            )
            ph_rows = await cur.fetchall()

            # 如果 price_history 数据足够（>= 3条），直接返回
            if len(ph_rows) >= 3:
                result = []
                for r in ph_rows:
                    src = r.get("sources", "")
                    result.append({
                        "date": r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"]),
                        "price": float(r["price"]),
                        "count": r["count"],
                        "source": "estimated" if "ai_estimated" in src else "real",
                    })
                return result

            # 数据不足时，合并 published_items 的数据
            await cur.execute(
                """SELECT
                       DATE(created_at) as date,
                       AVG(suggested_price) as price,
                       COUNT(*) as count
                   FROM published_items
                   WHERE status = 'published'
                     AND brand = %s
                     AND model LIKE %s
                     AND suggested_price IS NOT NULL
                     AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                   GROUP BY DATE(created_at)
                   ORDER BY date ASC""",
                (brand, f"%{model}%", days),
            )
            pub_rows = await cur.fetchall()

            # 合并去重（price_history 优先）
            seen_dates = set()
            result = []
            for r in ph_rows:
                d = r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])
                seen_dates.add(d)
                src = r.get("sources", "")
                result.append({
                    "date": d,
                    "price": float(r["price"]),
                    "count": r["count"],
                    "source": "estimated" if "ai_estimated" in src else "real",
                })
            for r in pub_rows:
                d = r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])
                if d not in seen_dates:
                    seen_dates.add(d)
                    result.append({
                        "date": d,
                        "price": float(r["price"]),
                        "count": r["count"],
                        "source": "published",
                    })

            result.sort(key=lambda x: x["date"])
            return result


async def get_price_stats_from_tables(brand: str, model: str) -> dict:
    """
    从 price_history + published_items 获取价格统计数据

    Args:
        brand: 品牌
        model: 型号

    Returns:
        dict: {total, avg, min, max}
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 先从 price_history 取
            await cur.execute(
                """SELECT COUNT(*) as total, AVG(price) as avg, MIN(price) as min, MAX(price) as max
                   FROM price_history
                   WHERE brand = %s AND model LIKE %s AND price_type = 'avg'""",
                (brand, f"%{model}%"),
            )
            ph = await cur.fetchone()

            # 再从 published_items 取
            await cur.execute(
                """SELECT COUNT(*) as total, AVG(suggested_price) as avg,
                          MIN(suggested_price) as min, MAX(suggested_price) as max
                   FROM published_items
                   WHERE status = 'published'
                     AND brand = %s AND model LIKE %s
                     AND suggested_price IS NOT NULL""",
                (brand, f"%{model}%"),
            )
            pub = await cur.fetchone()

            # 合并统计
            total = (ph["total"] if ph and ph["total"] else 0) + (pub["total"] if pub and pub["total"] else 0)

            all_avgs = []
            all_mins = []
            all_maxs = []
            if ph and ph["avg"]:
                all_avgs.append(float(ph["avg"]))
                all_mins.append(float(ph["min"]))
                all_maxs.append(float(ph["max"]))
            if pub and pub["avg"]:
                all_avgs.append(float(pub["avg"]))
                all_mins.append(float(pub["min"]))
                all_maxs.append(float(pub["max"]))

            return {
                "total": total,
                "avg": round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else 0,
                "min": min(all_mins) if all_mins else 0,
                "max": max(all_maxs) if all_maxs else 0,
            }


async def has_sufficient_price_history(brand: str, model: str, min_records: int = 3) -> bool:
    """
    检查是否有足够的历史价格记录

    Args:
        brand: 品牌
        model: 型号
        min_records: 最少记录数

    Returns:
        bool: 是否有足够记录
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT COUNT(*) as cnt FROM price_history
                   WHERE brand = %s AND model LIKE %s""",
                (brand, f"%{model}%"),
            )
            row = await cur.fetchone()
            return (row["cnt"] if row else 0) >= min_records


async def get_market_price_for_estimate(brand: str, model: str) -> dict | None:
    """
    获取用于AI估算的当前市场价格（优先 market_prices，其次 published_items）

    Args:
        brand: 品牌
        model: 型号

    Returns:
        dict | None: {avg_price, low_price, high_price} 或 None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 先查 market_prices
            await cur.execute(
                """SELECT avg_price, low_price, high_price FROM market_prices
                   WHERE brand = %s AND model LIKE %s AND is_active = 1""",
                (brand, f"%{model}%"),
            )
            row = await cur.fetchone()
            if row and row["avg_price"]:
                return {
                    "avg_price": float(row["avg_price"]),
                    "low_price": float(row["low_price"]),
                    "high_price": float(row["high_price"]),
                }

            # 回退到 published_items 的均价
            await cur.execute(
                """SELECT AVG(suggested_price) as avg, MIN(suggested_price) as min, MAX(suggested_price) as max
                   FROM published_items
                   WHERE status = 'published' AND brand = %s AND model LIKE %s
                     AND suggested_price IS NOT NULL""",
                (brand, f"%{model}%"),
            )
            row = await cur.fetchone()
            if row and row["avg"]:
                return {
                    "avg_price": float(row["avg"]),
                    "low_price": float(row["min"]),
                    "high_price": float(row["max"]),
                }
            return None


async def delete_old_estimated_history(brand: str, model: str) -> int:
    """
    删除旧的 AI 估算历史数据（在重新估算前调用）

    Returns:
        int: 删除的记录数
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            result = await cur.execute(
                """DELETE FROM price_history
                   WHERE brand = %s AND model LIKE %s
                     AND source IN ('ai_estimated', 'fallback_estimate')""",
                (brand, f"%{model}%"),
            )
            return result