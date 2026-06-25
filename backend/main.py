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

app = FastAPI(title="智能二手商品发布助手", version="1.0.0")

# --- CORS 中间件（允许前端开发服务器跨域）---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 挂载路由 ---
app.include_router(auth.router, prefix="/api/v1")
app.include_router(detect.router, prefix="/api/v1")
app.include_router(extract.router, prefix="/api/v1")
app.include_router(generate.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(price.router, prefix="/api/v1")
app.include_router(process.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")

# --- 挂载静态文件目录（图片访问）---
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"service": "智能二手商品发布助手", "version": "1.0.0"}