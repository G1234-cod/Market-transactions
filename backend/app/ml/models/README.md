# ML 模型权重目录

此目录用于存放训练好的模型权重文件。

## 需要的模型文件

| 文件名 | 用途 | 训练来源 |
|--------|------|----------|
| `defect_best.pt` | YOLO 瑕疵检测模型（Kaputt 7类） | `trainzui/train2/train.py` |
| `damage_seg.pt` | YOLOv8-Seg 损伤分割模型 | 外部训练 |
| `best.pt` | YOLO 通用检测模型 | `trainzui/train1/train.py` |

## 训练命令

### 瑕疵检测模型
```bash
cd trainzui/train2
python convert_kaputt.py   # 先转换数据格式
python train.py             # 训练模型
```

### 损伤分割模型
```bash
# 需要先准备 Kaputt 分割数据集
```

## 注意

- 模型文件较大（通常 5-50 MB），请勿提交到 Git
- 运行前请确保模型文件已放入此目录
