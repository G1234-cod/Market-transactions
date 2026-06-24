"""
中文字体工具 - 一键配置
"""
from PIL import ImageFont
import os
import logging

logger = logging.getLogger(__name__)

# 缓存字体对象
_font_cache = {}


def get_chinese_font(size: int = 20):
    """
    获取中文字体，自动适配不同系统
    缓存字体对象，避免重复加载
    """
    if size in _font_cache:
        return _font_cache[size]

    # 按优先级尝试不同系统的字体路径
    font_paths = [
        # Windows
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        # Mac
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[size] = font
                logger.info(f"✅ 加载中文字体: {path}")
                return font
            except Exception as e:
                logger.warning(f"字体加载失败 {path}: {e}")
                continue

    # 全部失败，使用默认字体（不支持中文）
    logger.warning("⚠️ 未找到中文字体，将使用默认字体")
    _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def get_font_or_default(size: int = 20):
    """获取字体，如果中文不可用则返回默认"""
    return get_chinese_font(size)