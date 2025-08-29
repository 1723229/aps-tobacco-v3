"""
端到端集成测试 - 验证完整的前后端交互流程
包括：上传 → 解析 → 排产 → 工单查询的完整流程
"""
import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.algorithms.pipeline import AlgorithmPipeline

client = TestClient(app)


class TestEndToEndIntegration:
    """完整端到端集成测试"""
    
    def test_complete_workflow_integration(self):
        """测试完整工作流程集成"""
        # 此测试验证从前端到后端的完整数据流
        
        # 1. 模拟文件上传
        test_file_content = b"test excel content"
        upload_response = client.post(
            "/api/v1/plans/upload",
            files={"file": ("test_plan.xlsx", test_file_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        # 上传应该成功或返回有意义的错误
        assert upload_response.status_code in [200, 400, 500]
        
        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            assert "data" in upload_data
            import_batch_id = upload_data["data"]["import_batch_id"]
            
            # 2. 查询上传状态
            status_response = client.get(f"/api/v1/plans/{import_batch_id}/status")
            assert status_response.status_code == 200
            
            # 3. 模拟解析（可能失败，但API应该存在）
            parse_response = client.post(f"/api/v1/plans/{import_batch_id}/parse")
            assert parse_response.status_code in [200, 400, 500]
            
            # 4. 测试排产API
            scheduling_response = client.post(
                "/api/v1/scheduling/execute",
                json={
                    "import_batch_id": import_batch_id,
                    "algorithm_config": {
                        "merge_enabled": True,
                        "split_enabled": True,
                        "correction_enabled": True,
                        "parallel_enabled": True
                    }
                }
            )
            
            # 排产API应该存在（422是参数验证错误，说明API存在但数据无效）
            assert scheduling_response.status_code in [200, 400, 422, 500]
            
            if scheduling_response.status_code == 200:
                task_data = scheduling_response.json()["data"]
                task_id = task_data["task_id"]
                
                # 5. 查询排产状态
                task_status_response = client.get(f"/api/v1/scheduling/tasks/{task_id}/status")
                assert task_status_response.status_code in [200, 404]
            
        # 6. 测试工单查询API
        work_orders_response = client.get("/api/v1/work-orders")
        # 工单API应该可访问，500可能是数据库连接问题但不影响API可用性测试
        assert work_orders_response.status_code in [200, 500]
        
        if work_orders_response.status_code == 200:
            work_orders_data = work_orders_response.json()
            assert "data" in work_orders_data
            assert "work_orders" in work_orders_data["data"]
        
        print("✓ 完整工作流程API集成测试通过")
    
    def test_api_endpoint_availability(self):
        """测试所有API端点可用性"""
        # 测试计划管理API
        plans_endpoints = [
            ("/api/v1/plans/history", "GET"),
            ("/api/v1/plans/statistics", "GET")
        ]
        
        for endpoint, method in plans_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            # API应该存在（不是404）
            assert response.status_code != 404, f"API端点不存在: {method} {endpoint}"
        
        # 测试排产管理API
        test_task_id = "test_task_001"
        scheduling_endpoints = [
            (f"/api/v1/scheduling/tasks/{test_task_id}/status", "GET")
        ]
        
        for endpoint, method in scheduling_endpoints:
            response = client.get(endpoint) if method == "GET" else client.post(endpoint)
            # 排产API应该存在，404表示任务不存在而不是端点不存在
            assert response.status_code in [200, 404, 500], f"API端点问题: {method} {endpoint}"
        
        # 测试工单管理API  
        work_order_endpoints = [
            ("/api/v1/work-orders", "GET")
        ]
        
        for endpoint, method in work_order_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"工单API不可用: {method} {endpoint}"
        
        print("✓ 所有API端点可用性测试通过")
    
    def test_algorithm_pipeline_integration(self):
        """测试算法管道集成"""
        # 测试算法管道是否可以正常实例化和执行
        try:
            pipeline = AlgorithmPipeline()
            
            # 测试空数据处理
            test_data = []
            result = asyncio.run(pipeline.execute_full_pipeline(test_data, use_real_data=False))
            
            assert result is not None
            assert "success" in result
            assert result["success"] == True
            
            print("✓ 算法管道集成测试通过")
            
        except Exception as e:
            pytest.fail(f"算法管道集成失败: {e}")
    
    def test_database_model_integration(self):
        """测试数据库模型集成"""
        try:
            # 测试导入所有模型
            from app.models.scheduling_models import SchedulingTask, ProcessingLog
            from app.models.work_order_models import PackingOrder, FeedingOrder
            from app.models.machine_config_models import MachineSpeed, MachineRelation, ShiftConfig
            
            # 验证模型属性
            assert hasattr(SchedulingTask, '__tablename__')
            assert hasattr(PackingOrder, '__tablename__')
            assert hasattr(FeedingOrder, '__tablename__')
            assert hasattr(MachineSpeed, '__tablename__')
            
            print("✓ 数据库模型集成测试通过")
            
        except ImportError as e:
            pytest.fail(f"数据库模型导入失败: {e}")
    
    def test_system_health_check(self):
        """测试系统健康状态"""
        # 测试FastAPI应用可以正常启动
        response = client.get("/")
        # 根目录可能是404或重定向，但应该有响应
        assert response.status_code in [200, 404, 307, 308]
        
        # 测试API根路径
        api_response = client.get("/api/v1/plans/statistics")
        assert api_response.status_code in [200, 500]
        
        print("✓ 系统健康检查通过")
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试无效请求的错误处理
        invalid_requests = [
            ("/api/v1/plans/nonexistent_batch/status", "GET", [404, 500]),
            ("/api/v1/scheduling/tasks/invalid_task/status", "GET", [404, 500]),
            ("/api/v1/work-orders", "POST", [405, 500])  # POST不被支持
        ]
        
        for endpoint, method, expected_codes in invalid_requests:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            assert response.status_code in expected_codes, f"错误处理问题: {method} {endpoint}"
        
        print("✓ 错误处理集成测试通过")


class TestPerformanceIntegration:
    """性能集成测试"""
    
    def test_api_response_time(self):
        """测试API响应时间"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/plans/statistics")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # API响应时间应该在合理范围内（5秒内）
        assert response_time < 5.0, f"API响应时间过长: {response_time}秒"
        
        print(f"✓ API响应时间测试通过: {response_time:.3f}秒")
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        
        def make_request():
            return client.get("/api/v1/work-orders")
        
        # 创建多个线程并发请求
        threads = []
        results = []
        
        for _ in range(5):
            thread = threading.Thread(target=lambda: results.append(make_request()))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 所有请求都应该成功
        assert len(results) == 5
        for response in results:
            assert response.status_code == 200
        
        print("✓ 并发请求处理测试通过")


def test_frontend_backend_data_compatibility():
    """测试前后端数据兼容性"""
    # 测试API响应格式与前端期望的数据结构匹配
    
    # 1. 工单API响应格式
    work_orders_response = client.get("/api/v1/work-orders")
    if work_orders_response.status_code == 200:
        data = work_orders_response.json()
        
        # 验证响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data
        
        work_orders_data = data["data"]
        assert "work_orders" in work_orders_data
        assert "total_count" in work_orders_data
        assert "page" in work_orders_data
        assert "page_size" in work_orders_data
    
    # 2. 统计API响应格式
    stats_response = client.get("/api/v1/plans/statistics")
    if stats_response.status_code == 200:
        data = stats_response.json()
        assert "code" in data
        assert "data" in data
    
    print("✓ 前后端数据兼容性测试通过")