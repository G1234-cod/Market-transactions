"""
速率限制中间件 — 基于滑动窗口的简易实现

保护付费 LLM API 调用（DeepSeek、Qwen-VL）、计算密集型端点（图像处理）
免受滥用。使用内存存储，单进程适用。

生产环境建议：使用 Redis 后端 + slowapi 库
"""
import time
import asyncio
from collections import defaultdict
from typing import Tuple

from fastapi import HTTPException, Request, status

import logging
logger = logging.getLogger(__name__)


# ============================================================
# 滑动窗口速率限制器
# ============================================================

class SlidingWindowLimiter:
    """
    基于滑动窗口的速率限制器

    每个窗口内允许 max_requests 次请求，
    使用滑动窗口（非固定窗口）避免边界突发问题。
    """

    def __init__(self):
        # key -> list of timestamps
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def _cleanup(self, key: str, window: float) -> None:
        """清理过期的请求记录"""
        now = time.monotonic()
        self._windows[key] = [t for t in self._windows[key] if now - t < window]

    async def is_allowed(self, key: str, max_requests: int, window: float) -> Tuple[bool, float]:
        """
        检查是否允许请求

        Args:
            key: 限制键（如 IP 地址）
            max_requests: 窗口内最大请求数
            window: 窗口长度（秒）

        Returns:
            (is_allowed, retry_after_seconds)
        """
        async with self._lock:
            await self._cleanup(key, window)

            if len(self._windows[key]) < max_requests:
                self._windows[key].append(time.monotonic())
                return True, 0

            # 计算需要等待的时间
            oldest = self._windows[key][0]
            retry_after = window - (time.monotonic() - oldest)
            return False, max(0.1, retry_after)


# 全局单例
_limiter = SlidingWindowLimiter()


def get_limiter() -> SlidingWindowLimiter:
    return _limiter


# ============================================================
# 端点速率限制配置
# ============================================================

# 格式: (max_requests, window_seconds)
RATE_LIMITS = {
    # 付费 LLM 端点 — 严格限制
    "/api/v1/extract":        (10, 60),    # Qwen-VL: 10次/分钟
    "/api/v1/generate":       (20, 60),    # DeepSeek 文本: 20次/分钟
    "/api/v1/price/evaluate": (20, 60),    # DeepSeek 定价: 20次/分钟

    # 计算密集型 — 中等限制
    "/api/v1/process/image":  (30, 60),    # 全链路处理: 30次/分钟
    "/api/v1/yolo/detect":    (60, 60),    # YOLO 检测: 60次/分钟

    # 搜索 — 宽松限制
    "/api/v1/search/image":   (60, 60),    # 以图搜图: 60次/分钟
    "/api/v1/search/text":    (120, 60),   # 以文搜图: 120次/分钟

    # 认证 — 严格限制（防爆破）
    "/api/v1/login":          (10, 60),    # 登录: 10次/分钟
    "/api/v1/register":       (5, 60),     # 注册: 5次/分钟
}


async def rate_limit_dependency(request: Request) -> None:
    """
    FastAPI 依赖项 — 对请求进行速率限制

    使用方式：
        @router.post("/endpoint")
        async def endpoint(rate: None = Depends(rate_limit_dependency)):
            ...

    根据请求路径自动匹配限制规则。
    """
    path = request.url.path.rstrip("/")

    # 查找匹配的限制规则
    limit_config = RATE_LIMITS.get(path)
    if limit_config is None:
        return  # 无限制规则，放行

    max_requests, window = limit_config

    # ✅ 修复：使用 request.client.host（由 ASGI 服务器提供，不可伪造）
    # 如需反向代理支持，请在 settings 中配置 TRUSTED_PROXY_IPS
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{path}:{client_ip}"

    limiter = get_limiter()
    allowed, retry_after = await limiter.is_allowed(rate_key, max_requests, window)

    if not allowed:
        logger.warning(f"⚠️ 速率限制触发: {path} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "请求过于频繁，请稍后再试",
                "retry_after_seconds": round(retry_after, 1),
                "limit": f"{max_requests}次/{window}秒",
            },
            headers={"Retry-After": str(int(retry_after + 1))},
        )


# ============================================================
# ✅ 定期清理：防止内存泄漏
# ============================================================
async def periodic_cleanup(interval: int = 300):
    """定期清理所有过期的限流记录（每5分钟）"""
    import asyncio as _asyncio
    while True:
        await _asyncio.sleep(interval)
        limiter = get_limiter()
        async with limiter._lock:
            now = time.monotonic()
            # 清理超过 10 分钟未活跃的 key
            stale_keys = [
                k for k, timestamps in limiter._windows.items()
                if not timestamps or now - timestamps[-1] > 600
            ]
            for k in stale_keys:
                del limiter._windows[k]
            if stale_keys:
                logger.debug(f"🧹 限流内存清理: 移除 {len(stale_keys)} 个过期 key")


# ============================================================
# 便捷函数：创建端点专属限流器
# ============================================================

def create_rate_limit(max_requests: int, window: float = 60.0):
    """
    创建自定义速率限制的依赖项

    使用方式：
        @router.post("/custom")
        async def custom(rate: None = Depends(create_rate_limit(5, 60))):
            ...

    Args:
        max_requests: 窗口内最大请求数
        window: 窗口长度（秒）
    """
    async def _limiter(request: Request) -> None:
        path = request.url.path.rstrip("/")
        # ✅ 修复：使用 request.client.host
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"custom:{path}:{client_ip}"

        limiter = get_limiter()
        allowed, retry_after = await limiter.is_allowed(rate_key, max_requests, window)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "请求过于频繁，请稍后再试",
                    "retry_after_seconds": round(retry_after, 1),
                },
                headers={"Retry-After": str(int(retry_after + 1))},
            )
    return _limiter
