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
    # CLIP 模型配置
    # ============================================================
    CLIP_MODEL_NAME: str = os.getenv("CLIP_MODEL_NAME", "ViT-B/32")

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
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    upload_path = settings.BASE_DIR / settings.UPLOAD_DIR
    upload_path.mkdir(parents=True, exist_ok=True)
    for subdir in ["raw", "bg_removed", "annotated"]:
        (upload_path / subdir).mkdir(parents=True, exist_ok=True)
    
    data_dir = settings.BASE_DIR / "data"
    for subdir in ["error_data", "faiss_index", "crawler_data", "hard_cases", "qdrant"]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    error_data_dir = settings.BASE_DIR / settings.ERROR_DATA_DIR
    for subdir in ["images", "labels", "metadata"]:
        (error_data_dir / subdir).mkdir(parents=True, exist_ok=True)


ensure_directories()


# ============================================================
# URL 工具函数（统一在这里定义）
# ============================================================

def get_base_url(request: Optional[Request] = None) -> str:
    """
    获取服务器基础URL
    
    Args:
        request: FastAPI Request 对象（可选）
    
    Returns:
        str: 基础URL，如 https://yourdomain.com
        
    优先级：
    1. 从请求头 X-Forwarded-Proto 和 Host 推断（生产环境推荐）
    2. 从 request 对象推断
    3. 从配置文件读取 BASE_URL
    4. 默认值 http://localhost:8000
    """
    if request is not None:
        # 检查是否在代理后面（生产环境常见）
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        forwarded_host = request.headers.get("X-Forwarded-Host")
        
        if forwarded_proto and forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}"
        
        # 直接从请求推断
        return f"{request.url.scheme}://{request.url.netloc}"
    
    # 从配置文件读取
    return settings.BASE_URL


def build_full_url(
    relative_path: str,
    request: Optional[Request] = None,
    base_url: Optional[str] = None,
) -> str:
    """
    构建完整的 URL
    
    Args:
        relative_path: 相对路径，如 /static/uploads/raw/test.jpg
        request: FastAPI Request 对象（可选）
        base_url: 自定义基础URL（覆盖其他设置）
    
    Returns:
        str: 完整URL
    """
    if not relative_path:
        return ""
    
    # 如果已经是完整URL，直接返回
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return relative_path
    
    if base_url is None:
        base_url = get_base_url(request)
    
    # 确保相对路径以 / 开头
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    
    return f"{base_url}{relative_path}"


def get_static_url(
    file_path: str,
    request: Optional[Request] = None,
) -> str:
    """
    获取静态文件的完整URL
    
    Args:
        file_path: 文件相对路径，如 uploads/raw/test.jpg
        request: FastAPI Request 对象（可选）
    
    Returns:
        str: 完整URL
    """
    if not file_path:
        return ""
    
    # 如果已经是完整URL，直接返回
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path
    
    # 确保路径不以 / 开头
    if file_path.startswith("/"):
        file_path = file_path[1:]
    
    return build_full_url(f"/{settings.STATIC_PREFIX}/{file_path}", request)


# ============================================================
# 便捷函数
# ============================================================

def get_model_path(model_type: str = "yolo") -> Path:
    if model_type == "defect":
        return Path(settings.DEFECT_MODEL_PATH)
    return Path(settings.YOLO_MODEL_PATH)


def is_production() -> bool:
    return settings.ENV == "production"


def is_development() -> bool:
    return settings.ENV == "development"


def get_error_data_dir() -> Path:
    return settings.BASE_DIR / settings.ERROR_DATA_DIR


def get_qdrant_data_dir() -> Path:
    return settings.BASE_DIR / "data" / "qdrant"


# ============================================================
# 打印配置信息
# ============================================================

def print_config():
    print("=" * 70)
    print("📋 项目配置信息")
    print("=" * 70)
    print(f"\n🔧 运行环境:")
    print(f"  ENV: {settings.ENV}")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"\n🌐 服务器:")
    print(f"  BASE_URL: {settings.BASE_URL}")
    print(f"  STATIC_PREFIX: {settings.STATIC_PREFIX}")
    print(f"\n💾 数据库:")
    print(f"  DB_HOST: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"  DB_NAME: {settings.DB_NAME}")
    print(f"\n📁 ML 模型:")
    print(f"  MODELS_DIR: {settings.MODELS_DIR}")
    print(f"  YOLO_MODEL_PATH: {settings.YOLO_MODEL_PATH}")
    print(f"  DEFECT_MODEL_PATH: {settings.DEFECT_MODEL_PATH}")
    print(f"\n🔍 Qdrant:")
    print(f"  QDRANT_HOST: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    print(f"  QDRANT_COLLECTION: {settings.QDRANT_COLLECTION}")
    print(f"\n🌍 CORS:")
    print(f"  ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
    print("=" * 70)


if __name__ == "__main__":
    print_config()