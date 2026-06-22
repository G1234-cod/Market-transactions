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
            # 检查是否已存在
            await cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if await cur.fetchone():
                return False, None, "用户名已被占用"
            # 创建
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
            # 第1层：精确匹配
            await cur.execute(
                "SELECT category, brand, model, avg_price, low_price, high_price "
                "FROM market_prices WHERE brand=%s AND model=%s",
                (brand, model),
            )
            row = await cur.fetchone()
            if row:
                return row

            # 第2层：模糊匹配（difflib）
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

            # 第3层：无匹配
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
    """查询商城商品（全用户已发布 + JOIN users 获取用户名）"""
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
    import aiomysql

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
