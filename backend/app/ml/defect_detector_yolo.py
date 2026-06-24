"""
YOLOv8 瑕疵检测器（需要训练好的 defect_best.pt）

功能：
1. YOLO 推理检测瑕疵
2. 不同形状 + 不同颜色代表不同程度的损伤
3. 程度信息不告诉用户（仅内部使用）
4. 返回结构化数据供 DeepSeek 定价
"""
import torch
from ultralytics import YOLO
from PIL import Image, ImageDraw
import logging
from pathlib import Path
from app.utils.font_utils import get_chinese_font

logger = logging.getLogger(__name__)


class DefectDetector:
    """
    YOLO 瑕疵检测器
    """
    
    # ==================== 瑕疵类别映射 ====================
    DEFECT_CLASSES = {
        0: 'scratch',
        1: 'dent',
        2: 'stain',
        3: 'crack',
        4: 'peeling',
        5: 'deformation'
    }
    
    DEFECT_NAMES_CN = {
        'scratch': '划痕',
        'dent': '磕碰',
        'stain': '污渍',
        'crack': '裂痕',
        'peeling': '掉漆',
        'deformation': '变形'
    }
    
    # ==================== 程度等级配置 ====================
    # 不同形状 + 不同颜色 = 不同程度
    SEVERITY_CONFIG = {
        'severe': {      # 重度 - 圆形 + 红色
            'shape': 'circle',
            'color': '#FF0000',
            'label': '重度'
        },
        'moderate': {    # 中度 - 矩形 + 橙色
            'shape': 'rectangle',
            'color': '#FF8C00',
            'label': '中度'
        },
        'minor': {       # 轻度 - 多边形 + 黄色
            'shape': 'polygon',
            'color': '#FFD700',
            'label': '轻度'
        },
        'slight': {      # 轻微 - 虚线框 + 蓝色
            'shape': 'dashed_box',
            'color': '#00BFFF',
            'label': '轻微'
        }
    }
    
    # 程度显示顺序（前端展示时，这个不显示，只显示类型名称）
    SEVERITY_ORDER = ['severe', 'moderate', 'minor', 'slight']

    def __init__(self):
        """初始化检测器，加载模型"""
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = None
        
        model_path = Path(__file__).parent / "models" / "defect_best.pt"
        if model_path.exists():
            self.model = YOLO(str(model_path))
            logger.info(f"✅ YOLO 瑕疵检测器加载完成，设备: {self.device}")
        else:
            logger.warning("⚠️ 未找到瑕疵检测模型 defect_best.pt，请先训练")
    
    def _determine_severity(self, defect_type: str, area_ratio: float, confidence: float) -> str:
        """
        根据瑕疵类型、面积占比、置信度判断程度等级
        
        Args:
            defect_type: 瑕疵类型 (scratch/dent/stain/crack/peeling/deformation)
            area_ratio: 瑕疵面积占图片比例
            confidence: 检测置信度
            
        Returns:
            str: severe / moderate / minor / slight
        """
        # 裂痕和变形 → 重度
        if defect_type in ['crack', 'deformation']:
            return 'severe'
        
        # 磕碰：面积大 → 中度，面积小 → 轻度
        if defect_type == 'dent':
            if area_ratio > 0.001:
                return 'moderate'
            else:
                return 'minor'
        
        # 划痕：长且面积大 → 中度，否则轻度
        if defect_type == 'scratch':
            if area_ratio > 0.0005:
                return 'moderate'
            else:
                return 'minor'
        
        # 污渍 → 轻微
        if defect_type == 'stain':
            return 'slight'
        
        # 掉漆：面积大 → 中度，面积小 → 轻度
        if defect_type == 'peeling':
            if area_ratio > 0.0005:
                return 'moderate'
            else:
                return 'minor'
        
        return 'minor'
    
    def _draw_shape(self, draw, x1, y1, x2, y2, shape: str, color: str, width: int = 3):
        """
        根据形状类型画不同的标注框
        
        Args:
            draw: ImageDraw 对象
            x1, y1, x2, y2: 边界框坐标
            shape: circle / rectangle / polygon / dashed_box
            color: 颜色
            width: 边框宽度
        """
        if shape == 'circle':
            # 圆形
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            radius = max((x2 - x1), (y2 - y1)) // 2
            draw.ellipse(
                [(center_x - radius, center_y - radius), 
                 (center_x + radius, center_y + radius)],
                outline=color, 
                width=width
            )
            
        elif shape == 'dashed_box':
            # 虚线框
            step = 8
            # 上边
            for i in range(0, (x2 - x1), step * 2):
                draw.line([(x1 + i, y1), (x1 + i + step, y1)], fill=color, width=width)
            # 下边
            for i in range(0, (x2 - x1), step * 2):
                draw.line([(x1 + i, y2), (x1 + i + step, y2)], fill=color, width=width)
            # 左边
            for i in range(0, (y2 - y1), step * 2):
                draw.line([(x1, y1 + i), (x1, y1 + i + step)], fill=color, width=width)
            # 右边
            for i in range(0, (y2 - y1), step * 2):
                draw.line([(x2, y1 + i), (x2, y1 + i + step)], fill=color, width=width)
                
        elif shape == 'polygon':
            # 多边形（六边形）
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            w = (x2 - x1) // 2
            h = (y2 - y1) // 2
            points = [
                (cx, y1),
                (x2, int(cy - h * 0.5)),
                (x2, int(cy + h * 0.5)),
                (cx, y2),
                (x1, int(cy + h * 0.5)),
                (x1, int(cy - h * 0.5))
            ]
            draw.polygon(points, outline=color, width=width)
            
        else:
            # 默认矩形
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=width)
    
    def detect_defects(self, image: Image.Image) -> list:
        """检测瑕疵（YOLO 推理）"""
        if self.model is None:
            return []
        
        results = self.model(image, conf=0.3)
        defects = []
        
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    class_name = self.DEFECT_CLASSES.get(cls_id, 'unknown')
                    class_cn = self.DEFECT_NAMES_CN.get(class_name, class_name)
                    
                    # 计算面积占比
                    area = (x2 - x1) * (y2 - y1)
                    area_ratio = area / (image.width * image.height)
                    
                    # 判断程度等级
                    severity = self._determine_severity(class_name, area_ratio, conf)
                    
                    defects.append({
                        'type': class_name,
                        'type_cn': class_cn,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'area': int(area),
                        'area_ratio': round(area_ratio, 4),
                        'severity': severity,          # 🔑 程度等级（内部使用）
                        'severity_label': self.SEVERITY_CONFIG[severity]['label'],  # 程度中文
                        'shape': self.SEVERITY_CONFIG[severity]['shape'],
                        'color': self.SEVERITY_CONFIG[severity]['color']
                    })
        
        logger.info(f"YOLO 检测到 {len(defects)} 个瑕疵")
        return defects

    def draw_annotations(self, image: Image.Image, defects: list) -> Image.Image:
        """
        在图片上画标注框
        ⚠️ 不同形状 + 不同颜色 = 不同程度
        但程度标签不显示给用户，只显示瑕疵类型
        """
        img = image.copy()
        draw = ImageDraw.Draw(img)
        font = get_chinese_font(20)
        
        for defect in defects:
            x1, y1, x2, y2 = defect['bbox']
            color = defect['color']
            shape = defect['shape']
            
            # 🔑 只显示类型名称，不显示程度
            label = defect['type_cn']
            
            # 画不同形状的框
            self._draw_shape(draw, x1, y1, x2, y2, shape, color, width=3)
            
            # 文字背景和标签
            draw.rectangle([(x1, y1 - 22), (x1 + 50, y1)], fill=color)
            draw.text((x1 + 2, y1 - 20), label, fill='white', font=font)
        
        return img

    def remove_background(self, image: Image.Image) -> Image.Image:
        """YOLO 版本不需要去背景，直接返回原图（接口兼容）"""
        return image

    def process(self, image: Image.Image) -> dict:
        """
        完整处理流程
        
        Returns:
            dict: {
                'bg_removed': 原图,
                'annotated': 标注图（不同形状+颜色，但程度不显示给用户）,
                'defects': 前端展示的瑕疵列表（不含程度）,
                'defects_for_ds': 发给 DeepSeek 的瑕疵列表（含程度）,
                'defect_count': 瑕疵总数
            }
        """
        # 1. 瑕疵检测
        defects = self.detect_defects(image)
        
        # 2. 画框标注（不同形状+颜色，程度不显示给用户）
        annotated = self.draw_annotations(image, defects)
        
        # 3. 分离数据：前端用的（不含程度）和 DeepSeek 用的（含程度）
        defects_for_frontend = []
        defects_for_ds = []
        
        for d in defects:
            # 前端数据：不包含程度信息
            defects_for_frontend.append({
                'type': d['type'],
                'type_cn': d['type_cn'],
                'bbox': d['bbox'],
                'confidence': d['confidence']
            })
            
            # DeepSeek 数据：包含程度信息
            defects_for_ds.append({
                'type': d['type'],
                'type_cn': d['type_cn'],
                'bbox': d['bbox'],
                'area': d['area'],
                'area_ratio': d['area_ratio'],
                'confidence': d['confidence'],
                'severity': d['severity'],           # 🔑 程度等级
                'severity_label': d['severity_label']  # 🔑 程度中文
            })
        
        return {
            'bg_removed': image,
            'annotated': annotated,
            'defects': defects_for_frontend,      # 前端展示（不含程度）
            'defects_for_ds': defects_for_ds,     # DeepSeek 定价（含程度）
            'defect_count': len(defects)
        }
    
    def get_defects_for_deepseek(self, defects: list) -> dict:
        """
        生成发送给 DeepSeek 的结构化数据
        
        Args:
            defects: 瑕疵列表（含程度信息）
            
        Returns:
            dict: DeepSeek 定价请求数据
        """
        if not defects:
            return {
                'has_defects': False,
                'summary': '商品外观完好，无瑕疵',
                'defects': [],
                'severity_summary': {'severe': 0, 'moderate': 0, 'minor': 0, 'slight': 0}
            }
        
        # 统计各程度数量
        severity_count = {'severe': 0, 'moderate': 0, 'minor': 0, 'slight': 0}
        for d in defects:
            severity_count[d['severity']] = severity_count.get(d['severity'], 0) + 1
        
        # 生成摘要
        has_severe = severity_count['severe'] > 0
        has_moderate = severity_count['moderate'] > 0
        
        if has_severe:
            summary = f"检测到 {severity_count['severe']} 处重度损伤，严重影响使用"
        elif has_moderate:
            summary = f"检测到 {severity_count['moderate']} 处中度损伤，影响外观"
        elif severity_count['minor'] > 0:
            summary = f"检测到 {severity_count['minor']} 处轻度损伤，细微痕迹"
        else:
            summary = f"检测到 {severity_count['slight']} 处轻微污渍，可清理"
        
        return {
            'has_defects': True,
            'summary': summary,
            'defects': defects,
            'severity_summary': severity_count,
            'total': len(defects)
        }