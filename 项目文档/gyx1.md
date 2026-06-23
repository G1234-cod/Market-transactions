

---

# 📦 项目改动与操作手册

---

## 第一部分：项目更改文件详细说明

### 一、修改的文件（已存在的文件）

|          文件          | 相对路径                       | 修改内容                                                   | 功能说明                                            |
| :------------------: | :------------------------- | :----------------------------------------------------- | :---------------------------------------------- |
|     **main.py**      | `backend/main.py`          | 添加了 YOLO 路由注册                                          | 让 `/api/v1/yolo/detect` 接口可以被访问，这是 YOLO 检测功能的入口 |
| **requirements.txt** | `backend/requirements.txt` | 添加了 ultralytics、opencv-python、Pillow、torch、torchvision | YOLO 运行所需的 Python 依赖包                           |

---

### 二、新增的文件

| 文件 | 相对路径 | 功能说明 |
|:---:|:---|:---|
| `__init__.py` | `backend/app/ml/__init__.py` | Python 包标识文件，让 `ml/` 目录可以被 import |
| **yolo_detector.py** | `backend/app/ml/yolo_detector.py` | YOLO 检测器核心类：加载模型、检测图片、画框标注、转 Base64 |
| `__init__.py` | `backend/app/ml/models/__init__.py` | Python 包标识文件，让 `models/` 目录可以被 import |
| **detect.py** | `backend/app/routers/detect.py` | API 路由：提供图片检测接口 `/api/v1/yolo/detect` |
| **data.yaml** | `train/data.yaml` | 数据集配置文件：告诉训练程序 COCO 数据集的位置和类别信息 |
| **train.py** | `train/train.py` | 训练脚本：在朋友电脑上运行，用 COCO 数据集训练 YOLOv8 模型 |
| **gyx.md** | `项目文档/gyx.md` | 项目说明文档，记录改动信息和操作指南 |

---

### 三、新增文件夹

| 文件夹 | 相对路径 | 功能说明 |
|:---:|:---|:---|
| **ml/** | `backend/app/ml/` | 存放所有机器学习相关代码，与 `db/`、`llm/`、`models/` 等模块平级 |
| **models/** | `backend/app/ml/models/` | 存放训练好的模型权重文件（如 `best.pt`） |

---

### 四、目录结构总览

```
backend/
├── main.py                          # ⚠️ 已修改
├── requirements.txt                 # ⚠️ 已修改
├── app/
│   ├── ml/                          # 🆕 新增文件夹
│   │   ├── __init__.py              # 🆕 新增
│   │   ├── yolo_detector.py         # 🆕 新增
│   │   └── models/                  # 🆕 新增文件夹
│   │       └── __init__.py          # 🆕 新增
│   └── routers/
│       └── detect.py                # 🆕 新增
├── train/                           # 🆕 新增文件夹
│   ├── data.yaml                    # 🆕 新增
│   └── train.py                     # 🆕 新增
└── 项目文档/
    └── gyx.md                       # 🆕 新增
```

---

## 第二部分：给兄弟的完整操作手册（每一步都有命令）

---

### 🔰 第一步：接收文件

从我这接收以下内容，放到 `D:\Market-train\` 目录下：

| 文件名 | 说明 |
|:---|:---|
| `train.py` | 训练脚本 |
| `data.yaml` | 数据集配置文件 |
| `requirements.txt` | Python 依赖清单 |

---

### 🐍 第二步：安装 Python

**如果没有 Python：**

1. 打开浏览器，访问 [python.org](https://www.python.org)
2. 点击 **Downloads** → **Python 3.10.x**
3. 下载后双击安装
4. ⚠️ **一定要勾选 "Add Python to PATH"**
5. 点击 **Install Now**

**验证安装：**

```bash
python --version
```

---

### 📁 第三步：进入项目目录并创建虚拟环境

```bash
# 1. 进入项目目录
D:
cd D:\Market-train

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境（必须执行，看到 (venv) 开头才算成功）
venv\Scripts\activate
```

> ✅ 激活成功后，命令行前面会出现 `(venv)` 字样。

---

### 🖥️ 第四步：查看你的 CUDA 版本

```bash
nvidia-smi
```

查看右上角显示的 **CUDA Version**，例如：`11.8`、`12.1` 或其他版本。**请记下这个版本号**，下一步会用到。

---

### 📦 第五步：安装 PyTorch（根据 CUDA 版本选一个）

**✅ 如果 CUDA 是 11.8：**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**✅ 如果 CUDA 是 12.1：**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**✅ 如果没有 NVIDIA 显卡或不知道 CUDA 版本：**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

---

### 📥 第六步：安装项目依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果下载太慢，用这个命令（清华镜像源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### ✅ 第七步：验证 GPU 是否可用

```bash
python -c "import torch; print('CUDA可用:', torch.cuda.is_available())"
```

| 输出结果 | 含义 |
|:---|:---|
| `CUDA可用: True` | ✅ GPU 配置成功，训练速度很快 |
| `CUDA可用: False` | ⚠️ 也能训练，只是速度慢很多（使用 CPU） |

---

### 🌐 第八步：下载 COCO 数据集（约 20GB）

#### 方式一：用 fiftyone 自动下载（推荐，但需要外网）

```bash
# 1. 安装 fiftyone
pip install fiftyone

# 2. 下载 COCO 训练集（约18GB，需要几小时，保持网络稳定）
python -c "import fiftyone.zoo as foz; foz.load_zoo_dataset('coco-2017', split='train', dataset_dir='./datasets/coco')"
```

#### 方式二：手动下载（如果方式一太慢或报错）

1. 打开浏览器，访问 [cocodataset.org](https://cocodataset.org)
2. 点击 **Download**
3. 下载这三个文件（建议用迅雷或 IDM 加速）：

| 文件名 | 大小 |
|:---|:---:|
| `train2017.zip` | 18GB |
| `val2017.zip` | 1GB |
| `annotations_trainval2017.zip` | 241MB |

4. 下载完成后，解压到对应目录：

| 压缩包 | 解压目标路径 |
|:---|:---|
| `train2017.zip` | `D:\Market-train\datasets\coco\train2017\` |
| `val2017.zip` | `D:\Market-train\datasets\coco\val2017\` |
| `annotations_trainval2017.zip` | `D:\Market-train\datasets\coco\annotations\` |

---

### 🔍 第九步：验证数据集目录结构

```bash
dir datasets\coco
```

应该看到：

```
datasets/coco/
├── train2017/          # 里面是图片文件
├── val2017/            # 里面是图片文件
└── annotations/        # 里面是 JSON 文件
```

---

### 🚀 第十步：开始训练

```bash
# 1. 进入 train 目录
cd train

# 2. 如果显卡内存不够（比如显卡是 6GB），修改 batch size
# 用记事本打开 train.py，找到 BATCH = 16
# 改成 BATCH = 8 或 BATCH = 4，然后保存

# 3. 启动训练
python train.py
```

**训练开始后，你会看到类似这样的输出：**

```
============================================================
YOLOv8 COCO 完整数据集训练
============================================================
模型: yolov8m.pt
数据集: coco.yaml
轮数: 50
图片尺寸: 640
============================================================
Downloading https://github.com/ultralytics/assets/releases/...
...
Epoch    GPU_mem   box_loss   cls_loss   dfl_loss  Instances       Size
1/50      8.2G      1.234      2.456      1.789         32        640
2/50      8.3G      1.198      2.312      1.765         32        640
...
```

> ⏱️ **训练时间：约 16-24 小时（取决于显卡性能）**

---

### 🎯 第十一步：训练完成后

```bash
# 1. 查看模型文件
dir runs\train\coco_yolov8m\weights\
# 应该看到 best.pt

# 2. 验证模型效果（可选）
yolo val model=runs/train/coco_yolov8m/weights/best.pt data=data.yaml

# 3. 测试单张图片（可选）
yolo predict model=runs/train/coco_yolov8m/weights/best.pt source=test.jpg
```

---

### 📤 第十二步：把模型发给我

训练完成后，把 `best.pt` 发给我：

| 项目 | 信息 |
|:---|:---|
| 文件位置 | `D:\Market-train\train\runs\train\coco_yolov8m\weights\best.pt` |
| 文件大小 | 约 50MB |
| 传输方式 | 微信或网盘都可以 |

---

## ⚠️ 常见问题解决

| 问题 | 解决办法 |
|:---|:---|
| **CUDA out of memory** | 打开 `train.py`，把 `BATCH = 16` 改成 `BATCH = 8` 或 `BATCH = 4` |
| **pip 下载太慢** | 用清华镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| **fiftyone 下载报错** | 用方式二手动下载 |
| **训练中途断开** | 重新运行 `python train.py`，会自动从断点继续 |
| **nvidia-smi 不是内部命令** | 说明 NVIDIA 驱动没装好，先装显卡驱动 |
| **Python 版本不对** | 需要 Python 3.8-3.11，用 `python --version` 查看 |

---

## 📊 训练时间参考

| 显卡 | 训练时间（50 epochs） |
|:---|:---:|
| RTX 3060 (12GB) | 约 20-24 小时 |
| RTX 3070 (8GB) | 约 18-22 小时 |
| RTX 3080 (10GB) | 约 14-18 小时 |
| RTX 4090 (24GB) | 约 8-12 小时 |

> 💡 如果用 `yolov8n.pt`（轻量模型）替代 `yolov8m.pt`，时间可以缩短一半。

---

## 📞 有问题联系我

遇到任何报错，把错误信息发给我，我帮你解决！ 💪