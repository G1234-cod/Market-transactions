"""
将 COCO 格式的缺陷数据集转换为 YOLO 格式
"""
import os
import json
from tqdm import tqdm

# 路径配置
DATASET_ROOT = 'backend/dataset/defect_dataset'
ANNOTATIONS_DIR = os.path.join(DATASET_ROOT, 'annotations')
IMAGES_DIR = os.path.join(DATASET_ROOT, 'images')
LABELS_DIR = os.path.join(DATASET_ROOT, 'labels')

# 创建标签目录
os.makedirs(os.path.join(LABELS_DIR, 'train'), exist_ok=True)
os.makedirs(os.path.join(LABELS_DIR, 'val'), exist_ok=True)

print("="*60)
print("COCO 转 YOLO 格式转换")
print("="*60)

def convert_coco_to_yolo(json_path, image_dir, output_dir, split_name):
    """转换单个 COCO 标注文件"""
    print(f"\n🔄 转换 {split_name} 集...")
    
    if not os.path.exists(json_path):
        print(f"   ❌ 文件不存在: {json_path}")
        return 0
    
    with open(json_path, 'r', encoding='utf-8') as f:
        coco_data = json.load(f)
    
    images = {img['id']: img for img in coco_data['images']}
    categories = {cat['id']: cat for cat in coco_data['categories']}
    
    # 显示类别信息
    print(f"   类别: {len(categories)} 种")
    for cat_id, cat in categories.items():
        print(f"     - {cat['name']} (ID: {cat_id})")
    
    # 按图片分组
    annotations_by_image = {}
    for ann in coco_data['annotations']:
        img_id = ann['image_id']
        if img_id not in annotations_by_image:
            annotations_by_image[img_id] = []
        annotations_by_image[img_id].append(ann)
    
    print(f"   找到 {len(annotations_by_image)} 张图片")
    
    # 转换
    success_count = 0
    error_count = 0
    for img_id, anns in tqdm(annotations_by_image.items(), desc=f"   {split_name}进度"):
        img_info = images.get(img_id)
        if not img_info:
            continue
        
        # 只取文件名，去掉路径
        img_filename = os.path.basename(img_info['file_name'])
        img_filename = os.path.splitext(img_filename)[0]
        
        img_width = img_info['width']
        img_height = img_info['height']
        
        yolo_lines = []
        for ann in anns:
            cat_id = ann['category_id']
            if cat_id not in categories:
                continue
            
            x, y, w, h = ann['bbox']
            
            # 转换为 YOLO 格式（归一化）
            center_x = (x + w / 2) / img_width
            center_y = (y + h / 2) / img_height
            width = w / img_width
            height = h / img_height
            
            # 确保值在 [0, 1] 范围内
            center_x = max(0, min(1, center_x))
            center_y = max(0, min(1, center_y))
            width = max(0, min(1, width))
            height = max(0, min(1, height))
            
            # COCO ID 从 1 开始，YOLO 从 0 开始
            class_id = cat_id - 1
            
            yolo_lines.append(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}")
        
        if yolo_lines:
            output_path = os.path.join(output_dir, f"{img_filename}.txt")
            try:
                with open(output_path, 'w') as f:
                    f.write('\n'.join(yolo_lines))
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"   ⚠️ 写入失败: {img_filename} - {e}")
    
    print(f"   ✅ {split_name} 转换完成: {success_count} 个标签文件")
    if error_count > 0:
        print(f"   ⚠️  {error_count} 个文件写入失败")
    return success_count

# 转换训练集
train_json = os.path.join(ANNOTATIONS_DIR, 'instances_train.json')
if os.path.exists(train_json):
    convert_coco_to_yolo(
        train_json,
        os.path.join(IMAGES_DIR, 'train'),
        os.path.join(LABELS_DIR, 'train'),
        'train'
    )
else:
    print(f"❌ 找不到: {train_json}")

# 转换验证集
val_json = os.path.join(ANNOTATIONS_DIR, 'instances_val.json')
if os.path.exists(val_json):
    convert_coco_to_yolo(
        val_json,
        os.path.join(IMAGES_DIR, 'val'),
        os.path.join(LABELS_DIR, 'val'),
        'val'
    )
else:
    print(f"❌ 找不到: {val_json}")

print("\n" + "="*60)
print("🎉 所有转换完成！")
print(f"   标签目录: {LABELS_DIR}")
print("="*60)

# 统计结果
print("\n📊 转换结果统计:")
for split in ['train', 'val']:
    label_dir = os.path.join(LABELS_DIR, split)
    if os.path.exists(label_dir):
        count = len([f for f in os.listdir(label_dir) if f.endswith('.txt')])
        print(f"   {split}: {count} 个标签文件")