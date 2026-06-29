"""
JWT 认证处理器
"""
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt

from app.config import settings

# ============================================================
# 密码哈希（PBKDF2，与 crud.py 一致）
# ============================================================

# ✅ 修复：OWASP 2026 建议 PBKDF2-SHA256 至少 600,000 次迭代
_PBKDF2_ITERATIONS = 600_000
_OLD_ITERATIONS = 100_000

def hash_password(password: str, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """
    PBKDF2 哈希密码

    Args:
        password: 明文密码
        iterations: 迭代次数（默认 600,000）

    Returns:
        str: salt:hash 格式
    """
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return salt.hex() + ":" + h.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码（兼容旧哈希）

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码 (salt:hash)

    Returns:
        bool: 是否匹配
    """
    try:
        salt_hex, hash_hex = hashed_password.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        # 先用新迭代数试
        h = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, _PBKDF2_ITERATIONS)
        if h.hex() == hash_hex:
            return True
        # 兼容旧数据
        h = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, _OLD_ITERATIONS)
        return h.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


# ============================================================
# JWT Token 创建与解析
# ============================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT Token

    Args:
        data: 要编码的数据（必须包含 sub 字段；建议包含 role 字段）

    Returns:
        str: JWT Token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # ✅ 添加标准 JWT claims：iat（签发时间）、exp（过期时间）
    now = datetime.now(timezone.utc)
    to_encode.update({
        "iat": now,
        "exp": expire,
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT Token

    Args:
        token: JWT Token

    Returns:
        Optional[Dict]: 解码后的数据，失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    从 Token 中获取用户 ID

    Args:
        token: JWT Token

    Returns:
        Optional[int]: 用户 ID，失败返回 None
    """
    payload = decode_access_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            try:
                return int(user_id)
            except (ValueError, TypeError):
                return None
    return None


def get_username_from_token(token: str) -> Optional[str]:
    """
    从 Token 中获取用户名

    Args:
        token: JWT Token

    Returns:
        Optional[str]: 用户名，失败返回 None
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("username")
    return None
