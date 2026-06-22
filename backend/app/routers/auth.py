"""POST /api/v1/login + POST /api/v1/register"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import LoginRequest, RegisterRequest, LoginResponse
from app.db import crud

router = APIRouter(tags=["用户"])


@router.post("/register", response_model=LoginResponse)
async def register(payload: RegisterRequest):
    """注册新用户"""
    username = payload.username.strip()
    password = payload.password
    if len(username) < 2:
        raise HTTPException(400, "用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")

    ok, uid, msg = await crud.register_user(username, password)
    if not ok:
        raise HTTPException(400, msg)
    return LoginResponse(id=uid, username=username)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """用户名 + 密码登录"""
    username = payload.username.strip()
    password = payload.password

    ok, uid, msg = await crud.authenticate_user(username, password)
    if not ok:
        raise HTTPException(400, msg)
    return LoginResponse(id=uid, username=username)
