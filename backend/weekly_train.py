"""
每周自动训练脚本
读取 error_data/ 中的错误图片，微调模型
"""
import os
import shutil
import random
import yaml
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
TRAIN_RATIO = 0.8  # 80% 训练，20% 验证
MIX_RATIO = 0.5    # 50% 本周数据 + 50% 历史数据
# =========================


def prepare_dataset():
    """从错误数据生成训练集"""
    images_dir = ERROR_DATA_DIR / "images"
    labels_dir = ERROR_DATA_DIR / "labels"
    
    if not images_dir.exists():
        logger.warning("没有错误数据，跳过训练")
        return None
    
    # 获取所有错误图片
    image_files = list(images_dir.glob("*.jpg"))
    if len(image_files) < 10:
        logger.warning(f"错误数据不足 ({len(image_files)} 张)，至少需要 10 张")
        return None
    
    logger.info(f"找到 {len(image_files)} 张错误图片")
    
    # 按时间排序（最新的在后）
    image_files.sort(key=lambda x: x.stat().st_mtime)
    
    # 分割：80% 训练，20% 验证
    split_idx = int(len(image_files) * TRAIN_RATIO)
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:]
    
    # 创建 YOLO 数据集目录
    dataset_dir = Path("datasets/error_dataset")
    train_img_dir = dataset_dir / "images" / "train"
    train_label_dir = dataset_dir / "labels" / "train"
    val_img_dir = dataset_dir / "images" / "val"
    val_label_dir = dataset_dir / "labels" / "val"
    
    for d in [train_img_dir, train_label_dir, val_img_dir, val_label_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 复制图片和标签（需要从标签文件中读取正确分类）
    # 注意：这里需要根据你的实际情况调整标签格式
    # 简化版：直接复制图片，标签需要转换
    for f in train_files:
        shutil.copy(f, train_img_dir / f.name)
        # 对应的标签文件需要转换格式
        label_file = labels_dir / (f.stem + ".txt")
        if label_file.exists():
            # 读取正确分类，生成 YOLO 格式标签
            # 这里需要根据你的类别映射实现
            pass
    
    # 生成 data.yaml
    data_yaml = {
        'path': str(dataset_dir.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'nc': 80,  # COCO 类别数
        'names': ['person', 'bicycle', ...]  # 完整 COCO 类别名
    }
    
    yaml_path = dataset_dir / "data.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(data_yaml, f)
    
    logger.info(f"✅ 数据集已生成: {dataset_dir}")
    return str(yaml_path)


def train():
    """执行训练"""
    # 1. 准备数据集
    data_yaml = prepare_dataset()
    if data_yaml is None:
        return
    
    # 2. 加载模型
    if MODEL_PATH.exists():
        model = YOLO(str(MODEL_PATH))
        logger.info(f"✅ 加载模型: {MODEL_PATH}")
    else:
        model = YOLO('yolov8n.pt')
        logger.info("✅ 使用预训练模型")
    
    # 3. 训练（少量轮数，防过拟合）
    logger.info("🚀 开始微调训练...")
    results = model.train(
        data=data_yaml,
        epochs=20,           # 少量轮数
        imgsz=640,
        batch=8,
        device=0,
        workers=4,
        augment=True,        # 数据增强
        weight_decay=0.0005,
        dropout=0.2,
        patience=5,
        project=str(OUTPUT_DIR),
        name='finetune',
        verbose=True
    )
    
    # 4. 更新模型
    new_model = OUTPUT_DIR / 'finetune' / 'weights' / 'best.pt'
    if new_model.exists():
        shutil.copy(new_model, MODEL_PATH)
        logger.info(f"✅ 模型已更新: {MODEL_PATH}")
    else:
        logger.error("❌ 训练失败，模型未生成")


if __name__ == '__main__':
    train()