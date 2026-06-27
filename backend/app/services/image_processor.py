"""图片预处理服务 - 为 AI 识别和 YOLO 检测优化图片

⚠️ 预处理管线说明：
- 本模块使用 PREPROCESS_SIZE=1024 的尺寸做坐标转换（供 damage_detector.py 使用）
- app/utils/preprocess.py 使用 target_size=448 做另一种预处理（供 routers 中的视觉识别使用）
- 两条管线独立运行，各自由对应的路由调用，不会交叉污染

如需调整坐标转换精度，请修改此处的 PREPROCESS_SIZE。
"""
import os
import uuid
from typing import Tuple
import cv2
import numpy as np
from PIL import Image


# 预处理后的目标尺寸（用于坐标转换）
# 注意：damage_detector.py 中的 _convert_polygon_to_original 依赖此常量
PREPROCESS_SIZE = 1024


def preprocess_image(original_path: str, output_dir: str) -> Tuple[str, float, float]:
    """对图片进行预处理优化

    处理流程：
    1. 去噪（高斯模糊 + 中值滤波）
    2. 亮度/对比度自适应增强
    3. 锐化（拉普拉斯锐化）
    4. 尺寸归一化到正方形

    Args:
        original_path: 原图路径
        output_dir: 预处理后图片的输出目录

    Returns:
        Tuple[预处理后图片路径, 宽度比例, 高度比例]
        比例用于后续坐标转换
    """
    # 读取图片
    img = cv2.imread(original_path)
    if img is None:
        raise ValueError(f"无法读取图片: {original_path}")

    original_height, original_width = img.shape[:2]

    # 1. 去噪 - 使用高斯模糊和中值滤波
    img = _denoise(img)

    # 2. 亮度/对比度增强
    img = _enhance_brightness_contrast(img)

    # 3. 锐化 - 增强边缘细节
    img = _sharpen(img)

    # 4. 尺寸归一化 - 等比缩放后padding到正方形
    img, scale_x, scale_y = _resize_to_square(img, PREPROCESS_SIZE)

    # 保存预处理后的图片
    filename = f"{uuid.uuid4().hex}_processed.jpg"
    output_path = os.path.join(output_dir, filename)
    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    return output_path, scale_x, scale_y


def _denoise(img: np.ndarray) -> np.ndarray:
    """去噪处理"""
    # 转换为灰度图进行去噪
    # 使用快速NL-means去噪
    img_denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    return img_denoised


def _enhance_brightness_contrast(img: np.ndarray) -> np.ndarray:
    """自适应亮度/对比度增强"""
    # 转换为LAB色彩空间
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # 对L通道进行CLAHE（对比度受限自适应直方图均衡化）
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    # 合并通道
    lab = cv2.merge([l, a, b])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # 轻微增加饱和度
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = np.clip(s * 1.1, 0, 255).astype(np.uint8)
    hsv = cv2.merge([h, s, v])
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return img


def _sharpen(img: np.ndarray) -> np.ndarray:
    """锐化处理 - 增强边缘细节"""
    # 创建锐化 kernel
    kernel = np.array([
        [-1, -1, -1],
        [-1,  9, -1],
        [-1, -1, -1]
    ], dtype=np.float32)

    # 可选：添加USM锐化（更自然）
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

    return img


def _resize_to_square(img: np.ndarray, target_size: int) -> Tuple[np.ndarray, float, float]:
    """等比缩放图片到正方形，空白区域用灰色填充

    Returns:
        Tuple[处理后的图片, 宽度比例, 高度比例]
        比例用于将检测坐标转换回原图坐标
    """
    h, w = img.shape[:2]

    # 计算缩放比例
    scale = min(target_size / w, target_size / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # 缩放图片
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 创建正方形画布（灰色背景）
    canvas = np.full((target_size, target_size, 3), 128, dtype=np.uint8)

    # 计算居中偏移量
    x_offset = (target_size - new_w) // 2
    y_offset = (target_size - new_h) // 2

    # 将缩放后的图片放到画布中央
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = img_resized

    return canvas, w / new_w, h / new_h


def convert_coords_to_original(
    processed_coords: list,
    original_width: int,
    original_height: int,
    scale_x: float,
    scale_y: float
) -> list:
    """将预处理后图片的坐标转换回原图坐标

    Args:
        processed_coords: 预处理后图片中的坐标 [[x1,y1], [x2,y2], ...]
        original_width: 原图宽度
        original_height: 原图高度
        scale_x: 预处理时x方向缩放比例
        scale_y: 预处理时y方向缩放比例

    Returns:
        转换到原图的坐标列表
    """
    original_coords = []
    for x, y in processed_coords:
        # 先转回原图缩放后的尺寸，再乘以比例得到原图坐标
        orig_x = int((x - (PREPROCESS_SIZE - original_width / scale_x) / 2) * scale_x)
        orig_y = int((y - (PREPROCESS_SIZE - original_height / scale_y) / 2) * scale_y)
        # 确保坐标在原图范围内
        orig_x = max(0, min(orig_x, original_width))
        orig_y = max(0, min(orig_y, original_height))
        original_coords.append([orig_x, orig_y])
    return original_coords


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """获取图片尺寸"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")
    h, w = img.shape[:2]
    return w, h
