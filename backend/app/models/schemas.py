"""Pydantic 数据模型 —— 统一请求/响应/内部 DTO"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


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
    user_id: int = 1
    image_url: str
    title: str
    desc: str
    price: float
    status: str = "published"
    category: str = ""  # 🆕 品类字段（用于以图搜图索引）


# ============================================================
# 发布历史
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
    likes: int = 0
    category: Optional[str] = None
    item_condition: str = "unknown"


# ============================================================
# 商城
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
    item_condition: str = "unknown"
    views: int = 0
    likes: int = 0
    created_at: str
    is_liked: bool = False


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
    DamageType.STAIN: (0, 255, 0),        # 绿色
    DamageType.OTHER: (255, 165, 0),      # 橙色
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
# 通用响应
# ============================================================

class BaseResponse(BaseModel):
    success: bool
    message: str = ""
    error: Optional[str] = None
    timestamp: str = ""