"""
历史价格数据服务

根据品牌型号生成过去6个月的价格走势数据（每3天一个点，约60个点），
用于前端绘制价格曲线图。优先使用 DeepSeek 生成，失败则公式兜底。
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

DAYS_PER_POINT = 3
TOTAL_POINTS = 180 // DAYS_PER_POINT  # ~60 points for 6 months


class HistoryEstimator:
    """历史价格数据生成"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

        if not self.api_key:
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=45,
            )

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _build_prompt(
        self,
        brand: str,
        model_name: str,
        current_avg_price: float,
        current_low_price: float,
        current_high_price: float,
    ) -> str:
        today = self._today_str()
        return f"""你是二手数码市场价格数据专家。请生成该商品过去6个月的每周价格数据。

**基准日期：{today}，所有日期基于今天向前推算。**

## 商品
- 品牌：{brand}
- 型号：{model_name}
- 当前市场均价：¥{current_avg_price}
- 当前最低价：¥{current_low_price}
- 当前最高价：¥{current_high_price}

## 数据生成规则
1. 二手数码每月自然贬值 3%-8%，整体呈下降趋势
2. **价格必须有真实感波动**：不能是平滑直线，要有上下起伏（每周 ±1%~±3%），形成锯齿状波浪
3. 偶尔出现连续 2-3 周小幅上涨（市场短期回暖），但大趋势向下
4. 热门型号（iPhone、Mate 系列）价格更稳定，波动更小

## 输出要求
strict JSON：
{{
    "points": [
        {{"day_offset": -180, "price": 整数, "low": 整数, "high": 整数}},
        {{"day_offset": -177, "price": 整数, "low": 整数, "high": 整数}},
        ...
        {{"day_offset": -3, "price": 整数, "low": 整数, "high": 整数}}
    ],
    "trend": "趋势简述",
    "depreciation_rate": 0.05
}}

- 共 {TOTAL_POINTS} 个数据点（每 {DAYS_PER_POINT} 天一个）
- day_offset=-3 时价格接近 ¥{current_avg_price}，day_offset=-180 时价格高出 {6*5}%-{6*7}%
- 相邻两点价格必须有涨有跌，不要单调下降
"""

    async def estimate_history(
        self,
        brand: str,
        model_name: str,
        current_avg_price: float,
        current_low_price: float = 0,
        current_high_price: float = 0,
    ) -> dict:
        if current_low_price <= 0:
            current_low_price = round(current_avg_price * 0.85)
        if current_high_price <= 0:
            current_high_price = round(current_avg_price * 1.15)

        if self.client is not None:
            try:
                return await self._call_deepseek(
                    brand, model_name,
                    current_avg_price, current_low_price, current_high_price,
                )
            except Exception as e:
                logger.warning(f"DeepSeek failed, using formula: {e}")

        return self._formula_estimate(
            brand, model_name,
            current_avg_price, current_low_price, current_high_price,
        )

    async def _call_deepseek(
        self, brand: str, model_name: str,
        avg_price: float, low_price: float, high_price: float,
    ) -> dict:
        prompt = self._build_prompt(brand, model_name, avg_price, low_price, high_price)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是二手数码产品价格数据专家。请严格输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=4000,
        )

        content = response.choices[0].message.content if response.choices else ""
        start = content.find("{")
        if start < 0:
            return self._formula_estimate(brand, model_name, avg_price, low_price, high_price)

        depth = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        result = json.loads(content[start:end])
        ai_points = result.get("points", [])

        today = datetime.now()
        points = []
        for p in ai_points:
            offset = int(p.get("day_offset", 0))
            real_date = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
            points.append({
                "date": real_date,
                "price": float(p.get("price", 0)),
                "low": float(p.get("low", 0)),
                "high": float(p.get("high", 0)),
                "day_offset": offset,
            })

        points.sort(key=lambda x: x["date"])

        return {
            "success": True,
            "price_points": points,
            "avg_price": avg_price,
            "min_price": low_price,
            "max_price": high_price,
            "trend": result.get("trend", ""),
            "depreciation_rate": result.get("depreciation_rate", 0.05),
            "source": "deepseek",
        }

    def _formula_estimate(
        self, brand: str, model_name: str,
        avg_price: float, low_price: float, high_price: float,
    ) -> dict:
        """公式生成：含随机波动的真实感价格数据"""
        import math
        import random

        is_apple = "apple" in brand.lower()
        monthly_rate = 0.035 if is_apple else 0.055
        daily_rate = monthly_rate / 30

        today = datetime.now()
        seed = hash(f"{brand}{model_name}") % 10000
        rng = random.Random(seed)

        points = []
        for offset in range(-180, 0, DAYS_PER_POINT):
            real_date = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
            abs_days = abs(offset)
            # 基础贬值趋势
            trend_factor = (1 + daily_rate) ** abs_days
            # 中周期波动（~30天一个周期）
            medium_wave = 1 + 0.025 * math.sin(abs_days * 0.21 + seed * 0.01)
            # 短周期波动（~7天一个周期，模拟周级起伏）
            short_wave = 1 + 0.015 * math.sin(abs_days * 0.9 + seed * 0.03)
            # 随机噪声
            noise = 1 + rng.uniform(-0.012, 0.012)
            factor = trend_factor * medium_wave * short_wave * noise

            points.append({
                "date": real_date,
                "price": round(avg_price * factor),
                "low": round(low_price * factor),
                "high": round(high_price * factor),
                "day_offset": offset,
            })

        return {
            "success": True,
            "price_points": points,
            "avg_price": avg_price,
            "min_price": low_price,
            "max_price": high_price,
            "trend": "",
            "depreciation_rate": monthly_rate,
            "source": "formula",
        }


_estimator: Optional[HistoryEstimator] = None


def get_history_estimator() -> HistoryEstimator:
    global _estimator
    if _estimator is None:
        _estimator = HistoryEstimator()
    return _estimator
