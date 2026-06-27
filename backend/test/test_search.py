"""
以图搜图测试
"""
import pytest


class TestSearch:
    """以图搜图测试"""

    def test_search_by_image(self, client, sample_image, auth_headers):
        """测试以图搜图"""
        files = {"image": ("test.jpg", sample_image, "image/jpeg")}
        data = {"top_k": 5}
        response = client.post("/api/v1/search/image", files=files, data=data, headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "results" in result

    def test_search_stats(self, client):
        """测试索引统计"""
        response = client.get("/api/v1/search/stats")
        assert response.status_code == 200
        assert "total_items" in response.json()

    def test_search_by_text(self, client, auth_headers):
        """测试以文搜图"""
        data = {"text": "手机", "top_k": 5}
        response = client.post("/api/v1/search/text", data=data, headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True