"""
价格查询测试
"""
import pytest


class TestPrice:
    """价格查询测试"""

    def test_query_price_success(self, client):
        """测试价格查询成功"""
        response = client.get("/api/v1/price", params={
            "brand": "Apple",
            "model": "iPhone 13"
        })
        assert response.status_code == 200
        data = response.json()
        assert "avg_price" in data

    def test_query_price_no_match(self, client):
        """测试价格查询无匹配"""
        response = client.get("/api/v1/price", params={
            "brand": "UnknownBrand",
            "model": "UnknownModel"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("matched") is False

    def test_query_price_missing_params(self, client):
        """测试缺少参数"""
        response = client.get("/api/v1/price")
        assert response.status_code == 422