"""FastAPI 应用入口"""
import os

from fastapi import FastAPI
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

app = FastAPI(title="智能二手商品发布助手", version="1.0.0")


# ============================================================
# CORS 配置（修复 allow_origins=["*"] + allow_credentials=True）
# ============================================================

# ✅ 使用 config.py 中的 ALLOWED_ORIGINS
allowed_origins = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,        # ✅ 明确列表，不使用 "*"
    allow_credentials=True,               # ✅ 允许携带 Cookie/Token
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,                          # 预检请求缓存 10 分钟
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
# 挂载静态文件目录（图片访问）
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
    return {"status": "ok"}