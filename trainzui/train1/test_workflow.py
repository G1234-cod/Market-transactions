import json
import os
import shutil
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=== 测试数据转换和训练流程 ===\n")

test_dir = "test_dataset"
os.makedirs(test_dir, exist_ok=True)

with open('photo/annotations/instances_val2017.json', 'r', encoding='utf-8') as f:
    coco = json.load(f)

images = coco['images'][:2]
annotations = coco['annotations']
categories = coco['categories']

ann_by_image = {}
for a in annotations:
    ann_by_image.setdefault(a['image_id'], []).append(a)

cat_ids = sorted(c['id'] for c in categories)
class_map = {cid: i for i, cid in enumerate(cat_ids)}

img_train_dir = os.path.join(test_dir, 'images', 'train')
lbl_train_dir = os.path.join(test_dir, 'labels', 'train')
os.makedirs(img_train_dir, exist_ok=True)
os.makedirs(lbl_train_dir, exist_ok=True)

for img in images:
    img_w, img_h = img['width'], img['height']
    info = ann_by_image.get(img['id'], [])
    file_name = img['file_name']
    stem = Path(file_name).stem
    
    lines = []
    for a in info:
        cid = a.get('category_id')
        if cid not in class_map:
            continue
        x, y, w, h = a['bbox']
        cx = max(0, min(1, (x + w / 2) / img_w))
        cy = max(0, min(1, (y + h / 2) / img_h))
        nw = max(0, min(1, w / img_w))
        nh = max(0, min(1, h / img_h))
        if nw <= 0 or nh <= 0:
            continue
        lines.append(f"{class_map[cid]} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
    
    lbl_path = os.path.join(lbl_train_dir, f"{stem}.txt")
    with open(lbl_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    
    src_img = os.path.join('photo/val2017', file_name)
    dst_img = os.path.join(img_train_dir, file_name)
    if os.path.exists(src_img) and not os.path.exists(dst_img):
        shutil.copy2(src_img, dst_img)

with open(os.path.join(test_dir, 'data.yaml'), 'w', encoding='utf-8') as f:
    f.write(f"path: .\ntrain: images/train\nval: images/train\n\nnc: 80\n")

print(f"✅ 测试数据准备完成")
print(f"  测试图片: {len(os.listdir(img_train_dir))}")
print(f"  测试标签: {len(os.listdir(lbl_train_dir))}")

sample_lbl = os.listdir(lbl_train_dir)[0]
with open(os.path.join(lbl_train_dir, sample_lbl), 'r', encoding='utf-8') as f:
    content = f.read()
print(f"\n📋 示例标签文件 {sample_lbl}:")
print(content if content else "  (空标签)")

print("\n=== 环境检测 ===")
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    free, total = torch.cuda.mem_get_info(0)
    print(f"显存: {free/1024**3:.1f}GB / {total/1024**3:.1f}GB")

print("\n=== 训练命令 ===")
print("在另一台电脑上运行:")
print("  python train.py")
print("\n训练配置 (train.py 中可修改):")
print("  MODEL_NAME = 'yolov8m.pt'  # 模型大小: n(小) / s / m / l / x(大)")
print("  EPOCHS = 5                  # 训练轮数")
print("  BATCH = 8                   # 批次大小 (显存不够改小)")
print("  IMGSZ = 640                 # 图片尺寸")

import shutil
shutil.rmtree(test_dir)
print("\n✅ 测试完成，临时文件已清理")
