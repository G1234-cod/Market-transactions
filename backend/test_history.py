# -*- coding: utf-8 -*-
"""DeepSeek 历史价格推算测试"""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()

from app.services.history_estimator import HistoryEstimator

async def main():
    estimator = HistoryEstimator()
    
    if estimator.client is None:
        print("X: DeepSeek API Key not configured")
        return
    
    print("=" * 55)
    print("DeepSeek Historical Price Estimation Test")
    print("=" * 55)
    
    tests = [
        ("Apple", "iPhone 13 128G", "Phone", 2400, 1200, 3600),
        ("Huawei", "Mate 60 Pro", "Phone", 4200, 3500, 5200),
    ]
    
    for brand, model, cat, avg, low, high in tests:
        print(f"\n>>> {brand} {model}")
        print(f"    Current avg: {avg}")
        
        price = {"avg": avg, "low": low, "high": high}
        result = await estimator.estimate(brand, model, cat, price)
        
        if result:
            print(f"    Estimated history ({len(result)} months):")
            for item in sorted(result, key=lambda x: x["month"]):
                arrow = " <<< current" if item["month"] == "2026-06" else ""
                print(f"      {item['month']}: {item['price']}{arrow}")
        else:
            print("    FAILED")
    
    print(f"\n{'=' * 55}")
    print("Done!")
    
asyncio.run(main())
