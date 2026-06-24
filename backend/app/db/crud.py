"""数据库 CRUD 操作"""
import json
from difflib import SequenceMatcher

import aiomysql

from app.db.connection import get_pool


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
                "SELECT category, brand, model, avg_price, low_price, high_price "
                "FROM market_prices WHERE brand=%s AND model=%s",
                (brand, model),
            )
            row = await cur.fetchone()
            if row:
                return row

            await cur.execute(
                "SELECT category, brand, model, avg_price, low_price, high_price "
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
) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO published_items (user_id, original_image_url, ai_generated_title, "
                "ai_generated_desc, suggested_price, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, image_url, title, desc, price, status),
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
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, user_id, original_image_url, ai_generated_title, "
                "ai_generated_desc, suggested_price, status, created_at "
                "FROM published_items WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
                (user_id,),
            )
            return await cur.fetchall()


async def get_market_items(
    keyword: str = "",
    category: str = "",
) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = (
                "SELECT p.id, p.user_id, u.username, p.original_image_url, "
                "p.ai_generated_title, p.ai_generated_desc, p.suggested_price, p.created_at "
                "FROM published_items p JOIN users u ON p.user_id = u.id "
                "WHERE p.status = 'published'"
            )
            params = []
            if keyword:
                sql += " AND (p.ai_generated_title LIKE %s OR p.ai_generated_desc LIKE %s)"
                kw = f"%{keyword}%"
                params.extend([kw, kw])
            if category:
                sql += " AND p.ai_generated_title LIKE %s"
                params.append(f"%{category}%")
            sql += " ORDER BY p.created_at DESC LIMIT 100"
            await cur.execute(sql, params)
            return await cur.fetchall()


# ============================================================
# 🆕 published_items — 瑕疵数据更新
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
            defect_json = json.dumps(defect_data, ensure_ascii=False) if defect_data else None
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
    """根据ID获取商品信息"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM published_items WHERE id = %s",
                (item_id,)
            )
            return await cur.fetchone()


# ============================================================
# 🆕 hard_cases — 错误数据记录
# ============================================================

async def insert_hard_case(
    image_url: str,
    wrong_label: str,
    correct_label: str,
    user_id: int,
    item_id: int = None,
    model_version: str = None
):
    """
    插入错误数据到 hard_cases 表
    
    Args:
        image_url: 错误图片URL
        wrong_label: 本地模型错误分类
        correct_label: Qwen正确分类
        user_id: 用户ID
        item_id: 商品ID（可选）
        model_version: 模型版本（可选）
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO hard_cases 
                   (image_url, wrong_label, correct_label, user_id, item_id, model_version)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (image_url, wrong_label, correct_label, user_id, item_id, model_version)
            )


async def get_hard_cases(limit: int = 100) -> list[dict]:
    """获取错误数据列表（用于训练）"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, image_url, wrong_label, correct_label, user_id, 
                          item_id, model_version, is_fixed, created_at
                   FROM hard_cases 
                   WHERE is_fixed = 0
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,)
            )
            return await cur.fetchall()


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
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            raw_json = json.dumps(raw_ai_response, ensure_ascii=False) if raw_ai_response else None
            await cur.execute(
                "INSERT INTO ai_audit_logs (user_id, action_type, model_name, input_summary, "
                "raw_ai_response, execution_time_ms, status, error_message) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, action_type, model_name, input_summary, raw_json, execution_time_ms, status, error_message),
            )