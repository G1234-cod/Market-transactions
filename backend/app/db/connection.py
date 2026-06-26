"""MySQL 连接池管理（基于 aiomysql）"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

import aiomysql

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# 全局变量（线程安全）
# ============================================================

_pool: Optional[aiomysql.Pool] = None
_pool_lock: asyncio.Lock = asyncio.Lock()


# ============================================================
# 连接池管理
# ============================================================

async def get_pool() -> aiomysql.Pool:
    """
    获取数据库连接池（单例）
    
    使用 asyncio.Lock 确保并发环境下只创建一个连接池
    """
    global _pool
    
    # ✅ 快速路径：如果已存在，直接返回（无锁）
    if _pool is not None:
        return _pool
    
    # ✅ 慢速路径：使用锁确保只有一个协程创建连接池
    async with _pool_lock:
        # ✅ 双重检查：获取锁后再次检查（防止其他协程已创建）
        if _pool is not None:
            return _pool
        
        logger.info("📦 创建 MySQL 连接池...")
        try:
            _pool = await aiomysql.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                charset="utf8mb4",
                autocommit=True,
                minsize=1,
                maxsize=10,
                pool_recycle=3600,      # 连接回收时间（秒）
                connect_timeout=10,     # 连接超时
                echo=False,             # 不打印 SQL 日志
            )
            logger.info(f"✅ MySQL 连接池创建成功: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
            return _pool
        except Exception as e:
            logger.error(f"❌ MySQL 连接池创建失败: {e}")
            raise


async def close_pool() -> None:
    """
    关闭数据库连接池（应用关闭时调用）
    """
    global _pool
    
    # ✅ 使用锁保护，防止与 get_pool() 竞争
    async with _pool_lock:
        if _pool is not None:
            logger.info("🔄 关闭 MySQL 连接池...")
            _pool.close()
            await _pool.wait_closed()
            _pool = None
            logger.info("✅ MySQL 连接池已关闭")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiomysql.Connection, None]:
    """
    获取数据库连接的上下文管理器
    
    使用方式:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def health_check() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        bool: 连接正常返回 True
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await asyncio.wait_for(cur.execute("SELECT 1"), timeout=5.0)
                await asyncio.wait_for(cur.fetchone(), timeout=5.0)
        logger.debug("✅ 数据库健康检查通过")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库健康检查失败: {e}")
        return False


async def reset_pool() -> None:
    """
    重置连接池（用于测试）
    """
    global _pool
    async with _pool_lock:
        if _pool is not None:
            _pool.close()
            await _pool.wait_closed()
            _pool = None
            logger.info("🔄 MySQL 连接池已重置")


# ============================================================
# 应用生命周期管理
# ============================================================

async def init_db() -> None:
    """初始化数据库连接池（应用启动时调用）"""
    await get_pool()


async def shutdown_db() -> None:
    """关闭数据库连接池（应用关闭时调用）"""
    await close_pool()