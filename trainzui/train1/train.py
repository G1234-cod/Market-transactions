"""
通用目标检测训练 — 输出 best.pt
自动检测GPU/CPU，支持断点续训，分段训练
每轮结果写入 training_log.txt，控制台仅显示进度

用法:
    # 首次训练（或重新开始）
    python train.py
    
    # 断点续训（自动检测 last.pt）
    python train.py
    
    # 指定训练轮数（分段训练）
    python train.py --epochs 10
    
    # 查看帮助
    python train.py --help

首次运行自动下载 yolov8m.pt (~52MB)
"""
import os, sys, shutil, io, torch, csv, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from ultralytics import YOLO

# ============================================================
# 配置（按需修改）
# ============================================================
MODEL_NAME = 'yolov8m.pt'              # 基础模型
DATA_YAML  = 'dataset/data.yaml'       # 数据集配置
EPOCHS     = 10                        # 默认每次训练轮数
IMGSZ      = 640                       # 图片尺寸
BATCH      = 8                         # 批次大小（显存不够改小）
WORKERS    = 4                         # 数据加载线程
# ============================================================

DEVICE = 0 if torch.cuda.is_available() else 'cpu'
PROJECT  = 'runs/train'
NAME     = 'yolo_model'
PATIENCE = 10

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

LOG_FILE = 'training_log.txt'
START_TIME = None


def parse_args():
    parser = argparse.ArgumentParser(description='YOLOv8 目标检测训练脚本')
    parser.add_argument('--epochs', type=int, default=EPOCHS, help='每次训练轮数')
    parser.add_argument('--batch', type=int, default=BATCH, help='批次大小')
    parser.add_argument('--imgsz', type=int, default=IMGSZ, help='图片尺寸')
    parser.add_argument('--resume', action='store_true', help='强制从断点续训')
    parser.add_argument('--model', type=str, default=MODEL_NAME, help='模型名称或路径')
    parser.add_argument('--data', type=str, default=DATA_YAML, help='数据集配置文件')
    return parser.parse_args()


def check_gpu():
    info = []
    if DEVICE == 0:
        info.append(f"GPU: {torch.cuda.get_device_name(0)}")
        try:
            free, total = torch.cuda.mem_get_info(0)
            info.append(f"显存: {free/1024**3:.1f}G 可用 / {total/1024**3:.1f}G 总计")
        except AttributeError:
            info.append(f"显存: 已分配 {torch.cuda.memory_allocated(0)/1024**3:.1f}G / 缓存 {torch.cuda.memory_reserved(0)/1024**3:.1f}G")
    else:
        info.append("设备: CPU (训练会很慢)")
    return info


def check_dataset(yaml_path):
    import yaml
    if not os.path.exists(yaml_path):
        return False, f"data.yaml 不存在: {yaml_path}", None

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
    except UnicodeDecodeError:
        try:
            with open(yaml_path, 'r', encoding='gbk') as f:
                cfg = yaml.safe_load(f)
        except Exception as e:
            return False, f"无法读取 data.yaml: {e}", None
    except Exception as e:
        return False, f"读取 data.yaml 失败: {e}", None

    if not cfg:
        return False, "data.yaml 内容为空或格式错误", None

    base = os.path.dirname(yaml_path)
    errors = []
    stats = {}
    
    required_fields = ['train', 'val', 'nc', 'names']
    for field in required_fields:
        if field not in cfg:
            errors.append(f"  data.yaml 缺少 '{field}' 字段")
    
    if errors:
        return False, "数据集配置不完整:\n" + "\n".join(errors), None
    
    for key in ['train', 'val']:
        rel_path = cfg.get(key, '')
        d = os.path.join(base, rel_path) if not os.path.isabs(rel_path) else rel_path
        
        if not os.path.isdir(d):
            errors.append(f"  缺少目录: {key} → {d}")
            continue
            
        imgs = [f for f in os.listdir(d) if os.path.splitext(f)[1].lower() in IMG_EXTS]
        stats[f'{key}_images'] = len(imgs)
        
        if not imgs:
            errors.append(f"  {key} 目录无图片: {d}")
            continue

        possible_label_dirs = [
            d.replace('images', 'labels'),
            os.path.join(os.path.dirname(d), 'labels', os.path.basename(d)),
            os.path.join(base, 'labels', key)
        ]
        
        label_dir = None
        for possible_dir in possible_label_dirs:
            if os.path.isdir(possible_dir):
                label_dir = possible_dir
                break
        
        if not label_dir:
            errors.append(f"  找不到 labels 目录: 请检查 {d} 对应的 labels 文件夹")
            stats[f'{key}_labels'] = 0
        else:
            labels = [f for f in os.listdir(label_dir) if f.endswith('.txt')]
            stats[f'{key}_labels'] = len(labels)
            if not labels:
                errors.append(f"  {label_dir} 目录无标签文件")
            elif len(labels) < len(imgs) * 0.5:
                errors.append(f"  警告: 标签文件数量({len(labels)}) 远少于图片数量({len(imgs)})")

    stats['nc'] = cfg.get('nc', 0)
    stats['names'] = cfg.get('names', [])
    
    if errors:
        return False, "数据集不完整:\n" + "\n".join(errors), stats
    
    return True, f"数据集验证通过", stats


def log_epoch_metrics(epoch, total_epochs, metrics, lr, log_file):
    train_box = metrics.get('train/box_loss', 0.0)
    train_cls = metrics.get('train/cls_loss', 0.0)
    train_dfl = metrics.get('train/dfl_loss', 0.0)
    
    val_box = metrics.get('val/box_loss', 0.0)
    val_cls = metrics.get('val/cls_loss', 0.0)
    val_dfl = metrics.get('val/dfl_loss', 0.0)
    
    precision = metrics.get('metrics/precision(B)', 0.0)
    recall = metrics.get('metrics/recall(B)', 0.0)
    map50 = metrics.get('metrics/mAP50(B)', 0.0)
    map50_95 = metrics.get('metrics/mAP50-95(B)', 0.0)
    
    print(f"[EPOCH {epoch:3d}/{total_epochs:3d}] 训练中...")
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{epoch},{train_box:.4f},{train_cls:.4f},{train_dfl:.4f},{val_box:.4f},{val_cls:.4f},{val_dfl:.4f},{precision:.4f},{recall:.4f},{map50:.4f},{map50_95:.4f},{lr:.2e}\n")


def print_training_summary(save_dir, results, args, dataset_stats, gpu_info):
    global START_TIME
    end_time = time.time()
    total_time = end_time - START_TIME if START_TIME else 0
    
    print(f"\n{'='*80}")
    print("                        训练结果总结")
    print(f"{'='*80}")
    
    print(f"\n[训练配置]")
    print(f"  基础模型: {args.model}")
    print(f"  数据集:   {args.data}")
    print(f"  图片尺寸: {args.imgsz}x{args.imgsz}")
    print(f"  批次大小: {args.batch}")
    print(f"  训练轮数: {args.epochs}")
    print(f"  设备类型: {'GPU' if DEVICE == 0 else 'CPU'}")
    for line in gpu_info:
        print(f"  {line}")
    
    print(f"\n[数据集统计]")
    if dataset_stats:
        print(f"  训练集图片数: {dataset_stats.get('train_images', 0)}")
        print(f"  训练集标签数: {dataset_stats.get('train_labels', 0)}")
        print(f"  验证集图片数: {dataset_stats.get('val_images', 0)}")
        print(f"  验证集标签数: {dataset_stats.get('val_labels', 0)}")
        print(f"  类别总数:     {dataset_stats.get('nc', 0)}")
    
    print(f"\n[训练时间]")
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    print(f"  总训练时间:   {hours}小时{minutes}分钟{seconds}秒")
    print(f"  开始时间:     {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(START_TIME))}" if START_TIME else "")
    print(f"  结束时间:     {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    
    results_csv = os.path.join(save_dir, 'results.csv')
    if os.path.exists(results_csv):
        best_epoch = -1
        best_map50 = 0.0
        best_map50_95 = 0.0
        best_train_loss = float('inf')
        best_val_loss = float('inf')
        all_metrics = []
        
        with open(results_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                epoch = int(row['epoch'])
                map50 = float(row['metrics/mAP50(B)'])
                map50_95 = float(row['metrics/mAP50-95(B)'])
                train_loss = float(row['train/box_loss']) + float(row['train/cls_loss']) + float(row['train/dfl_loss'])
                val_loss = float(row['val/box_loss']) + float(row['val/cls_loss']) + float(row['val/dfl_loss'])
                all_metrics.append((epoch, map50, map50_95, train_loss, val_loss))
                if map50 > best_map50:
                    best_map50 = map50
                    best_map50_95 = map50_95
                    best_epoch = epoch
                    best_train_loss = train_loss
                    best_val_loss = val_loss
        
        print(f"\n[最佳指标]")
        print(f"  最佳 Epoch:      {best_epoch}")
        print(f"  最佳 mAP50:      {best_map50:.4f}")
        print(f"  最佳 mAP50-95:   {best_map50_95:.4f}")
        print(f"  最佳训练总损失:   {best_train_loss:.4f}")
        print(f"  最佳验证总损失:   {best_val_loss:.4f}")
        
        print(f"\n[各轮 mAP50 趋势]")
        for epoch, map50, _, train_loss, val_loss in all_metrics:
            marker = "*" if epoch == best_epoch else " "
            print(f"  Epoch {epoch:3d}: {marker} mAP50={map50:.4f}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")
    
    if hasattr(results, 'results_dict'):
        r = results.results_dict
        print(f"\n[最终验证指标]")
        print(f"  精确率 (Precision): {r.get('metrics/precision(B)', 0):.4f}")
        print(f"  召回率 (Recall):    {r.get('metrics/recall(B)', 0):.4f}")
        print(f"  mAP@0.5:           {r.get('metrics/mAP50(B)', 0):.4f}")
        print(f"  mAP@0.5:0.95:      {r.get('metrics/mAP50-95(B)', 0):.4f}")
        
        print(f"\n[最终损失值]")
        print(f"  训练框损失 (box):   {r.get('train/box_loss', 0):.4f}")
        print(f"  训练分类损失 (cls): {r.get('train/cls_loss', 0):.4f}")
        print(f"  训练DFL损失:        {r.get('train/dfl_loss', 0):.4f}")
        print(f"  验证框损失 (box):   {r.get('val/box_loss', 0):.4f}")
        print(f"  验证分类损失 (cls): {r.get('val/cls_loss', 0):.4f}")
        print(f"  验证DFL损失:        {r.get('val/dfl_loss', 0):.4f}")
    
    if hasattr(results, 'speed'):
        s = results.speed
        print(f"\n[训练速度]")
        print(f"  预处理时间: {s.get('preprocess', 0):.2f} ms/张")
        print(f"  推理时间:   {s.get('inference', 0):.2f} ms/张")
        print(f"  损失计算:   {s.get('loss', 0):.2f} ms/张")
        print(f"  后处理时间: {s.get('postprocess', 0):.2f} ms/张")
    
    if hasattr(results, 'model'):
        model_info = results.model
        print(f"\n[模型架构]")
        try:
            print(f"  模型类型: {type(model_info).__name__}")
            num_params = sum(p.numel() for p in model_info.parameters())
            print(f"  参数数量: {num_params:,}")
        except:
            pass
    
    best_pt = os.path.join(save_dir, 'weights', 'best.pt')
    last_pt = os.path.join(save_dir, 'weights', 'last.pt')
    if os.path.exists(best_pt):
        size_mb = os.path.getsize(best_pt) / 1024**2
        print(f"\n[模型文件]")
        print(f"  best.pt: {size_mb:.1f} MB")
        print(f"  路径:    {os.path.abspath(best_pt)}")
    
    if os.path.exists(last_pt):
        size_mb = os.path.getsize(last_pt) / 1024**2
        print(f"  last.pt: {size_mb:.1f} MB (用于断点续训)")
    
    print(f"\n[学习率策略]")
    print(f"  策略: Cosine Annealing")
    print(f"  预热轮数: 2")
    
    print(f"\n[数据增强]")
    print(f"  Mosaic: 启用")
    print(f"  MixUp: 启用")
    print(f"  其他增强: 启用")
    
    print(f"\n[早停设置]")
    print(f"  Patience: {PATIENCE} (连续{PATIENCE}轮无提升则停止)")
    
    if dataset_stats and 'names' in dataset_stats and dataset_stats['names']:
        print(f"\n[类别列表]")
        names = dataset_stats['names']
        if isinstance(names, list):
            for i, name in enumerate(names):
                print(f"  {i:2d}: {name}")
        elif isinstance(names, dict):
            for i, name in sorted(names.items()):
                print(f"  {int(i):2d}: {name}")
    
    print(f"\n{'='*80}")
    print(f"  提示: 下次运行 python train.py 将自动从 last.pt 断点续训")
    print(f"  提示: 训练日志已保存到 training_log.txt")
    print(f"{'='*80}")


def main():
    global START_TIME
    START_TIME = time.time()
    
    args = parse_args()
    
    gpu_info = check_gpu()
    print(f"\n{'='*80}")
    print(f"  GPU信息: {gpu_info[0]}")
    print(f"{'='*80}\n")

    ok, msg, dataset_stats = check_dataset(args.data)
    print(f"数据集检查:\n{msg}\n")
    if not ok:
        print("请按以下结构准备数据集:\n")
        print("  dataset/")
        print("  ├── data.yaml")
        print("  ├── images/train/")
        print("  ├── images/val/")
        print("  ├── labels/train/")
        print("  └── labels/val/")
        sys.exit(1)

    save_dir = os.path.join(PROJECT, NAME)
    last_pt = os.path.join(save_dir, 'weights', 'last.pt')
    has_ckpt = os.path.exists(last_pt) or args.resume

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n# 训练重启: {time.strftime('%Y-%m-%d %H:%M:%S')} epochs={args.epochs}\n")
    else:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# 训练开始: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("epoch,train_box_loss,train_cls_loss,train_dfl_loss,val_box_loss,val_cls_loss,val_dfl_loss,precision,recall,map50,map50_95,lr\n")

    if has_ckpt:
        print(f"🔄 从断点续训: {last_pt}")
        model = YOLO(last_pt)
    else:
        print(f"🚀 首次训练 ({args.epochs} 轮)")
        if not os.path.exists(args.model):
            print(f"📥 正在下载 {args.model}...")
        model = YOLO(args.model)

    print(f"  数据: {args.data}  |  设备: {DEVICE}  |  批次: {args.batch}")
    print(f"  图片尺寸: {args.imgsz}  |  线程数: {WORKERS}\n")

    def on_fit_epoch_end(trainer):
        metrics = trainer.metrics
        lr = trainer.optimizer.param_groups[0]['lr']
        log_epoch_metrics(trainer.epoch + 1, trainer.epochs, metrics, lr, LOG_FILE)

    model.add_callback('on_fit_epoch_end', on_fit_epoch_end)

    try:
        results = model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
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
            cos_lr=True,
            warmup_epochs=2,
        )

        best_pt = os.path.join(save_dir, 'weights', 'best.pt')
        if os.path.exists(best_pt):
            shutil.copy(best_pt, "best.pt")
            print(f"\n✅ 训练完成 → best.pt ({(os.path.getsize('best.pt')/1024**2):.1f}MB)")
        else:
            print("\n❌ 未生成模型文件，请检查训练日志")
            
        print_training_summary(save_dir, results, args, dataset_stats, gpu_info)

    except KeyboardInterrupt:
        print("\n⚠️  训练被用户中断，模型已保存到 runs/ 目录")
        print(f"   下次运行 python train.py 可从 last.pt 续训")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 训练出错: {e}")
        print("请检查数据集路径和格式")
        sys.exit(1)


if __name__ == '__main__':
    main()
