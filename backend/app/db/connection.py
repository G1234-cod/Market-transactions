"""MySQL 连接池管理（基于 aiomysql）"""
import aiomysql
from app.config import settings


async def get_pool():
    """获取数据库连接池（单例）"""
    if not hasattr(get_pool, "_pool"):
        get_pool._pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=5,
        )
    return get_pool._pool


async def close_pool():
    """关闭连接池"""
    if hasattr(get_pool, "_pool"):
        get_pool._pool.close()
        await get_pool._pool.wait_closed()
