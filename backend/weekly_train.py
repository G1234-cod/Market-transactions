"""
每周自动训练脚本
读取 error_data/ 中的错误图片，微调模型
"""
import os
import shutil
import random
import yaml
import json
import re
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 配置 ==========
ERROR_DATA_DIR = Path("data/error_data")
MODEL_PATH = Path("app/ml/models/best.pt")
OUTPUT_DIR = Path(f"runs/train/weekly_{datetime.now().strftime('%Y%m%d')}")
TRAIN_RATIO = 0.8
MIX_RATIO = 0.5  # 50% 本周 + 50% 历史
MIN_SAMPLES = 10

# COCO 80 类别名称（用于 YOLO 格式）
COCO_NAMES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]


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
    """获取类别ID（映射到 COCO 类别）"""
    # 先尝试直接匹配
    for idx, name in enumerate(COCO_NAMES):
        if name.lower() == class_name.lower():
            return idx
    
    # 常见映射
    mapping = {
        '手机': 'cell phone',
        '笔记本': 'laptop',
        '鼠标': 'mouse',
        '键盘': 'keyboard',
        '耳机': 'headphone',  # COCO 没有耳机，用替代
        '平板': 'tablet',     # COCO 没有平板，用替代
    }
    
    mapped = mapping.get(class_name, class_name)
    for idx, name in enumerate(COCO_NAMES):
        if name.lower() == mapped.lower():
            return idx
    
    return 0  # 默认映射到 person


def prepare_dataset():
    """从错误数据生成训练集"""
    images_dir = ERROR_DATA_DIR / "images"
    labels_dir = ERROR_DATA_DIR / "labels"
    
    if not images_dir.exists():
        logger.warning("没有错误数据，跳过训练")
        return None
    
    # 获取所有错误图片
    image_files = list(images_dir.glob("*.jpg"))
    
    if len(image_files) < MIN_SAMPLES:
        logger.warning(f"错误数据不足 ({len(image_files)} 张)，至少需要 {MIN_SAMPLES} 张")
        return None
    
    logger.info(f"✅ 找到 {len(image_files)} 张错误图片")
    
    # 按时间排序
    image_files.sort(key=lambda x: x.stat().st_mtime)
    
    # 分割：训练/验证
    split_idx = int(len(image_files) * TRAIN_RATIO)
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:]
    
    logger.info(f"📊 训练集: {len(train_files)} 张，验证集: {len(val_files)} 张")
    
    # 创建 YOLO 数据集目录
    dataset_dir = Path("datasets/error_dataset")
    train_img_dir = dataset_dir / "images" / "train"
    train_label_dir = dataset_dir / "labels" / "train"
    val_img_dir = dataset_dir / "images" / "val"
    val_label_dir = dataset_dir / "labels" / "val"
    
    for d in [train_img_dir, train_label_dir, val_img_dir, val_label_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 复制图片并生成标签
    def process_files(file_list, img_dir, label_dir):
        for f in file_list:
            # 复制图片
            shutil.copy(f, img_dir / f.name)
            
            # 生成 YOLO 标签
            label_file = labels_dir / (f.stem + ".txt")
            label_path = label_dir / (f.stem + ".txt")
            
            if label_file.exists():
                _, wrong_label, correct_label = parse_label_file(label_file)
                if correct_label:
                    cls_id = get_class_id(correct_label)
                    # 注意：这里需要实际的 bbox 坐标
                    # 由于错误数据没有标注 bbox，这里使用全图作为检测目标
                    # 实际应该从标签文件或其他来源获取 bbox
                    with open(label_path, 'w') as lf:
                        # 格式: class_id x_center y_center width height
                        # 假设目标占据图片 80%，居中
                        lf.write(f"{cls_id} 0.5 0.5 0.8 0.8\n")
    
    process_files(train_files, train_img_dir, train_label_dir)
    process_files(val_files, val_img_dir, val_label_dir)
    
    # 生成 data.yaml
    data_yaml = {
        'path': str(dataset_dir.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'nc': 80,
        'names': COCO_NAMES
    }
    
    yaml_path = dataset_dir / "data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, allow_unicode=True)
    
    logger.info(f"✅ 数据集已生成: {dataset_dir}")
    return str(yaml_path)


def train():
    """执行训练"""
    # 1. 准备数据集
    data_yaml = prepare_dataset()
    if data_yaml is None:
        logger.info("⏭️ 跳过训练")
        return
    
    # 2. 检查 GPU
    import torch
    if torch.cuda.is_available():
        logger.info(f"✅ 使用 GPU: {torch.cuda.get_device_name(0)}")
        device = 0
    else:
        logger.warning("⚠️ 未检测到 GPU，使用 CPU（训练会很慢）")
        device = 'cpu'
    
    # 3. 加载模型
    if MODEL_PATH.exists():
        model = YOLO(str(MODEL_PATH))
        logger.info(f"✅ 加载模型: {MODEL_PATH}")
    else:
        model = YOLO('yolov8n.pt')
        logger.info("✅ 使用预训练模型 yolov8n.pt")
    
    # 4. 训练
    logger.info("🚀 开始微调训练...")
    results = model.train(
        data=data_yaml,
        epochs=20,
        imgsz=640,
        batch=8,
        device=device,
        workers=4,
        augment=True,
        weight_decay=0.0005,
        dropout=0.2,
        patience=5,
        project=str(OUTPUT_DIR),
        name='finetune',
        verbose=True,
        exist_ok=True
    )
    
    # 5. 更新模型
    new_model = OUTPUT_DIR / 'finetune' / 'weights' / 'best.pt'
    if new_model.exists():
        # 备份旧模型
        if MODEL_PATH.exists():
            backup_path = MODEL_PATH.with_suffix('.pt.bak')
            shutil.copy(MODEL_PATH, backup_path)
            logger.info(f"✅ 旧模型已备份: {backup_path}")
        
        shutil.copy(new_model, MODEL_PATH)
        logger.info(f"✅ 模型已更新: {MODEL_PATH}")
    else:
        logger.error("❌ 训练失败，模型未生成")


if __name__ == '__main__':
    train()