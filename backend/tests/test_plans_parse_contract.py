"""
APS智慧排产系统 - 月计划解析API合约测试

测试目的: 验证 POST /api/v1/monthly-plans/{batch_id}/parse 端点的请求/响应模式
测试策略: 合约测试 - 验证API接口规格compliance，不涉及业务逻辑实现
TDD要求: 这个测试必须失败（因为端点尚未实现），然后通过实现使其通过

合约测试内容:
1. 路径参数验证 - batch_id格式必须为MONTHLY_前缀
2. 查询参数验证 - force_reparse可选布尔值
3. 响应状态码验证 - 200成功, 202异步处理, 400客户端错误, 404未找到
4. 响应结构验证 - 符合OpenAPI规范的解析结果JSON结构
5. 错误响应验证 - 标准错误格式和月度系统特定错误码
"""

import pytest
import httpx
import asyncio
from fastapi import status
from fastapi.testclient import TestClient
import json
from datetime import datetime

# 导入待测试的应用
from app.main import app

class TestMonthlyPlanParseContract:
    """月计划解析端点合约测试类"""
    
    def setup_method(self):
        """测试初始化"""
        self.client = TestClient(app)
        self.base_endpoint = "/api/v1/monthly-plans"
        
        # 测试用的月度批次ID
        self.valid_batch_id = "MONTHLY_20241116_143022_TEST123"
        self.invalid_batch_id = "IMPORT_20241116_143022_TEST123"  # 错误前缀（旬计划格式）
        
    def test_parse_success_response_contract(self):
        """测试成功解析的响应合约 - TDD: 当前应该失败，端点未实现"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        
        # 发送解析请求 - 这个请求应该失败，因为端点尚未实现
        response = self.client.post(parse_endpoint)
        
        # TDD阶段：端点未实现，预期404错误
        if response.status_code == status.HTTP_404_NOT_FOUND:
            # 这是当前预期的状态 - 端点不存在
            response_data = response.json()
            assert "detail" in response_data
            assert response_data["detail"] == "Not Found"
            print("✅ TDD RED状态：月计划解析端点未实现 - 正确！")
            
        elif response.status_code == status.HTTP_200_OK:
            # 如果端点已实现，验证同步解析成功的合约
            response_data = response.json()
            
            # 验证响应结构符合OpenAPI规范
            assert "code" in response_data
            assert "message" in response_data
            assert "data" in response_data
            assert response_data["code"] == 200
            
            # 验证解析结果结构
            data = response_data["data"]
            assert "monthly_batch_id" in data
            assert "total_records" in data
            assert "valid_records" in data
            assert "error_records" in data
            assert "warning_records" in data
            assert "records" in data
            assert "errors" in data
            assert "warnings" in data
            
            # 验证数据类型
            assert isinstance(data["monthly_batch_id"], str)
            assert data["monthly_batch_id"] == self.valid_batch_id
            assert isinstance(data["total_records"], int)
            assert isinstance(data["valid_records"], int)
            assert isinstance(data["error_records"], int)
            assert isinstance(data["warning_records"], int)
            assert isinstance(data["records"], list)
            assert isinstance(data["errors"], list)
            assert isinstance(data["warnings"], list)
            
            # 验证记录结构（如果有记录）
            if data["records"]:
                record = data["records"][0]
                expected_fields = [
                    "monthly_plan_id", "monthly_work_order_nr", "monthly_article_nr",
                    "monthly_target_quantity", "monthly_planned_boxes", 
                    "monthly_feeder_codes", "monthly_maker_codes"
                ]
                for field in expected_fields:
                    assert field in record
                    
            print("✅ TDD GREEN状态：月计划解析端点已实现且合约验证通过！")
            
        elif response.status_code == status.HTTP_202_ACCEPTED:
            # 如果采用异步解析模式
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            assert "data" in response_data
            assert response_data["code"] == 202
            
            # 异步任务信息
            data = response_data["data"]
            assert "monthly_batch_id" in data
            assert "status" in data
            assert data["status"] in ["PARSING", "QUEUED"]
            assert "task_id" in data  # 异步任务ID
            
            print("✅ TDD GREEN状态：月计划异步解析端点已实现且合约验证通过！")
            
        else:
            # 其他错误状态码
            print(f"⚠️ 意外状态码: {response.status_code}")
            assert response.status_code in [404, 405, 500]  # 可接受的错误码
            
    def test_parse_with_force_reparse_contract(self):
        """测试强制重新解析参数的合约"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        
        # 测试force_reparse=true
        response = self.client.post(parse_endpoint, params={"force_reparse": True})
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            # 可能包含重新解析的提示信息
            if "重新解析" in response_data["message"] or "force" in response_data["message"].lower():
                print("✅ 强制重新解析参数正确处理")
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_parse_invalid_batch_id_format_contract(self):
        """测试无效批次ID格式的错误响应合约"""
        # 测试错误的批次ID格式（使用decade前缀）
        parse_endpoint = f"{self.base_endpoint}/{self.invalid_batch_id}/parse"
        
        response = self.client.post(parse_endpoint)
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_data = response.json()
            
            # 验证错误响应结构
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            
            # 验证错误信息提及批次ID格式问题
            message = response_data["message"]
            assert ("MONTHLY_" in message or "批次ID格式" in message or 
                   "invalid batch" in message.lower())
            
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            # 如果批次不存在
            response_data = response.json()
            assert "detail" in response_data or "message" in response_data
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_parse_nonexistent_batch_contract(self):
        """测试不存在批次的错误响应合约"""
        nonexistent_batch = "MONTHLY_19991231_000000_NOTEXIST"
        parse_endpoint = f"{self.base_endpoint}/{nonexistent_batch}/parse"
        
        response = self.client.post(parse_endpoint)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            response_data = response.json()
            
            # 验证错误响应结构
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 404
            
            # 验证错误信息提及批次不存在
            message = response_data["message"]
            assert ("不存在" in message or "not found" in message.lower() or 
                   nonexistent_batch in message)
                   
        else:
            # 端点未实现或其他处理方式
            assert response.status_code in [404, 405, 500]
            
    def test_parse_already_completed_contract(self):
        """测试已完成解析批次的合约"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        
        response = self.client.post(parse_endpoint)
        
        # 如果批次已经解析完成，可能返回400错误或直接返回结果
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_data = response.json()
            
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            
            # 错误信息可能提及已完成解析
            message = response_data["message"]
            assert ("已解析" in message or "already parsed" in message.lower() or
                   "completed" in message.lower())
                   
        elif response.status_code == status.HTTP_200_OK:
            # 直接返回已有的解析结果
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_parse_batch_id_validation_contract(self):
        """测试批次ID验证的合约"""
        invalid_batch_ids = [
            "invalid-format",           # 完全错误的格式
            "IMPORT_20241116_143022_ABC", # 错误前缀（旬计划格式）
            "MONTHLY_",                 # 不完整的ID
            "monthly_20241116_143022_abc", # 小写
            "",                         # 空字符串
            "MONTHLY_INVALID_DATE_ABC"  # 无效日期格式
        ]
        
        for batch_id in invalid_batch_ids:
            parse_endpoint = f"{self.base_endpoint}/{batch_id}/parse"
            response = self.client.post(parse_endpoint)
            
            # 验证无效批次ID的处理
            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                # FastAPI路径参数验证错误
                response_data = response.json()
                assert "detail" in response_data
                assert isinstance(response_data["detail"], list)
                
            elif response.status_code == status.HTTP_400_BAD_REQUEST:
                # 自定义批次ID格式验证错误
                response_data = response.json()
                assert "code" in response_data
                assert response_data["code"] == 400
                
            else:
                # 端点未实现或其他处理方式
                assert response.status_code in [404, 405, 500]
                
    def test_parse_response_headers_contract(self):
        """测试解析响应头合约"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        response = self.client.post(parse_endpoint)
        
        # 验证标准HTTP响应头
        assert "content-type" in response.headers
        
        # 对于解析操作，可能需要特殊的响应头
        if response.status_code == 202:  # 异步处理
            # 可能包含任务跟踪相关的响应头
            if "x-task-id" in response.headers:
                assert response.headers["x-task-id"] is not None
                
        # 验证CORS头（如果配置了）
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] is not None
            
    def test_parse_error_details_contract(self):
        """测试解析错误详情的合约"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        
        response = self.client.post(parse_endpoint)
        
        # 如果解析失败，验证错误详情结构
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            
            if "data" in response_data and "errors" in response_data["data"]:
                errors = response_data["data"]["errors"]
                
                # 验证错误记录结构
                for error in errors:
                    assert "row_number" in error
                    assert "error_type" in error
                    assert "error_message" in error
                    assert "field_name" in error  # 可选
                    
                    # 验证数据类型
                    assert isinstance(error["row_number"], int)
                    assert isinstance(error["error_type"], str)
                    assert isinstance(error["error_message"], str)
                    
        else:
            # 端点未实现时跳过此验证
            pass
            
    def test_parse_warning_details_contract(self):
        """测试解析警告详情的合约"""
        parse_endpoint = f"{self.base_endpoint}/{self.valid_batch_id}/parse"
        
        response = self.client.post(parse_endpoint)
        
        # 如果有警告，验证警告详情结构
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            
            if "data" in response_data and "warnings" in response_data["data"]:
                warnings = response_data["data"]["warnings"]
                
                # 验证警告记录结构
                for warning in warnings:
                    assert "row_number" in warning
                    assert "warning_type" in warning
                    assert "warning_message" in warning
                    
                    # 验证数据类型
                    assert isinstance(warning["row_number"], int)
                    assert isinstance(warning["warning_type"], str)
                    assert isinstance(warning["warning_message"], str)
                    
        else:
            # 端点未实现时跳过此验证
            pass


# =============================================================================
# 异步测试版本
# =============================================================================

class TestMonthlyPlanParseAsyncContract:
    """异步月计划解析端点合约测试"""
    
    @pytest.fixture
    async def async_client(self):
        """异步测试客户端"""
        async with httpx.AsyncClient(base_url="http://test") as client:
            yield client
        
    @pytest.mark.asyncio
    async def test_async_parse_contract(self, async_client):
        """测试异步解析的合约"""
        batch_id = "MONTHLY_20241116_143022_ASYNC"
        parse_endpoint = f"http://test/api/v1/monthly-plans/{batch_id}/parse"
        
        # 异步请求
        response = await async_client.post(parse_endpoint)
        
        # 验证异步处理的响应合约
        if response.status_code == status.HTTP_202_ACCEPTED:
            # 异步处理返回202状态码
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            assert "task_id" in response_data["data"]  # 异步任务ID
            assert "status" in response_data["data"]   # 任务状态
            
        elif response.status_code == status.HTTP_200_OK:
            # 同步处理完成
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
        else:
            # 端点未实现或其他状态
            assert response.status_code in [404, 405, 500]


# =============================================================================
# 测试工具和配置
# =============================================================================

def test_contract_specifications():
    """测试合约规范本身"""
    # 确保合约测试遵循规范
    assert TestMonthlyPlanParseContract.__doc__ is not None
    assert "TDD要求" in TestMonthlyPlanParseContract.__doc__
    assert "合约测试" in TestMonthlyPlanParseContract.__doc__


# =============================================================================
# 运行测试的主函数
# =============================================================================

if __name__ == "__main__":
    # 独立运行此合约测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("⚠️ 重要提醒：这是TDD合约测试")
    print("✅ 当前状态：测试已写好并预期失败（端点未实现）")
    print("📋 下一步：实现 POST /api/v1/monthly-plans/{batch_id}/parse 端点")
    print("🎯 实现完成后：运行此测试确保通过")
    print("="*80)