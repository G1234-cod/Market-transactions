# YOLO 目标检测 — 使用说明书

## 项目简介

基于 YOLOv8 的通用目标检测训练项目，输出 `best.pt` 模型文件。

- **数据集**：COCO 2017（80 类）
- **基础模型**：yolov8m.pt（首次运行自动下载）
- **输出**：`best.pt`（项目根目录）

---

## 目录结构

```text
项目根目录
├── README.md               ← 本说明书
├── coco2yolo.py            ← 格式转换工具（支持多种来源）
├── prepare_data.py         ← 数据准备脚本（简化版 COCO→YOLO）
├── test_workflow.py        ← 流程测试脚本
├── train.py                ← 训练脚本（主入口）
├── dataset/                ← 训练用数据集（转换后）
│   ├── data.yaml           ←   数据集配置
│   ├── images/train/       ←   训练图片
│   ├── images/val/         ←   验证图片
│   ├── labels/train/       ←   训练标签（YOLO .txt）
│   └── labels/val/         ←   验证标签（YOLO .txt）
├── photo/                  ← 原始 COCO 数据（下载后）
│   ├── train2017/          ←   训练图片（118287张）
│   ├── val2017/            ←   验证图片（5000张）
│   └── annotations/        ←   COCO JSON 标注
├── runs/train/             ← 训练输出
│   └── yolo_model/weights/
│       ├── best.pt         ←   最佳模型
│       └── last.pt         ←   断点续训用
└── best.pt                 ← 最终模型副本
```

---

## 1. 环境要求

| 项目 | 最低要求 | 推荐 |
| ---- | ---- | ---- |
| 操作系统 | Windows 10 / Linux / macOS | Windows 11 |
| Python | 3.8+ | 3.10+ |
| GPU | 无（CPU 也可） | NVIDIA 8GB+ 显存 |
| 磁盘 | 30GB 空闲 | 50GB+ SSD |

## 2. 安装依赖

```bash
# 有 NVIDIA GPU
pip install torch torchvision ultralytics

# 仅 CPU
pip install ultralytics
```

## 3. 准备数据集

选择你当前的情况，按步骤操作。

---

### 情况 A：还没下载（从零开始）

**第 1 步 — 下载 COCO 2017 数据集：**

下载以下三个文件到项目根目录：
- `train2017.zip`（约 18GB）
- `val2017.zip`（约 1GB）
- `annotations_trainval2017.zip`（约 250MB）

> 推荐使用迅雷等下载工具，下载速度更快。

**第 2 步 — 解压到 photo/ 目录：**

```bash
cd <项目目录>

# Windows 自带 tar（Win10 1803+），一行一个
mkdir photo
tar -xf train2017.zip -C photo
tar -xf val2017.zip -C photo
tar -xf annotations_trainval2017.zip -C photo
```

解压之后：

```text
<项目目录>/photo/
├── train2017/               ← 118287 张训练图片
├── val2017/                 ← 5000 张验证图片
└── annotations/             ← COCO JSON 标注
    ├── instances_train2017.json
    └── instances_val2017.json
```

**第 3 步 — 格式转换：**

使用简化脚本一键转换：

```bash
python prepare_data.py
```

或使用完整工具分别转换：

```bash
# 转换训练集（~5 分钟）
python coco2yolo.py --coco_json photo/annotations/instances_train2017.json --images_dir photo/train2017 --subset train

# 转换验证集（~30 秒）
python coco2yolo.py --coco_json photo/annotations/instances_val2017.json --images_dir photo/val2017 --subset val
```

**第 4 步 — 验证：**

```bash
python train.py
# 会自动检查 dataset/ 结构，没问题就开始训练
```

---

### 情况 B：已下载好三个 zip 文件（在其他盘）

假设 zip 文件在 `E:\downloads\` 下面：

```text
E:\downloads\
├── train2017.zip                (18GB)
├── val2017.zip                  (1GB)
└── annotations_trainval2017.zip (250MB)
```

**第 1 步 — 复制到项目根目录并解压：**

```bash
cd <项目目录>
mkdir photo

copy E:\downloads\train2017.zip                .
copy E:\downloads\val2017.zip                  .
copy E:\downloads\annotations_trainval2017.zip .

tar -xf train2017.zip -C photo
tar -xf val2017.zip -C photo
tar -xf annotations_trainval2017.zip -C photo
```

**第 2 步 — 格式转换：**

```bash
python prepare_data.py
```

**第 3 步 — 验证：**

```bash
python train.py
```

---

### 情况 C：已经解压好了（在其他盘）

假设已解压在 `E:\coco\`：

```text
E:\coco\
├── train2017/               ← 训练图片
├── val2017/                 ← 验证图片
└── annotations/             ← JSON 标注
    ├── instances_train2017.json
    └── instances_val2017.json
```

**推荐做法：复制到项目 photo/ 目录**

```bash
cd <项目目录>
mkdir photo
xcopy /E E:\coco\train2017       photo\train2017\
xcopy /E E:\coco\val2017         photo\val2017\
xcopy /E E:\coco\annotations     photo\annotations\

python prepare_data.py
```

**或直接指定路径转换（不推荐）：**

```bash
cd <项目目录>

python coco2yolo.py --coco_json E:\coco\annotations\instances_train2017.json --images_dir E:\coco\train2017 --subset train
python coco2yolo.py --coco_json E:\coco\annotations\instances_val2017.json --images_dir E:\coco\val2017 --subset val
```

> ⚠️ 直接指定路径时图片不会复制到项目目录，训练时需确保 data.yaml 配置正确。

---

## 4. 训练模型

```bash
python train.py
```

### 训练参数配置

编辑 `train.py` 顶部即可调整：

```python
MODEL_NAME = 'yolov8m.pt'   # YOLOv8 模型大小: n(小) / s / m / l / x(大)
EPOCHS     = 10             # 训练轮数（建议 50~300）
IMGSZ      = 640            # 输入图片尺寸
BATCH      = 8              # 批次大小（显存不足改小，如 4 或 2）
WORKERS    = 4              # 数据加载线程
```

### 断点续训

训练中断后重新运行 `python train.py` 会自动从 `runs/train/yolo_model/weights/last.pt` 续训，无需额外操作。

---

## 5. 自定义数据

### 5.1 自己的 COCO JSON

```bash
python coco2yolo.py \
    --coco_json my_annotations.json \
    --images_dir my_images \
    --split 0.9
```

`--split 0.9` 表示 90% 训练、10% 验证。

### 5.2 按类别文件夹组织的数据

如果数据是按 class 子文件夹存放的：

```text
my_data/
├── images/train/
│   ├── 0/          ← class 0 图片
│   ├── 1/          ← class 1 图片
│   └── ...
└── labels/train/
    ├── 0/          ← class 0 标签（.txt 或 .json）
    ├── 1/
    └── ...
```

转换命令：

```bash
python coco2yolo.py --from_folders my_data
```

### 5.3 修改类别

编辑 `dataset/data.yaml`：

```yaml
nc: 10                    # 改成你的类别数
names:
  0: cat
  1: dog
  # ... 列出所有类别
```

---

## 6. 模型输出

训练完成后：

| 文件 | 位置 | 用途 |
| ---- | ---- | ---- |
| `best.pt` | 项目根目录 | 最终模型，直接使用 |
| `last.pt` | `runs/train/yolo_model/weights/` | 断点续训 |
| `best.pt`（原始） | `runs/train/yolo_model/weights/` | 训练原始输出 |

### 使用模型推理

```python
from ultralytics import YOLO

model = YOLO("best.pt")
results = model("your_image.jpg")       # 单张图片
results = model("your_video.mp4")       # 视频
results = model(0)                       # 摄像头
```

---

## 7. 常见问题

### Q: 显存不足（CUDA out of memory）

修改 `train.py` 将 `BATCH` 改小：

```python
BATCH = 4   # 或 2
```

### Q: CPU 训练太慢

建议使用 GPU。如必须用 CPU，减少训练量：

```python
EPOCHS = 3
BATCH  = 2
```

### Q: 下载太慢

使用迅雷等下载工具手动下载三个 zip 文件，放到项目根目录后按"情况 B"的步骤解压和转换。

### Q: 训练中断了怎么办

直接重新运行 `python train.py`，自动从断点续训。

### Q: 只想用小数据集试一下

使用 val2017 作为训练集快速验证流程：

```bash
python coco2yolo.py --coco_json photo/annotations/instances_val2017.json --images_dir photo/val2017 --split 0.9
python train.py
```

### Q: 如何验证环境和数据流程是否正确

运行测试脚本来验证环境和数据转换流程：

```bash
python test_workflow.py
```

该脚本会：
- 从验证集取少量数据测试 COCO→YOLO 转换
- 检测 PyTorch 和 CUDA 环境
- 输出训练命令参考
- 测试完成后自动清理临时文件

### Q: 训练效果不好

- 增加 `EPOCHS`（建议 100~300）
- 换更大的基础模型（`yolov8l.pt` 或 `yolov8x.pt`）
- 增大 `IMGSZ`（如 1280）

---

## 8. 快速命令参考

```bash
# 环境
pip install torch torchvision ultralytics  # 有 NVIDIA GPU
pip install ultralytics                    # 仅 CPU

# 数据准备（二选一）
python prepare_data.py                     # 简化版一键转换（需先准备 photo/ 目录）
python coco2yolo.py --coco_json ...        # 完整工具手动转换

# 训练
python train.py                            # 开始训练 / 断点续训
python train.py --epochs 20                # 指定训练轮数

# 推理
python -c "from ultralytics import YOLO; YOLO('best.pt').predict('test.jpg', save=True)"
```
