"""
Kaputt 数据集 → YOLO 格式转换
===============================
mask PNG（分割掩码）+ Parquet（缺陷类型元数据）→ YOLO txt 标签

用法:
    python convert_kaputt.py                  # 用全部数据
    python convert_kaputt.py --max-gb 1.0     # 随机选 ~1GB 图片
    python convert_kaputt.py --max-gb 2.5     # 随机选 ~2.5GB

输入: dataset/  （原始 Kaputt 数据）
输出: photo/    （YOLO 格式训练数据）

数据来源:
    dataset/datasets/query-{train,validation}.parquet   ← 元数据
    dataset/data/{train,validation}/query-data/image/*.jpg  ← 图片
    dataset/data/{train,validation}/query-data/mask/*.png   ← 分割掩码

输出结构:
    photo/
    ├── data.yaml           ← YOLO 数据集配置
    ├── images/train/       ← 训练图片
    ├── images/val/         ← 验证图片
    ├── labels/train/       ← YOLO txt 标签
    └── labels/val/         ← YOLO txt 标签
"""
import os, sys, shutil, argparse, random
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

# ============================================================
# 配置
# ============================================================
SRC_DIR     = 'dataset'       # 原始 Kaputt 数据目录
OUT_DIR     = 'photo'         # YOLO 格式输出目录
TRAIN_RATIO = 0.8             # train/val 划分比例
SEED        = 42              # 随机种子

# 7 类缺陷映射: 英文名 → class_id
DEFECT_MAP = {
    'penetration':    0,
    'deformation':    1,
    'actuation':      2,
    'deconstruction': 3,
    'spillage':       4,
    'superficial':    5,
    'missing_unit':   6,
}
# ============================================================


def find_parquet_dir(src):
    """找到 parquet 文件所在目录

    支持两种布局:
      - dataset/query-train.parquet       (parquet 直接在根)
      - dataset/datasets/query-train.parquet (parquet 在子目录)
    """
    datasets_dir = os.path.join(src, 'datasets')
    if os.path.isdir(datasets_dir):
        pq_files = list(Path(datasets_dir).glob('query-*.parquet'))
        if pq_files:
            return datasets_dir

    pq_files = list(Path(src).glob('query-*.parquet'))
    if pq_files:
        return src

    return None


def find_image_root(src):
    """找到图片根目录（data/ 或 kaputt-release/）"""
    for name in ['data', 'kaputt-release']:
        d = os.path.join(src, name)
        if os.path.isdir(d):
            return d
    return None


def load_parquet_metadata(pq_dir):
    """读所有 query-*.parquet，按 split 返回

    返回: {
        'train': [{capture_id, query_image, query_mask, defect_types, ...}, ...],
        'validation': [...],
    }
    """
    samples_by_split = {}

    for pq_path in sorted(Path(pq_dir).glob('query-*.parquet')):
        stem = pq_path.stem  # query-train
        split = stem.replace('query-', '')  # train, validation, test

        df = pd.read_parquet(pq_path)
        print(f"   {pq_path.name}: {len(df)} rows, cols: {list(df.columns)}")

        required = ['query_image', 'query_mask']
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"   skip {pq_path.name}: missing {missing}")
            continue

        samples_by_split[split] = df.to_dict('records')

    return samples_by_split


def mask_to_yolo_bboxes(mask_path, img_w, img_h, class_ids):
    """从 mask PNG 提取轮廓 -> YOLO bbox 列表

    返回: [(class_id, x_center, y_center, width, height), ...]
    """
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None

    _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    min_area = img_w * img_h * 0.0005

    for cnt in contours:
        if len(cnt) < 3:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < min_area:
            continue

        x_center = (x + w / 2) / img_w
        y_center = (y + h / 2) / img_h
        norm_w   = w / img_w
        norm_h   = h / img_h

        for cid in class_ids:
            bboxes.append((cid, x_center, y_center, norm_w, norm_h))

    return bboxes


def collect_defective_samples(src, pq_dir):
    """从所有 parquet 中收集有缺陷样本

    返回: [(capture_id, img_path, mask_path, [class_ids], img_size_bytes), ...]
    """
    samples_by_split = load_parquet_metadata(pq_dir)
    if not samples_by_split:
        print("no parquet data found")
        return []

    all_samples = []
    stats = {'total': 0, 'defective': 0, 'no_defect': 0}

    for split, rows in samples_by_split.items():
        for row in rows:
            stats['total'] += 1

            query_img_rel  = str(row.get('query_image', ''))
            query_mask_rel = str(row.get('query_mask', ''))

            if not query_img_rel:
                continue

            img_path  = os.path.join(src, query_img_rel)
            mask_path = os.path.join(src, query_mask_rel) if query_mask_rel else ''

            # defect types
            defect_str = str(row.get('defect_types', '')).strip().lower()
            if defect_str and defect_str not in ('nan', 'none', ''):
                types = [t.strip() for t in defect_str.split(',') if t.strip()]
            else:
                types = []

            if not types:
                stats['no_defect'] += 1
                continue

            # --> class_ids
            class_ids = []
            for dt in types:
                if dt in DEFECT_MAP:
                    class_ids.append(DEFECT_MAP[dt])
                else:
                    matched = False
                    for key, cid in DEFECT_MAP.items():
                        if key in dt or dt in key:
                            class_ids.append(cid)
                            matched = True
                            break
                    if not matched:
                        class_ids.append(5)  # superficial

            capture_id = str(row.get('capture_id', Path(query_img_rel).stem))

            # 文件大小（图片 + mask）
            size = 0
            if os.path.exists(img_path):
                size += os.path.getsize(img_path)
            if mask_path and os.path.exists(mask_path):
                size += os.path.getsize(mask_path)

            all_samples.append((capture_id, img_path, mask_path, class_ids, size))
            stats['defective'] += 1

    print(f"\n   total rows: {stats['total']}")
    print(f"   defective:   {stats['defective']}")
    print(f"   no defect:   {stats['no_defect']} (skipped)")
    return all_samples


def sample_by_size(samples, max_bytes):
    """随机选样本直到累计大小达到 max_bytes

    返回: selected_samples, total_bytes
    """
    random.seed(SEED)
    shuffled = samples[:]
    random.shuffle(shuffled)

    selected = []
    accumulated = 0

    for s in shuffled:
        if accumulated >= max_bytes:
            break
        selected.append(s)
        accumulated += s[4]  # s[4] = size in bytes

    return selected, accumulated


def convert_dataset(src, out, max_gb=None):
    """主转换函数

    max_gb: None=全部, 数字=上限 GB
    """
    print("=" * 55)
    print("  Kaputt -> YOLO format")
    print("=" * 55)

    # ---- 1. locate ----
    pq_dir = find_parquet_dir(src)
    if not pq_dir:
        print(f"no parquet found in {src}/")
        sys.exit(1)

    img_root = find_image_root(src)
    img_status = img_root if img_root else '(not found - extract query-image.tar.gz to dataset/)'
    print(f"\n  Parquet: {pq_dir}/")
    print(f"  Images:  {img_status}")

    # ---- 2. collect ----
    print(f"\ncollecting defective samples...")
    all_samples = collect_defective_samples(src, pq_dir)

    if not all_samples:
        print("no defective samples!")
        sys.exit(1)

    total_bytes = sum(s[4] for s in all_samples)
    print(f"   total image+mask size: {total_bytes / 1024**3:.2f} GB")

    # ---- 3. size-limited random selection ----
    if max_gb is not None:
        target_bytes = int(max_gb * 1024**3)
        selected, sel_bytes = sample_by_size(all_samples, target_bytes)
        print(f"\n  random selection: {len(selected)}/{len(all_samples)} samples")
        print(f"  selected size: {sel_bytes / 1024**3:.2f} GB (target ~{max_gb} GB)")
    else:
        selected = all_samples
        sel_bytes = total_bytes
        print(f"\n  using all {len(selected)} samples ({sel_bytes / 1024**3:.2f} GB)")

    # ---- 4. train/val split ----
    random.seed(SEED)
    random.shuffle(selected)
    split_idx = int(len(selected) * TRAIN_RATIO)
    train_samples = selected[:split_idx]
    val_samples   = selected[split_idx:]
    print(f"  train: {len(train_samples)}, val: {len(val_samples)}")

    # ---- 5. create output dirs ----
    for s in ['train', 'val']:
        Path(out, 'images', s).mkdir(parents=True, exist_ok=True)
        Path(out, 'labels', s).mkdir(parents=True, exist_ok=True)

    # ---- 6. convert & write ----
    print(f"\nconverting...")
    rs = {'train': {'done': 0, 'skip': 0, 'no_mask': 0},
          'val':   {'done': 0, 'skip': 0, 'no_mask': 0}}

    for split_name, split_samples in [('train', train_samples), ('val', val_samples)]:
        for capture_id, img_path, mask_path, class_ids, _size in split_samples:
            out_img  = Path(out, 'images', split_name, f"{capture_id}.jpg")
            out_label = Path(out, 'labels', split_name, f"{capture_id}.txt")

            if not os.path.exists(img_path):
                rs[split_name]['skip'] += 1
                continue

            if not out_img.exists():
                shutil.copy2(img_path, out_img)

            img = cv2.imread(img_path)
            if img is None:
                rs[split_name]['skip'] += 1
                continue
            h, w = img.shape[:2]

            bboxes = None
            if mask_path and os.path.exists(mask_path):
                bboxes = mask_to_yolo_bboxes(mask_path, w, h, class_ids)

            if bboxes is None or len(bboxes) == 0:
                rs[split_name]['no_mask'] += 1
                bboxes = [(cid, 0.5, 0.5, 1.0, 1.0) for cid in class_ids]

            with open(out_label, 'w') as f:
                for cid, xc, yc, bw, bh in bboxes:
                    xc = max(0.0, min(1.0, xc))
                    yc = max(0.0, min(1.0, yc))
                    bw = max(0.0, min(1.0, bw))
                    bh = max(0.0, min(1.0, bh))
                    f.write(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

            rs[split_name]['done'] += 1
            if rs[split_name]['done'] % 500 == 0:
                print(f"   {split_name}: {rs[split_name]['done']} done...")

    print(f"\n   train: {rs['train']['done']} done"
          + (f", {rs['train']['no_mask']} no-mask" if rs['train']['no_mask'] else "")
          + (f", {rs['train']['skip']} skipped" if rs['train']['skip'] else ""))
    print(f"   val:   {rs['val']['done']} done"
          + (f", {rs['val']['no_mask']} no-mask" if rs['val']['no_mask'] else "")
          + (f", {rs['val']['skip']} skipped" if rs['val']['skip'] else ""))

    # ---- 7. write data.yaml ----
    yaml_path = os.path.join(out, 'data.yaml')
    abs_out = os.path.abspath(out).replace('\\', '/')
    yaml_content = f"""# Kaputt Defect Detection - YOLO config (auto-generated)
path: {abs_out}
train: images/train
val: images/val

nc: 7
names:
  0: penetration
  1: deformation
  2: actuation
  3: deconstruction
  4: spillage
  5: superficial
  6: missing_unit
"""
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    total_done = rs['train']['done'] + rs['val']['done']
    print(f"\n  Done!")
    print(f"  Output:  {out}/")
    print(f"  Samples: train={rs['train']['done']}, val={rs['val']['done']}")
    print(f"  Classes: 7")
    print(f"  YAML:    {yaml_path}")
    return yaml_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Kaputt -> YOLO conversion')
    parser.add_argument('--max-gb', type=float, default=None,
                        help='Max GB of images to use (e.g. 1.0). Default: all data')
    parser.add_argument('--src', type=str, default=SRC_DIR)
    parser.add_argument('--out', type=str, default=OUT_DIR)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()

    convert_dataset(args.src, args.out, args.max_gb)
