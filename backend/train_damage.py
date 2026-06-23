"""
YOLOv8-Seg 损伤检测模型训练脚本（两阶段训练）

使用方法:

=== 阶段1: 预训练（使用公开数据集）===
python train_damage.py --phase pretrain --data dataset/pretrain.yaml

=== 阶段2: 微调（使用自定义数据集）===
python train_damage.py --phase finetune --data dataset/custom.yaml --pretrained runs/pretrain/weights/best.pt

参数说明:
--phase: pretrain（预训练）或 finetune（微调）
--data: 数据集配置文件路径
--pretrained: 预训练模型路径（微调时必填）
--epochs: 训练轮数（默认100）
--batch: 批次大小（默认8）
--imgsz: 输入图片尺寸（默认1024）

注意: 建议在高性能电脑（GPU: RTX 4060 或更高）上运行训练
"""
import os
import argparse
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8损伤检测模型训练")
    parser.add_argument("--phase", type=str, required=True, choices=["pretrain", "finetune"],
                        help="训练阶段: pretrain（预训练）或 finetune（微调）")
    parser.add_argument("--data", type=str, required=True, help="数据集配置文件路径")
    parser.add_argument("--pretrained", type=str, default=None,
                        help="预训练模型路径（微调阶段必填）")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--batch", type=int, default=8, help="批次大小")
    parser.add_argument("--imgsz", type=int, default=1024, help="输入图片尺寸")
    parser.add_argument("--model", type=str, default="yolov8n-seg.pt",
                        help="基础模型: yolov8n-seg, yolov8s-seg, yolov8m-seg, yolov8l-seg, yolov8x-seg")
    return parser.parse_args()


def train_pretrain(data_yaml, epochs, batch, imgsz, model_size):
    """阶段1: 使用公开数据集预训练"""
    print("=" * 60)
    print("阶段1: 预训练模式")
    print("=" * 60)
    
    model = YOLO(model_size)
    
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=20,
        save=True,
        save_period=10,
        device=0,
        
        # 数据增强
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10,
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        
        # 输出设置
        project="runs/pretrain",
        name="damage_pretrain",
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
    )
    
    best_model = "runs/pretrain/damage_pretrain/weights/best.pt"
    print(f"\n预训练完成！最佳模型: {best_model}")
    return best_model


def train_finetune(data_yaml, pretrained_model, epochs, batch, imgsz):
    """阶段2: 使用自定义数据集微调"""
    print("=" * 60)
    print("阶段2: 微调模式")
    print(f"加载预训练模型: {pretrained_model}")
    print("=" * 60)
    
    if not os.path.exists(pretrained_model):
        raise ValueError(f"预训练模型不存在: {pretrained_model}")
    
    # 加载预训练模型
    model = YOLO(pretrained_model)
    
    # 微调训练（使用较小的学习率）
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=15,
        save=True,
        save_period=5,
        device=0,
        
        # 微调时数据增强可以稍微保守一些
        hsv_h=0.01,
        hsv_s=0.5,
        hsv_v=0.3,
        degrees=5,
        translate=0.05,
        scale=0.3,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.5,
        
        # 输出设置
        project="runs/finetune",
        name="damage_finetune",
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.0001,  # 微调时使用更小的学习率
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
    )
    
    best_model = "runs/finetune/damage_finetune/weights/best.pt"
    print(f"\n微调完成！最佳模型: {best_model}")
    return best_model


def main():
    args = parse_args()
    
    if args.phase == "pretrain":
        train_pretrain(
            data_yaml=args.data,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            model_size=args.model
        )
    elif args.phase == "finetune":
        if not args.pretrained:
            raise ValueError("微调阶段必须指定 --pretrained 参数")
        
        best_model = train_finetune(
            data_yaml=args.data,
            pretrained_model=args.pretrained,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz
        )
        
        # 复制最终模型到部署位置
        os.makedirs("models", exist_ok=True)
        import shutil
        shutil.copy(best_model, "models/damage_seg.pt")
        print(f"\n✅ 已复制最终模型到: models/damage_seg.pt")


if __name__ == "__main__":
    main()