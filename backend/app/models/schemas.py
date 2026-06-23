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


# ============================================================
# 损伤检测
# ============================================================

class DamageType(str):
    SCRATCH = "scratch"       # 划痕 - 红色
    DENT = "dent"             # 凹陷 - 蓝色
    CRACK = "crack"           # 裂纹 - 黄色
    STAIN = "stain"           # 污渍 - 绿色
    OTHER = "other"           # 其他 - 橙色


DAMAGE_COLORS = {
    DamageType.SCRATCH: (255, 0, 0),      # 红色
    DamageType.DENT: (0, 0, 255),         # 蓝色
    DamageType.CRACK: (255, 255, 0),      # 黄色
    DamageType.STAIN: (0, 255, 0),         # 绿色
    DamageType.OTHER: (255, 165, 0),      # 橙色
}


class DamageRegion(BaseModel):
    """损伤区域"""
    damage_type: str           # 损伤类型：scratch/dent/crack/stain/other
    confidence: float          # 置信度 0-1
    # 多边形顶点坐标（相对于原图）
    polygon: list[list[float]]  # [[x1,y1], [x2,y2], [x3,y3], ...]


class DamageDetectionResult(BaseModel):
    """单张图片的损伤检测结果"""
    image_url: str             # 原图URL
    annotated_image_url: str   # 标注后的图片URL
    regions: list[DamageRegion]  # 检测到的损伤区域列表
    total_regions: int        # 总损伤区域数


class DamageDetectionResponse(BaseModel):
    """损伤检测响应"""
    success: bool
    data: list[DamageDetectionResult] | None = None
    error: str | None = None


class DamageDetectionRecord(BaseModel):
    """数据库存储的损伤检测记录"""
    id: int
    published_item_id: int     # 关联的发布记录ID
    original_image_url: str
    annotated_image_url: str    # 标注图URL
    regions_json: str          # 损伤区域JSON存储
    created_at: str
