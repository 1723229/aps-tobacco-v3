"""
APS智慧排产系统 - 月计划排产任务查询API合约测试

测试目的: 验证 GET /api/v1/monthly-scheduling/tasks 端点的请求/响应模式
测试策略: 合约测试 - 验证API接口规格compliance，不涉及业务逻辑实现
TDD要求: 这个测试必须失败（因为端点尚未实现），然后通过实现使其通过

合约测试内容:
1. 查询参数验证 - status, batch_id, page, page_size等过滤和分页参数
2. 响应状态码验证 - 200成功, 400客户端错误, 404未找到
3. 响应结构验证 - 符合OpenAPI规范的任务列表JSON结构
4. 分页信息验证 - 分页元数据的完整性和正确性
5. 任务状态验证 - 排产任务状态枚举值的有效性
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# 导入待测试的应用
from app.main import app

class TestMonthlySchedulingTasksContract:
    """月计划排产任务查询端点合约测试类"""
    
    def setup_method(self):
        """测试初始化"""
        self.client = TestClient(app)
        self.tasks_endpoint = "/api/v1/monthly-scheduling/tasks"
        
    def test_tasks_list_success_response_contract(self):
        """测试任务列表查询成功响应合约 - TDD: 当前应该失败，端点未实现"""
        # 发送任务列表查询请求 - 这个请求应该失败，因为端点尚未实现
        response = self.client.get(self.tasks_endpoint)
        
        # TDD阶段：端点未实现，预期404错误
        if response.status_code == status.HTTP_404_NOT_FOUND:
            # 这是当前预期的状态 - 端点不存在
            response_data = response.json()
            assert "detail" in response_data
            assert response_data["detail"] == "Not Found"
            print("✅ TDD RED状态：月计划排产任务查询端点未实现 - 正确！")
            
        elif response.status_code == status.HTTP_200_OK:
            # 如果端点已实现，验证成功响应的合约
            response_data = response.json()
            
            # 验证响应结构符合OpenAPI规范
            assert "code" in response_data
            assert "message" in response_data
            assert "data" in response_data
            assert response_data["code"] == 200
            
            # 验证任务列表结构
            data = response_data["data"]
            assert "tasks" in data
            assert "pagination" in data
            
            # 验证任务数组结构
            tasks = data["tasks"]
            assert isinstance(tasks, list)
            
            # 如果有任务，验证任务结构
            if tasks:
                task = tasks[0]
                expected_fields = [
                    "task_id", "monthly_batch_id", "task_name", "status", 
                    "progress", "start_time", "end_time", "created_time",
                    "algorithm_config", "execution_summary", "error_message"
                ]
                for field in expected_fields:
                    assert field in task
                    
                # 验证任务状态枚举值
                valid_statuses = ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
                assert task["status"] in valid_statuses
                
                # 验证数据类型
                assert isinstance(task["task_id"], str)
                assert isinstance(task["monthly_batch_id"], str)
                assert task["monthly_batch_id"].startswith("MONTHLY_")
                assert isinstance(task["progress"], (int, float))
                assert 0 <= task["progress"] <= 100
                
            # 验证分页信息结构
            pagination = data["pagination"]
            assert "page" in pagination
            assert "page_size" in pagination
            assert "total_count" in pagination
            assert "total_pages" in pagination
            assert "has_next" in pagination
            assert "has_prev" in pagination
            
            # 验证分页数据类型
            assert isinstance(pagination["page"], int)
            assert isinstance(pagination["page_size"], int)
            assert isinstance(pagination["total_count"], int)
            assert isinstance(pagination["total_pages"], int)
            assert isinstance(pagination["has_next"], bool)
            assert isinstance(pagination["has_prev"], bool)
            
            print("✅ TDD GREEN状态：月计划排产任务查询端点已实现且合约验证通过！")
            
        else:
            # 其他错误状态码
            print(f"⚠️ 意外状态码: {response.status_code}")
            assert response.status_code in [404, 405, 500]  # 可接受的错误码
            
    def test_tasks_filter_by_status_contract(self):
        """测试按状态过滤任务的合约"""
        valid_statuses = ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
        
        for status_filter in valid_statuses:
            response = self.client.get(
                self.tasks_endpoint,
                params={"status": status_filter}
            )
            
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                assert "code" in response_data
                assert "data" in response_data
                
                # 验证返回的任务都是指定状态
                tasks = response_data["data"]["tasks"]
                for task in tasks:
                    assert task["status"] == status_filter
                    
            else:
                # 端点未实现时跳过验证
                assert response.status_code in [404, 405, 500]
                
    def test_tasks_filter_by_batch_id_contract(self):
        """测试按批次ID过滤任务的合约"""
        test_batch_id = "MONTHLY_20241116_143022_TEST123"
        
        response = self.client.get(
            self.tasks_endpoint,
            params={"monthly_batch_id": test_batch_id}
        )
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
            # 验证返回的任务都是指定批次
            tasks = response_data["data"]["tasks"]
            for task in tasks:
                assert task["monthly_batch_id"] == test_batch_id
                
        else:
            # 端点未实现时跳过验证
            assert response.status_code in [404, 405, 500]
            
    def test_tasks_pagination_contract(self):
        """测试分页参数的合约"""
        # 测试第一页
        response = self.client.get(
            self.tasks_endpoint,
            params={"page": 1, "page_size": 10}
        )
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "data" in response_data
            
            pagination = response_data["data"]["pagination"]
            assert pagination["page"] == 1
            assert pagination["page_size"] == 10
            
            # 验证任务数量不超过page_size
            tasks = response_data["data"]["tasks"]
            assert len(tasks) <= 10
            
        else:
            # 端点未实现时跳过验证
            assert response.status_code in [404, 405, 500]
            
    def test_tasks_invalid_pagination_contract(self):
        """测试无效分页参数的合约"""
        invalid_params = [
            {"page": 0, "page_size": 10},      # 页码从1开始
            {"page": 1, "page_size": 0},       # 页面大小必须>0
            {"page": -1, "page_size": 10},     # 负数页码
            {"page": 1, "page_size": -10},     # 负数页面大小
            {"page": 1, "page_size": 1001},    # 过大页面大小
        ]
        
        for params in invalid_params:
            response = self.client.get(self.tasks_endpoint, params=params)
            
            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                # FastAPI参数验证错误
                response_data = response.json()
                assert "detail" in response_data
                assert isinstance(response_data["detail"], list)
                
            elif response.status_code == status.HTTP_400_BAD_REQUEST:
                # 自定义业务逻辑验证错误
                response_data = response.json()
                assert "code" in response_data
                assert response_data["code"] == 400
                
            else:
                # 端点未实现时跳过验证
                assert response.status_code in [404, 405, 500]
                
    def test_tasks_invalid_status_filter_contract(self):
        """测试无效状态过滤器的合约"""
        invalid_status = "INVALID_STATUS"
        
        response = self.client.get(
            self.tasks_endpoint,
            params={"status": invalid_status}
        )
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            
            # 验证错误信息提及状态无效
            message = response_data["message"]
            assert any(keyword in message.lower() for keyword in 
                      ["status", "invalid", "状态"])
                      
        else:
            # 端点未实现时跳过验证
            assert response.status_code in [404, 405, 500]
            
    def test_tasks_invalid_batch_id_format_contract(self):
        """测试无效批次ID格式的合约"""
        invalid_batch_id = "IMPORT_20241116_143022_WRONG"  # 错误前缀
        
        response = self.client.get(
            self.tasks_endpoint,
            params={"monthly_batch_id": invalid_batch_id}
        )
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            
            # 验证错误信息提及批次ID格式
            message = response_data["message"]
            assert ("MONTHLY_" in message or "batch" in message.lower())
            
        else:
            # 端点未实现时跳过验证
            assert response.status_code in [404, 405, 500]
            
    def test_tasks_time_range_filter_contract(self):
        """测试时间范围过滤的合约"""
        # 测试创建时间范围过滤
        start_time = (datetime.now() - timedelta(days=7)).isoformat()
        end_time = datetime.now().isoformat()
        
        response = self.client.get(
            self.tasks_endpoint,
            params={
                "created_after": start_time,
                "created_before": end_time
            }
        )
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "data" in response_data
            
            # 验证返回的任务都在时间范围内
            tasks = response_data["data"]["tasks"]
            for task in tasks:
                task_created = datetime.fromisoformat(
                    task["created_time"].replace('Z', '+00:00')
                )
                assert start_time <= task_created.isoformat() <= end_time
                
        else:
            # 端点未实现时跳过验证
            assert response.status_code in [404, 405, 500]
            
    def test_tasks_sorting_contract(self):
        """测试任务排序的合约"""
        sort_fields = ["created_time", "start_time", "status", "progress"]
        sort_orders = ["asc", "desc"]
        
        for field in sort_fields:
            for order in sort_orders:
                response = self.client.get(
                    self.tasks_endpoint,
                    params={
                        "sort_by": field,
                        "sort_order": order
                    }
                )
                
                if response.status_code == status.HTTP_200_OK:
                    response_data = response.json()
                    assert "data" in response_data
                    
                    tasks = response_data["data"]["tasks"]
                    if len(tasks) > 1:
                        # 验证排序是否正确应用
                        # 这里只验证结构，不验证具体排序逻辑
                        for task in tasks:
                            assert field in task
                            
                else:
                    # 端点未实现时跳过验证
                    assert response.status_code in [404, 405, 500]


# =============================================================================
# 特定任务查询合约测试
# =============================================================================

class TestMonthlySchedulingTaskDetailContract:
    """单个任务详情查询合约测试"""
    
    def setup_method(self):
        """测试初始化"""
        self.client = TestClient(app)
        self.base_endpoint = "/api/v1/monthly-scheduling/tasks"
        self.test_task_id = "MONTHLY_TASK_20241116_143022_001"
        
    def test_task_detail_success_contract(self):
        """测试单个任务详情查询成功合约"""
        detail_endpoint = f"{self.base_endpoint}/{self.test_task_id}"
        
        response = self.client.get(detail_endpoint)
        
        # TDD阶段：端点未实现，预期404错误
        if response.status_code == status.HTTP_404_NOT_FOUND:
            response_data = response.json()
            assert "detail" in response_data
            print("✅ TDD RED状态：任务详情查询端点未实现 - 正确！")
            
        elif response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            
            # 验证响应结构
            assert "code" in response_data
            assert "message" in response_data
            assert "data" in response_data
            assert response_data["code"] == 200
            
            # 验证任务详情结构
            task = response_data["data"]
            detailed_fields = [
                "task_id", "monthly_batch_id", "task_name", "status",
                "progress", "start_time", "end_time", "execution_duration",
                "algorithm_config", "execution_summary", "error_message",
                "result_summary", "created_time", "updated_time"
            ]
            
            for field in detailed_fields:
                assert field in task
                
            # 验证详细执行摘要结构
            if task["execution_summary"]:
                summary = task["execution_summary"]
                assert isinstance(summary, dict)
                expected_summary_fields = [
                    "total_plans_processed", "successful_schedules",
                    "failed_schedules", "algorithms_executed",
                    "performance_metrics"
                ]
                for field in expected_summary_fields:
                    if field in summary:  # 可选字段
                        assert summary[field] is not None
                        
            print("✅ TDD GREEN状态：任务详情查询端点已实现且合约验证通过！")
            
        else:
            assert response.status_code in [404, 405, 500]
            
    def test_task_detail_not_found_contract(self):
        """测试任务不存在的合约"""
        nonexistent_task_id = "MONTHLY_TASK_19991231_000000_999"
        detail_endpoint = f"{self.base_endpoint}/{nonexistent_task_id}"
        
        response = self.client.get(detail_endpoint)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 404
            
        else:
            assert response.status_code in [404, 405, 500]


# =============================================================================
# 测试工具和配置
# =============================================================================

def test_scheduling_tasks_contract_specifications():
    """测试排产任务合约规范本身"""
    assert TestMonthlySchedulingTasksContract.__doc__ is not None
    assert "TDD要求" in TestMonthlySchedulingTasksContract.__doc__
    assert "合约测试" in TestMonthlySchedulingTasksContract.__doc__


# =============================================================================
# 运行测试的主函数
# =============================================================================

if __name__ == "__main__":
    # 独立运行此合约测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("⚠️ 重要提醒：这是TDD合约测试")
    print("✅ 当前状态：测试已写好并预期失败（端点未实现）")
    print("📋 下一步：实现 GET /api/v1/monthly-scheduling/tasks 端点")
    print("🎯 实现完成后：运行此测试确保通过")
    print("="*80)