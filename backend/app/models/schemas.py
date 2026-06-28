"""Pydantic 数据模型 —— 统一请求/响应/内部 DTO"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ============================================================
# 用户认证
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应（含 JWT Token）"""
    success: bool = True
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    message: str = "登录成功"


class RegisterResponse(BaseModel):
    """注册响应"""
    success: bool = True
    user_id: int
    username: str
    message: str = "注册成功"


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
    data: Optional[ExtractResult] = None
    image_urls: List[str] = []
    error: Optional[str] = None


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
    image_urls: List[str] = []
    avg_price: Optional[float] = None
    low_price: Optional[float] = None
    high_price: Optional[float] = None


class GenerateSaveRequest(BaseModel):
    user_id: Optional[int] = None
    image_url: str
    title: str
    desc: str
    price: float
    status: str = "published"
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    condition: Optional[str] = None


# ============================================================
# 发布历史（✅ 统一使用 condition）
# ============================================================

class HistoryItem(BaseModel):
    id: int
    user_id: int
    original_image_url: str
    ai_generated_title: str
    ai_generated_desc: Optional[str] = None
    suggested_price: Optional[float] = None
    status: str
    created_at: str
    views: int = 0
    category: Optional[str] = None
    condition: Optional[str] = None  # ✅ 改为 condition
    
    # ✅ 兼容旧字段名
    @property
    def item_condition(self) -> Optional[str]:
        return self.condition
    
    class Config:
        populate_by_name = True


# ============================================================
# 商城（✅ 统一使用 condition）
# ============================================================

class MarketItem(BaseModel):
    id: int
    user_id: int
    username: str
    original_image_url: str
    ai_generated_title: str
    ai_generated_desc: Optional[str] = None
    suggested_price: Optional[float] = None
    category: Optional[str] = None
    condition: Optional[str] = None  # ✅ 改为 condition
    views: int = 0
    created_at: str

    # ✅ 兼容旧字段名
    @property
    def item_condition(self) -> Optional[str]:
        return self.condition
    
    class Config:
        populate_by_name = True


# ============================================================
# 以图搜图
# ============================================================

class SearchResult(BaseModel):
    id: int
    title: str
    price: Optional[float] = None
    image_url: str
    similarity: float
    category: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult] = []
    count: int = 0


# ============================================================
# 损伤检测
# ============================================================

class DamageType(str, Enum):
    PENETRATION = "penetration"           # 穿透 - 红色
    DEFORMATION = "deformation"           # 变形 - 蓝色
    ACTUATION = "actuation"               # 功能故障 - 黄色
    DECONSTRUCTION = "deconstruction"     # 结构损坏 - 紫色
    SPILLAGE = "spillage"                 # 溢漏 - 绿色
    SUPERFICIAL = "superficial"           # 表面瑕疵 - 青色
    MISSING_UNIT = "missing_unit"         # 部件缺失 - 橙色


DAMAGE_COLORS = {
    DamageType.PENETRATION: (255, 0, 0),          # 红色
    DamageType.DEFORMATION: (0, 0, 255),          # 蓝色
    DamageType.ACTUATION: (255, 255, 0),           # 黄色
    DamageType.DECONSTRUCTION: (128, 0, 128),      # 紫色
    DamageType.SPILLAGE: (0, 255, 0),              # 绿色
    DamageType.SUPERFICIAL: (0, 255, 255),         # 青色
    DamageType.MISSING_UNIT: (255, 165, 0),        # 橙色
}


class DamageRegion(BaseModel):
    """损伤区域"""
    damage_type: str           # 损伤类型：scratch/dent/crack/stain/other
    confidence: float          # 置信度 0-1
    polygon: List[List[float]]  # 多边形顶点坐标 [[x1,y1], [x2,y2], ...]


class DamageDetectionResult(BaseModel):
    """单张图片的损伤检测结果"""
    image_url: str             # 原图URL
    annotated_image_url: str   # 标注后的图片URL
    regions: List[DamageRegion]  # 检测到的损伤区域列表
    total_regions: int        # 总损伤区域数


class DamageDetectionResponse(BaseModel):
    """损伤检测响应"""
    success: bool
    data: Optional[List[DamageDetectionResult]] = None
    error: Optional[str] = None


class DamageDetectionRecord(BaseModel):
    """数据库存储的损伤检测记录"""
    id: int
    published_item_id: int     # 关联的发布记录ID
    original_image_url: str
    annotated_image_url: str   # 标注图URL
    regions_json: str          # 损伤区域JSON存储
    created_at: str


# ============================================================
# 瑕疵检测（新版）
# ============================================================

class DefectInfo(BaseModel):
    """瑕疵信息（前端展示，不含程度）"""
    type: str                  # scratch/dent/stain/crack/peeling
    type_cn: str               # 划痕/磕碰/污渍/裂痕/掉漆
    bbox: List[int]            # [x1, y1, x2, y2]
    confidence: float          # 置信度


class DefectInfoDS(BaseModel):
    """瑕疵信息（DeepSeek 定价用，含程度）"""
    type: str
    type_cn: str
    bbox: List[int]
    area: int
    area_ratio: float
    confidence: float
    severity: str              # severe/moderate/minor/slight
    severity_label: str        # 重度/中度/轻度/轻微


class ProcessImageResponse(BaseModel):
    """全链路图片处理响应"""
    success: bool
    data: dict
    saved_files: dict
    preprocess_info: dict
    message: str
    deepseek_data: Optional[dict] = None
    price_suggestion: Optional[dict] = None


# ============================================================
# 分页
# ============================================================

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[Any] = []


# ============================================================
# 商城筛选 + 分页
# ============================================================

class MarketFilterParams(PaginationParams):
    """商城筛选 & 分页参数"""
    keyword: str = Field(default="", description="搜索关键词")
    category: str = Field(default="", description="品类筛选")
    condition: str = Field(default="", description="成色筛选")
    price_min: Optional[float] = Field(default=None, ge=0, description="最低价")
    price_max: Optional[float] = Field(default=None, ge=0, description="最高价")
    sort_by: str = Field(default="created_at", description="排序字段: created_at / price")
    sort_order: str = Field(default="desc", description="排序方向: asc / desc")


class MarketListResponse(BaseModel):
    """商城分页响应"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[Any] = []


# ============================================================
# 通用响应
# ============================================================

class BaseResponse(BaseModel):
    success: bool
    message: str = ""
    error: Optional[str] = None
    timestamp: str = ""