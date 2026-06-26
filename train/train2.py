"""
YOLOv8 瑕疵检测训练脚本（COCO 格式缺陷数据集）
训练完成后模型保存为 defect_best.pt

特点：
1. ✅ 每次运行训练 8 轮（约 2-3 小时）
2. ✅ 下次运行自动从断点继续（第9轮开始）
3. ✅ 过拟合防护（数据增强 + 权重衰减 + Dropout）
4. ✅ 损失不下降时自动停止
5. ✅ 每轮结束后显示详细效果
6. ✅ 自动调参
"""
from ultralytics import YOLO
import os
import pandas as pd
from datetime import datetime
import torch
import shutil
import math

# ========== 配置参数（按需修改） ==========
MODEL_NAME = 'yolov8n.pt'

# 数据集路径 - 使用 defect_dataset 和其中的 data.yaml
DATASET_PATH = '../backend/dataset/defect_dataset'
DATA_YAML = '../backend/dataset/defect_dataset/data.yaml'  # 修正路径

EPOCHS_PER_RUN = 8                     # 🔑 每次训练 8 轮（约 2-3 小时）
IMGSZ = 640
BATCH = 16

# 🔑 自动检测设备（GPU或CPU）
if torch.cuda.is_available():
    DEVICE = 0                         # GPU编号（0=第一张显卡）
    print(f"✅ GPU可用: {torch.cuda.get_device_name(0)}")
    print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    DEVICE = 'cpu'                     # 使用CPU
    print("⚠️ 未检测到GPU，将使用CPU训练（速度会很慢）")

PATIENCE = 10
PROJECT = 'runs/train_defect'
NAME = 'defect_detector'
# ==========================================


class AutoTuner:
    """自动调参器"""
    
    def __init__(self):
        self.history = []
        self.best_loss = float('inf')
        self.patience_counter = 0
        self.current_lr = 0.001
        
    def record_epoch(self, epoch, box_loss, cls_loss, dfl_loss, lr):
        total_loss = box_loss + cls_loss + dfl_loss
        self.history.append({
            'epoch': epoch,
            'box_loss': box_loss,
            'cls_loss': cls_loss,
            'dfl_loss': dfl_loss,
            'total_loss': total_loss,
            'lr': lr
        })
        
        if total_loss < self.best_loss:
            self.best_loss = total_loss
            self.patience_counter = 0
            return True
        else:
            self.patience_counter += 1
            return False
    
    def suggest_next_lr(self):
        if len(self.history) < 2:
            return self.current_lr
        
        recent = self.history[-3:] if len(self.history) >= 3 else self.history
        losses = [h['total_loss'] for h in recent]
        
        if len(losses) >= 2:
            change_rate = (losses[-1] - losses[0]) / losses[0]
            
            if change_rate < -0.05:
                lr = self.current_lr * 1.05
                print(f"  📈 损失快速下降，学习率提高 5%")
            elif change_rate < -0.01:
                lr = self.current_lr * 1.02
                print(f"  📈 损失稳步下降，学习率提高 2%")
            elif change_rate < 0:
                lr = self.current_lr * 0.98
                print(f"  📉 损失趋于平稳，学习率降低 2%")
            else:
                lr = self.current_lr * 0.9
                print(f"  📉 损失上升，学习率降低 10%")
        else:
            lr = self.current_lr
        
        lr = max(0.0001, min(0.01, lr))
        self.current_lr = lr
        return lr


def check_gpu():
    """检查 GPU 状态"""
    print("\n" + "="*70)
    print("🖥️  GPU 检查")
    print("="*70)
    print(f"  PyTorch CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU 名称: {torch.cuda.get_device_name(0)}")
        print(f"  GPU 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        print(f"  使用设备: GPU 0")
    else:
        print(f"  使用设备: CPU")
        print(f"  💡 提示: 可安装GPU版本: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    print("="*70 + "\n")


def check_dataset_structure(dataset_path):
    """检查数据集结构是否正确"""
    print("\n" + "="*70)
    print("📂 检查数据集结构")
    print("="*70)
    
    # 检查 data.yaml
    data_yaml = os.path.join(dataset_path, 'data.yaml')
    if os.path.exists(data_yaml):
        print(f"  ✅ data.yaml: {data_yaml}")
    else:
        print(f"  ❌ data.yaml 不存在: {data_yaml}")
        return False
    
    # 检查 images 目录
    images_dir = os.path.join(dataset_path, 'images')
    if not os.path.exists(images_dir):
        print(f"  ❌ images 目录不存在: {images_dir}")
        return False
    
    # 检查 train 和 val
    train_dir = os.path.join(images_dir, 'train')
    val_dir = os.path.join(images_dir, 'val')
    
    if os.path.exists(train_dir):
        train_count = len([f for f in os.listdir(train_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"  ✅ train: {train_count} 张图片")
    else:
        print(f"  ❌ train 目录不存在: {train_dir}")
        return False
    
    if os.path.exists(val_dir):
        val_count = len([f for f in os.listdir(val_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"  ✅ val: {val_count} 张图片")
    else:
        print(f"  ❌ val 目录不存在: {val_dir}")
        return False
    
    # 检查 labels 目录
    labels_dir = os.path.join(dataset_path, 'labels')
    if os.path.exists(labels_dir):
        train_labels = os.path.join(labels_dir, 'train')
        val_labels = os.path.join(labels_dir, 'val')
        
        if os.path.exists(train_labels):
            label_count = len([f for f in os.listdir(train_labels) if f.endswith('.txt')])
            print(f"  ✅ labels/train: {label_count} 个标签")
        else:
            print(f"  ⚠️  labels/train 不存在（需要转换 COCO 标注）")
        
        if os.path.exists(val_labels):
            label_count = len([f for f in os.listdir(val_labels) if f.endswith('.txt')])
            print(f"  ✅ labels/val: {label_count} 个标签")
        else:
            print(f"  ⚠️  labels/val 不存在（需要转换 COCO 标注）")
    else:
        print(f"  ⚠️  labels 目录不存在（需要转换 COCO 标注）")
    
    print("\n✅ 数据集结构检查完成")
    return True


def get_training_status(save_dir):
    """获取当前训练状态"""
    csv_path = os.path.join(save_dir, 'results.csv')
    if not os.path.exists(csv_path):
        return None, 0, False
    
    df = pd.read_csv(csv_path)
    last_epoch = int(df['epoch'].iloc[-1]) if len(df) > 0 else 0
    
    if len(df) >= 10:
        recent = df['box_loss'].iloc[-10:].values
        improvement = recent[0] - recent[-1]
        is_converged = improvement < 0.001 and len(df) > 20
    else:
        is_converged = False
    
    return df, last_epoch, is_converged


def print_epoch_summary(df, epoch, auto_tuner=None):
    """打印单轮训练摘要"""
    if df is None or len(df) == 0 or epoch > len(df):
        return
    
    row = df.iloc[epoch - 1]
    print(f"\n{'─'*65}")
    print(f"📍 第 {int(row['epoch'])} 轮训练完成")
    print(f"{'─'*65}")
    print(f"  📉 边框损失:  {row['box_loss']:.6f}  (越小越好)")
    print(f"  📉 分类损失:  {row['cls_loss']:.6f}  (越小越好)")
    print(f"  📉 分布损失:  {row['dfl_loss']:.6f}  (越小越好)")
    if 'GPU_mem' in row:
        print(f"  💾 显存占用:  {row['GPU_mem']}")
    if 'lr/pg0' in row:
        print(f"  📈 学习率:    {row['lr/pg0']:.8f}")
    print(f"  📅 时间:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─'*65}\n")


def print_full_history(save_dir, max_rows=50):
    """打印所有历史训练轮次的汇总表格"""
    csv_path = os.path.join(save_dir, 'results.csv')
    if not os.path.exists(csv_path):
        return
    
    df = pd.read_csv(csv_path)
    if len(df) == 0:
        return
    
    print(f"\n{'='*80}")
    print(f"📊 训练历史汇总 (共 {len(df)} 轮)")
    print(f"{'='*80}")
    print(f"{'轮次':>6} | {'边框损失':>12} | {'分类损失':>12} | {'分布损失':>12} | {'显存':>8}")
    print(f"{'-'*80}")
    
    start_idx = max(0, len(df) - max_rows)
    for i in range(start_idx, len(df)):
        row = df.iloc[i]
        epoch = int(row['epoch'])
        box = row['box_loss']
        cls = row['cls_loss']
        dfl = row['dfl_loss']
        gpu = row.get('GPU_mem', 'N/A')
        if isinstance(gpu, float):
            gpu = f"{gpu:.1f}G"
        print(f"{epoch:>6} | {box:>12.6f} | {cls:>12.6f} | {dfl:>12.6f} | {gpu:>8}")
    
    print(f"{'='*80}\n")
    
    best_idx = df['box_loss'].idxmin()
    best_row = df.iloc[best_idx]
    print(f"🏆 最佳模型在第 {int(best_row['epoch'])} 轮，边框损失 = {best_row['box_loss']:.6f}")
    print(f"   保存在: {save_dir}/weights/best.pt\n")


def print_convergence_info(df):
    """打印收敛状态"""
    if df is None or len(df) < 10:
        return
    
    recent = df['box_loss'].iloc[-10:].values
    improvement = recent[0] - recent[-1]
    
    print(f"\n{'─'*65}")
    print(f"📈 收敛状态检查 (最近10轮)")
    print(f"{'─'*65}")
    print(f"  最近10轮第1轮边框损失:  {recent[0]:.6f}")
    print(f"  最近10轮最后1轮边框损失:  {recent[-1]:.6f}")
    print(f"  改进幅度:                {improvement:.6f}")
    
    if improvement < 0.001:
        print(f"  ⚠️  改进幅度小于 0.001，模型已收敛，可以停止训练")
    else:
        print(f"  ✅ 仍有改进空间，建议继续训练")
    print(f"{'─'*65}\n")


def train():
    # 检查 GPU
    check_gpu()
    
    auto_tuner = AutoTuner()
    
    save_dir = os.path.join(PROJECT, NAME)
    has_checkpoint = os.path.exists(os.path.join(save_dir, 'weights', 'last.pt'))
    
    # ===== 检查数据集 =====
    if not os.path.exists(DATASET_PATH):
        print(f"\n❌ 数据集不存在: {DATASET_PATH}")
        print("\n📥 请创建数据集目录并放入图片")
        print("   目录结构应为:")
        print(f"   {DATASET_PATH}/")
        print("   ├── images/")
        print("   │   ├── train/  (训练图片)")
        print("   │   └── val/    (验证图片)")
        print("   ├── labels/")
        print("   │   ├── train/  (训练标签)")
        print("   │   └── val/    (验证标签)")
        print("   └── data.yaml   (数据集配置)")
        return
    
    # ===== 检查 data.yaml =====
    if not os.path.exists(DATA_YAML):
        print(f"\n❌ data.yaml 不存在: {DATA_YAML}")
        print("   请创建 data.yaml 文件")
        return
    
    # ===== 检查数据集结构 =====
    check_dataset_structure(DATASET_PATH)
    
    # ===== 检查是否有之前的训练进度 =====
    if has_checkpoint:
        df, last_epoch, is_converged = get_training_status(save_dir)
        
        print_full_history(save_dir)
        
        if is_converged:
            print(f"\n{'='*70}")
            print("✅ 模型已收敛！连续 10 轮损失没有明显下降。")
            print(f"   共训练 {last_epoch} 轮")
            print(f"   最佳模型: {save_dir}/weights/best.pt")
            print(f"{'='*70}\n")
            print_convergence_info(df)
            return
        
        print(f"\n{'='*70}")
        print(f"🔄 检测到已有训练进度 (已训练 {last_epoch} 轮)")
        print(f"   🔥 本次将从第 {last_epoch + 1} 轮开始，再训练 {EPOCHS_PER_RUN} 轮")
        print(f"   → 完成后到达第 {last_epoch + EPOCHS_PER_RUN} 轮")
        print(f"{'='*70}\n")
        print_convergence_info(df)
        
    else:
        print(f"\n{'='*70}")
        print("🚀 首次训练瑕疵检测模型")
        print(f"   🔥 本次将从第 1 轮开始，训练 {EPOCHS_PER_RUN} 轮")
        print(f"   → 完成后到达第 {EPOCHS_PER_RUN} 轮")
        print(f"   预计用时: {EPOCHS_PER_RUN * 0.3:.1f} - {EPOCHS_PER_RUN * 0.5:.1f} 小时")
        print(f"{'='*70}\n")
    
    # ===== 加载模型 =====
    if has_checkpoint:
        model = YOLO(os.path.join(save_dir, 'weights', 'last.pt'))
        print(f"✅ 加载检查点: {save_dir}/weights/last.pt")
    else:
        model = YOLO(MODEL_NAME)
        print(f"✅ 加载预训练模型: {MODEL_NAME}")
    
    # ===== 开始训练 =====
    print(f"\n{'─'*70}")
    print(f"🏋️  开始训练瑕疵检测模型...")
    print(f"   本轮训练: {EPOCHS_PER_RUN} 轮")
    print(f"   批次大小: {BATCH}")
    print(f"   图片尺寸: {IMGSZ}")
    print(f"   设备: {'GPU 0' if DEVICE == 0 else 'CPU'}")
    print(f"   自动调参: ✅ 已开启")
    print(f"   数据集: {DATASET_PATH}")
    print(f"   配置文件: {DATA_YAML}")
    print(f"{'─'*70}\n")
    
    # 使用 data.yaml 进行训练
    results = model.train(
        data=DATA_YAML,                  # 使用 data.yaml 配置文件
        epochs=EPOCHS_PER_RUN,
        imgsz=IMGSZ,
        batch=BATCH,
        resume=has_checkpoint,          # 🔑 自动从断点继续
        patience=PATIENCE,
        save_period=1,
        project=PROJECT,
        name=NAME,
        device=DEVICE,                  # 🔑 自动选择的设备
        workers=4,
        verbose=True,
        augment=True,
        weight_decay=0.0005,
        dropout=0.1,
        cos_lr=True,
        warmup_epochs=3,
    )
    
    # ===== 训练完成后，复制模型 =====
    src = f"{save_dir}/weights/best.pt"
    dst = "../app/ml/models/defect_best.pt"
    if os.path.exists(src):
        os.makedirs("../app/ml/models", exist_ok=True)
        shutil.copy(src, dst)
        print(f"\n✅ 模型已复制到: {dst}")
    
    # ===== 打印训练详情 =====
    print(f"\n{'='*70}")
    print("✅ 本轮训练完成！")
    print(f"{'='*70}")
    
    df, last_epoch, is_converged = get_training_status(save_dir)
    
    if df is not None:
        start_epoch = max(1, last_epoch - EPOCHS_PER_RUN + 1)
        for e in range(start_epoch, last_epoch + 1):
            if e <= len(df):
                print_epoch_summary(df, e, auto_tuner)
        
        print_full_history(save_dir)
        print_convergence_info(df)
    
    # ===== 判断下一步 =====
    if is_converged:
        print(f"\n{'='*70}")
        print("🎉 模型已收敛！训练自动停止。")
        print(f"   共训练 {last_epoch} 轮")
        print(f"   最佳模型: {save_dir}/weights/best.pt")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'='*70}")
        print("💡 下次继续训练")
        print(f"   🔥 下次运行 'python train2.py' 将从第 {last_epoch + 1} 轮继续")
        print(f"   当前进度: 第 {last_epoch} 轮 / 已完成")
        print(f"   最佳模型: {save_dir}/weights/best.pt")
        print(f"{'='*70}\n")


if __name__ == '__main__':
    train()