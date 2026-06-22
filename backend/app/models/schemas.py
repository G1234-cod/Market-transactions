"""Pydantic 数据模型 —— 统一请求/响应/内部 DTO"""
from pydantic import BaseModel, Field


# ============================================================
# 用户
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str


# ============================================================
# 视觉识别
# ============================================================

class ExtractResult(BaseModel):
    category: str = ""
    brand: str = ""
    model: str = ""
    condition: str = ""


class ExtractResponse(BaseModel):
    success: bool
    data: ExtractResult | None = None
    image_urls: list[str] = []
    error: str | None = None


# ============================================================
# 查价
# ============================================================

class PriceResult(BaseModel):
    category: str = ""
    brand: str = ""
    model: str = ""
    avg_price: float = 0
    low_price: float = 0
    high_price: float = 0
    matched: bool = False
    note: str = ""


# ============================================================
# 文案生成
# ============================================================

class GenerateRequest(BaseModel):
    user_id: int = 1
    category: str
    brand: str
    model: str
    condition: str
    image_urls: list[str] = []
    avg_price: float | None = None
    low_price: float | None = None
    high_price: float | None = None


class GenerateSaveRequest(BaseModel):
    user_id: int = 1
    image_url: str
    title: str
    desc: str
    price: float
    status: str = "published"


# ============================================================
# 发布历史
# ============================================================

class HistoryItem(BaseModel):
    id: int
    user_id: int
    original_image_url: str
    ai_generated_title: str
    ai_generated_desc: str | None
    suggested_price: float | None
    status: str
    created_at: str


# ============================================================
# 商城
# ============================================================

class MarketItem(BaseModel):
    id: int
    username: str
    original_image_url: str
    ai_generated_title: str
    ai_generated_desc: str | None
    suggested_price: float | None
    created_at: str
