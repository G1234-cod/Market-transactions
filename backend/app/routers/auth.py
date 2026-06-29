"""POST /api/v1/login + POST /api/v1/register"""
from fastapi import APIRouter, HTTPException, status, Depends, Request

from app.models.schemas import LoginRequest, RegisterRequest, LoginResponse, RegisterResponse
from app.db import crud
from app.auth.jwt_handler import create_access_token
from app.middleware.rate_limit import create_rate_limit

router = APIRouter(tags=["用户"])


@router.post("/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, rate: None = Depends(create_rate_limit(5, 60))):
    """注册新用户（速率限制: 5次/分钟）"""
    username = payload.username.strip()
    password = payload.password
    
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    role = getattr(payload, 'role', 'user') or 'user'
    ok, uid, msg = await crud.register_user(username, password, role)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    return RegisterResponse(
        success=True,
        user_id=uid,
        username=username,
        message="注册成功"
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, rate: None = Depends(create_rate_limit(10, 60))):
    """用户名 + 密码登录，返回 JWT Token（速率限制: 10次/分钟，防暴力破解）"""
    username = payload.username.strip()
    password = payload.password

    ok, uid, msg, role = await crud.authenticate_user(username, password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    
    # ✅ 生成 JWT Token（包含 role，便于权限验证和审计）
    access_token = create_access_token(data={"sub": str(uid), "role": role})
    
    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user_id=uid,
        username=username,
        role=role,
        message="登录成功"
    )