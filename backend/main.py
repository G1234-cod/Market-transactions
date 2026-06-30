"""FastAPI 应用入口"""
import os

# ✅ 国内网络环境：使用 HuggingFace 镜像下载模型
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

import logging
from contextlib import asynccontextmanager

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
    notifications,
    price,
    price_history,
    process,
    recognition,
    search,
    admin,
)
from app.config import settings
from app.db.connection import init_db, shutdown_db

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# ✅ 应用生命周期管理（使用 lifespan 替代弃用的 on_event）
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期管理"""
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

    # 启动后台限流清理任务
    cleanup_task = None
    try:
        from app.middleware.rate_limit import periodic_cleanup
        import asyncio as _asyncio
        cleanup_task = _asyncio.create_task(periodic_cleanup())
    except Exception as e:
        logger.warning(f"⚠️ 后台限流清理任务启动失败: {e}")

    # ✅ 启动每周自动训练调度器
    try:
        from app.routers.admin import start_weekly_scheduler
        start_weekly_scheduler()
    except Exception as e:
        logger.warning(f"⚠️ 每周自动训练调度器启动失败: {e}")

    logger.info("✅ 应用启动完成")

    yield  # 应用运行中

    logger.info("🔄 应用关闭中...")
    if cleanup_task:
        cleanup_task.cancel()
    await shutdown_db()
    logger.info("✅ 应用已关闭")


app = FastAPI(title="智能二手商品发布助手", version="1.0.0", lifespan=lifespan)


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
        # ✅ 生产环境 CSP：允许 Google Fonts + Cloudflare 的脚本和样式
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' https:; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ============================================================
# CORS 配置（收紧：仅允许必要的 methods 和 headers）
# ============================================================

allowed_origins = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Content-Type"],
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
app.include_router(price_history.router, prefix="/api/v1")
app.include_router(process.router, prefix="/api/v1")
app.include_router(recognition.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")


# ============================================================
# 挂载静态文件目录
# ============================================================

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# ✅ 修复：使用显式的 STATIC_DIR 配置，而非从 UPLOAD_DIR 解析
static_dir = str(settings.BASE_DIR / "static")
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
    except Exception:
        # ✅ 修复：不暴露内部错误详情
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "database": "error", "env": settings.ENV}
        )


# ============================================================
# SPA 回退路由：前端 Vue Router 的 history 模式需要
# 所有非 API / 非静态文件 / 非健康检查 的 GET 请求都返回 index.html
# ============================================================

from fastapi.responses import HTMLResponse

SPA_ROUTES = {
    "/market", "/market/",
    "/history", "/history/",
    "/login", "/login/",
    "/register", "/register/",
    "/search", "/search/",
    "/home", "/home/",
    "/admin", "/admin/",
    "/notifications", "/notifications/",
    "/price-history", "/price-history/",
}

SPA_INDEX_PATH = os.path.join(frontend_dist_dir, "index.html") if os.path.exists(frontend_dist_dir) else None


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str, request: Request):
    """SPA 回退：将前端路由请求返回 index.html"""
    # API / 静态文件 / 文档 等路径不拦截
    if full_path.startswith("api/") or full_path.startswith("static/") or full_path == "health" or full_path.startswith("docs") or full_path == "openapi.json":
        raise HTTPException(status_code=404)

    if SPA_INDEX_PATH:
        with open(SPA_INDEX_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html")
    raise HTTPException(status_code=404)
