"""
AI辅助标注工具

使用方法:
1. 安装依赖: pip install pillow openai
2. 设置环境变量: export OPENAI_API_KEY=your-api-key
3. 运行: python ai_annotate.py --input dataset/crawl --output dataset/labels

注意: 需要有OpenAI API Key才能使用
"""
import os
import argparse
import json
from PIL import Image
import base64
from io import BytesIO


def encode_image(image_path):
    """将图片编码为base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def annotate_with_ai(image_path, api_key):
    """使用AI进行辅助标注"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        base64_image = encode_image(image_path)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """请识别图片中商品的损伤区域。

类别定义:
- scratch: 划痕、刮痕（细长的损伤）
- dent: 凹陷、磕碰（表面向内凹陷）
- crack: 裂纹、裂痕（表面破裂）
- stain: 污渍、染色（表面有污渍）
- other: 其他损伤

请以JSON格式输出检测到的损伤区域:
{
  "regions": [
    {
      "type": "scratch",
      "polygon": [[x1,y1], [x2,y2], [x3,y3], ...]
    }
  ]
}

注意:
1. 坐标是相对于图片的像素坐标（左上角为原点）
2. 多边形需要至少3个点
3. 如果没有检测到损伤，返回空数组
4. 只输出JSON，不要有其他内容"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        return json.loads(result)
    
    except Exception as e:
        print(f"AI标注失败: {str(e)}")
        return {"regions": []}


def convert_to_yolo_format(regions, image_width, image_height):
    """将AI标注转换为YOLO格式"""
    yolo_lines = []
    
    class_mapping = {
        "scratch": 0,
        "dent": 1,
        "crack": 2,
        "stain": 3,
        "other": 4
    }
    
    for region in regions:
        damage_type = region.get("type", "other")
        polygon = region.get("polygon", [])
        
        if len(polygon) < 3:
            continue
        
        cls_id = class_mapping.get(damage_type, 4)
        
        # 归一化坐标
        normalized_points = []
        for x, y in polygon:
            nx = x / image_width
            ny = y / image_height
            normalized_points.append(f"{nx} {ny}")
        
        if normalized_points:
            yolo_line = f"{cls_id} {' '.join(normalized_points)}"
            yolo_lines.append(yolo_line)
    
    return yolo_lines


def process_images(input_dir, output_dir, api_key):
    """批量处理图片"""
    os.makedirs(output_dir, exist_ok=True)
    
    image_extensions = (".jpg", ".jpeg", ".png", ".bmp")
    images = [f for f in os.listdir(input_dir) if f.lower().endswith(image_extensions)]
    
    for img_name in images:
        img_path = os.path.join(input_dir, img_name)
        
        try:
            # 获取图片尺寸
            with Image.open(img_path) as img:
                width, height = img.size
            
            # AI标注
            print(f"正在标注: {img_name}")
            result = annotate_with_ai(img_path, api_key)
            
            # 转换为YOLO格式
            yolo_lines = convert_to_yolo_format(result.get("regions", []), width, height)
            
            # 保存标签文件
            label_name = os.path.splitext(img_name)[0] + ".txt"
            label_path = os.path.join(output_dir, label_name)
            
            with open(label_path, "w") as f:
                f.write("\n".join(yolo_lines))
            
            print(f"标注完成: {len(yolo_lines)} 个损伤区域")
            
        except Exception as e:
            print(f"处理失败 {img_name}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="AI辅助标注工具")
    parser.add_argument("--input", type=str, required=True, help="图片目录")
    parser.add_argument("--output", type=str, required=True, help="标签输出目录")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API Key")
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("请设置 OPENAI_API_KEY 环境变量或使用 --api-key 参数")
    
    process_images(args.input, args.output, api_key)


if __name__ == "__main__":
    main()