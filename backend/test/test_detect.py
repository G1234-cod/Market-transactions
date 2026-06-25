"""
YOLO 检测测试
"""
import pytest


class TestDetect:
    """YOLO 检测测试"""

    def test_yolo_detect_success(self, client, sample_image):
        """测试 YOLO 检测成功"""
        files = {"image": ("test.jpg", sample_image, "image/jpeg")}
        response = client.post("/api/v1/yolo/detect", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "detections" in data
        assert "annotated_image" in data

    def test_yolo_detect_no_image(self, client):
        """测试不上传图片"""
        response = client.post("/api/v1/yolo/detect")
        assert response.status_code == 422

    def test_yolo_health(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/yolo/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"