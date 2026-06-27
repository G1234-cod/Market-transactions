"""
YOLOv8 物品检测器 - 独立模块
"""
from ultralytics import YOLO
from PIL import Image, ImageDraw
import torch
import logging
from pathlib import Path
import base64
import io
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLOv8 检测器"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.5,
        device: str = "auto"
    ):
        """
        初始化检测器
        
        Args:
            model_path: 模型权重路径，默认从 settings 读取
            conf_threshold: 置信度阈值
            device: 运行设备 (cpu/cuda/auto)
        """
        # 设备选择
        if device == "auto":
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        self.conf_threshold = conf_threshold
        self.model_path = None  # 记录实际加载的模型路径
        
        # ✅ 加载模型（多级回退）
        self.model = self._load_model(model_path)
        
        if self.model is not None:
            logger.info(f"YOLOv8 加载完成")
            logger.info(f"   模型路径: {self.model_path}")
            logger.info(f"   设备: {self.device}")
    
    def _load_model(self, model_path: Optional[str] = None) -> YOLO:
        """加载 YOLO 模型（多级回退）"""
        # 1. 优先使用传入的路径
        if model_path and Path(model_path).exists():
            logger.info(f"✅ 使用传入模型: {model_path}")
            self.model_path = str(model_path)
            return YOLO(model_path)
        
        # 2. 使用配置文件中的路径
        config_path = Path(settings.YOLO_MODEL_PATH)
        if config_path.exists():
            logger.info(f"✅ 使用配置模型: {config_path}")
            self.model_path = str(config_path)
            return YOLO(str(config_path))
        
        # 3. 使用默认路径（相对于当前文件）
        default_path = Path(__file__).parent / "models" / "best.pt"
        if default_path.exists():
            logger.info(f"✅ 使用默认模型: {default_path}")
            self.model_path = str(default_path)
            return YOLO(str(default_path))
        
        # 4. 回退到预训练模型
        from app.config import settings as _settings
        pretrained = _settings.YOLO_PRETRAINED_PATH
        logger.warning(f"⚠️ 未找到模型文件，使用预训练模型 {pretrained}")
        self.model_path = pretrained
        return YOLO(pretrained)
    
    def detect(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        检测图片中的物品
        
        Args:
            image: PIL Image 对象
            conf_threshold: 置信度阈值（覆盖默认值）
        
        Returns:
            检测结果列表，每个结果包含:
                - class_name: str
                - confidence: float
                - bbox: [x1, y1, x2, y2] (float)
        """
        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        
        results = self.model(image, conf=conf, device=self.device, verbose=False)
        detections = []
        
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    class_name = self.model.names[int(box.cls[0])]
                    
                    detections.append({
                        'class_name': class_name,
                        'confidence': float(box.conf[0]),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]  # ✅ float 类型
                    })
        
        return detections
    
    def draw_boxes(
        self,
        image: Image.Image,
        detections: List[Dict[str, Any]],
        show_confidence: bool = True
    ) -> Image.Image:
        """
        在图片上画圈标注
        
        Args:
            image: PIL Image 对象
            detections: 检测结果列表
            show_confidence: 是否显示置信度
        
        Returns:
            标注后的 PIL Image
        """
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        # 颜色映射（按类别）
        colors = {
            'phone': '#FF6B6B',
            'laptop': '#4ECDC4',
            'tablet': '#45B7D1',
            'ipad': '#45B7D1',
            'camera': '#96CEB4',
            'headphone': '#FFEAA7',
            'watch': '#DDA0DD',
            'default': '#FF6B6B'
        }
        
        for d in detections:
            # ✅ 将 float 转为 int（PIL 需要 int 坐标）
            bbox = d['bbox']
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            
            class_name = d['class_name']
            confidence = d['confidence']
            
            # 根据类别选择颜色
            color = colors.get(class_name.lower(), colors['default'])
            
            # 标签文字
            if show_confidence:
                label = f"{class_name} {confidence:.2f}"
            else:
                label = class_name
            
            # 画矩形框
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
            
            # 画标签背景
            try:
                # 获取文字大小
                bbox = draw.textbbox((0, 0), label)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 画文字背景
                draw.rectangle(
                    [(x1, y1 - text_height - 4), (x1 + text_width, y1)],
                    fill=color
                )
                # 写文字
                draw.text((x1, y1 - text_height - 2), label, fill='white')
            except Exception:
                # 简化版
                draw.text((x1, y1 - 10), label, fill=color)
        
        return img
    
    def to_base64(self, img: Image.Image) -> str:
        """转换为 Base64"""
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    
    def predict(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None,
        show_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        完整预测流程
        
        Args:
            image: PIL Image 对象
            conf_threshold: 置信度阈值
            show_confidence: 是否在标注图中显示置信度
        
        Returns:
            {
                'detections': [...],
                'annotated_base64': '...',
                'count': int
            }
        """
        detections = self.detect(image, conf_threshold)
        annotated = self.draw_boxes(image, detections, show_confidence)
        
        return {
            'detections': detections,
            'annotated_base64': self.to_base64(annotated),
            'count': len(detections)
        }
    
    def predict_from_path(
        self,
        image_path: str,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        从文件路径加载图片并预测
        
        Args:
            image_path: 图片文件路径
            conf_threshold: 置信度阈值
        
        Returns:
            同 predict()
        """
        image = Image.open(image_path)
        return self.predict(image, conf_threshold)


# ============================================================
# 单例实例（懒加载）
# ============================================================

_detector: Optional[YOLODetector] = None


def get_yolo_detector(
    model_path: Optional[str] = None,
    conf_threshold: float = 0.5
) -> YOLODetector:
    """
    获取 YOLO 检测器单例
    
    Args:
        model_path: 模型路径（仅首次调用时生效）
        conf_threshold: 置信度阈值（仅首次调用时生效）
    
    Returns:
        YOLODetector 实例
    """
    global _detector
    if _detector is None:
        _detector = YOLODetector(
            model_path=model_path,
            conf_threshold=conf_threshold
        )
    return _detector


# ============================================================
# 便捷函数
# ============================================================

def detect_objects(
    image: Image.Image,
    conf_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    快捷检测函数
    
    Args:
        image: PIL Image 对象
        conf_threshold: 置信度阈值
    
    Returns:
        检测结果列表
    """
    detector = get_yolo_detector()
    return detector.detect(image, conf_threshold)


def detect_objects_from_path(
    image_path: str,
    conf_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    从文件路径快捷检测
    
    Args:
        image_path: 图片文件路径
        conf_threshold: 置信度阈值
    
    Returns:
        检测结果列表
    """
    image = Image.open(image_path)
    return detect_objects(image, conf_threshold)