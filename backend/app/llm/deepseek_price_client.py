"""
DeepSeek 定价辅助客户端
根据瑕疵检测结果，给出参考价格调整建议
"""
import os
import json
import logging
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekPriceClient:
    """DeepSeek 定价辅助客户端"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        
        if not self.api_key:
            logger.warning("⚠️ DEEPSEEK_API_KEY 未设置，定价功能不可用")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30
            )
    
    def _build_prompt(self, product_info: dict, defects_data: dict) -> str:
        """
        构建定价提示词
        
        Args:
            product_info: 商品基本信息
                {
                    "category": "手机",
                    "brand": "Apple",
                    "model": "iPhone 14 Pro",
                    "market_avg_price": 5000,
                    "user_expected_price": 4500
                }
            defects_data: 瑕疵数据（来自 defect_detector_yolo）
                {
                    "has_defects": True,
                    "summary": "检测到 2 处中度损伤",
                    "defects": [...],
                    "severity_summary": {"severe": 0, "moderate": 2, "minor": 1, "slight": 0},
                    "total": 3
                }
        """
        prompt = f"""你是一个专业的二手商品估价专家。请根据商品信息和瑕疵检测结果，给出参考价格调整建议。

## 商品信息
- 品类：{product_info.get('category', '未知')}
- 品牌：{product_info.get('brand', '未知')}
- 型号：{product_info.get('model', '未知')}
- 市场参考价：¥{product_info.get('market_avg_price', 0)}

## 瑕疵检测结果
{defects_data.get('summary', '商品外观完好')}

详细瑕疵列表：
"""
        for d in defects_data.get('defects', []):
            prompt += f"- {d.get('type_cn', '未知')}（{d.get('severity_label', '未知')}）\n"

        prompt += f"""
## 输出要求
请输出 JSON 格式的价格建议，包含以下字段：
{{
    "estimated_price": 建议售价（整数）,
    "price_range": {{"low": 最低建议价, "high": 最高建议价}},
    "discount_ratio": 相比市场价的折扣比例（0-1之间的小数）,
    "reason": "价格调整理由（一句话）",
    "severity_impact": {{
        "severe": "重度损伤对价格的影响说明",
        "moderate": "中度损伤对价格的影响说明",
        "minor": "轻度损伤对价格的影响说明"
    }},
    "suggestion": "给卖家的具体定价建议"
}}

注意：
1. 重度损伤（如穿透、结构损坏、部件缺失）建议降价 20%-40%
2. 中度损伤（如变形、功能故障）建议降价 10%-20%
3. 轻度损伤（如溢漏）建议降价 3%-10%
4. 轻微表面瑕疵基本不影响价格
5. 结合市场参考价给出合理区间
"""
        return prompt
    
    async def get_price_suggestion(
        self,
        product_info: dict,
        defects_data: dict
    ) -> dict:
        """
        获取定价建议
        
        Args:
            product_info: 商品基本信息
            defects_data: 瑕疵数据
            
        Returns:
            dict: 定价建议
        """
        if self.client is None:
            return {
                'success': False,
                'error': 'DeepSeek API 未配置',
                'suggestion': '请设置 DEEPSEEK_API_KEY'
            }
        
        try:
            # 构建提示词
            prompt = self._build_prompt(product_info, defects_data)
            
            # 调用 DeepSeek
            # ✅ response_format={"type": "json_object"} 可能不被某些 API 端点支持
            # 先尝试带 response_format 的调用，失败则回退到不带 response_format
            extra_kwargs = {
                "temperature": 0.3,  # 低温度，输出更稳定
                "max_tokens": 500,
            }
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是专业的二手商品估价专家，请根据商品信息和瑕疵情况给出合理的价格建议。"},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    **extra_kwargs,
                )
            except Exception:
                logger.warning("⚠️ response_format 不支持，回退到普通调用")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是专业的二手商品估价专家，请根据商品信息和瑕疵情况给出合理的价格建议。请仅输出 JSON，不要包含其他文字。"},
                        {"role": "user", "content": prompt}
                    ],
                    **extra_kwargs,
                )
            
            # 解析返回结果
            if not response.choices:
                return {
                    'success': False,
                    'error': 'DeepSeek 返回空结果',
                    'suggestion': '请稍后重试'
                }
            content = response.choices[0].message.content
            
            # 提取 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result['success'] = True
                return result
            else:
                return {
                    'success': False,
                    'error': '无法解析 DeepSeek 返回结果',
                    'raw_response': content
                }
                
        except Exception as e:
            logger.error(f"DeepSeek 定价调用失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }