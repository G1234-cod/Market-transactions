"""
错误数据收集器
当本地模型与 Qwen 结果不一致时，保存错误图片、标签文件，并写入数据库
"""
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from PIL import Image
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DataCollector:
    """错误数据收集器（带可靠异步保存机制）"""
    
    def __init__(self, base_dir: str = "data/error_data"):
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "images"
        self.labels_dir = self.base_dir / "labels"
        self.metadata_dir = self.base_dir / "metadata"
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 后台任务队列
        self._pending_tasks: List[asyncio.Task] = []
        
        logger.info(f"✅ 错误数据收集器初始化完成，保存目录: {self.base_dir}")
    
    # ============================================================
    # 主收集方法
    # ============================================================
    
    def collect(
        self,
        image: Image.Image,
        wrong_label: str,
        correct_label: str,
        user_id: int,
        item_id: int = None,
        confidence: float = 0.0,
        save_to_db: bool = True
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
            save_to_db: 是否保存到数据库
            
        Returns:
            dict: 保存结果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"item_{item_id or 'unknown'}_{timestamp}"
        
        # 1. 保存图片（✅ 修复：RGBA 转 RGB，确保 JPEG 兼容）
        img_path = self.images_dir / f"{filename}.jpg"
        
        # ✅ 如果是 RGBA 模式，转换为 RGB
        if image.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', image.size, (255, 255, 255))
            # 将 RGBA 图片粘贴到白色背景上
            background.paste(image, mask=image.split()[3])  # 使用 alpha 通道作为掩码
            save_image = background
        else:
            save_image = image.convert('RGB')  # 确保其他模式也转为 RGB
        
        save_image.save(img_path, 'JPEG', quality=95)
        
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
        
        result = {
            'success': True,
            'filename': filename,
            'image_path': str(img_path),
            'label_path': str(label_path),
            'wrong_label': wrong_label,
            'correct_label': correct_label
        }
        
        # 3. 保存到数据库（使用可靠方式）
        if save_to_db:
            self._save_to_db_safe(
                image_url=str(img_path),
                wrong_label=wrong_label,
                correct_label=correct_label,
                user_id=user_id,
                item_id=item_id,
                model_version=None,
                confidence=confidence
            )
        
        return result
    
    # ============================================================
    # 可靠的数据库保存（带重试和备份）
    # ============================================================
    
    def _save_to_db_safe(
        self,
        image_url: str,
        wrong_label: str,
        correct_label: str,
        user_id: int,
        item_id: int = None,
        model_version: str = None,
        confidence: float = 0.0,
        retries: int = 3
    ):
        """
        安全保存到数据库（带重试和备份）
        
        Args:
            retries: 重试次数
        """
        try:
            from app.db import crud
            
            async def _save_with_retry():
                """带重试的保存函数"""
                last_error = None
                for attempt in range(retries + 1):
                    try:
                        await crud.insert_hard_case(
                            image_url=image_url,
                            wrong_label=wrong_label,
                            correct_label=correct_label,
                            user_id=user_id,
                            item_id=item_id,
                            model_version=model_version,
                            confidence=confidence
                        )
                        logger.debug(f"✅ 错误数据已保存到数据库: {image_url}")
                        return True
                    except Exception as e:
                        last_error = e
                        if attempt < retries:
                            wait_time = 1.0 * (2 ** attempt)  # 指数退避
                            logger.warning(
                                f"⚠️ 数据库保存失败 (尝试 {attempt+1}/{retries+1}): {e}, "
                                f"{wait_time:.1f}s 后重试"
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"❌ 数据库保存失败，重试 {retries} 次后仍失败: {e}")
                
                # 所有重试都失败，保存到本地备份
                self._save_to_local_backup(
                    image_url=image_url,
                    wrong_label=wrong_label,
                    correct_label=correct_label,
                    user_id=user_id,
                    item_id=item_id,
                    error=str(last_error)
                )
                return False
            
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
                # 在 async 上下文中，创建后台任务
                task = loop.create_task(_save_with_retry())
                self._pending_tasks.append(task)
                # 添加完成回调，清理任务列表
                task.add_done_callback(
                    lambda t: self._pending_tasks.remove(t) if t in self._pending_tasks else None
                )
                logger.debug(f"📤 后台任务已创建: {image_url}")
                
            except RuntimeError:
                # 没有运行中的事件循环，使用 asyncio.run()
                logger.warning("⚠️ 没有运行中的事件循环，使用 asyncio.run() 同步执行")
                asyncio.run(_save_with_retry())
                
        except Exception as e:
            logger.error(f"❌ 保存到数据库失败: {e}")
            # 保存到本地备份
            self._save_to_local_backup(
                image_url=image_url,
                wrong_label=wrong_label,
                correct_label=correct_label,
                user_id=user_id,
                item_id=item_id,
                error=str(e)
            )
    
    def _save_to_local_backup(
        self,
        image_url: str,
        wrong_label: str,
        correct_label: str,
        user_id: int,
        item_id: int = None,
        error: str = ""
    ):
        """保存到本地备份文件（数据库失败时使用）"""
        backup_file = self.metadata_dir / f"failed_db_insert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'image_url': image_url,
            'wrong_label': wrong_label,
            'correct_label': correct_label,
            'user_id': user_id,
            'item_id': item_id,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 错误数据已保存到本地备份: {backup_file}")
    
    # ============================================================
    # 批量保存
    # ============================================================
    
    def collect_batch(
        self,
        error_list: List[Dict[str, Any]]
    ) -> List[dict]:
        """
        批量收集错误数据
        
        Args:
            error_list: 错误数据列表，每个包含:
                - image: PIL Image
                - wrong_label: str
                - correct_label: str
                - user_id: int
                - item_id: int (可选)
                - confidence: float (可选)
        
        Returns:
            List[dict]: 保存结果列表
        """
        results = []
        for error in error_list:
            try:
                result = self.collect(
                    image=error['image'],
                    wrong_label=error['wrong_label'],
                    correct_label=error['correct_label'],
                    user_id=error['user_id'],
                    item_id=error.get('item_id'),
                    confidence=error.get('confidence', 0.0)
                )
                results.append(result)
            except Exception as e:
                logger.error(f"❌ 批量收集错误数据失败: {e}")
                results.append({'success': False, 'error': str(e)})
        
        return results
    
    # ============================================================
    # 任务管理
    # ============================================================
    
    async def flush_pending_tasks(self, timeout: float = 5.0):
        """
        等待所有后台任务完成
        
        Args:
            timeout: 超时时间（秒）
        """
        if not self._pending_tasks:
            logger.debug("✅ 没有待处理的后台任务")
            return
        
        logger.info(f"⏳ 等待 {len(self._pending_tasks)} 个后台任务完成...")
        
        try:
            done, pending = await asyncio.wait(
                self._pending_tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            if pending:
                logger.warning(f"⚠️ {len(pending)} 个任务超时未完成，已取消")
                for task in pending:
                    task.cancel()
            else:
                logger.info("✅ 所有后台任务已完成")
                
        except Exception as e:
            logger.error(f"❌ 等待任务完成时出错: {e}")
        
        self._pending_tasks.clear()
    
    def get_pending_count(self) -> int:
        """获取待处理任务数量"""
        return len(self._pending_tasks)
    
    # ============================================================
    # 统计和汇总
    # ============================================================
    
    def get_weekly_summary(self) -> dict:
        """获取每周错误数据汇总"""
        import re
        from collections import Counter
        
        error_pairs = []
        for label_file in self.labels_dir.glob("*.txt"):
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    wrong_match = re.search(r'错误分类.*?：(.*)', content)
                    correct_match = re.search(r'正确分类.*?：(.*)', content)
                    if wrong_match and correct_match:
                        error_pairs.append({
                            'wrong': wrong_match.group(1).strip(),
                            'correct': correct_match.group(1).strip()
                        })
            except Exception as e:
                logger.warning(f"⚠️ 读取标签文件失败: {label_file}, {e}")
        
        if not error_pairs:
            return {
                'total_errors': 0,
                'most_common_wrong': [],
                'most_common_correct': [],
                'error_pairs': []
            }
        
        wrong_counter = Counter([p['wrong'] for p in error_pairs])
        correct_counter = Counter([p['correct'] for p in error_pairs])
        
        return {
            'total_errors': len(error_pairs),
            'most_common_wrong': wrong_counter.most_common(10),
            'most_common_correct': correct_counter.most_common(10),
            'error_pairs': error_pairs[:100]  # 只返回前100条
        }
    
    def save_weekly_metadata(self) -> dict:
        """保存每周汇总数据"""
        summary = self.get_weekly_summary()
        week_num = datetime.now().strftime("%Y-W%W")
        metadata_path = self.metadata_dir / f"error_summary_{week_num}.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 每周汇总已保存: {metadata_path}")
        return summary
    
    def get_all_error_files(self) -> List[Dict[str, str]]:
        """
        获取所有错误数据文件列表
        
        Returns:
            List[Dict]: 包含 image_path, label_path 的列表
        """
        files = []
        for label_file in sorted(self.labels_dir.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True):
            image_file = self.images_dir / label_file.stem
            # 尝试找到对应的图片（可能是jpg或png）
            for ext in ['.jpg', '.jpeg', '.png']:
                if (image_file.with_suffix(ext)).exists():
                    files.append({
                        'image_path': str(image_file.with_suffix(ext)),
                        'label_path': str(label_file),
                        'filename': label_file.stem
                    })
                    break
        return files


# ============================================================
# 全局单例
# ============================================================

_data_collector: Optional[DataCollector] = None


def get_data_collector() -> DataCollector:
    """获取数据收集器单例"""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector


def reset_data_collector():
    """重置数据收集器（用于测试）"""
    global _data_collector
    _data_collector = None


# ============================================================
# 便捷函数
# ============================================================

def collect_error_data(
    image: Image.Image,
    wrong_label: str,
    correct_label: str,
    user_id: int,
    item_id: int = None,
    confidence: float = 0.0
) -> dict:
    """
    快捷收集错误数据
    
    使用示例:
        collect_error_data(
            image=pil_image,
            wrong_label="iPhone 12",
            correct_label="iPhone 13",
            user_id=1,
            item_id=123,
            confidence=0.75
        )
    """
    collector = get_data_collector()
    return collector.collect(
        image=image,
        wrong_label=wrong_label,
        correct_label=correct_label,
        user_id=user_id,
        item_id=item_id,
        confidence=confidence
    )


async def flush_data_collector(timeout: float = 5.0):
    """
    刷新数据收集器（等待所有后台任务完成）
    
    建议在应用关闭时调用:
        @app.on_event("shutdown")
        async def shutdown():
            await flush_data_collector()
    """
    collector = get_data_collector()
    await collector.flush_pending_tasks(timeout)


def get_error_stats() -> dict:
    """获取错误数据统计"""
    collector = get_data_collector()
    return {
        'pending_tasks': collector.get_pending_count(),
        'total_files': len(list(collector.labels_dir.glob("*.txt"))),
        'summary': collector.get_weekly_summary()
    }