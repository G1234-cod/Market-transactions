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
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.utils.font_utils import get_chinese_font

logger = logging.getLogger(__name__)


class DefectDetector:
    """
    YOLO 瑕疵检测器
    """
    
    # ==================== 瑕疵类别映射 ====================
    # ✅ Kaputt 7 类缺陷（与 trainzui/train2 训练数据一致）
    DEFECT_CLASSES = {
        0: 'penetration',       # 穿透
        1: 'deformation',       # 变形
        2: 'actuation',         # 功能故障
        3: 'deconstruction',    # 结构损坏
        4: 'spillage',          # 溢漏
        5: 'superficial',       # 表面瑕疵
        6: 'missing_unit',      # 部件缺失
    }

    DEFECT_NAMES_CN = {
        'penetration': '穿透',
        'deformation': '变形',
        'actuation': '功能故障',
        'deconstruction': '结构损坏',
        'spillage': '溢漏',
        'superficial': '表面瑕疵',
        'missing_unit': '部件缺失',
    }
    
    # ==================== 程度等级配置 ====================
    SEVERITY_CONFIG = {
        'severe': {
            'shape': 'circle',
            'color': '#FF0000',
            'label': '重度',
            'rgb_color': (255, 0, 0)
        },
        'moderate': {
            'shape': 'rectangle',
            'color': '#FF8C00',
            'label': '中度',
            'rgb_color': (255, 140, 0)
        },
        'minor': {
            'shape': 'polygon',
            'color': '#FFD700',
            'label': '轻度',
            'rgb_color': (255, 215, 0)
        },
        'slight': {
            'shape': 'dashed_box',
            'color': '#00BFFF',
            'label': '轻微',
            'rgb_color': (0, 191, 255)
        }
    }
    
    SEVERITY_ORDER = ['severe', 'moderate', 'minor', 'slight']

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.3,
        device: str = "auto"
    ):
        """
        初始化瑕疵检测器
        
        Args:
            model_path: 模型权重路径，默认从 settings 读取
            conf_threshold: 置信度阈值
            device: 运行设备 (cpu/cuda/auto)
        """
        if device == "auto":
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        self.conf_threshold = conf_threshold
        self.model_path = None
        self._load_failed = False
        
        # ✅ 加载模型（不降级到通用模型）
        self.model = self._load_model(model_path)
        
        if self.model is not None:
            logger.info(f"✅ YOLO 瑕疵检测器加载完成")
            logger.info(f"   模型路径: {self.model_path}")
            logger.info(f"   设备: {self.device}")
            logger.info(f"   类别数: {len(self.DEFECT_CLASSES)}")
            logger.info(f"   类别: {list(self.DEFECT_CLASSES.values())}")
        else:
            logger.error("❌ 瑕疵检测器未加载！")
            logger.error("   请确保以下路径存在:")
            logger.error(f"   - 配置路径: {settings.DEFECT_MODEL_PATH}")
            logger.error(f"   - 默认路径: {Path(__file__).parent / 'models' / 'defect_best.pt'}")
            self._load_failed = True
    
    def _load_model(self, model_path: Optional[str] = None) -> Optional[YOLO]:
        """
        加载 YOLO 模型（仅尝试瑕疵检测模型，不降级到通用模型）
        
        优先级：
        1. 传入的 model_path 参数
        2. settings.DEFECT_MODEL_PATH（配置文件）
        3. 默认路径 app/ml/models/defect_best.pt
        4. 所有路径都失败 → 返回 None（不加载通用模型）
        """
        # 1. 优先使用传入的路径
        if model_path and Path(model_path).exists():
            logger.info(f"✅ 使用传入模型: {model_path}")
            self.model_path = str(model_path)
            return YOLO(model_path)
        
        # 2. 使用配置文件中的路径
        config_path = Path(settings.DEFECT_MODEL_PATH)
        if config_path.exists():
            logger.info(f"✅ 使用配置模型: {config_path}")
            self.model_path = str(config_path)
            return YOLO(str(config_path))
        
        # 3. 使用默认路径（相对于当前文件）
        default_path = Path(__file__).parent / "models" / "defect_best.pt"
        if default_path.exists():
            logger.info(f"✅ 使用默认模型: {default_path}")
            self.model_path = str(default_path)
            return YOLO(str(default_path))
        
        # 4. ✅ 所有路径都失败 → 返回 None，不加载通用模型
        logger.error("❌ 未找到瑕疵检测模型")
        logger.error(f"   尝试过的路径:")
        logger.error(f"   - 传入: {model_path}")
        logger.error(f"   - 配置: {settings.DEFECT_MODEL_PATH}")
        logger.error(f"   - 默认: {Path(__file__).parent / 'models' / 'defect_best.pt'}")
        logger.error("   ⚠️ 不会降级到通用 YOLO 模型（COCO 模型无法检测瑕疵）")
        self.model_path = None
        return None
    
    def _determine_severity(
        self,
        defect_type: str,
        area_ratio: float,
        confidence: float,
        bbox: List[float]
    ) -> str:
        """
        根据瑕疵类型、面积占比、置信度判断程度等级

        Kaputt 7 类 → 严重程度映射：
          penetration    穿透      → 重度
          deformation    变形      → 面积大→重度，否则中度
          actuation      功能故障  → 重度
          deconstruction 结构损坏  → 重度
          spillage       溢漏      → 面积大→中度，否则轻度
          superficial    表面瑕疵  → 轻微
          missing_unit   部件缺失  → 重度

        Args:
            defect_type: 瑕疵类型
            area_ratio: 瑕疵面积占图片比例
            confidence: 检测置信度
            bbox: 边界框 [x1, y1, x2, y2] (float)

        Returns:
            str: severe / moderate / minor / slight
        """
        # 穿透 → 重度
        if defect_type == 'penetration':
            return 'severe'

        # 变形：面积大 → 重度，否则中度
        if defect_type == 'deformation':
            if area_ratio > 0.002:
                return 'severe'
            return 'moderate'

        # 功能故障 → 重度
        if defect_type == 'actuation':
            return 'severe'

        # 结构损坏 → 重度
        if defect_type == 'deconstruction':
            return 'severe'

        # 溢漏：面积大 → 中度，否则轻度
        if defect_type == 'spillage':
            if area_ratio > 0.001:
                return 'moderate'
            return 'minor'

        # 表面瑕疵 → 轻微
        if defect_type == 'superficial':
            if area_ratio > 0.001:
                return 'minor'
            return 'slight'

        # 部件缺失 → 重度
        if defect_type == 'missing_unit':
            return 'severe'

        return 'minor'
    
    def _draw_shape(
        self,
        draw: ImageDraw.Draw,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        shape: str,
        color: str,
        width: int = 3
    ):
        """根据形状类型画不同的标注框"""
        if shape == 'circle':
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
            step = 10
            for i in range(0, (x2 - x1), step * 2):
                draw.line([(x1 + i, y1), (x1 + min(i + step, x2 - x1), y1)], fill=color, width=width)
            for i in range(0, (x2 - x1), step * 2):
                draw.line([(x1 + i, y2), (x1 + min(i + step, x2 - x1), y2)], fill=color, width=width)
            for i in range(0, (y2 - y1), step * 2):
                draw.line([(x1, y1 + i), (x1, y1 + min(i + step, y2 - y1))], fill=color, width=width)
            for i in range(0, (y2 - y1), step * 2):
                draw.line([(x2, y1 + i), (x2, y1 + min(i + step, y2 - y1))], fill=color, width=width)
                
        elif shape == 'polygon':
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
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=width)
    
    def detect_defects(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        检测瑕疵
        
        Returns:
            瑕疵列表，如果没有模型则返回空列表
        """
        # ✅ 如果没有模型，返回空列表
        if self.model is None or self._load_failed:
            logger.warning("⚠️ 瑕疵检测模型未加载，返回空结果")
            return []
        
        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        results = self.model(image, conf=conf, device=self.device, verbose=False)
        defects = []
        
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # ✅ 如果模型输出的类别不在 DEFECT_CLASSES 中，跳过（防止 COCO 类别污染）
                    if cls_id not in self.DEFECT_CLASSES:
                        logger.warning(f"⚠️ 跳过非瑕疵类别: {cls_id} (模型可能不是瑕疵检测模型)")
                        continue
                    
                    class_name = self.DEFECT_CLASSES.get(cls_id, 'other')
                    class_cn = self.DEFECT_NAMES_CN.get(class_name, '其他')
                    
                    bbox = [float(x1), float(y1), float(x2), float(y2)]
                    area = (x2 - x1) * (y2 - y1)
                    area_ratio = area / (image.width * image.height)
                    
                    severity = self._determine_severity(class_name, area_ratio, conf, bbox)
                    
                    defects.append({
                        'type': class_name,
                        'type_cn': class_cn,
                        'confidence': round(conf, 3),
                        'bbox': bbox,
                        'area': int(area),
                        'area_ratio': round(area_ratio, 4),
                        'severity': severity,
                        'severity_label': self.SEVERITY_CONFIG[severity]['label'],
                        'shape': self.SEVERITY_CONFIG[severity]['shape'],
                        'color': self.SEVERITY_CONFIG[severity]['color'],
                        'rgb_color': self.SEVERITY_CONFIG[severity]['rgb_color']
                    })
        
        logger.info(f"YOLO 检测到 {len(defects)} 个瑕疵")
        return defects

    def draw_annotations(
        self,
        image: Image.Image,
        defects: List[Dict[str, Any]],
        show_severity: bool = False
    ) -> Image.Image:
        """在图片上画标注框"""
        img = image.copy()
        draw = ImageDraw.Draw(img)
        font = get_chinese_font(18)
        
        for defect in defects:
            bbox = defect['bbox']
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            
            color = defect['color']
            shape = defect['shape']
            severity = defect['severity']
            
            width_map = {
                'severe': 4,
                'moderate': 3,
                'minor': 2,
                'slight': 2
            }
            width = width_map.get(severity, 3)
            
            self._draw_shape(draw, x1, y1, x2, y2, shape, color, width)
            
            if show_severity:
                label = f"{defect['type_cn']}({defect['severity_label']})"
            else:
                label = defect['type_cn']
            
            try:
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                draw.rectangle(
                    [(x1, y1 - text_height - 6), (x1 + text_width + 4, y1)],
                    fill=color
                )
                draw.text((x1 + 2, y1 - text_height - 4), label, fill='white', font=font)
            except Exception:
                draw.text((x1, y1 - 12), label, fill=color)
        
        return img

    def process(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """完整处理流程"""
        defects = self.detect_defects(image, conf_threshold)
        annotated = self.draw_annotations(image, defects, show_severity=False)
        
        defects_for_frontend = []
        defects_for_ds = []
        severity_count = {'severe': 0, 'moderate': 0, 'minor': 0, 'slight': 0}
        
        for d in defects:
            defects_for_frontend.append({
                'type': d['type'],
                'type_cn': d['type_cn'],
                'bbox': d['bbox'],
                'confidence': d['confidence']
            })
            
            defects_for_ds.append({
                'type': d['type'],
                'type_cn': d['type_cn'],
                'bbox': d['bbox'],
                'area': d['area'],
                'area_ratio': d['area_ratio'],
                'confidence': d['confidence'],
                'severity': d['severity'],
                'severity_label': d['severity_label']
            })
            
            severity_count[d['severity']] = severity_count.get(d['severity'], 0) + 1
        
        # ✅ R4: 计算成色分级
        condition_grade = self.grade_condition(severity_count)

        return {
            'bg_removed': image,
            'annotated': annotated,
            'defects': defects_for_frontend,
            'defects_for_ds': defects_for_ds,
            'defect_count': len(defects),
            'severity_summary': severity_count,
            'condition_grade': condition_grade,
        }
    
    def get_defects_for_deepseek(self, defects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成发送给 DeepSeek 的结构化数据"""
        if not defects:
            return {
                'has_defects': False,
                'summary': '商品外观完好，无瑕疵',
                'defects': [],
                'severity_summary': {'severe': 0, 'moderate': 0, 'minor': 0, 'slight': 0},
                'total': 0
            }
        
        severity_count = {'severe': 0, 'moderate': 0, 'minor': 0, 'slight': 0}
        for d in defects:
            severity_count[d['severity']] = severity_count.get(d['severity'], 0) + 1
        
        has_severe = severity_count['severe'] > 0
        has_moderate = severity_count['moderate'] > 0
        has_minor = severity_count['minor'] > 0
        has_slight = severity_count['slight'] > 0
        
        if has_severe:
            summary = f"检测到 {severity_count['severe']} 处重度损伤，严重影响使用"
        elif has_moderate:
            summary = f"检测到 {severity_count['moderate']} 处中度损伤，影响外观"
        elif has_minor:
            summary = f"检测到 {severity_count['minor']} 处轻度损伤，细微痕迹"
        elif has_slight:
            summary = f"检测到 {severity_count['slight']} 处轻微污渍，可清理"
        else:
            summary = "商品外观完好，无瑕疵"
        
        sorted_defects = sorted(
            defects,
            key=lambda x: self.SEVERITY_ORDER.index(x['severity'])
        )
        
        return {
            'has_defects': True,
            'summary': summary,
            'defects': sorted_defects,
            'severity_summary': severity_count,
            'total': len(defects)
        }

    # ============================================================
    # ✅ R4: 5级成色分级
    # ============================================================
    CONDITION_GRADES = {
        0: "完整",
        1: "轻微瑕疵",
        2: "中度瑕疵",
        3: "重度瑕疵",
        4: "完全损坏",
    }

    def grade_condition(self, severity_summary: Dict[str, int]) -> Dict[str, Any]:
        """
        根据瑕疵严重程度汇总，返回5级成色分级

        Args:
            severity_summary: {'severe': N, 'moderate': N, 'minor': N, 'slight': N}

        Returns:
            {'grade': int 0-4, 'grade_label': str, 'defect_count': int, 'severity_summary': dict}
        """
        severe = severity_summary.get('severe', 0)
        moderate = severity_summary.get('moderate', 0)
        minor = severity_summary.get('minor', 0)
        slight = severity_summary.get('slight', 0)
        total = severe + moderate + minor + slight

        if total == 0:
            grade = 0   # 完整
        elif severe >= 3:
            grade = 4   # 完全损坏
        elif severe >= 1:
            grade = 3   # 重度瑕疵
        elif moderate >= 2:
            grade = 2   # 中度瑕疵
        elif moderate >= 1 or minor >= 2:
            grade = 2   # 中度瑕疵
        elif minor >= 1 or slight >= 1:
            grade = 1   # 轻微瑕疵
        else:
            grade = 1   # 轻微瑕疵（兜底）

        return {
            'grade': grade,
            'grade_label': self.CONDITION_GRADES[grade],
            'defect_count': total,
            'severity_summary': severity_summary,
        }


# ============================================================
# 单例实例（懒加载，线程安全）
# ============================================================

_defect_detector: Optional[DefectDetector] = None
_defect_detector_lock = threading.Lock()


def get_defect_detector(
    model_path: Optional[str] = None,
    conf_threshold: float = 0.3
) -> DefectDetector:
    """
    获取瑕疵检测器单例（线程安全）

    Args:
        model_path: 模型路径（仅首次调用时生效）
        conf_threshold: 置信度阈值（仅首次调用时生效）

    Returns:
        DefectDetector 实例
    """
    global _defect_detector

    # ✅ 快速路径（无锁）
    if _defect_detector is not None:
        return _defect_detector

    # ✅ 慢速路径（有锁，双重检查）
    with _defect_detector_lock:
        if _defect_detector is not None:
            return _defect_detector
        _defect_detector = DefectDetector(
            model_path=model_path,
            conf_threshold=conf_threshold
        )
        return _defect_detector


# ============================================================
# 便捷函数
# ============================================================

def detect_defects(
    image: Image.Image,
    conf_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    快捷检测函数
    
    Args:
        image: PIL Image 对象
        conf_threshold: 置信度阈值
    
    Returns:
        瑕疵列表
    """
    detector = get_defect_detector()
    return detector.detect_defects(image, conf_threshold)


def detect_defects_from_path(
    image_path: str,
    conf_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    从文件路径快捷检测
    
    Args:
        image_path: 图片文件路径
        conf_threshold: 置信度阈值
    
    Returns:
        瑕疵列表
    """
    image = Image.open(image_path)
    return detect_defects(image, conf_threshold)