"""
COCO / class-folder → YOLO 格式转换
====================================
支持两种来源，统一输出到 dataset/ 目录：

用法:
    cd D:\train-general

    # 方式1: COCO JSON
    python coco2yolo.py --coco_json D:/data/annotations.json --images_dir D:/data/images

    # 方式2: class 子文件夹（如 images/train/0/ images/train/1/ ...）
    python coco2yolo.py --from_folders D:/data/train

输出结构 (train.py 直接可用):
    dataset/
    ├── data.yaml
    ├── images/train/      ← 训练图片
    ├── images/val/        ← 验证图片
    ├── labels/train/      ← YOLO .txt 标签
    └── labels/val/        ← YOLO .txt 标签

COCO bbox: [x, y, w, h] (像素)  →  YOLO bbox: [cls, cx, cy, w, h] (归一化)
"""

import json
import os
import sys
import shutil
import random
import argparse
import re
from pathlib import Path

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================
# 配置
# ============================================================
OUTPUT_DIR  = "dataset"       # 输出到 dataset/
SPLIT_RATIO = 0.9             # 训练 / 验证划分
IMG_EXTS    = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
RANDOM_SEED = 42

# ============================================================
# 工具函数
# ============================================================
def banner(text):
    print(f"\n{'='*55}\n  {text}\n{'='*55}")

def get_image_size(img_path: str):
    """快速获取图片宽高（PIL / 文件头 fallback）"""
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            return im.size  # (w, h)
    except ImportError:
        pass

    # 纯 Python JPEG fallback
    try:
        with open(img_path, "rb") as f:
            f.seek(2)
            while True:
                marker = f.read(2)
                if not marker or len(marker) < 2:
                    break
                if marker[0] != 0xFF:
                    break
                m = marker[1]
                if m in (0xC0, 0xC1, 0xC2):
                    f.read(3)
                    hh, ww = f.read(2), f.read(2)
                    return int.from_bytes(ww, "big"), int.from_bytes(hh, "big")
                length = int.from_bytes(f.read(2), "big")
                f.read(length - 2)
    except Exception:
        pass

    return None


# ============================================================
# 模式 A: 标准 COCO JSON → YOLO
# ============================================================
def mode_coco_json(coco_json: str, images_dir: str, output_dir: str,
                   split: float, copy_images: bool, subset: str = None):
    """
    从 COCO JSON 标注文件转换。
    JSON 结构: {"images": [...], "annotations": [...], "categories": [...]}

    subset: "train" / "val" → 全部写入该子集；None → 自动按 split 切分
    """
    if not os.path.exists(coco_json):
        print(f"  ❌ 文件不存在: {coco_json}")
        sys.exit(1)

    with open(coco_json, "r", encoding="utf-8") as f:
        coco = json.load(f)

    images_list  = coco.get("images", [])
    annotations  = coco.get("annotations", [])
    categories   = coco.get("categories", [])

    print(f"  图片: {len(images_list)}  |  标注: {len(annotations)}  |  类别: {len(categories)}")

    if not images_list:
        print("  ❌ JSON 中无图片信息")
        sys.exit(1)

    # --- 类别映射: COCO cat_id → 0-based index ---
    cat_ids = sorted(c["id"] for c in categories)
    class_map = {cid: i for i, cid in enumerate(cat_ids)}

    for c in categories[:8]:
        print(f"    COCO id={c['id']} \"{c['name']}\" → YOLO class={class_map[c['id']]}")
    if len(categories) > 8:
        print(f"    ... 共 {len(categories)} 类")

    # --- image_id → annotations 索引 ---
    ann_by_image = {}
    for a in annotations:
        ann_by_image.setdefault(a["image_id"], []).append(a)

    # --- 创建输出目录 ---
    out = _make_output_dirs(output_dir)

    # --- 划分 train/val ---
    if subset in ("train", "val"):
        # 全部归入指定子集，不切分
        if subset == "train":
            train_imgs, val_imgs = images_list, []
        else:
            train_imgs, val_imgs = [], images_list
        print(f"  全部写入: {subset}")
    else:
        random.Random(RANDOM_SEED).shuffle(images_list)
        n = int(len(images_list) * split)
        train_imgs, val_imgs = images_list[:n], images_list[n:]
        print(f"  划分: train={len(train_imgs)} / val={len(val_imgs)}")

    # --- 转换 ---
    def _convert(img_list, lbl_dir, tag):
        ok = 0
        for img in _tqdm(img_list, f"  转换 {tag}"):
            img_w, img_h = img["width"], img["height"]
            info = ann_by_image.get(img["id"], [])
            stem = Path(img["file_name"]).stem
            lbl_path = os.path.join(lbl_dir, f"{stem}.txt")

            lines = []
            for a in info:
                cid = a.get("category_id")
                if cid not in class_map:
                    continue
                x, y, w, h = a["bbox"]
                cx = max(0, min(1, (x + w / 2) / img_w))
                cy = max(0, min(1, (y + h / 2) / img_h))
                nw = max(0, min(1, w / img_w))
                nh = max(0, min(1, h / img_h))
                if nw <= 0 or nh <= 0:
                    continue
                lines.append(f"{class_map[cid]} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            with open(lbl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
            ok += 1
        return ok

    train_ok = _convert(train_imgs, out["lbl_train"], "train")
    val_ok   = _convert(val_imgs,   out["lbl_val"],   "val")
    print(f"  ✅ train 标签: {train_ok}  |  val 标签: {val_ok}")

    # --- 复制图片 ---
    if copy_images and images_dir:
        _copy_images_coco(train_imgs, images_dir, out["img_train"], "train")
        _copy_images_coco(val_imgs,   images_dir, out["img_val"],   "val")

    # --- 更新 data.yaml ---
    _update_yaml(output_dir, len(class_map))

    _summary(output_dir, len(class_map), train_ok, val_ok)


# ============================================================
# 模式 B: class 子文件夹 → YOLO
# ============================================================
def mode_from_folders(src_dir: str, output_dir: str, split: float, copy_images: bool):
    """
    将按 class 分子文件夹的数据打平到 dataset/。

    源结构:
        src_dir/
        ├── images/train/
        │   ├── 0/   ← class 0 图片
        │   ├── 1/   ← class 1 图片
        │   └── ...
        └── labels/train/
            ├── 0/   ← class 0 标注 (YOLO .txt 或 COCO json)
            ├── 1/
            └── ...

    输出 (dataset/):
        images/train/*.jpg  +  labels/train/*.txt  (打平，不再分子文件夹)
    """
    src = Path(src_dir)

    # --- 自动检测源目录结构 ---
    possible_img_dirs = [
        src / "images" / "train",
        src / "images",
        src,
    ]
    possible_lbl_dirs = [
        src / "labels" / "train",
        src / "labels",
        src,
    ]

    img_root = None
    for d in possible_img_dirs:
        if d.is_dir():
            img_root = d
            break
    lbl_root = None
    for d in possible_lbl_dirs:
        if d.is_dir():
            lbl_root = d
            break

    if img_root is None:
        print(f"  ❌ 找不到图片目录\n  尝试了: {[str(d) for d in possible_img_dirs]}")
        sys.exit(1)

    print(f"  图片源: {img_root}")
    print(f"  标注源: {lbl_root}")

    # --- 扫描 class 子文件夹 ---
    class_dirs = sorted(
        [d for d in img_root.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )
    if not class_dirs:
        print(f"  ❌ {img_root} 下没有 class 子文件夹 (如 0/, 1/, ...)")
        sys.exit(1)

    # 尝试将文件夹名解析为 class_id
    class_ids = []
    for d in class_dirs:
        try:
            class_ids.append(int(d.name))
        except ValueError:
            class_ids.append(d.name)  # 保留为字符串

    num_classes = max([int(c) if isinstance(c, int) else -1 for c in class_ids]) + 1
    print(f"  class 子文件夹: {len(class_dirs)} 个")
    print(f"  推断类别数: {num_classes}")

    # --- 收集所有图片路径 ---
    all_pairs = []  # [(img_path, class_id)]
    for d, cid in zip(class_dirs, class_ids):
        class_id = int(cid) if isinstance(cid, int) else cid
        for f in d.iterdir():
            if f.suffix.lower() in IMG_EXTS:
                all_pairs.append((str(f), class_id))

    if not all_pairs:
        print(f"  ❌ 未找到图片文件")
        sys.exit(1)

    print(f"  总图片: {len(all_pairs)}")

    # --- 打乱并划分 ---
    random.Random(RANDOM_SEED).shuffle(all_pairs)
    n = int(len(all_pairs) * split)
    train_pairs, val_pairs = all_pairs[:n], all_pairs[n:]
    print(f"  划分: train={len(train_pairs)} / val={len(val_pairs)}")

    # --- 创建输出目录 ---
    out = _make_output_dirs(output_dir)

    # --- 处理 train ---
    lbl_map = _scan_label_files(lbl_root)  # stem → path

    train_ok = _flatten_split(train_pairs, out["img_train"], out["lbl_train"],
                              lbl_root, lbl_map, "train", copy_images)
    val_ok   = _flatten_split(val_pairs,   out["img_val"],   out["lbl_val"],
                              lbl_root, lbl_map, "val", copy_images)

    print(f"  ✅ train 标签: {train_ok}  |  val 标签: {val_ok}")

    # --- 更新 data.yaml ---
    _update_yaml(output_dir, num_classes)

    _summary(output_dir, num_classes, train_ok, val_ok)


# ============================================================
# 辅助函数
# ============================================================
def _make_output_dirs(output_dir):
    """创建 dataset/ 输出目录"""
    out = {}
    for k in ["img_train", "img_val", "lbl_train", "lbl_val"]:
        out[k] = os.path.join(output_dir, *{
            "img_train":  ["images", "train"],
            "img_val":    ["images", "val"],
            "lbl_train":  ["labels", "train"],
            "lbl_val":    ["labels", "val"],
        }[k])
        os.makedirs(out[k], exist_ok=True)
    return out


def _scan_label_files(lbl_root):
    """扫描标注目录，返回 {stem: (class_folder_name, label_path)}"""
    if lbl_root is None or not os.path.isdir(lbl_root):
        return {}
    lbl_map = {}
    for d in Path(lbl_root).iterdir():
        if not d.is_dir():
            continue
        for f in d.iterdir():
            lbl_map[f.stem] = (d.name, str(f))
    return lbl_map


def _flatten_split(pairs, img_dst, lbl_dst, lbl_root, lbl_map, tag, copy_images):
    """将 class 子文件夹中的图片+标注打平到目标目录"""
    ok = 0
    for img_path, class_id in _tqdm(pairs, f"  处理 {tag}"):
        stem = Path(img_path).stem
        dst_img = os.path.join(img_dst, os.path.basename(img_path))
        dst_lbl = os.path.join(lbl_dst, f"{stem}.txt")

        # 复制图片
        if copy_images and not os.path.exists(dst_img):
            shutil.copy2(img_path, dst_img)

        # 查找对应的标注文件
        found = False
        if lbl_root and os.path.isdir(lbl_root):
            if stem in lbl_map:
                _, lbl_path = lbl_map[stem]
                found = _process_label_file(lbl_path, dst_lbl, class_id)
            else:
                cls_lbl_dir = os.path.join(lbl_root, str(class_id))
                if os.path.isdir(cls_lbl_dir):
                    for ext in [".txt", ".json"]:
                        candidate = os.path.join(cls_lbl_dir, f"{stem}{ext}")
                        if os.path.exists(candidate):
                            found = _process_label_file(candidate, dst_lbl, class_id)
                            break

        # 无标注 → 空标签文件
        if not found:
            with open(dst_lbl, "w", encoding="utf-8") as lf:
                pass

        ok += 1
    return ok


def _process_label_file(src_label: str, dst_lbl: str, fallback_class_id: int) -> bool:
    """
    处理单个标注文件，转换为 YOLO .txt。
    支持 .txt (YOLO 格式) 和 .json (COCO 单图标注)。
    返回 True 表示写入了非空标签。
    """
    ext = os.path.splitext(src_label)[1].lower()

    if ext == ".txt":
        # 已经是 YOLO 格式，直接复制
        shutil.copy2(src_label, dst_lbl)
        return os.path.getsize(dst_lbl) > 0

    elif ext == ".json":
        try:
            with open(src_label, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        # 获取图片尺寸
        img_w, img_h = data.get("width", 0), data.get("height", 0)
        if not img_w or not img_h:
            # 尝试找同名图片获取尺寸
            img_path = os.path.splitext(src_label)[0]
            for ext_img in IMG_EXTS:
                if os.path.exists(img_path + ext_img):
                    size = get_image_size(img_path + ext_img)
                    if size:
                        img_w, img_h = size
                        break

        if not img_w or not img_h:
            # 无法获取尺寸，跳过
            return False

        lines = []
        anns = data.get("annotations", data.get("objects", []))
        for a in anns:
            cid = a.get("category_id", a.get("class_id", fallback_class_id))
            bbox = a.get("bbox", [])
            if len(bbox) != 4:
                continue
            x, y, w, h = bbox
            cx = max(0, min(1, (x + w / 2) / img_w))
            cy = max(0, min(1, (y + h / 2) / img_h))
            nw = max(0, min(1, w / img_w))
            nh = max(0, min(1, h / img_h))
            if nw <= 0 or nh <= 0:
                continue
            lines.append(f"{cid} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        with open(dst_lbl, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        return len(lines) > 0

    return False


def _copy_images_coco(img_list, src_dir, dst_dir, tag):
    """从 COCO JSON 的 file_name 复制图片"""
    ok = 0
    for img in _tqdm(img_list, f"  图片 → {tag}"):
        name = img["file_name"]
        src = os.path.join(src_dir, name)
        dst = os.path.join(dst_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            ok += 1
    print(f"  📷 {tag}: {ok} 张")


def _update_yaml(output_dir, num_classes):
    """更新 dataset/data.yaml 中的 nc"""
    yaml_path = os.path.join(output_dir, "data.yaml")
    if os.path.exists(yaml_path):
        content = Path(yaml_path).read_text(encoding="utf-8")
        content = re.sub(r'^nc:\s*\d+', f'nc: {num_classes}', content, flags=re.MULTILINE)
        Path(yaml_path).write_text(content, encoding="utf-8")
        print(f"  📝 已更新 data.yaml → nc: {num_classes}")
    else:
        print(f"  ⚠️  data.yaml 不存在，请手动设置 nc: {num_classes}")


def _summary(output_dir, num_classes, train_n, val_n):
    banner("✅ 转换完成")
    print(f"  输出目录: {Path(output_dir).resolve()}")
    print(f"  类别数:   {num_classes}")
    print(f"  训练集:   {train_n} 张")
    print(f"  验证集:   {val_n} 张")
    print(f"\n  下一步: python train.py\n")


def _tqdm(it, desc):
    """轻量进度条（优先 tqdm，否则纯 Python）"""
    try:
        from tqdm import tqdm as _tqdm
        return _tqdm(it, desc=desc, ncols=80)
    except ImportError:
        total = len(it) if hasattr(it, "__len__") else None
        printed = 0
        for item in it:
            yield item
            printed += 1
            if total and (printed % max(1, total // 10) == 0 or printed == total):
                print(f"  {desc} ... {printed}/{total}", end="\r")
        if total:
            print(f"  {desc} ... {total}/{total}")


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="COCO / class-folder → YOLO 格式转换 → dataset/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
=== COCO 2017 标准用法 ===

  1. 下载并解压到项目根目录:
     train2017.zip  →  train2017/
     val2017.zip    →  val2017/
     annotations_trainval2017.zip  →  annotations/

  2. 转换训练集:
     python coco2yolo.py --coco_json annotations/instances_train2017.json --images_dir train2017 --subset train

  3. 转换验证集:
     python coco2yolo.py --coco_json annotations/instances_val2017.json --images_dir val2017 --subset val

=== 其他用法 ===

  # 一份 JSON 自动切分 train/val
  python coco2yolo.py --coco_json D:/data/annotations.json --images_dir D:/data/images

  # Class 子文件夹打平
  python coco2yolo.py --from_folders D:/data/train

  # 调整切分比例
  python coco2yolo.py --coco_json ann.json --split 0.8
        """,
    )

    parser.add_argument("--coco_json", default=None,
                        help="COCO 标注 JSON 文件路径")
    parser.add_argument("--from_folders", default=None,
                        help="Class 子文件夹根目录 (如 train/)")
    parser.add_argument("--images_dir", default="images",
                        help="COCO 模式下，原始图片目录 (默认: images)")
    parser.add_argument("--output_dir", default=OUTPUT_DIR,
                        help=f"输出目录 (默认: {OUTPUT_DIR})")
    parser.add_argument("--split", type=float, default=SPLIT_RATIO,
                        help=f"训练集比例 (默认: {SPLIT_RATIO})，--subset 指定时忽略")
    parser.add_argument("--subset", default=None, choices=["train", "val"],
                        help="全部写入 train 或 val（COCO 有独立 train/val JSON 时使用）")
    parser.add_argument("--no_copy", action="store_true",
                        help="不复制图片，仅生成标签")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED,
                        help=f"随机种子 (默认: {RANDOM_SEED})")

    args = parser.parse_args()

    banner("COCO → YOLO 格式转换")

    # --- 模式选择 ---
    if args.from_folders:
        # 模式 B: class 子文件夹打平
        if not os.path.isdir(args.from_folders):
            print(f"  ❌ 目录不存在: {args.from_folders}")
            sys.exit(1)
        mode_from_folders(
            src_dir=args.from_folders,
            output_dir=args.output_dir,
            split=args.split,
            copy_images=not args.no_copy,
        )
    elif args.coco_json:
        # 模式 A: COCO JSON
        mode_coco_json(
            coco_json=args.coco_json,
            images_dir=args.images_dir,
            output_dir=args.output_dir,
            split=args.split,
            copy_images=not args.no_copy,
            subset=args.subset,
        )
    else:
        print("  请指定 --coco_json 或 --from_folders\n")
        print("  示例:")
        print("    python coco2yolo.py --coco_json annotations.json --images_dir images")
        print("    python coco2yolo.py --from_folders D:/data/train")
        sys.exit(1)


if __name__ == "__main__":
    main()
