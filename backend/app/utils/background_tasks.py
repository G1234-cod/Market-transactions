# app/utils/background_tasks.py

"""
可靠的后台任务管理器
支持：重试、错误日志、失败回调
"""
import asyncio
import logging
from typing import Optional, Callable, Any
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    可靠的后台任务管理器
    
    特性：
    - 自动捕获异常并记录日志
    - 支持重试机制
    - 支持失败回调
    - 防止事件循环不存在的问题
    """

    @staticmethod
    def run_async(
        coro,
        task_name: Optional[str] = None,
        retries: int = 3,
        retry_delay: float = 1.0,
        on_failure: Optional[Callable] = None,
    ):
        """
        安全地运行后台异步任务
        
        Args:
            coro: 协程对象
            task_name: 任务名称（用于日志）
            retries: 重试次数
            retry_delay: 重试间隔（秒）
            on_failure: 失败回调函数
        """
        task_name = task_name or coro.__name__ if hasattr(coro, '__name__') else 'unknown'

        try:
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 没有运行中的事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 创建任务
            task = loop.create_task(
                _run_with_retry(
                    coro=coro,
                    task_name=task_name,
                    retries=retries,
                    retry_delay=retry_delay,
                    on_failure=on_failure,
                )
            )

            # 添加任务完成回调，记录日志
            task.add_done_callback(
                lambda t: BackgroundTaskManager._log_task_result(t, task_name)
            )

            return task

        except Exception as e:
            logger.error(f"❌ 创建后台任务失败 [{task_name}]: {e}")
            return None

    @staticmethod
    def _log_task_result(task, task_name: str):
        """记录任务执行结果"""
        try:
            if task.exception():
                logger.error(f"❌ 后台任务失败 [{task_name}]: {task.exception()}")
            else:
                logger.debug(f"✅ 后台任务完成 [{task_name}]")
        except asyncio.CancelledError:
            logger.warning(f"⏹️ 后台任务被取消 [{task_name}]")
        except Exception as e:
            logger.error(f"❌ 处理任务结果时出错 [{task_name}]: {e}")


async def _run_with_retry(
    coro,
    task_name: str,
    retries: int,
    retry_delay: float,
    on_failure: Optional[Callable] = None,
):
    """带重试的执行协程"""
    last_error = None

    for attempt in range(retries + 1):
        try:
            result = await coro
            if attempt > 0:
                logger.info(f"✅ 任务 [{task_name}] 在第 {attempt + 1} 次尝试后成功")
            return result

        except Exception as e:
            last_error = e
            if attempt < retries:
                wait_time = retry_delay * (2 ** attempt)  # 指数退避
                logger.warning(
                    f"⚠️ 任务 [{task_name}] 第 {attempt + 1}/{retries + 1} 次失败: {e}，"
                    f"{wait_time:.1f}s 后重试"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ 任务 [{task_name}] 重试 {retries} 次后仍失败: {e}")

    # 所有重试都失败
    if on_failure:
        try:
            await on_failure(last_error) if asyncio.iscoroutinefunction(on_failure) else on_failure(last_error)
        except Exception as e:
            logger.error(f"❌ 失败回调执行失败: {e}")

    raise last_error


# ============================================================
# 便捷函数
# ============================================================

def run_background(
    coro,
    task_name: Optional[str] = None,
    retries: int = 3,
    retry_delay: float = 1.0,
    on_failure: Optional[Callable] = None,
):
    """
    运行后台任务的便捷函数
    
    使用示例:
        run_background(
            crud.insert_hard_case(data),
            task_name="insert_hard_case",
            retries=3,
        )
    """
    return BackgroundTaskManager.run_async(
        coro=coro,
        task_name=task_name,
        retries=retries,
        retry_delay=retry_delay,
        on_failure=on_failure,
    )


def safe_create_task(coro, task_name: str = None) -> Optional[asyncio.Task]:
    """
    安全创建 asyncio 任务（兼容没有事件循环的情况）
    """
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        # 没有运行中的事件循环
        logger.warning(f"⚠️ 没有运行中的事件循环，使用 asyncio.run() 执行任务 [{task_name}]")
        try:
            return asyncio.run(coro)
        except Exception as e:
            logger.error(f"❌ 同步执行任务失败 [{task_name}]: {e}")
            return None
    except Exception as e:
        logger.error(f"❌ 创建任务失败 [{task_name}]: {e}")
        return None