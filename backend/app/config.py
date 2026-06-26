"""应用配置管理 —— 从 .env 文件读取所有环境变量"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import Request

load_dotenv()


class Settings:
    # ============================================================
    # DeepSeek API
    # ============================================================
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ============================================================
    # Qwen API（阿里云百炼）
    # ============================================================
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    QWEN_VL_MODEL: str = os.getenv("QWEN_VL_MODEL", "qwen-vl-max")

    # ============================================================
    # MySQL 数据库
    # ============================================================
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "market_transactions")

    # ============================================================
    # JWT 认证配置
    # ============================================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # ============================================================
    # 图片上传
    # ============================================================
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "static/uploads")
    MAX_IMAGE_COUNT: int = int(os.getenv("MAX_IMAGE_COUNT", "3"))
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB

    # ============================================================
    # ML 模型路径
    # ============================================================
    BASE_DIR: Path = Path(__file__).parent.parent
    MODELS_DIR: Path = BASE_DIR / "app" / "ml" / "models"

    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", str(MODELS_DIR / "best.pt"))
    DEFECT_MODEL_PATH: str = os.getenv("DEFECT_MODEL_PATH", str(MODELS_DIR / "defect_best.pt"))
    YOLO_PRETRAINED_PATH: str = os.getenv("YOLO_PRETRAINED_PATH", "yolov8n.pt")

    # ============================================================
    # Qdrant 向量数据库配置
    # ============================================================
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "market_items")
    QDRANT_VECTOR_SIZE: int = int(os.getenv("QDRANT_VECTOR_SIZE", "512"))

    # ============================================================
    # ✅ CLIP 模型配置（使用 open_clip 兼容格式：连字符）
    # ============================================================
    # open_clip 期望格式: ViT-B-32, ViT-B-16, RN50, RN101
    # HuggingFace 格式 (ViT-B/32) 不兼容！
    CLIP_MODEL_NAME: str = os.getenv("CLIP_MODEL_NAME", "ViT-B-32")
    CLIP_PRETRAINED: str = os.getenv("CLIP_PRETRAINED", "laion2b_s34b_b79k")

    # ============================================================
    # 服务器配置
    # ============================================================
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    STATIC_PREFIX: str = os.getenv("STATIC_PREFIX", "/static")

    # ============================================================
    # 后台任务配置
    # ============================================================
    BACKGROUND_TASK_RETRIES: int = int(os.getenv("BACKGROUND_TASK_RETRIES", "3"))
    BACKGROUND_TASK_RETRY_DELAY: float = float(os.getenv("BACKGROUND_TASK_RETRY_DELAY", "1.0"))
    BACKGROUND_TASK_ENABLED: bool = os.getenv("BACKGROUND_TASK_ENABLED", "true").lower() == "true"
    ERROR_DATA_DIR: str = os.getenv("ERROR_DATA_DIR", "data/error_data")

    # ============================================================
    # 日志与运行环境
    # ============================================================
    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ============================================================
    # CORS 配置
    # ============================================================
    @property
    def ALLOWED_ORIGINS(self) -> list:
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if origins_str:
            return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
        if self.ENV == "development":
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
            ]
        return ["https://yourdomain.com", "https://www.yourdomain.com"]


settings = Settings()


# ============================================================
# 确保必要的目录存在
# ============================================================

def ensure_directories():
    """确保所有必要的目录存在"""
    # 模型目录
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 上传目录
    upload_path = settings.BASE_DIR / settings.UPLOAD_DIR
    upload_path.mkdir(parents=True, exist_ok=True)
    for subdir in ["raw", "bg_removed", "annotated"]:
        (upload_path / subdir).mkdir(parents=True, exist_ok=True)
    
    # 数据目录
    data_dir = settings.BASE_DIR / "data"
    for subdir in ["error_data", "faiss_index", "crawler_data", "hard_cases", "qdrant"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    # 错误数据目录
    error_data_dir = settings.BASE_DIR / settings.ERROR_DATA_DIR
    for subdir in ["images", "labels", "metadata"]:
        (error_data_dir / subdir).mkdir(parents=True, exist_ok=True)


ensure_directories()


# ============================================================
# URL 工具函数
# ============================================================

def get_base_url(request: Optional[Request] = None) -> str:
    """
    获取服务器基础URL
    
    Args:
        request: FastAPI Request 对象（可选）
    
    Returns:
        str: 基础URL
        
    优先级：
    1. 从请求头 X-Forwarded-Proto 和 Host 推断
    2. 从 request 对象推断
    3. 从配置文件读取 BASE_URL
    """
    if request is not None:
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        forwarded_host = request.headers.get("X-Forwarded-Host")
        
        if forwarded_proto and forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}"
        
        return f"{request.url.scheme}://{request.url.netloc}"
    
    return settings.BASE_URL


def build_full_url(
    relative_path: str,
    request: Optional[Request] = None,
    base_url: Optional[str] = None,
) -> str:
    """
    构建完整的 URL
    """
    if not relative_path:
        return ""
    
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return relative_path
    
    if base_url is None:
        base_url = get_base_url(request)
    
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    
    return f"{base_url}{relative_path}"


def get_static_url(
    file_path: str,
    request: Optional[Request] = None,
) -> str:
    """
    获取静态文件的完整URL
    """
    if not file_path:
        return ""
    
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path
    
    if file_path.startswith("/"):
        file_path = file_path[1:]
    
    return build_full_url(f"/{settings.STATIC_PREFIX}/{file_path}", request)


# ============================================================
# 便捷函数
# ============================================================

def get_model_path(model_type: str = "yolo") -> Path:
    """获取模型路径"""
    if model_type == "defect":
        return Path(settings.DEFECT_MODEL_PATH)
    return Path(settings.YOLO_MODEL_PATH)


def is_production() -> bool:
    """是否为生产环境"""
    return settings.ENV == "production"


def is_development() -> bool:
    """是否为开发环境"""
    return settings.ENV == "development"


def get_error_data_dir() -> Path:
    """获取错误数据目录"""
    return settings.BASE_DIR / settings.ERROR_DATA_DIR


def get_qdrant_data_dir() -> Path:
    """获取 Qdrant 数据目录"""
    return settings.BASE_DIR / "data" / "qdrant"


# ============================================================
# ✅ CLIP 相关便捷函数
# ============================================================

def get_clip_model_name() -> str:
    """
    获取 CLIP 模型名称（确保格式兼容 open_clip）
    
    Returns:
        str: 模型名称，如 "ViT-B-32"
    """
    model_name = settings.CLIP_MODEL_NAME
    
    # ✅ 自动转换 HuggingFace 格式 (ViT-B/32 → ViT-B-32)
    if '/' in model_name:
        converted = model_name.replace('/', '-')
        logger.warning(f"⚠️ CLIP 模型名称 '{model_name}' 包含 '/'，自动转换为 '{converted}'")
        return converted
    
    return model_name


def get_clip_pretrained() -> str:
    """获取 CLIP 预训练权重名称"""
    return settings.CLIP_PRETRAINED


# ============================================================
# 配置验证
# ============================================================

def validate_config() -> list:
    """
    验证配置是否正确
    
    Returns:
        list: 错误列表（空表示全部正确）
    """
    errors = []

    # API Key 验证
    if not settings.DEEPSEEK_API_KEY:
        errors.append("❌ DEEPSEEK_API_KEY 未配置")
    if not settings.DASHSCOPE_API_KEY:
        errors.append("❌ DASHSCOPE_API_KEY 未配置")

    # 数据库验证
    if not settings.DB_HOST:
        errors.append("❌ DB_HOST 未配置")
    if not settings.DB_NAME:
        errors.append("❌ DB_NAME 未配置")

    # 模型文件验证（仅警告，不阻止启动）
    if not Path(settings.YOLO_MODEL_PATH).exists():
        errors.append(f"⚠️ YOLO_MODEL_PATH 不存在: {settings.YOLO_MODEL_PATH}")
    if not Path(settings.DEFECT_MODEL_PATH).exists():
        errors.append(f"⚠️ DEFECT_MODEL_PATH 不存在: {settings.DEFECT_MODEL_PATH}")

    # ✅ CLIP 模型名称验证
    clip_name = settings.CLIP_MODEL_NAME
    valid_clip_formats = ['ViT-B-32', 'ViT-B-16', 'ViT-L-14', 'RN50', 'RN101', 'RN50x4']
    if clip_name not in valid_clip_formats and '/' not in clip_name:
        errors.append(f"⚠️ CLIP_MODEL_NAME '{clip_name}' 可能不被 open_clip 支持")

    # 生产环境特殊验证
    if is_production():
        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            errors.append("❌ 生产环境 SECRET_KEY 使用默认值，请修改！")
        if "localhost" in settings.ALLOWED_ORIGINS:
            errors.append("⚠️ 生产环境 ALLOWED_ORIGINS 包含 localhost")

    return errors


def check_config():
    """检查配置并打印结果"""
    errors = validate_config()
    
    if errors:
        print("=" * 70)
        print("⚠️ 配置验证发现以下问题:")
        print("=" * 70)
        for err in errors:
            print(f"  {err}")
        print("=" * 70)
        return False
    else:
        print("✅ 配置验证通过")
        return True


# ============================================================
# 打印配置信息
# ============================================================

def print_config():
    """打印当前配置（隐藏敏感信息）"""
    print("=" * 70)
    print("📋 项目配置信息")
    print("=" * 70)
    
    print("\n🔧 运行环境:")
    print(f"  ENV: {settings.ENV}")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
    
    print("\n🌐 服务器:")
    print(f"  BASE_URL: {settings.BASE_URL}")
    print(f"  STATIC_PREFIX: {settings.STATIC_PREFIX}")
    
    print("\n💾 数据库:")
    print(f"  DB_HOST: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  DB_NAME: {settings.DB_NAME}")
    
    print("\n📁 ML 模型:")
    print(f"  MODELS_DIR: {settings.MODELS_DIR}")
    print(f"  YOLO_MODEL_PATH: {settings.YOLO_MODEL_PATH}")
    print(f"  DEFECT_MODEL_PATH: {settings.DEFECT_MODEL_PATH}")
    
    print("\n🔍 Qdrant:")
    print(f"  QDRANT_HOST: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    print(f"  QDRANT_COLLECTION: {settings.QDRANT_COLLECTION}")
    
    print("\n🔐 JWT:")
    print(f"  ALGORITHM: {settings.ALGORITHM}")
    print(f"  ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    print(f"  SECRET_KEY: {'*' * 20}（已隐藏）")
    
    print("\n🌍 CORS:")
    print(f"  ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
    
    print("\n🧠 CLIP 模型:")
    print(f"  CLIP_MODEL_NAME: {settings.CLIP_MODEL_NAME}")
    print(f"  CLIP_PRETRAINED: {settings.CLIP_PRETRAINED}")
    print(f"  → open_clip 兼容名称: {get_clip_model_name()}")
    
    print("=" * 70)


if __name__ == "__main__":
    print_config()
    print("\n")
    check_config()