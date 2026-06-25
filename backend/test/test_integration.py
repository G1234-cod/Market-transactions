"""
端到端集成测试
"""
import pytest


class TestIntegration:
    """完整流程测试"""

    def test_full_publish_flow(self, client, sample_image):
        """测试完整发布流程"""
        # 1. 注册
        client.post("/api/v1/register", json={
            "username": "flowuser",
            "password": "test123"
        })

        # 2. 登录
        login_resp = client.post("/api/v1/login", json={
            "username": "flowuser",
            "password": "test123"
        })
        assert login_resp.status_code == 200
        user_id = login_resp.json()["id"]

        # 3. 上传图片识别
        files = {"image": ("test.jpg", sample_image, "image/jpeg")}
        extract_resp = client.post("/api/v1/extract", files=files, data={"user_id": user_id})
        assert extract_resp.status_code == 200

        # 4. YOLO 检测
        detect_resp = client.post("/api/v1/yolo/detect", files=files)
        assert detect_resp.status_code == 200
        assert detect_resp.json()["success"] is True

        print("✅ 完整流程测试通过")