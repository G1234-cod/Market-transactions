# ============================================================
# YOLOv8-Seg 损伤检测数据集
# ============================================================

## 目录结构

```
dataset/
├── data.yaml          # 数据集配置文件
├── images/
│   ├── train/          # 训练图片
│   └── val/           # 验证图片
└── labels/
    ├── train/         # 训练标签（与图片一一对应）
    └── val/           # 验证标签
```

## 标注工具

推荐使用以下工具进行标注：

1. **Labelme** (推荐入门)
   ```bash
   pip install labelme
   labelme
   ```

2. **CVAT** (功能强大，支持团队协作)
   - https://cvat.org

3. **Label Studio** (多用途标注平台)
   - https://labelstudio.io

## 标注格式

使用 Labelme 标注后，需要转换为 YOLO 格式：

```bash
# 安装标注转换工具
pip install labelme2yolo

# 转换为 YOLO 格式
labelme2yolo dataset/labelme_json/ dataset/yolo/
```

## 标注类别（5类）

| 类别ID | 名称 | 颜色 | 说明 |
|--------|------|------|------|
| 0 | scratch | 红色 | 划痕、刮痕 |
| 1 | dent | 蓝色 | 凹陷、磕碰 |
| 2 | crack | 黄色 | 裂纹、裂痕 |
| 3 | stain | 绿色 | 污渍、染色 |
| 4 | other | 橙色 | 其他损伤 |

## 标注注意事项

1. **多边形要闭合**：起点和终点要重合
2. **紧贴边缘**：多边形边缘要尽量贴近损伤边界
3. **单个损伤一个框**：每种损伤单独标注
4. **清晰可辨**：只标注清晰可见的损伤
5. **数量建议**：每个类别至少 50-100 张图片效果会更好

## data.yaml 配置示例

```yaml
path: dataset
train: images/train
val: images/val

nc: 5  # 类别数量
names:
  0: scratch
  1: dent
  2: crack
  3: stain
  4: other
```

## 数据集准备流程

1. 收集图片（建议每个类别 50+ 张）
2. 使用 Labelme 进行多边形标注
3. 转换为 YOLO 格式
4. 检查标注是否正确（可视化）
5. 放到 images/train 和 images/val 目录
6. 同步 labels 目录
7. 修改 data.yaml 路径
8. 开始训练
