"""
瑕疵检测测试
"""
import pytest


class TestProcess:
    """瑕疵检测测试"""

    def test_process_image_success(self, client, sample_image):
        """测试全链路图片处理"""
        files = {"image": ("test.jpg", sample_image, "image/jpeg")}
        data = {
            "user_id": 1,
            "category": "手机",
            "brand": "Apple",
            "model": "iPhone 14",
            "market_avg_price": 5000
        }
        response = client.post("/api/v1/process/image", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "annotated_base64" in result["data"]
        assert "defects" in result["data"]
        assert "defect_count" in result["data"]

    def test_process_health(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/process/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"