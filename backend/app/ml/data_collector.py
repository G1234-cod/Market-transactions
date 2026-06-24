"""
错误数据收集器
当本地模型与 Qwen 结果不一致时，保存错误图片和标签
"""
import os
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class DataCollector:
    """错误数据收集器"""
    
    def __init__(self, base_dir: str = "data/error_data"):
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "images"
        self.labels_dir = self.base_dir / "labels"
        self.metadata_dir = self.base_dir / "metadata"
        
        # 创建目录
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def collect(
        self,
        image: Image.Image,
        wrong_label: str,
        correct_label: str,
        user_id: int,
        item_id: int = None,
        confidence: float = 0.0
    ) -> dict:
        """
        收集错误数据
        
        Args:
            image: PIL Image
            wrong_label: 本地模型输出的错误分类
            correct_label: Qwen 输出的正确分类
            user_id: 用户 ID
            item_id: 商品 ID（可选）
            confidence: 本地模型置信度（可选）
            
        Returns:
            dict: 保存结果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"item_{item_id or 'unknown'}_{timestamp}"
        
        # 1. 保存图片
        img_path = self.images_dir / f"{filename}.jpg"
        image.save(img_path, quality=95)
        
        # 2. 保存标签文件
        label_path = self.labels_dir / f"{filename}.txt"
        label_content = f"""图片名称：{filename}.jpg
错误分类（本地模型输出）：{wrong_label}
正确分类（Qwen 输出）：{correct_label}
比对时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用户ID：{user_id}
商品ID：{item_id or '未知'}
本地模型置信度：{confidence:.4f}
"""
        with open(label_path, 'w', encoding='utf-8') as f:
            f.write(label_content)
        
        logger.info(f"✅ 错误数据已收集: {filename}")
        
        return {
            'success': True,
            'filename': filename,
            'image_path': str(img_path),
            'label_path': str(label_path),
            'wrong_label': wrong_label,
            'correct_label': correct_label
        }
    
    def get_weekly_summary(self) -> dict:
        """获取本周错误数据汇总"""
        # 读取本周所有标签文件，生成汇总统计
        import re
        from collections import Counter
        
        error_pairs = []
        for label_file in self.labels_dir.glob("*.txt"):
            with open(label_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 解析错误和正确分类
                wrong_match = re.search(r'错误分类.*?：(.*)', content)
                correct_match = re.search(r'正确分类.*?：(.*)', content)
                if wrong_match and correct_match:
                    error_pairs.append({
                        'wrong': wrong_match.group(1).strip(),
                        'correct': correct_match.group(1).strip()
                    })
        
        # 统计最常见的错误
        wrong_counter = Counter([p['wrong'] for p in error_pairs])
        correct_counter = Counter([p['correct'] for p in error_pairs])
        
        return {
            'total_errors': len(error_pairs),
            'most_common_wrong': wrong_counter.most_common(10),
            'most_common_correct': correct_counter.most_common(10),
            'error_pairs': error_pairs
        }
    
    def save_weekly_metadata(self):
        """保存每周汇总 JSON"""
        summary = self.get_weekly_summary()
        week_num = datetime.now().strftime("%Y%W")
        metadata_path = self.metadata_dir / f"error_summary_{week_num}.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 每周汇总已保存: {metadata_path}")
        return summary