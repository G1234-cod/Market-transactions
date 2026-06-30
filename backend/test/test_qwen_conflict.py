"""
测试 Qwen-VL 对 YOLO 检测结果的冲突判断能力。

模拟 recognition.py 中的 YOLO→Qwen 冲突检测流程：
1. 模拟 YOLO 检测结果（指定分类名和置信度）
2. 将 YOLO 上下文注入到 Qwen-VL 的 System Prompt
3. Qwen-VL 结合图片和 YOLO 结果，输出 yolo_correct 和 yolo_judgment

用法：直接修改 main() 中的参数，然后运行：
    python test_qwen_conflict.py
"""
import os
import sys
import json
import base64
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from PIL import Image
from app.llm.qwen_vl_client import EXTRACT_SYSTEM_PROMPT
from app.services.vision_service import parse_to_extract_result


def build_yolo_context(class_name: str, confidence: float) -> str:
    """模拟 YOLO 检测结果，生成上下文文本（格式与 yolo_detector.format_context 一致）"""
    return f"YOLO 模型检测到以下物品：\n  1. 类别={class_name}，置信度={confidence:.2f}"


def test_conflict_detection(
    image_path: str,
    yolo_class: str,
    yolo_confidence: float = 0.85,
    model: str = "qwen-vl-max",
):
    """
    测试 Qwen-VL 对 YOLO 检测结果的冲突判断。

    Args:
        image_path:   测试图片路径（相对于 backend/ 或绝对路径）
        yolo_class:   模拟的 YOLO 分类结果（英文，如 "laptop" / "phone"）
        yolo_confidence: 模拟的 YOLO 置信度
        model:        Qwen-VL 模型名称

    Returns:
        dict: {
            'yolo_class': str,
            'yolo_confidence': float,
            'qwen_category': str,
            'qwen_brand': str,
            'qwen_model': str,
            'yolo_correct': bool | None,
            'yolo_judgment': str,
            'raw_response': str,
        }
    """
    # ----------------------------------------------------------
    # 1. 构建 System Prompt（注入模拟 YOLO 上下文）
    # ----------------------------------------------------------
    yolo_context = build_yolo_context(yolo_class, yolo_confidence)
    system_prompt = EXTRACT_SYSTEM_PROMPT.replace("{yolo_context}", yolo_context)

    print("=" * 60)
    print(f"YOLO 模拟检测: class={yolo_class}, confidence={yolo_confidence:.2f}")
    print("-" * 60)

    # ----------------------------------------------------------
    # 2. 读取并编码图片
    # ----------------------------------------------------------
    if not os.path.isabs(image_path):
        base_dir = os.path.join(os.path.dirname(__file__), "..")
        image_path = os.path.join(base_dir, image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片不存在: {image_path}")

    img = Image.open(image_path)
    # 尺寸控制：最大 1024px
    w, h = img.size
    max_dim = max(w, h)
    if max_dim > 1024:
        ratio = 1024 / max_dim
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=75)
    image_b64 = base64.b64encode(buf.getvalue()).decode()
    image_data_uri = f"data:image/jpeg;base64,{image_b64}"

    print(f"图片: {image_path} ({img.size[0]}x{img.size[1]}, {len(buf.getvalue())} bytes)")

    # ----------------------------------------------------------
    # 3. 调用 Qwen-VL
    # ----------------------------------------------------------
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未设置")

    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    print(f"调用 Qwen-VL ({model}) ...")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                    {"type": "text", "text": "请根据YOLO的检测结果和图片内容，进行精确识别"},
                ],
            },
        ],
    )
    raw_response = resp.choices[0].message.content or ""

    # ----------------------------------------------------------
    # 4. 解析结果
    # ----------------------------------------------------------
    result = parse_to_extract_result(raw_response)

    # ----------------------------------------------------------
    # 5. 输出
    # ----------------------------------------------------------
    print("-" * 60)
    print(f"Qwen-VL 识别结果:")
    print(f"  category:      {result.category}")
    print(f"  brand:         {result.brand}")
    print(f"  model:         {result.model}")
    print(f"  condition:     {result.condition}")
    print(f"  condition_grade: {result.condition_grade}")
    print()
    print(f"冲突判断:")
    print(f"  yolo_correct:  {result.yolo_correct}")
    print(f"  yolo_judgment: {result.yolo_judgment}")
    print()
    print(f"Qwen 原始响应:")
    print(f"  {raw_response[:500]}")
    print("=" * 60)

    return {
        'yolo_class': yolo_class,
        'yolo_confidence': yolo_confidence,
        'qwen_category': result.category,
        'qwen_brand': result.brand,
        'qwen_model': result.model,
        'yolo_correct': result.yolo_correct,
        'yolo_judgment': result.yolo_judgment,
        'raw_response': raw_response,
    }


# ============================================================
# 主函数 —— 修改这里的参数来测试不同场景
# ============================================================
def main():
    # -------------------- 修改这里 ↓ --------------------
    IMAGE_PATH = "static/uploads/aa360947.jpg"  # 测试图片路径
    YOLO_CLASS = "mouse"                         # YOLO 模拟分类
    YOLO_CONF = 0.85                             # YOLO 模拟置信度
    # -------------------- 修改这里 ↑ --------------------

    """
    测试场景建议：
    ┌─────────────────────────────────────────────────────┐
    │ 场景1: 正确识别  → YOLO_CLASS = 图片实际类别         │
    │   预期: yolo_correct=true, yolo_judgment="语义一致"  │
    │                                                      │
    │ 场景2: 错误识别  → YOLO_CLASS = 故意给一个错的       │
    │   预期: yolo_correct=false, yolo_judgment="识别错误"  │
    │                                                      │
    │ 场景3: 语义等价  → YOLO_CLASS="laptop" 图片是笔记本  │
    │   预期: yolo_correct=true, yolo_judgment="语义一致"  │
    └─────────────────────────────────────────────────────┘
    """
    test_conflict_detection(
        image_path=IMAGE_PATH,
        yolo_class=YOLO_CLASS,
        yolo_confidence=YOLO_CONF,
    )


if __name__ == "__main__":
    main()
