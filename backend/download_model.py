"""
下载预训练模型脚本

运行此脚本下载 YOLOv8-Seg 预训练模型
"""
from ultralytics import YOLO


def download_model(model_size: str = "n"):
    """下载预训练模型

    Args:
        model_size: n(纳米/最快), s(小), m(中), l(大), x(最大/最准)
    """
    model_name = f"yolov8{model_size}-seg.pt"

    print(f"正在下载 {model_name} ...")
    model = YOLO(model_name)
    print(f"模型已保存，可以开始训练了！")

    return model_name


if __name__ == "__main__":
    import sys

    # 默认下载纳米版
    size = sys.argv[1] if len(sys.argv) > 1 else "n"

    valid_sizes = ["n", "s", "m", "l", "x"]
    if size not in valid_sizes:
        print(f"无效的模型大小: {size}")
        print(f"可选: {valid_sizes}")
        sys.exit(1)

    download_model(size)
