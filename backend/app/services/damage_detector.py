"""YOLO损伤检测服务"""
import os
import uuid
from typing import Tuple, Optional

import cv2
import numpy as np

from app.models.schemas import DamageRegion, DAMAGE_COLORS


class DamageDetector:
    """YOLO损伤检测器

    使用 YOLOv8-Seg 模型进行实例分割检测，
    支持检测划痕、凹陷、裂纹、污渍等损伤类型。
    """

    # 模型路径（训练后放置于此）
    MODEL_PATH: str = "models/damage_seg.pt"
    CONFIDENCE_THRESHOLD: float = 0.5  # 置信度阈值

    # 损伤类别映射（与训练时的类别对应）
    CLASS_NAMES = {
        0: "scratch",   # 划痕
        1: "dent",      # 凹陷
        2: "crack",     # 裂纹
        3: "stain",     # 污渍
        4: "other",     # 其他
    }

    _instance: Optional['DamageDetector'] = None
    _model: Optional[any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._load_model()

    def _load_model(self):
        """加载YOLOv8模型"""
        if self._model is None:
            try:
                from ultralytics import YOLO
                
                if os.path.exists(self.MODEL_PATH):
                    self._model = YOLO(self.MODEL_PATH)
                    print(f"✅ 加载损伤检测模型成功: {self.MODEL_PATH}")
                else:
                    print(f"⚠️ 警告: 模型文件不存在: {self.MODEL_PATH}")
                    print("请先运行 train_damage.py 训练模型")
                    self._model = None
                    
            except ImportError:
                print("❌ 错误: ultralytics 未安装")
                print("请运行: pip install ultralytics")
                self._model = None

    def detect(
        self,
        processed_image_path: str,
        original_image_path: str,
        scale_x: float,
        scale_y: float,
        output_dir: str
    ) -> Tuple[str, list[DamageRegion]]:
        """对预处理后的图片进行损伤检测，并在原图上标注

        Args:
            processed_image_path: 预处理后的图片路径
            original_image_path: 原图路径
            scale_x: 预处理时x方向缩放比例
            scale_y: 预处理时y方向缩放比例
            output_dir: 标注图输出目录

        Returns:
            Tuple[标注图URL, 损伤区域列表]
        """
        if self._model is None:
            return "", []

        original_img = cv2.imread(original_image_path)
        if original_img is None:
            raise ValueError(f"无法读取原图: {original_image_path}")

        original_height, original_width = original_img.shape[:2]
        results = self._model(processed_image_path, conf=self.CONFIDENCE_THRESHOLD)

        damage_regions = []
        annotated_img = original_img.copy()

        for result in results:
            if result.masks is None:
                continue

            for i, (mask, box, cls) in enumerate(zip(
                result.masks.xy,
                result.boxes,
                result.boxes.cls
            )):
                cls_id = int(cls)
                confidence = float(result.boxes.conf[i])
                damage_type = self.CLASS_NAMES.get(cls_id, "other")

                original_coords = self._convert_polygon_to_original(
                    mask, original_width, original_height, scale_x, scale_y
                )

                region = DamageRegion(
                    damage_type=damage_type,
                    confidence=confidence,
                    polygon=original_coords
                )
                damage_regions.append(region)

                annotated_img = self._draw_polygon(
                    annotated_img, original_coords, damage_type, confidence
                )

        annotated_filename = f"{uuid.uuid4().hex}_annotated.jpg"
        annotated_path = os.path.join(output_dir, annotated_filename)
        cv2.imwrite(annotated_path, annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

        annotated_url = f"/static/uploads/{annotated_filename}"
        return annotated_url, damage_regions

    def _convert_polygon_to_original(
        self,
        processed_polygon: np.ndarray,
        original_width: int,
        original_height: int,
        scale_x: float,
        scale_y: float
    ) -> list[list[float]]:
        """将预处理后图片的多边形坐标转换回原图坐标"""
        from app.services.image_processor import PREPROCESS_SIZE

        original_coords = []
        for point in processed_polygon:
            x, y = point[0], point[1]
            orig_x = (x - (PREPROCESS_SIZE - original_width / scale_x) / 2) * scale_x
            orig_y = (y - (PREPROCESS_SIZE - original_height / scale_y) / 2) * scale_y
            orig_x = max(0.0, min(float(orig_x), float(original_width)))
            orig_y = max(0.0, min(float(orig_y), float(original_height)))
            original_coords.append([float(orig_x), float(orig_y)])
        return original_coords

    def _draw_polygon(
        self,
        img: np.ndarray,
        polygon: list[list[float]],
        damage_type: str,
        confidence: float
    ) -> np.ndarray:
        """在图片上绘制多边形标注"""
        if len(polygon) < 3:
            return img

        color = DAMAGE_COLORS.get(damage_type, (255, 165, 0))
        points = np.array([[int(x), int(y)] for x, y in polygon], dtype=np.int32)

        overlay = img.copy()
        cv2.fillPoly(overlay, [points], color)
        cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
        cv2.polylines(img, [points], True, color, 2)

        center_x = int(np.mean([p[0] for p in polygon]))
        center_y = int(np.mean([p[1] for p in polygon]))
        label = f"{damage_type} {confidence:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)

        cv2.rectangle(
            img,
            (center_x - 5, center_y - text_h - 5),
            (center_x + text_w + 5, center_y + 5),
            color,
            -1
        )
        cv2.putText(img, label, (center_x, center_y - 2), font, font_scale, (255, 255, 255), thickness)

        return img


detector = DamageDetector()