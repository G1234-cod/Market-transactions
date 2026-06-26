"""
CLIP 特征提取器
将图片和文本转换为 512 维向量
"""
import torch
import open_clip
from PIL import Image
import numpy as np
import logging
import threading
from typing import Optional

from app.config import settings, get_clip_model_name, get_clip_pretrained

logger = logging.getLogger(__name__)


class CLIPExtractor:
    """CLIP 特征提取器"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        pretrained: Optional[str] = None
    ):
        """
        初始化 CLIP 提取器
        
        Args:
            model_name: 模型名称（如 ViT-B-32），默认从配置读取
            pretrained: 预训练权重，默认从配置读取
        """
        # ✅ 从配置读取，并确保格式兼容
        self.model_name = model_name or get_clip_model_name()
        self.pretrained = pretrained or get_clip_pretrained()
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name=self.model_name,
            pretrained=self.pretrained
        )
        self.model.eval()
        self.model.to(self.device)
        self.tokenizer = open_clip.get_tokenizer(self.model_name)
        self.embed_dim = 512
        
        logger.info(f"✅ CLIP 加载完成")
        logger.info(f"   模型: {self.model_name}")
        logger.info(f"   预训练: {self.pretrained}")
        logger.info(f"   设备: {self.device}")
        logger.info(f"   向量维度: {self.embed_dim}")

    def extract_image(self, image: Image.Image) -> np.ndarray:
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(image_tensor)
        features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().cpu().numpy().astype(np.float32)

    def extract_text(self, text: str) -> np.ndarray:
        text_tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad():
            features = self.model.encode_text(text_tokens)
        features = features / features.norm(dim=-1, keepdim=True)
        return features.squeeze().cpu().numpy().astype(np.float32)


# ============================================================
# ✅ 线程安全的单例（双重检查锁定）
# ============================================================

_extractor: Optional[CLIPExtractor] = None
_lock = threading.Lock()


def get_extractor(
    model_name: Optional[str] = None,
    pretrained: Optional[str] = None
) -> CLIPExtractor:
    """
    获取 CLIP 提取器单例（线程安全）
    
    Args:
        model_name: 模型名称，默认从配置读取
        pretrained: 预训练权重，默认从配置读取
    
    Returns:
        CLIPExtractor: 单例实例
    """
    global _extractor
    
    # ✅ 快速路径（无锁）
    if _extractor is not None:
        return _extractor
    
    # ✅ 慢速路径（有锁）
    with _lock:
        # ✅ 双重检查
        if _extractor is not None:
            return _extractor
        
        logger.info("🔄 初始化 CLIP 提取器（单例）...")
        _extractor = CLIPExtractor(
            model_name=model_name,
            pretrained=pretrained
        )
        return _extractor


def reset_extractor() -> None:
    """重置提取器（用于测试）"""
    global _extractor
    with _lock:
        if _extractor is not None:
            if hasattr(_extractor, 'model'):
                del _extractor.model
            _extractor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("🔄 CLIP 提取器已重置")