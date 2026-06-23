# 📦 项目改动与操作手册（完整版）


## 🖥️ 硬件要求（请先确认）

| 项目 | 要求 |
|:---|:---|
| **显卡** | NVIDIA 显卡，显存 6GB 以上（RTX 3060/4060 及以上） |
| **硬盘** | 剩余空间 50GB 以上（数据集 20GB + 解压 20GB + 其他） |
| **内存** | 16GB 以上 |
| **系统** | Windows 10/11 |

> ⚠️ 如果显存只有 4GB，需要把 BATCH 改成 2 或 4，训练会更慢。


## 第一部分：项目更改文件详细说明

### 一、修改的文件（已存在的文件）

| 文件 | 相对路径 | 修改内容 | 功能说明 |
|:---:|:---|:---|:---|
| **main.py** | `backend/main.py` | 添加了 YOLO 路由注册 | 让 `/api/v1/yolo/detect` 接口可以被访问，这是 YOLO 检测功能的入口 |
| **requirements.txt** | `backend/requirements.txt` | 添加了 ultralytics、opencv-python、Pillow、torch、torchvision、pandas、numpy | YOLO 运行所需的 Python 依赖包 |

---

### 二、新增的文件

| 文件 | 相对路径 | 功能说明 |
|:---:|:---|:---|
| `__init__.py` | `backend/app/ml/__init__.py` | Python 包标识文件，让 `ml/` 目录可以被 import |
| **yolo_detector.py** | `backend/app/ml/yolo_detector.py` | YOLO 检测器核心类：加载模型、检测图片、画框标注、转 Base64 |
| `__init__.py` | `backend/app/ml/models/__init__.py` | Python 包标识文件，让 `models/` 目录可以被 import |
| **detect.py** | `backend/app/routers/detect.py` | API 路由：提供图片检测接口 `/api/v1/yolo/detect` |
| **data.yaml** | `train/data.yaml` | 数据集配置文件：告诉训练程序 COCO 数据集的位置和类别信息 |
| **train.py** | `train/train.py` | 训练脚本（分段训练版）：每次训练5轮，自动断点续训，自动停止 |
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
│   └── train.py                     # 🆕 新增（分段训练版）
└── 项目文档/
    └── gyx.md                       # 🆕 新增
```


## 第二部分：给兄弟的完整操作手册（每一步都有命令）


### 🔰 第一步：接收文件

从我这接收以下内容，放到 `D:\Market-train\` 目录下：

| 文件名 | 说明 |
|:---|:---|
| `train.py` | 训练脚本（分段训练版，每次5轮） |
| `data.yaml` | 数据集配置文件 |
| `requirements.txt` | Python 依赖清单（已添加 pandas） |

📩 **文件获取方式：**

我会通过微信/QQ 把以上文件发给你（压缩包）。收到后，在 D 盘根目录新建 `Market-train` 文件夹，把文件放进去即可。


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

💡 **虚拟环境是什么？**

你可以把它理解成一个独立的「小房间」，这个房间里装的 Python 包只在这个项目里用，不影响电脑上其他项目。

以后每次重新打开命令行训练时，都需要先执行：
```bash
venv\Scripts\activate
```
看到命令行前面出现 `(venv)` 才表示进入了正确的环境。


### 🖥️ 第四步：查看你的 CUDA 版本

```bash
nvidia-smi
```

查看右上角显示的 **CUDA Version**，例如：`11.8`、`12.1` 或其他版本。**请记下这个版本号**，下一步会用到。


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


### 📥 第六步：安装项目依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果下载太慢，用这个命令（清华镜像源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

📦 **requirements.txt 包含以下依赖**（自动安装，不用手动操作）：

| 依赖包 | 说明 |
|:---|:---|
| `ultralytics` | YOLOv8 框架 |
| `opencv-python` | 图像处理 |
| `Pillow` | 图片读写 |
| `torch` + `torchvision` | PyTorch 深度学习框架（第五步已装） |
| `pandas` | 读取训练历史数据，显示汇总表格 |
| `numpy` | 数值计算（pandas 依赖） |


### ✅ 第七步：验证 GPU 是否可用

```bash
python -c "import torch; print('CUDA可用:', torch.cuda.is_available())"
```

| 输出结果 | 含义 |
|:---|:---|
| `CUDA可用: True` | ✅ GPU 配置成功，训练速度很快 |
| `CUDA可用: False` | ⚠️ 也能训练，只是速度慢很多（使用 CPU） |


### 🌐 第八步：下载 COCO 数据集（约 20GB）

#### 方式一：用 fiftyone 自动下载（需要外网）

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

🔗 **迅雷下载链接**（直接复制到迅雷新建任务）：

| 文件 | 下载链接 |
|:---|:---|
| train2017.zip（18GB） | `http://images.cocodataset.org/zips/train2017.zip` |
| val2017.zip（1GB） | `http://images.cocodataset.org/zips/val2017.zip` |
| annotations_trainval2017.zip（241MB） | `http://images.cocodataset.org/annotations/annotations_trainval2017.zip` |

> 💡 用迅雷下载比浏览器快很多，18GB 约 30-60 分钟可下完。

4. 下载完成后，解压到对应目录：

| 压缩包 | 解压目标路径 |
|:---|:---|
| `train2017.zip` | `D:\Market-train\datasets\coco\train2017\` |
| `val2017.zip` | `D:\Market-train\datasets\coco\val2017\` |
| `annotations_trainval2017.zip` | `D:\Market-train\datasets\coco\annotations\` |


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


### ⚙️ 第十步：确认 GPU 配置（train.py 已配置好）

新版 `train.py` 已默认配置 GPU，**无需修改代码**。

```python
# train.py 中已配置
DEVICE = 0  # 使用 GPU 0
```

如果需要确认训练时是否使用 GPU，看训练日志中是否有：
- `device=0` 或 `device=cuda:0`
- `GPU_mem` 列显示显存占用


### 🚀 第十一步：开始训练

```bash
# 1. 进入 train 目录
cd train

# 2. 如果显卡内存不够（比如显卡是 6GB），修改 batch size
# 用记事本打开 train.py，找到 BATCH = 8
# 改成 BATCH = 4，然后保存

# 3. 启动训练（每次只训练5轮，约1.5-2小时，可随时中断）
python train.py
```

> 💡 **训练说明**：
> - 每次运行只训练 **5 轮**，约 **1.5-2 小时**
> - 训练完成后会显示本轮每一轮的误差详情
> - 下次再运行 `python train.py`，会自动从断点继续训练
> - 连续 **10 轮** 误差没有明显下降，训练会自动停止
> - 不需要一直守在电脑前，可以关掉显示器

**训练开始后，你会看到类似这样的输出：**

```
================================================================================
🖥️  系统检查
================================================================================
  PyTorch CUDA 可用: True
  GPU 名称: NVIDIA GeForce RTX 4060
  GPU 显存: 8.0 GB
================================================================================

================================================================================
🚀 首次训练，本次将训练 5 轮
   预计用时: 1.5 - 2 小时
================================================================================

✅ 加载预训练模型: yolov8m.pt

────────────────────────────────────────────────────────────────────
🏋️  开始训练...
   本次轮数: 5 轮
   批次大小: 8
   图片尺寸: 640
   设备: GPU 0
────────────────────────────────────────────────────────────────────

Epoch    GPU_mem   box_loss   cls_loss   dfl_loss  Instances       Size
1/5      7.2G      1.234      2.456      1.789         32        640
2/5      7.4G      1.198      2.312      1.765         32        640
3/5      7.5G      1.176      2.285      1.751         32        640
4/5      7.6G      1.168      2.273      1.745         32        640
5/5      7.6G      1.162      2.264      1.740         32        640

================================================================================
✅ 本轮训练完成！
================================================================================

────────────────────────────────────────────────────────────────────
📍 第 1 轮训练完成
────────────────────────────────────────────────────────────────────
  📉 边框损失:  1.234567  (越小越好)
  📉 分类损失:  2.456789  (越小越好)
  📉 分布损失:  1.789012  (越小越好)
  💾 显存占用:  7.2G
  📅 时间:      2026-06-23 20:30:15
────────────────────────────────────────────────────────────────────

... (第 2-5 轮同样显示)

================================================================================
📊 训练历史汇总 (共 5 轮)
================================================================================
  轮次 |    边框损失 |    分类损失 |    分布损失 |  显存
--------------------------------------------------------------------------------
     1 |    1.234567 |    2.456789 |    1.789012 |    7.2G
     2 |    1.198765 |    2.312345 |    1.765432 |    7.4G
     3 |    1.176543 |    2.285678 |    1.751234 |    7.5G
     4 |    1.168432 |    2.273456 |    1.745678 |    7.6G
     5 |    1.162345 |    2.264123 |    1.740123 |    7.6G
================================================================================

🏆 最佳模型在第 5 轮，边框损失 = 1.162345
   保存在: runs/train/coco_yolov8m/weights/best.pt

────────────────────────────────────────────────────────────────────
📈 收敛状态检查 (最近10轮)
────────────────────────────────────────────────────────────────────
  最近10轮第1轮边框损失:  1.234567
  最近10轮最后1轮边框损失:  1.162345
  改进幅度:                0.072222
  ✅ 仍有改进空间，建议继续训练
────────────────────────────────────────────────────────────────────

================================================================================
💡 下次运行 'python train.py' 将接着训练
   当前进度: 第 5 轮 / 共 10 轮
   最佳模型: runs/train/coco_yolov8m/weights/best.pt
================================================================================
```

> ⏱️ **训练时间**：每次 5 轮约 1.5-2 小时（RTX 4060），总共可能需要 10-20 次运行（50-100 轮）

💡 **训练过程中常见问题：**

| 问题 | 回答 |
|:---|:---|
| **需要一直守着电脑吗？** | 不需要。训练开始后可以关掉显示器，让电脑自己跑。但要确保：①电源选项里设置「从不睡眠」②笔记本要插电源 |
| **训练中途断开了怎么办？** | 重新运行 `python train.py`，会自动从最近的 checkpoint 继续训练，不会从头开始 |
| **训练时电脑会很卡吗？** | 会。训练时 GPU 占满，电脑会变卡，不建议同时打游戏或看视频。建议晚上睡觉前启动，第二天起来看结果 |
| **每次运行训练多少轮？** | 脚本配置为每次 5 轮，约 1.5-2 小时 |
| **什么时候自动停止？** | 连续 10 轮边框损失下降小于 0.001 时，自动停止 |


### 🎯 第十二步：训练完成后

训练完成后（自动停止或手动停止），查看模型文件：

```bash
# 1. 查看模型文件
dir runs\train\coco_yolov8m\weights\
# 应该看到 best.pt

# 2. 验证模型效果（可选）
yolo val model=runs/train/coco_yolov8m/weights/best.pt data=data.yaml

# 3. 测试单张图片（可选）
yolo predict model=runs/train/coco_yolov8m/weights/best.pt source=test.jpg
```


### 📤 第十三步：把模型发给我

训练完成后，把 `best.pt` 发给我：

| 项目 | 信息 |
|:---|:---|
| 文件位置 | `D:\Market-train\train\runs\train\coco_yolov8m\weights\best.pt` |
| 文件大小 | 约 50MB |
| 传输方式 | 微信或网盘都可以 |

⚠️ **注意：** 训练完成后会生成多个 `.pt` 文件，**只需要发 `best.pt` 给我**：

- `best.pt` ← **这个给我**（验证集上效果最好的模型）
- `last.pt` ← 这个不用发（训练结束时保存的最后一个 epoch，效果不如 best.pt）


## ⚠️ 常见问题解决

| 问题 | 解决办法 |
|:---|:---|
| **CUDA out of memory** | 打开 `train.py`，把 `BATCH = 8` 改成 `BATCH = 4` 或 `BATCH = 2` |
| **pip 下载太慢** | 用清华镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| **fiftyone 下载报错** | 用方式二手动下载 |
| **训练中途断开** | 重新运行 `python train.py`，会自动从断点继续 |
| **nvidia-smi 不是内部命令** | 说明 NVIDIA 驱动没装好，先装显卡驱动 |
| **Python 版本不对** | 需要 Python 3.8-3.11，用 `python --version` 查看 |
| **训练时电脑自动休眠了** | 打开 Windows 设置 → 电源和睡眠 → 都设为「从不」，训练完再改回来 |
| **YOLO 权重下载慢/超时** | 用迅雷手动下载 `yolov8m.pt`（约 50MB），放到 `D:\Market-train\train\` 目录下，训练时会自动跳过下载 |
| **解压 18GB zip 报错** | 用 7-Zip 或 WinRAR 解压，Windows 自带解压对大文件支持不好 |
| **训练时显示 device=cpu 而不是 cuda** | 检查 train.py 中 `DEVICE = 0` 是否正确配置 |
| **torch.cuda.is_available() 返回 False** | ①检查显卡驱动是否安装 ②确认第五步安装的是 CUDA 版本而非 CPU 版本 ③尝试重启电脑 |
| **ModuleNotFoundError: No module named 'pandas'** | 运行 `pip install pandas -i https://pypi.tuna.tsinghua.edu.cn/simple` |


## 📊 训练时间参考

| 显卡 | 每次5轮时间 | 总计50轮时间 |
|:---|:---:|:---:|
| RTX 3060 (12GB) | 约 2-2.5 小时 | 约 20-24 小时 |
| RTX 3070 (8GB) | 约 1.8-2.2 小时 | 约 18-22 小时 |
| RTX 3080 (10GB) | 约 1.5-1.8 小时 | 约 14-18 小时 |
| RTX 4060 (8GB) | 约 1.5-2 小时 | 约 20-24 小时 |
| RTX 4090 (24GB) | 约 0.8-1.2 小时 | 约 8-12 小时 |

> 💡 如果用 `yolov8n.pt`（轻量模型）替代 `yolov8m.pt`，时间可以缩短一半。


## 📞 有问题联系我

遇到任何报错，把错误信息发给我，我帮你解决！ 💪