from ultralytics import YOLO
import os

# ============================================================
# 配置
# ============================================================
MODEL = 'yolov8m.pt'  # 可选: yolov8n/s/m/l/x
DATASET = 'coco.yaml'  # COCO 完整数据集配置
EPOCHS = 50
IMGSZ = 640
BATCH = 16  # 根据 GPU 内存调整

# ============================================================
# 训练
# ============================================================
def main():
    print("=" * 60)
    print("YOLOv8 COCO 完整数据集训练")
    print("=" * 60)
    print(f"模型: {MODEL}")
    print(f"数据集: {DATASET}")
    print(f"轮数: {EPOCHS}")
    print(f"图片尺寸: {IMGSZ}")
    print("=" * 60)
    
    # 检查数据集是否存在
    if not os.path.exists('datasets/coco'):
        print("❌ 请先下载 COCO 数据集！")
        print("下载命令:")
        print("  pip install fiftyone")
        print("  python -c \"import fiftyone.zoo as foz; foz.load_zoo_dataset('coco-2017', split='train', dataset_dir='./datasets/coco')\"")
        return
    
    # 加载模型
    model = YOLO(MODEL)
    
    # 训练
    results = model.train(
        data=DATASET,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device='cuda' if os.system('nvidia-smi') == 0 else 'cpu',
        workers=4,
        patience=20,
        save=True,
        project='runs/train',
        name='coco_yolov8m'
    )
    
    print("=" * 60)
    print("✅ 训练完成！")
    print(f"模型保存在: runs/train/coco_yolov8m/weights/best.pt")
    print("=" * 60)

if __name__ == "__main__":
    main()