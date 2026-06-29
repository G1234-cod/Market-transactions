"""
FastAPI 依赖项 —— JWT 认证
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_handler import get_user_id_from_token
from app.db import crud

# ============================================================
# ✅ 创建两个安全实例
# ============================================================

# 强制认证：缺少 token 时自动返回 401
security = HTTPBearer()

# ✅ 可选认证：缺少 token 时返回 None，不抛出异常
security_optional = HTTPBearer(auto_error=False)


# ============================================================
# 强制认证依赖
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    获取当前登录用户的 ID（强制认证）
    
    所有需要认证的接口都应该使用此依赖项
    
    Returns:
        int: 当前用户 ID
    
    Raises:
        HTTPException: 401 未认证或无效 Token
    """
    token = credentials.credentials
    user_id = get_user_id_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证用户是否存在
    user = await crud.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    
    return user_id


# ============================================================
# 可选认证依赖
# ============================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[int]:
    """
    获取当前登录用户的 ID（可选认证）
    
    用于商城、价格查询等不需要强制登录的接口
    
    Returns:
        Optional[int]: 用户 ID，未登录时返回 None
    
    Note:
        使用 auto_error=False 的 HTTPBearer 实例，
        没有 token 时 credentials 为 None，不会抛出异常
    """
    # ✅ 现在可以正常处理 credentials 为 None 的情况
    if credentials is None:
        return None
    
    token = credentials.credentials
    user_id = get_user_id_from_token(token)
    
    if user_id is None:
        return None
    
    user = await crud.get_user_by_id(user_id)
    if user is None:
        return None
    
    return user_id