"""FastAPI 应用入口"""
import os
import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth,
    detect,
    extract,
    generate,
    history,
    market,
    price,
    process,
    search,
)
from app.config import settings
from app.db.connection import init_db, shutdown_db

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="智能二手商品发布助手", version="1.0.0")


# ============================================================
# 应用生命周期管理
# ============================================================

@app.on_event("startup")
async def startup():
    """应用启动时初始化资源"""
    logger.info("🚀 应用启动中...")
    await init_db()
    logger.info("✅ 应用启动完成")


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时释放资源"""
    logger.info("🔄 应用关闭中...")
    await shutdown_db()
    logger.info("✅ 应用已关闭")


# ============================================================
# CORS 配置
# ============================================================

allowed_origins = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


# ============================================================
# 挂载路由
# ============================================================

app.include_router(auth.router, prefix="/api/v1")
app.include_router(detect.router, prefix="/api/v1")
app.include_router(extract.router, prefix="/api/v1")
app.include_router(generate.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(price.router, prefix="/api/v1")
app.include_router(process.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


# ============================================================
# 挂载静态文件目录
# ============================================================

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================
# 健康检查 / 根路径
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "智能二手商品发布助手",
        "version": "1.0.0",
        "env": settings.ENV,
    }


@app.get("/health")
async def health():
    """健康检查接口"""
    try:
        from app.db.connection import health_check
        db_ok = await health_check()
        if not db_ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "unhealthy", "database": "disconnected", "env": settings.ENV}
            )
        return {
            "status": "healthy",
            "database": "connected",
            "env": settings.ENV,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e), "env": settings.ENV}
        )