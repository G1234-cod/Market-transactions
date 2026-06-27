"""
瑕疵检测训练 — 输出 defect_best.pt
自动检测GPU/CPU，支持断点续训

用法:
    cd D:\train-defect
    python convert_kaputt.py --max-gb 1.0   # 先转换（随机选1GB）
    python train.py                          # 训练

首次运行自动下载 yolov8n.pt (~6MB)

数据流:
    dataset/              原始 Kaputt 数据（mask PNG + Parquet）
      ↓ convert_kaputt.py --max-gb 1.0
    photo/                YOLO 格式（images/ + labels/ + data.yaml）
      ↓ train.py
    defect_best.pt        训练好的模型
"""
from ultralytics import YOLO
import os, sys, shutil, torch

# ============================================================
# 配置（按需修改）
# ============================================================
MODEL_NAME   = 'yolov8n.pt'            # 基础模型 (nano, 可换 s/m/l/x)
DATA_YAML    = 'photo/data.yaml'       # 转换后的数据集配置
EPOCHS       = 8                       # 每次训练轮数
IMGSZ        = 640                     # 图片尺寸
BATCH        = 16                      # 批次大小（显存不够改小）
WORKERS      = 4                       # 数据加载线程
# ============================================================

DEVICE = 0 if torch.cuda.is_available() else 'cpu'
PROJECT  = 'runs/train_defect'
NAME     = 'defect_detector'
PATIENCE = 10

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# Kaputt 7 类缺陷
CLASS_IDS = {
    0: 'penetration',
    1: 'deformation',
    2: 'actuation',
    3: 'deconstruction',
    4: 'spillage',
    5: 'superficial',
    6: 'missing_unit',
}


def check_gpu():
    print(f"\n{'='*55}")
    if DEVICE == 0:
        free, total = torch.cuda.mem_get_info(0)
        print(f"  ✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"  显存: {free/1024**3:.1f}G 可用 / {total/1024**3:.1f}G 总计")
        print(f"  批次: {BATCH} (显存不够可改小)")
    else:
        print("  ⚠️  CPU 模式，训练会很慢")
    print(f"{'='*55}\n")


def check_dataset(yaml_path):
    """检查数据集完整性"""
    import yaml
    if not os.path.exists(yaml_path):
        return False, f"❌ data.yaml 不存在: {yaml_path}\n   请先运行: python convert_kaputt.py"

    with open(yaml_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    base = os.path.dirname(os.path.abspath(yaml_path))
    errors = []
    total_imgs = 0

    for key in ['train', 'val']:
        d = os.path.join(base, cfg.get(key, ''))
        if not os.path.isdir(d):
            errors.append(f"  缺少目录: {key} → {d}")
            continue
        imgs = [f for f in os.listdir(d) if os.path.splitext(f)[1].lower() in IMG_EXTS]
        if not imgs:
            errors.append(f"  {key} 目录无图片: {d}")
        else:
            total_imgs += len(imgs)

        label_dir = d.replace('images', 'labels')
        if not os.path.isdir(label_dir):
            errors.append(f"  缺少目录: labels/{key} → {label_dir}")
        else:
            labels = [f for f in os.listdir(label_dir) if f.endswith('.txt')]
            if not labels:
                errors.append(f"  labels/{key} 目录无标签文件")

    if errors:
        return False, "数据集不完整:\n" + "\n".join(errors)
    if total_imgs < 10:
        return False, f"图片太少 ({total_imgs}张)，建议至少每个类别50张"
    return True, f"共 {total_imgs} 张图片，结构正确"


def main():
    check_gpu()

    # 检查数据集
    ok, msg = check_dataset(DATA_YAML)
    print(f"📂 数据集检查:\n{msg}\n")
    if not ok:
        print("❌ 请先运行格式转换:\n")
        print("  python convert_kaputt.py              # 全部数据")
        print("  python convert_kaputt.py --subset 0.5 # 一半数据")
        print(f"\n  当前类别 ({len(CLASS_IDS)} 类): {CLASS_IDS}")
        sys.exit(1)

    # 检查断点
    save_dir = os.path.join(PROJECT, NAME)
    last_pt = os.path.join(save_dir, 'weights', 'last.pt')
    has_ckpt = os.path.exists(last_pt)

    if has_ckpt:
        print(f"🔄 从断点续训: {last_pt}")
        model = YOLO(last_pt)
    else:
        print(f"🚀 首次训练 ({EPOCHS} 轮)")
        model = YOLO(MODEL_NAME)

    print(f"   数据: {DATA_YAML}  |  设备: {DEVICE}  |  批次: {BATCH}\n")

    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        resume=has_ckpt,
        patience=PATIENCE,
        save_period=1,
        project=PROJECT,
        name=NAME,
        device=DEVICE,
        workers=WORKERS,
        verbose=True,
        augment=True,
        weight_decay=0.0005,
        dropout=0.1,
        cos_lr=True,
        warmup_epochs=2,
    )

    # 导出模型
    best_pt = os.path.join(save_dir, 'weights', 'best.pt')
    if os.path.exists(best_pt):
        shutil.copy(best_pt, "defect_best.pt")
        print(f"\n✅ 训练完成 → defect_best.pt ({(os.path.getsize('defect_best.pt')/1024**2):.1f}MB)")
    else:
        print(f"\n❌ 未生成模型文件，请检查训练日志")


if __name__ == '__main__':
    main()
