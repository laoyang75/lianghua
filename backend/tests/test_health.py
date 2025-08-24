"""
健康检查API测试
"""

import pytest


@pytest.mark.api
def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应结构
    assert "status" in data
    assert "timestamp" in data
    assert "service" in data
    
    # 验证状态值
    assert data["status"] == "healthy"
    assert data["service"] == "量化回测系统后端"


@pytest.mark.api
def test_health_detailed(client):
    """测试详细健康检查"""
    response = client.get("/api/v1/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应结构
    assert "status" in data
    assert "checks" in data
    assert "timestamp" in data
    
    # 验证检查项
    checks = data["checks"]
    assert "database" in checks
    assert "memory" in checks
    
    # 数据库检查
    db_check = checks["database"]
    assert "status" in db_check
    assert "message" in db_check


@pytest.mark.unit
class TestHealthService:
    """健康检查服务单元测试"""
    
    def test_basic_health_status(self):
        """测试基本健康状态"""
        # 这里可以测试健康检查的业务逻辑
        assert True  # 占位测试
    
    def test_database_health_check(self):
        """测试数据库健康检查"""
        # 这里可以测试数据库连接检查逻辑
        assert True  # 占位测试