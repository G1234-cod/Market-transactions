"""FastAPI 应用入口"""
import os
import logging

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

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
# ✅ 安全响应头中间件
# ============================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全相关的 HTTP 响应头"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ============================================================
# 应用生命周期管理
# ============================================================

@app.on_event("startup")
async def startup():
    """应用启动时初始化资源"""
    logger.info("🚀 应用启动中...")
    await init_db()

    # 启动时验证配置
    from app.config import validate_config
    config_errors = validate_config()
    if config_errors:
        for err in config_errors:
            if err.startswith("❌"):
                logger.error(f"配置错误: {err}")
            else:
                logger.warning(f"配置警告: {err}")

    logger.info("✅ 应用启动完成")


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时释放资源"""
    logger.info("🔄 应用关闭中...")
    await shutdown_db()
    logger.info("✅ 应用已关闭")


# ============================================================
# CORS 配置（收紧：仅允许必要的 methods 和 headers）
# ============================================================

allowed_origins = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ 收紧：仅允许实际使用的 HTTP 方法
    allow_headers=["Authorization", "Content-Type", "Accept"],   # ✅ 收紧：仅允许必要请求头
    expose_headers=["Content-Type"],                              # ✅ 收紧：仅暴露必要响应头
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

# 确保上传目录存在（config.ensure_directories() 中已创建，此处作为兜底）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# 静态文件目录相对于项目根目录
static_dir = str(settings.BASE_DIR / settings.UPLOAD_DIR.split("/")[0])
app.mount(settings.STATIC_PREFIX, StaticFiles(directory=static_dir), name="static")

# ============================================================
# 挂载前端构建产物的资源文件
# ============================================================

frontend_dist_dir = str(settings.BASE_DIR / "static" / "dist")
if os.path.exists(frontend_dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_dir, "assets")), name="frontend-assets")

# ============================================================
# 健康检查 / 根路径
# ============================================================

@app.get("/")
async def root(request: Request):
    frontend_dist_dir = str(settings.BASE_DIR / "static" / "dist")
    index_path = os.path.join(frontend_dist_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=f.read(), media_type="text/html")
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