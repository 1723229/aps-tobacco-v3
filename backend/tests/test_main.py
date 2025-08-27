"""
APS智慧排产系统 - FastAPI应用测试

测试FastAPI应用的基础功能，包括健康检查、配置接口等
确保应用能够正常启动和响应请求
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    """测试客户端fixture"""
    return TestClient(app)


class TestApplicationRoutes:
    """应用路由测试类"""
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
    
    def test_config_endpoint(self, client):
        """测试配置信息接口"""
        response = client.get("/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "app_name" in data
        assert "app_version" in data
        assert "database" in data
        assert "redis" in data
        assert "upload" in data
        assert "business" in data
        
        # 验证敏感信息已脱敏
        assert "mysql_url" not in str(data)
        assert "redis_url" not in str(data)
        assert "secret_key" not in str(data)


class TestHealthCheck:
    """健康检查测试类"""
    
    @patch('app.main.DatabaseHealthCheck.ping')
    @patch('app.main.RedisHealthCheck.ping')
    def test_health_check_healthy(self, mock_redis_ping, mock_db_ping, client):
        """测试健康状态"""
        # Mock健康的数据库和Redis
        mock_db_ping.return_value = {"status": "healthy"}
        mock_redis_ping.return_value = {"status": "healthy"}
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
    
    @patch('app.main.DatabaseHealthCheck.ping')
    @patch('app.main.RedisHealthCheck.ping')
    def test_health_check_degraded(self, mock_redis_ping, mock_db_ping, client):
        """测试降级状态"""
        # Mock不健康的数据库
        mock_db_ping.return_value = {"status": "error"}
        mock_redis_ping.return_value = {"status": "healthy"}
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "degraded"


class TestApplicationConfiguration:
    """应用配置测试类"""
    
    def test_cors_configuration(self, client):
        """测试CORS配置"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Requested-With",
        })
        
        # CORS预检请求应该返回200
        assert response.status_code == 200
    
    def test_docs_endpoint(self, client):
        """测试API文档端点"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self, client):
        """测试ReDoc文档端点"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """错误处理测试类"""
    
    def test_404_endpoint(self, client):
        """测试404错误"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """测试方法不允许错误"""
        response = client.post("/")
        assert response.status_code == 405


# 集成测试
class TestIntegration:
    """集成测试类"""
    
    def test_application_startup(self, client):
        """测试应用启动流程"""
        # 测试多个端点以确保应用正常工作
        endpoints = ["/", "/health", "/config"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
    
    def test_response_format(self, client):
        """测试响应格式一致性"""
        response = client.get("/")
        data = response.json()
        
        # 验证响应是有效的JSON
        assert isinstance(data, dict)
        assert len(data) > 0