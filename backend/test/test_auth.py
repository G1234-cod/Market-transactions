"""
用户登录/注册测试
"""
import pytest


class TestAuth:
    """用户认证测试"""

    def test_register_success(self, client):
        """测试注册成功"""
        response = client.post("/api/v1/register", json={
            "username": "newuser",
            "password": "test123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert "id" in data

    def test_register_duplicate(self, client):
        """测试用户名已存在"""
        client.post("/api/v1/register", json={
            "username": "duplicate",
            "password": "test123"
        })
        response = client.post("/api/v1/register", json={
            "username": "duplicate",
            "password": "test123"
        })
        assert response.status_code in [400, 409]

    def test_register_password_too_short(self, client):
        """测试密码太短"""
        response = client.post("/api/v1/register", json={
            "username": "short",
            "password": "123"
        })
        assert response.status_code == 400

    def test_login_success(self, client):
        """测试登录成功"""
        client.post("/api/v1/register", json={
            "username": "loginuser",
            "password": "test123"
        })
        response = client.post("/api/v1/login", json={
            "username": "loginuser",
            "password": "test123"
        })
        assert response.status_code == 200
        assert response.json()["username"] == "loginuser"

    def test_login_wrong_password(self, client):
        """测试密码错误"""
        client.post("/api/v1/register", json={
            "username": "wrongpass",
            "password": "test123"
        })
        response = client.post("/api/v1/login", json={
            "username": "wrongpass",
            "password": "wrong"
        })
        assert response.status_code in [400, 401]

    def test_login_user_not_exist(self, client):
        """测试用户不存在"""
        response = client.post("/api/v1/login", json={
            "username": "nonexist",
            "password": "test123"
        })
        assert response.status_code in [400, 401]