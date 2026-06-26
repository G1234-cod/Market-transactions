"""
COCO 标注转 YOLO 格式
"""
import os
import json
from tqdm import tqdm

# 路径配置
DATA_ROOT = 'backend/dataset/coco'
TRAIN_PATH = os.path.join(DATA_ROOT, 'train2017')
VAL_PATH = os.path.join(DATA_ROOT, 'val2017')
ANNOTATIONS_PATH = os.path.join(DATA_ROOT, 'annotations')

# 创建标签目录
train_label_dir = os.path.join(DATA_ROOT, 'labels', 'train2017')
val_label_dir = os.path.join(DATA_ROOT, 'labels', 'val2017')
os.makedirs(train_label_dir, exist_ok=True)
os.makedirs(val_label_dir, exist_ok=True)

print("="*60)
print("COCO 标注转 YOLO 格式")
print("="*60)

def convert_coco_to_yolo(json_path, image_dir, output_dir):
    """转换 COCO 标注为 YOLO 格式"""
    print(f"\n🔄 转换: {os.path.basename(json_path)}")
    
    # 读取 COCO 标注
    with open(json_path, 'r', encoding='utf-8') as f:
        coco_data = json.load(f)
    
    # 构建映射
    images = {img['id']: img for img in coco_data['images']}
    categories = {cat['id']: cat for cat in coco_data['categories']}
    
    # 按图片分组标注
    annotations_by_image = {}
    for ann in coco_data['annotations']:
        img_id = ann['image_id']
        if img_id not in annotations_by_image:
            annotations_by_image[img_id] = []
        annotations_by_image[img_id].append(ann)
    
    print(f"   找到 {len(annotations_by_image)} 张图片的标注")
    
    # 转换每个图片的标注
    success_count = 0
    for img_id, anns in tqdm(annotations_by_image.items(), desc="   转换进度"):
        img_info = images.get(img_id)
        if not img_info:
            continue
        
        img_filename = os.path.splitext(img_info['file_name'])[0]
        img_width = img_info['width']
        img_height = img_info['height']
        
        yolo_lines = []
        for ann in anns:
            cat_id = ann['category_id']
            if cat_id not in categories:
                continue
            
            x, y, w, h = ann['bbox']
            
            # 转换为 YOLO 格式
            center_x = (x + w / 2) / img_width
            center_y = (y + h / 2) / img_height
            width = w / img_width
            height = h / img_height
            
            class_id = cat_id - 1  # COCO ID 从 1 开始
            
            yolo_lines.append(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}")
        
        if yolo_lines:
            output_path = os.path.join(output_dir, f"{img_filename}.txt")
            with open(output_path, 'w') as f:
                f.write('\n'.join(yolo_lines))
            success_count += 1
    
    print(f"   ✅ 转换完成: {success_count} 个标注文件")
    return success_count

# 转换训练集
train_json = os.path.join(ANNOTATIONS_PATH, 'instances_train2017.json')
if os.path.exists(train_json):
    convert_coco_to_yolo(train_json, TRAIN_PATH, train_label_dir)
else:
    print(f"❌ 找不到训练集标注: {train_json}")
    print("   请确认 annotations_trainval2017.zip 已解压")

# 转换验证集
val_json = os.path.join(ANNOTATIONS_PATH, 'instances_val2017.json')
if os.path.exists(val_json):
    convert_coco_to_yolo(val_json, VAL_PATH, val_label_dir)
else:
    print(f"❌ 找不到验证集标注: {val_json}")

print("\n" + "="*60)
print("🎉 所有标注转换完成！")
print(f"   训练集标签: {train_label_dir}")
print(f"   验证集标签: {val_label_dir}")
print("="*60)