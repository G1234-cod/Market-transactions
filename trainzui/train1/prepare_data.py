import json
import os
import shutil
from pathlib import Path

def convert_coco_to_yolo(coco_json, images_dir, output_dir, subset):
    print(f"Processing {subset}...")
    
    with open(coco_json, 'r', encoding='utf-8') as f:
        coco = json.load(f)
    
    images = coco['images']
    annotations = coco['annotations']
    categories = coco['categories']
    
    ann_by_image = {}
    for a in annotations:
        ann_by_image.setdefault(a['image_id'], []).append(a)
    
    cat_ids = sorted(c['id'] for c in categories)
    class_map = {cid: i for i, cid in enumerate(cat_ids)}
    
    img_out_dir = os.path.join(output_dir, 'images', subset)
    lbl_out_dir = os.path.join(output_dir, 'labels', subset)
    os.makedirs(img_out_dir, exist_ok=True)
    os.makedirs(lbl_out_dir, exist_ok=True)
    
    total = len(images)
    for idx, img in enumerate(images):
        if idx % 1000 == 0:
            print(f"  [{idx}/{total}]")
        
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
        
        lbl_path = os.path.join(lbl_out_dir, f"{stem}.txt")
        with open(lbl_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        
        src_img = os.path.join(images_dir, file_name)
        dst_img = os.path.join(img_out_dir, file_name)
        if os.path.exists(src_img) and not os.path.exists(dst_img):
            shutil.copy2(src_img, dst_img)
    
    print(f"  Done: {total} images")
    return len(categories)

if __name__ == "__main__":
    output_dir = "dataset"
    
    nc = convert_coco_to_yolo(
        "photo/annotations/instances_train2017.json",
        "photo/train2017",
        output_dir,
        "train"
    )
    
    convert_coco_to_yolo(
        "photo/annotations/instances_val2017.json",
        "photo/val2017",
        output_dir,
        "val"
    )
    
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(f"path: .\ntrain: images/train\nval: images/val\n\nnc: {nc}\n")
    
    print(f"\nDataset prepared!")
    print(f"  Train images: {len(os.listdir(os.path.join(output_dir, 'images', 'train')))}")
    print(f"  Val images: {len(os.listdir(os.path.join(output_dir, 'images', 'val')))}")
    print(f"  Train labels: {len(os.listdir(os.path.join(output_dir, 'labels', 'train')))}")
    print(f"  Val labels: {len(os.listdir(os.path.join(output_dir, 'labels', 'val')))}")
