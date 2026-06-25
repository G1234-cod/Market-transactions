"""
Qwen 视觉识别测试
"""
import pytest


class TestExtract:
    """Qwen 识别测试"""

    def test_extract_success(self, client, sample_image):
        """测试 Qwen 识别成功"""
        files = {"image": ("test.jpg", sample_image, "image/jpeg")}
        data = {"user_id": 1}
        response = client.post("/api/v1/extract", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert "data" in result

    def test_extract_no_image(self, client):
        """测试不上传图片"""
        response = client.post("/api/v1/extract")
        assert response.status_code == 422