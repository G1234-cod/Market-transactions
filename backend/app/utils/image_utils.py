"""
图片处理工具函数
"""
from PIL import Image
import base64
import io
import os
import cv2
import numpy as np


def pil_to_base64(image: Image.Image, format: str = 'PNG') -> str:
    """PIL Image 转 Base64"""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode()


def base64_to_pil(base64_str: str) -> Image.Image:
    """Base64 转 PIL Image"""
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]
    return Image.open(io.BytesIO(base64.b64decode(base64_str)))


def save_image(image: Image.Image, path: str):
    """保存图片"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, quality=95, optimize=True)


def resize_image(image: Image.Image, max_size: int = 1024) -> Image.Image:
    """保持比例缩放图片"""
    width, height = image.size
    if max(width, height) <= max_size:
        return image
    ratio = max_size / max(width, height)
    new_size = (int(width * ratio), int(height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """PIL Image 转 OpenCV 格式（BGR）"""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv_image: np.ndarray) -> Image.Image:
    """OpenCV 格式转 PIL Image（RGB）"""
    return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))