"""
YOLOv8 COCO 分段训练脚本
每次训练 5 轮，可随时中断，下次自动继续
当连续 10 轮没有提升时自动停止
每轮训练完成后实时显示误差信息（中文）
"""

from ultralytics import YOLO
import os
import pandas as pd
from datetime import datetime
import torch

# ========== 配置参数（按需修改） ==========
MODEL_NAME = 'yolov8m.pt'      # 模型文件（yolov8n/yolov8s/yolov8m/yolov8l/yolov8x）
DATA_YAML = 'data.yaml'        # 数据集配置文件
EPOCHS_PER_RUN = 5             # 🔑 每次只训练 5 轮（约 1.5-2 小时）
IMGSZ = 640                    # 图片尺寸
BATCH = 8                      # 批次大小（4060 8GB 显存建议 8）
DEVICE = 0                     # GPU 编号（0=第一张显卡）
PATIENCE = 10                  # 🔑 连续10轮没提升就自动停止
PROJECT = 'runs/train'         # 保存目录
NAME = 'coco_yolov8m'          # 项目名称
# ==========================================


def get_training_status(save_dir):
    """获取当前训练状态"""
    csv_path = os.path.join(save_dir, 'results.csv')
    if not os.path.exists(csv_path):
        return None, 0, False
    
    df = pd.read_csv(csv_path)
    last_epoch = int(df['epoch'].iloc[-1]) if len(df) > 0 else 0
    
    # 计算最近 10 轮的损失变化
    if len(df) >= 10:
        recent = df['box_loss'].iloc[-10:].values
        improvement = recent[0] - recent[-1]
        is_converged = improvement < 0.001 and len(df) > 20
    else:
        is_converged = False
    
    return df, last_epoch, is_converged


def print_epoch_summary(df, epoch):
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
    
    # 打印最佳轮次
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


def check_gpu():
    """检查 GPU 状态"""
    print("\n" + "="*70)
    print("🖥️  系统检查")
    print("="*70)
    
    # 检查 CUDA
    print(f"  PyTorch CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU 名称: {torch.cuda.get_device_name(0)}")
        print(f"  GPU 显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("="*70 + "\n")


def train():
    # 先检查 GPU
    check_gpu()
    
    save_dir = os.path.join(PROJECT, NAME)
    has_checkpoint = os.path.exists(os.path.join(save_dir, 'weights', 'last.pt'))
    
    # ===== 检查是否有之前的训练进度 =====
    if has_checkpoint:
        df, last_epoch, is_converged = get_training_status(save_dir)
        
        # 打印历史汇总
        print_full_history(save_dir)
        
        # 检查是否已收敛
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
        print(f"   本次将接着训练第 {last_epoch + 1} 到第 {last_epoch + EPOCHS_PER_RUN} 轮")
        print(f"{'='*70}\n")
        print_convergence_info(df)
        
    else:
        print(f"\n{'='*70}")
        print("🚀 首次训练，本次将训练 5 轮")
        print(f"   预计用时: 1.5 - 2 小时")
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
    print(f"🏋️  开始训练...")
    print(f"   本次轮数: {EPOCHS_PER_RUN} 轮")
    print(f"   批次大小: {BATCH}")
    print(f"   图片尺寸: {IMGSZ}")
    print(f"   设备: GPU {DEVICE}")
    print(f"{'─'*70}\n")
    
    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS_PER_RUN,
        imgsz=IMGSZ,
        batch=BATCH,
        resume=has_checkpoint,   # 🔑 自动从断点继续
        patience=PATIENCE,       # 🔑 连续10轮没提升自动停止
        save_period=1,           # 每轮都保存
        project=PROJECT,
        name=NAME,
        device=DEVICE,
        workers=4,
        verbose=True,
    )
    
    # ===== 训练完成后，打印详细信息 =====
    print(f"\n{'='*70}")
    print("✅ 本轮训练完成！")
    print(f"{'='*70}")
    
    df, last_epoch, is_converged = get_training_status(save_dir)
    
    if df is not None:
        # 打印本轮新增的每一轮
        start_epoch = max(1, last_epoch - EPOCHS_PER_RUN + 1)
        for e in range(start_epoch, last_epoch + 1):
            if e <= len(df):
                print_epoch_summary(df, e)
        
        # 打印完整历史汇总
        print_full_history(save_dir)
        
        # 打印收敛状态
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
        print(f"💡 下次运行 'python train.py' 将接着训练")
        print(f"   当前进度: 第 {last_epoch} 轮 / 共 {last_epoch + EPOCHS_PER_RUN} 轮")
        print(f"   最佳模型: {save_dir}/weights/best.pt")
        print(f"{'='*70}\n")


if __name__ == '__main__':
    train()