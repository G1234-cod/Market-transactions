"""应用配置管理 —— 从 .env 文件读取所有环境变量"""
import os
from dotenv import load_dotenv

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
    # 图片上传
    # ============================================================
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "static/uploads")
    MAX_IMAGE_COUNT: int = int(os.getenv("MAX_IMAGE_COUNT", "3"))

    # ============================================================
    # 🆕 ML 模型路径
    # ============================================================
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "app/ml/models/best.pt")
    DEFECT_MODEL_PATH: str = os.getenv("DEFECT_MODEL_PATH", "app/ml/models/defect_best.pt")


settings = Settings()