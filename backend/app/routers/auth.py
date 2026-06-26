"""POST /api/v1/login + POST /api/v1/register"""
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import LoginRequest, RegisterRequest, LoginResponse, RegisterResponse
from app.db import crud
from app.auth.jwt_handler import create_access_token

router = APIRouter(tags=["用户"])


@router.post("/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest):
    """注册新用户"""
    username = payload.username.strip()
    password = payload.password
    
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    ok, uid, msg = await crud.register_user(username, password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    return RegisterResponse(
        success=True,
        user_id=uid,
        username=username,
        message="注册成功"
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """用户名 + 密码登录，返回 JWT Token"""
    username = payload.username.strip()
    password = payload.password

    ok, uid, msg = await crud.authenticate_user(username, password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    
    # ✅ 生成 JWT Token
    access_token = create_access_token(data={"sub": str(uid)})
    
    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user_id=uid,
        username=username,
        message="登录成功"
    )