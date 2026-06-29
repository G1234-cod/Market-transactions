"""
历史价格推算服务
基于 DeepSeek AI 模型 + OneBound 当前市场价格，推算过去 6-12 个月的价格走势
"""
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List
from openai import AsyncOpenAI

from app.config import settings
from app.db import crud

logger = logging.getLogger(__name__)

MONTHS_TO_ESTIMATE = 6  # 推算过去几个月


class HistoryEstimator:
    """AI 价格历史推算器"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

        if not self.api_key:
            logger.warning("⚠️ DeepSeek API Key 未配置，历史价格推算不可用")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30,
            )

    def _build_prompt(
        self,
        brand: str,
        model: str,
        category: str,
        current_price: Dict[str, float],
    ) -> str:
        """构建历史价格推算提示词"""
        avg = current_price.get("avg", 0)
        low = current_price.get("low", 0)
        high = current_price.get("high", 0)

        return f"""你是专业的二手数码产品市场分析师。请根据当前市场价格，推算过去 {MONTHS_TO_ESTIMATE} 个月该商品的月度市场均价走势。

## 商品信息
- 品类: {category or "数码产品"}
- 品牌: {brand}
- 型号: {model}

## 当前市场价格 (OneBound 淘宝实时数据)
- 当前均价: ¥{avg:.0f}
- 最低价: ¥{low:.0f}
- 最高价: ¥{high:.0f}

## 推算规则
1. 二手电子产品每月贬值约 3%-8%（老旧型号更快，热门型号较慢）
2. 当前为 2026年6月，请推算 2026年1月 到 2026年6月（共 {MONTHS_TO_ESTIMATE} 个月）的均价
3. 价格应呈逐月上升趋势（越往过去越贵）
4. 考虑 iPhone/安卓 不同的贬值速度（iPhone 贬值较慢）
5. 价格应为整数，单位人民币

## 输出格式（纯 JSON，不要 Markdown 代码块）
{{"estimates":[{{"month":"2026-01","price":数字}},{{"month":"2026-02","price":数字}},{{"month":"2026-03","price":数字}},{{"month":"2026-04","price":数字}},{{"month":"2026-05","price":数字}},{{"month":"2026-06","price":{avg:.0f}}}],"analysis":"一句话分析"}}"""

    async def estimate(
        self,
        brand: str,
        model: str,
        category: str,
        current_price: Dict[str, float],
    ) -> List[Dict]:
        """
        推算历史价格并存入数据库

        Returns:
            list[dict]: 推算结果
        """
        if self.client is None:
            logger.warning("DeepSeek 未配置，跳过历史推算")
            return []

        try:
            prompt = self._build_prompt(brand, model, category, current_price)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是专业的二手数码产品市场分析师。请仅输出 JSON，不要包含 Markdown 代码块或其他文字。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            logger.info(f"DeepSeek 历史推算响应: {content[:300]}")

            # 解析 JSON
            import re
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                logger.error(f"无法解析 DeepSeek 响应: {content}")
                return []

            data = json.loads(json_match.group())
            estimates = data.get("estimates", [])
            analysis = data.get("analysis", "")

            if not estimates:
                return []

            # 存入 price_history 表
            avg_price = current_price.get("avg", 0)
            low_price = current_price.get("low", 0)
            high_price = current_price.get("high", 0)

            for est in estimates:
                try:
                    est_price = float(est.get("price", 0))
                    est_month = est.get("month", "")
                    if est_price <= 0:
                        continue

                    await crud.insert_price_history(
                        brand=brand,
                        model=model,
                        avg_price=est_price,
                        low_price=max(est_price * 0.85, low_price * 0.8),
                        high_price=min(est_price * 1.15, high_price * 1.2),
                        source=f"DeepSeek推算_{analysis[:30]}",
                    )
                except Exception as e:
                    logger.warning(f"保存推算历史失败: {e}")

            logger.info(f"历史推算完成: {brand} {model}, {len(estimates)} 个月, {analysis}")
            return estimates

        except Exception as e:
            logger.error(f"DeepSeek 历史推算失败: {e}")
            return []


# 单例
_estimator = None


def get_estimator() -> HistoryEstimator:
    global _estimator
    if _estimator is None:
        _estimator = HistoryEstimator()
    return _estimator
