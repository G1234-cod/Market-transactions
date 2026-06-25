"""
CLIP 特征提取器
将图片和文本转换为 512 维向量
"""
import torch
import open_clip
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CLIPExtractor:
    """CLIP 特征提取器"""
    
    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "laion2b_s34b_b79k"):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name=model_name,
            pretrained=pretrained
        )
        self.model.eval()
        self.model.to(self.device)
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.embed_dim = 512
        logger.info(f"✅ CLIP 加载完成，设备: {self.device}")

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


_extractor = None

def get_extractor():
    global _extractor
    if _extractor is None:
        _extractor = CLIPExtractor()
    return _extractor