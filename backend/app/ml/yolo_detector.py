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

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLOv8 检测器"""
    
    def __init__(self, model_path: str = None):
        """初始化检测器"""
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # 加载模型
        if model_path and Path(model_path).exists():
            self.model = YOLO(model_path)
        else:
            default_path = Path(__file__).parent / "models" / "best.pt"
            if default_path.exists():
                self.model = YOLO(str(default_path))
            else:
                logger.warning("未找到模型文件，使用预训练模型 yolov8n.pt")
                self.model = YOLO('yolov8n.pt')
        
        logger.info(f"YOLOv8 加载完成，设备: {self.device}")
    
    def detect(self, image: Image.Image, conf_threshold: float = 0.5):
        """检测图片中的物品"""
        results = self.model(image, conf=conf_threshold)
        detections = []
        
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    class_name = self.model.names[int(box.cls[0])]
                    
                    detections.append({
                        'class_name': class_name,
                        'confidence': float(box.conf[0]),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })
        
        return detections
    
    def draw_boxes(self, image: Image.Image, detections: list):
        """在图片上画圈标注"""
        img = image.copy()
        draw = ImageDraw.Draw(img)
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        
        for i, d in enumerate(detections):
            x1, y1, x2, y2 = d['bbox']
            color = colors[i % len(colors)]
            label = f"{d['class_name']} {d['confidence']:.2f}"
            
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
            draw.text((x1, y1-10), label, fill=color)
        
        return img
    
    def to_base64(self, img: Image.Image) -> str:
        """转换为 Base64"""
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    
    def predict(self, image: Image.Image):
        """完整预测流程"""
        detections = self.detect(image)
        annotated = self.draw_boxes(image, detections)
        
        return {
            'detections': detections,
            'annotated_base64': self.to_base64(annotated),
            'count': len(detections)
        }