"""
每周自动训练脚本
从 hard_cases 错误数据中生成训练样本，使用 YOLO 检测真实边界框
"""
import os
import sys
import shutil
import random
import yaml
import json
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ultralytics import YOLO
import torch

from app.db import crud
from app.config import settings
from app.ml.yolo_detector import get_yolo_detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 配置 ==========
ERROR_DATA_DIR = Path("data/error_data")
MODEL_PATH = Path("app/ml/models/best.pt")
OUTPUT_DIR = Path(f"runs/train/weekly_{datetime.now().strftime('%Y%m%d')}")
TRAIN_RATIO = 0.8
MIN_SAMPLES = 10
EPOCHS = 20
BATCH_SIZE = 8
IMAGE_SIZE = 640


def parse_label_file(label_path: Path) -> tuple:
    """
    解析标签文件，提取正确分类
    
    Args:
        label_path: 标签文件路径
        
    Returns:
        (filename, wrong_label, correct_label)
    """
    try:
        with open(label_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        wrong_match = re.search(r'错误分类.*?：(.*)', content)
        correct_match = re.search(r'正确分类.*?：(.*)', content)
        
        if wrong_match and correct_match:
            return (
                label_path.stem,
                wrong_match.group(1).strip(),
                correct_match.group(1).strip()
            )
    except Exception as e:
        logger.error(f"解析标签失败 {label_path}: {e}")
    
    return None, None, None


def get_class_id(class_name: str) -> int:
    """
    获取类别ID（从 YOLO 模型获取类别映射）
    
    Args:
        class_name: 类别名称（中文或英文）
        
    Returns:
        int: 类别ID，默认返回 0
    """
    if not class_name:
        return 0
    
    # 获取 YOLO 模型中的类别映射
    try:
        detector = get_yolo_detector()
        model = detector.model
        class_names = model.names  # {0: 'person', 1: 'bicycle', ...}
        
        # 1. 尝试精确匹配
        class_name_lower = class_name.lower()
        for idx, name in class_names.items():
            if name.lower() == class_name_lower:
                return idx
        
        # 2. 中文到英文映射
        cn_to_en = {
            '手机': 'cell phone',
            '笔记本': 'laptop',
            '平板': 'tablet',
            '耳机': 'headphone',
            '鼠标': 'mouse',
            '键盘': 'keyboard',
            '相机': 'camera',
            '手表': 'watch',
            '游戏机': 'game console',
            '划痕': 'scratch',
            '磕碰': 'dent',
            '污渍': 'stain',
            '裂痕': 'crack',
            '掉漆': 'peeling',
        }
        
        mapped = cn_to_en.get(class_name, class_name)
        for idx, name in class_names.items():
            if name.lower() == mapped.lower():
                return idx
        
        # 3. 部分匹配
        for idx, name in class_names.items():
            if class_name_lower in name.lower() or name.lower() in class_name_lower:
                return idx
        
    except Exception as e:
        logger.warning(f"获取类别ID失败: {e}")
    
    return 0  # 默认返回 0


async def get_error_cases_from_db(limit: int = 500) -> List[Dict[str, Any]]:
    """
    从数据库获取错误数据
    
    Args:
        limit: 获取数量限制
        
    Returns:
        List[Dict]: 错误数据列表
    """
    try:
        cases = await crud.get_hard_cases(
            limit=limit,
            is_fixed=False,
            sort_by="created_at"
        )
        logger.info(f"📊 从数据库获取到 {len(cases)} 条错误数据")
        return cases
    except Exception as e:
        logger.error(f"❌ 获取错误数据失败: {e}")
        return []


async def get_error_cases_from_local(limit: int = 500) -> List[Dict[str, Any]]:
    """
    从本地文件获取错误数据
    
    Args:
        limit: 获取数量限制
        
    Returns:
        List[Dict]: 错误数据列表
    """
    cases = []
    images_dir = ERROR_DATA_DIR / "images"
    labels_dir = ERROR_DATA_DIR / "labels"
    
    if not images_dir.exists():
        return cases
    
    image_files = list(images_dir.glob("*.jpg"))
    image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for img_file in image_files[:limit]:
        label_file = labels_dir / (img_file.stem + ".txt")
        
        if label_file.exists():
            _, wrong_label, correct_label = parse_label_file(label_file)
            if correct_label:
                cases.append({
                    'image_url': str(img_file),
                    'wrong_label': wrong_label or '',
                    'correct_label': correct_label,
                    'id': img_file.stem
                })
    
    logger.info(f"📊 从本地获取到 {len(cases)} 条错误数据")
    return cases


def download_image(image_url: str, save_path: Path) -> bool:
    """
    下载图片
    
    Args:
        image_url: 图片URL或本地路径
        save_path: 保存路径
        
    Returns:
        bool: 是否成功
    """
    try:
        # 如果是本地路径
        if not image_url.startswith("http"):
            # 处理相对路径
            if image_url.startswith("/static/"):
                image_url = f"{settings.BASE_URL}{image_url}"
            elif Path(image_url).exists():
                shutil.copy(image_url, save_path)
                return True
            
            # 尝试作为相对路径
            local_path = Path(image_url)
            if local_path.exists():
                shutil.copy(local_path, save_path)
                return True
        
        # HTTP 下载
        import requests
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        
        logger.warning(f"⚠️ 下载失败: {image_url} (HTTP {response.status_code})")
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ 下载异常: {image_url}, {e}")
        return False


def generate_yolo_label(
    image_path: Path,
    label_path: Path,
    correct_label: str,
    use_detection: bool = True
) -> bool:
    """
    ✅ 生成 YOLO 格式标签（使用 YOLO 检测真实边界框）
    
    Args:
        image_path: 图片路径
        label_path: 标签保存路径
        correct_label: 正确分类名称
        use_detection: 是否使用 YOLO 检测真实边界框
        
    Returns:
        bool: 是否成功
    """
    try:
        # 加载图片获取尺寸
        from PIL import Image
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # ✅ 使用 YOLO 检测真实边界框
        if use_detection:
            try:
                detector = get_yolo_detector()
                detections = detector.detect(str(image_path), conf_threshold=0.3)
                
                if detections:
                    # 使用置信度最高的检测结果
                    best_det = max(detections, key=lambda x: x['confidence'])
                    x1, y1, x2, y2 = best_det['bbox']
                    
                    # 转换为 YOLO 格式（归一化）
                    x_center = (x1 + x2) / 2 / img_width
                    y_center = (y1 + y2) / 2 / img_height
                    width = (x2 - x1) / img_width
                    height = (y2 - y1) / img_height
                    
                    # 获取类别ID
                    detected_class = best_det.get('class_name', '')
                    cls_id = get_class_id(correct_label or detected_class)
                    
                    # 写入标签
                    with open(label_path, 'w', encoding='utf-8') as lf:
                        lf.write(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                    
                    logger.debug(f"✅ 使用检测边界框: {image_path.name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ YOLO 检测失败，使用默认框: {e}")
        
        # 回退方案：使用全图框
        cls_id = get_class_id(correct_label)
        with open(label_path, 'w', encoding='utf-8') as lf:
            # 覆盖 90% 区域，略有偏移避免所有样本一致
            offset_x = random.uniform(-0.05, 0.05)
            offset_y = random.uniform(-0.05, 0.05)
            size = random.uniform(0.85, 0.95)
            
            lf.write(f"{cls_id} {0.5 + offset_x:.6f} {0.5 + offset_y:.6f} {size:.6f} {size:.6f}\n")
        
        logger.debug(f"✅ 使用默认边界框: {image_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 生成标签失败: {image_path}, {e}")
        return False


def prepare_dataset(
    cases: List[Dict[str, Any]],
    dataset_dir: Path
) -> Optional[Path]:
    """
    准备训练数据集
    
    Args:
        cases: 错误数据列表
        dataset_dir: 数据集目录
        
    Returns:
        Optional[Path]: data.yaml 路径，失败返回 None
    """
    if len(cases) < MIN_SAMPLES:
        logger.warning(f"⚠️ 样本不足 ({len(cases)} < {MIN_SAMPLES})，跳过训练")
        return None
    
    # 创建目录
    train_img_dir = dataset_dir / "images" / "train"
    train_label_dir = dataset_dir / "labels" / "train"
    val_img_dir = dataset_dir / "images" / "val"
    val_label_dir = dataset_dir / "labels" / "val"
    
    for d in [train_img_dir, train_label_dir, val_img_dir, val_label_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 打乱并分割
    random.shuffle(cases)
    split_idx = int(len(cases) * TRAIN_RATIO)
    train_cases = cases[:split_idx]
    val_cases = cases[split_idx:]
    
    logger.info(f"📊 训练集: {len(train_cases)} 张，验证集: {len(val_cases)} 张")
    
    # 处理函数
    def process_cases(case_list, img_dir, label_dir):
        success = 0
        for case in case_list:
            try:
                # 图片路径
                image_url = case.get('image_url', '')
                if not image_url:
                    continue
                
                correct_label = case.get('correct_label', '')
                case_id = case.get('id', hash(image_url))
                
                img_filename = f"case_{case_id}.jpg"
                img_path = img_dir / img_filename
                label_path = label_dir / f"case_{case_id}.txt"
                
                # 下载或复制图片
                if not download_image(image_url, img_path):
                    continue
                
                # ✅ 生成真实边界框标签
                if not generate_yolo_label(img_path, label_path, correct_label, use_detection=True):
                    img_path.unlink(missing_ok=True)
                    continue
                
                success += 1
                
            except Exception as e:
                logger.error(f"处理失败: {case.get('id', 'unknown')}, {e}")
                continue
        
        return success
    
    # 处理训练集
    train_count = process_cases(train_cases, train_img_dir, train_label_dir)
    val_count = process_cases(val_cases, val_img_dir, val_label_dir)
    
    if train_count < MIN_SAMPLES:
        logger.warning(f"⚠️ 训练样本不足 ({train_count} < {MIN_SAMPLES})")
        return None
    
    logger.info(f"✅ 成功处理: 训练 {train_count} 张，验证 {val_count} 张")
    
    # 生成 data.yaml
    data_yaml = {
        'path': str(dataset_dir.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'nc': 80,
        'names': ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
                  'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
                  'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
                  'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
                  'skis', 'snowboard', 'sports ball', 'baseball bat', 'baseball glove',
                  'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
                  'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
                  'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
                  'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
                  'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
                  'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
                  'hair drier', 'toothbrush']
    }
    
    yaml_path = dataset_dir / "data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, allow_unicode=True)
    
    return yaml_path


def run_training(data_yaml: Path, output_dir: Path) -> bool:
    """
    执行训练
    
    Args:
        data_yaml: data.yaml 文件路径
        output_dir: 输出目录
        
    Returns:
        bool: 是否成功
    """
    try:
        # 检查 GPU
        if torch.cuda.is_available():
            logger.info(f"✅ 使用 GPU: {torch.cuda.get_device_name(0)}")
            device = 0
        else:
            logger.warning("⚠️ 未检测到 GPU，使用 CPU（训练会很慢）")
            device = 'cpu'
        
        # 加载模型
        if MODEL_PATH.exists():
            model = YOLO(str(MODEL_PATH))
            logger.info(f"✅ 加载模型: {MODEL_PATH}")
        else:
            model = YOLO('yolov8n.pt')
            logger.info("✅ 使用预训练模型 yolov8n.pt")
        
        # 训练
        logger.info("🚀 开始微调训练...")
        model.train(
            data=str(data_yaml),
            epochs=EPOCHS,
            imgsz=IMAGE_SIZE,
            batch=BATCH_SIZE,
            device=device,
            workers=4,
            augment=True,
            weight_decay=0.0005,
            dropout=0.2,
            patience=10,
            project=str(output_dir),
            name='finetune',
            verbose=True,
            exist_ok=True
        )
        
        # 更新模型
        new_model = output_dir / 'finetune' / 'weights' / 'best.pt'
        if new_model.exists():
            # 备份旧模型
            if MODEL_PATH.exists():
                backup_path = MODEL_PATH.with_suffix('.pt.bak')
                shutil.copy(MODEL_PATH, backup_path)
                logger.info(f"✅ 旧模型已备份: {backup_path}")
            
            shutil.copy(new_model, MODEL_PATH)
            logger.info(f"✅ 模型已更新: {MODEL_PATH}")
            
            # 标记错误数据为已修复
            asyncio.run(mark_cases_fixed())
            return True
        else:
            logger.error("❌ 训练失败，模型未生成")
            return False
            
    except Exception as e:
        logger.error(f"❌ 训练失败: {e}")
        return False


async def mark_cases_fixed():
    """标记错误数据为已修复"""
    try:
        cases = await crud.get_hard_cases(limit=500, is_fixed=False)
        case_ids = [c['id'] for c in cases]
        if case_ids:
            await crud.mark_hard_cases_fixed(case_ids)
            logger.info(f"✅ 已标记 {len(case_ids)} 条错误数据为已修复")
    except Exception as e:
        logger.error(f"❌ 标记已修复失败: {e}")


async def main_async():
    """异步主函数"""
    logger.info("=" * 60)
    logger.info(f"🚀 每周自动训练 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 1. 获取错误数据
    cases = await get_error_cases_from_db(limit=500)
    if not cases:
        cases = get_error_cases_from_local(limit=500)
    
    if not cases:
        logger.info("✅ 没有错误数据，无需训练")
        return
    
    # 2. 准备数据集
    dataset_dir = Path(f"datasets/error_dataset_{datetime.now().strftime('%Y%m%d')}")
    data_yaml = prepare_dataset(cases, dataset_dir)
    
    if data_yaml is None:
        logger.info("⏭️ 跳过训练")
        return
    
    # 3. 执行训练
    output_dir = Path(f"runs/train/weekly_{datetime.now().strftime('%Y%m%d')}")
    success = run_training(data_yaml, output_dir)
    
    if success:
        logger.info("✅ 每周训练完成！")
    else:
        logger.error("❌ 每周训练失败")


def main():
    """同步入口"""
    asyncio.run(main_async())


if __name__ == '__main__':
    main()