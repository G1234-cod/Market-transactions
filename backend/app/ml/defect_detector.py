import cv2
import numpy as np
from PIL import Image, ImageDraw
from rembg import remove
import logging
from app.utils.image_utils import pil_to_cv2, cv2_to_pil

logger = logging.getLogger(__name__)


class DefectDetector:
    DEFECT_TYPES = {
        'scratch': '划痕',
        'dent': '磕碰',
        'stain': '污渍',
        'crack': '裂痕',
        'corrosion': '腐蚀'
    }

    def __init__(self):
        logger.info("瑕疵检测器初始化完成")

    def remove_background(self, image: Image.Image) -> Image.Image:
        try:
            result = remove(image)
            logger.debug("背景消除成功")
            return result
        except Exception as e:
            logger.error(f"背景消除失败: {e}")
            return image

    def detect_defects_opencv(self, image: Image.Image) -> list:
        cv_image = pil_to_cv2(image)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        defects = []
        img_height, img_width = gray.shape

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 50:
                continue
            if area > img_width * img_height * 0.3:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            if aspect_ratio > 3:
                defect_type = 'scratch'
            elif area > 500:
                defect_type = 'stain'
            else:
                defect_type = 'dent'

            area_ratio = area / (img_width * img_height)

            defects.append({
                'type': defect_type,
                'type_cn': self.DEFECT_TYPES.get(defect_type, defect_type),
                'bbox': [int(x), int(y), int(x + w), int(y + h)],
                'area': int(area),
                'area_ratio': round(area_ratio, 4),
                'confidence': 0.7
            })

        logger.info(f"检测到 {len(defects)} 个瑕疵")
        return defects

    def draw_annotations(self, image: Image.Image, defects: list) -> Image.Image:
        img = image.copy()
        draw = ImageDraw.Draw(img)

        color_map = {
            'scratch': '#FF0000',
            'dent': '#FF8C00',
            'stain': '#FFD700',
            'crack': '#8B00FF',
            'corrosion': '#00BFFF'
        }

        for defect in defects:
            x1, y1, x2, y2 = defect['bbox']
            color = color_map.get(defect['type'], '#FF0000')
            label = defect['type_cn']
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
            try:
                bbox = draw.textbbox((x1, y1 - 20), label)
                draw.rectangle([bbox[0] - 4, bbox[1] - 4, bbox[2] + 4, bbox[3] + 4], fill=color)
                draw.text((x1, y1 - 20), label, fill='white')
            except:
                draw.text((x1, y1 - 20), label, fill=color)

        return img

    def process(self, image: Image.Image) -> dict:
        bg_removed = self.remove_background(image)
        defects = self.detect_defects_opencv(bg_removed)
        annotated = self.draw_annotations(bg_removed, defects)

        return {
            'bg_removed': bg_removed,
            'annotated': annotated,
            'defects': defects,
            'defect_count': len(defects)
        }