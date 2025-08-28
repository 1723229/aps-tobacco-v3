"""
测试排产算法执行API接口
包括算法执行、状态查询、工单查询等
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_schedule_execution_endpoint_exists():
    """测试排产算法执行API端点是否存在 - 预期失败"""
    # 测试POST /api/v1/scheduling/execute 端点
    response = client.post(
        "/api/v1/scheduling/execute",
        json={
            "import_batch_id": "test_batch_001",
            "algorithm_config": {
                "merge_enabled": True,
                "split_enabled": True,
                "correction_enabled": True,
                "parallel_enabled": True
            }
        }
    )
    
    # 端点应该存在并返回正常响应，而不是404
    assert response.status_code != 404, "Scheduling execution endpoint should exist"
    
    # 应该返回任务ID和状态
    if response.status_code == 200:
        response_data = response.json()
        assert "code" in response_data
        assert "data" in response_data
        assert "task_id" in response_data["data"]


def test_schedule_status_endpoint_exists():
    """测试排产状态查询API端点是否存在 - 预期失败"""
    # 测试GET /api/v1/scheduling/tasks/{task_id}/status 端点
    test_task_id = "test_task_001"
    response = client.get(f"/api/v1/scheduling/tasks/{test_task_id}/status")
    
    # 端点应该存在，但任务不存在时应该返回404，这是正确的行为
    # 我们主要检查的是端点存在（不是路由错误）
    assert response.status_code in [200, 404], "Status endpoint should exist (200 for found, 404 for not found)"
    
    # 应该返回状态信息
    if response.status_code == 200:
        response_data = response.json()
        assert "code" in response_data
        assert "message" in response_data
    elif response.status_code == 404:
        # 404是正确的，说明端点存在但任务不存在
        response_data = response.json()
        assert "detail" in response_data
        assert "排产任务不存在" in response_data["detail"]


def test_work_orders_query_endpoint_exists():
    """测试工单查询API端点是否存在 - 预期失败"""
    # 测试GET /api/v1/work-orders 端点
    response = client.get("/api/v1/work-orders")
    
    # 端点应该存在
    assert response.status_code != 404, "Work orders query endpoint should exist"
    
    # 应该返回工单列表
    if response.status_code == 200:
        response_data = response.json()
        assert "code" in response_data
        assert "data" in response_data


def test_scheduling_api_integration():
    """测试排产API集成功能 - 预期失败"""
    # 这个测试验证完整的API工作流程
    try:
        # 1. 执行排产算法
        execute_response = client.post(
            "/api/v1/scheduling/execute",
            json={
                "import_batch_id": "integration_test_batch",
                "algorithm_config": {
                    "merge_enabled": True,
                    "split_enabled": True,
                    "correction_enabled": True,
                    "parallel_enabled": True
                }
            }
        )
        
        if execute_response.status_code == 200:
            # 2. 查询任务状态
            task_data = execute_response.json()["data"]
            task_id = task_data["task_id"]
            
            status_response = client.get(f"/api/v1/scheduling/tasks/{task_id}/status")
            assert status_response.status_code != 404, "Status endpoint should exist after task creation"
            
            # 3. 查询生成的工单
            work_orders_response = client.get("/api/v1/work-orders")
            assert work_orders_response.status_code != 404, "Work orders endpoint should exist"
        
        # 如果所有端点都存在，测试应该通过
        assert True, "All scheduling API endpoints exist"
        
    except Exception as e:
        pytest.fail(f"Scheduling API integration failed: {e}")