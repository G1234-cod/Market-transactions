"""
图像预处理管道：尺寸统一 + 多物体判断 + 去背景 + 去噪
"""
from PIL import Image
import cv2
import numpy as np
from rembg import remove
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图片预处理器"""
    
    def __init__(self, target_size: int = 448):
        """
        初始化预处理器
        
        Args:
            target_size: 目标尺寸（宽高一致），默认 448×448
        """
        self.target_size = target_size
    
    def resize(self, image: Image.Image) -> Image.Image:
        """尺寸统一到 target_size × target_size"""
        return image.resize((self.target_size, self.target_size), Image.Resampling.LANCZOS)
    
    def select_main_object(self, image: Image.Image) -> tuple:
        """
        多物体判断，选择占比最大的物体
        
        Returns:
            (裁剪后的图片, 主物体占比, 是否成功)
        """
        cv_image = np.array(image)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
        
        # 边缘检测找物体
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.warning("未检测到任何物体")
            return image, 0.0, False
        
        # 找最大轮廓
        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        
        total_area = image.width * image.height
        object_area = w * h
        area_ratio = object_area / total_area
        
        logger.info(f"主物体面积占比: {area_ratio:.2%}")
        
        if area_ratio > 0.6:
            # 裁剪出主物体
            cropped = image.crop((x, y, x + w, y + h))
            return cropped, area_ratio, True
        elif area_ratio > 0.4:
            # 占比接近，需要用户确认
            logger.warning(f"⚠️ 多物体检测: 主物体占比 {area_ratio:.2%}，建议用户重新上传单物品图片")
            return image, area_ratio, False
        else:
            logger.warning(f"⚠️ 主物体占比过低: {area_ratio:.2%}")
            return image, area_ratio, False
    
    def remove_background(self, image: Image.Image) -> Image.Image:
        """去背景（rembg）"""
        try:
            result = remove(image)
            logger.debug("背景消除成功")
            return result
        except Exception as e:
            logger.error(f"去背景失败: {e}")
            return image
    
    def denoise(self, image: Image.Image) -> Image.Image:
        """去噪（高斯滤波）"""
        cv_image = np.array(image)
        denoised = cv2.GaussianBlur(cv_image, (5, 5), 0)
        return Image.fromarray(denoised)
    
    def process(self, image: Image.Image) -> dict:
        """
        完整预处理流程
        
        Returns:
            {
                'original': 原始图,
                'resized': 尺寸统一后的图,
                'main_object': 主物体裁剪图,
                'bg_removed': 去背景图,
                'denoised': 去噪图,
                'success': 是否成功,
                'area_ratio': 主物体占比
            }
        """
        result = {
            'original': image,
            'resized': None,
            'main_object': None,
            'bg_removed': None,
            'denoised': None,
            'success': True,
            'area_ratio': 0.0,
            'message': '预处理完成'
        }
        
        # 1. 尺寸统一
        resized = self.resize(image)
        result['resized'] = resized
        logger.info(f"📐 尺寸统一: {image.size} → {resized.size}")
        
        # 2. 多物体判断
        main_obj, area_ratio, success = self.select_main_object(resized)
        result['main_object'] = main_obj
        result['area_ratio'] = area_ratio
        result['success'] = success
        
        if not success:
            if area_ratio > 0.4:
                result['message'] = '检测到多个物体，请上传单物品图片'
            else:
                result['message'] = '未检测到明显的主物体'
            return result
        
        # 3. 去背景
        bg_removed = self.remove_background(main_obj)
        result['bg_removed'] = bg_removed
        
        # 4. 去噪
        denoised = self.denoise(bg_removed)
        result['denoised'] = denoised
        
        result['message'] = f'预处理完成，主物体占比 {area_ratio:.1%}'
        return result


# ============================================================
# 全局单例
# ============================================================
_preprocessor = None


def get_preprocessor(target_size: int = 448):
    """获取预处理器单例"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ImagePreprocessor(target_size=target_size)
    return _preprocessor


# ============================================================
# 便捷函数
# ============================================================

def preprocess_image(image: Image.Image, target_size: int = 448) -> dict:
    """预处理图片的便捷函数"""
    preprocessor = get_preprocessor(target_size)
    return preprocessor.process(image)