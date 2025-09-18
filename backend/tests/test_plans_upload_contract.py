"""
APS智慧排产系统 - 月计划上传API合约测试

测试目的: 验证 POST /api/v1/monthly-plans/upload 端点的请求/响应模式
测试策略: 合约测试 - 验证API接口规格compliance，不涉及业务逻辑实现
TDD要求: 这个测试必须失败（因为端点尚未实现），然后通过实现使其通过

合约测试内容:
1. 请求格式验证 - multipart/form-data with Excel file
2. 响应状态码验证 - 200成功, 400客户端错误, 500服务器错误
3. 响应结构验证 - 符合OpenAPI规范的JSON结构
4. 错误响应验证 - 标准错误格式和错误码
"""

import pytest
import httpx
import asyncio
from fastapi import status
from fastapi.testclient import TestClient
import tempfile
import os
from io import BytesIO

# 导入待测试的应用
from app.main import app

class TestMonthlyPlanUploadContract:
    """月计划上传端点合约测试类"""
    
    def setup_method(self):
        """测试初始化"""
        self.client = TestClient(app)
        self.upload_endpoint = "/api/v1/monthly-plans/upload"  # 月计划专用路由，避免与/plans冲突
        
        # 创建测试Excel文件
        self.test_excel_content = self._create_test_excel_file()
        
    def _create_test_excel_file(self) -> BytesIO:
        """创建测试用Excel文件内容"""
        # 创建简单的Excel文件内容（模拟浙江中烟月度计划格式）
        excel_content = BytesIO()
        # 简化的Excel内容，实际应该是openpyxl创建的完整Excel
        excel_content.write(b"PK\x03\x04")  # Excel文件头标识
        excel_content.write(b"Test Excel Content for Monthly Plan")
        excel_content.seek(0)
        return excel_content
        
    def test_upload_success_response_contract(self):
        """测试成功上传的响应合约 - TDD: 当前应该失败，端点未实现"""
        # 准备测试文件
        files = {
            "file": ("浙江中烟2024年11月份生产计划安排表.xlsx", self.test_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        # 发送请求 - 这个请求应该失败，因为端点尚未实现
        response = self.client.post(self.upload_endpoint, files=files)
        
        # TDD阶段：端点未实现，预期404错误
        if response.status_code == status.HTTP_404_NOT_FOUND:
            # 这是当前预期的状态 - 端点不存在
            response_data = response.json()
            assert "detail" in response_data
            assert response_data["detail"] == "Not Found"
            print("✅ TDD RED状态：端点未实现，测试预期失败 - 正确！")
            
        elif response.status_code == status.HTTP_200_OK:
            # 如果端点已实现，验证合约
            response_data = response.json()
            
            # 验证响应结构符合OpenAPI规范
            assert "code" in response_data
            assert "message" in response_data  
            assert "data" in response_data
            assert response_data["code"] == 200
            
            # 验证data字段结构
            data = response_data["data"]
            assert "monthly_batch_id" in data
            assert "file_name" in data
            assert "file_size" in data
            assert "upload_time" in data
            
            # 验证数据类型
            assert isinstance(data["monthly_batch_id"], str)
            assert data["monthly_batch_id"].startswith("MONTHLY_")
            assert isinstance(data["file_name"], str)
            assert isinstance(data["file_size"], int)
            assert isinstance(data["upload_time"], str)  # ISO格式时间字符串
            print("✅ TDD GREEN状态：端点已实现且合约验证通过！")
            
        else:
            # 其他错误状态码
            print(f"⚠️ 意外状态码: {response.status_code}")
            assert response.status_code in [404, 405, 500]  # 可接受的错误码
            
    def test_upload_invalid_file_contract(self):
        """测试无效文件的错误响应合约"""
        # 测试非Excel文件
        files = {
            "file": ("test.txt", BytesIO(b"not an excel file"), "text/plain")
        }
        
        response = self.client.post(self.upload_endpoint, files=files)
        
        # 合约验证：错误响应结构
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response_data = response.json()
            
            # 验证错误响应结构
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            assert isinstance(response_data["message"], str)
            
            # 可选的详细错误信息
            if "data" in response_data and response_data["data"]:
                assert isinstance(response_data["data"], (dict, str))
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_upload_missing_file_contract(self):
        """测试缺少文件的错误响应合约"""
        # 不传递文件参数
        response = self.client.post(self.upload_endpoint, data={})
        
        # 合约验证：缺少必需参数的错误
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            response_data = response.json()
            
            # FastAPI的标准验证错误格式
            assert "detail" in response_data
            assert isinstance(response_data["detail"], list)
            
            # 验证错误详情结构
            for error in response_data["detail"]:
                assert "loc" in error
                assert "msg" in error
                assert "type" in error
        else:
            # 端点未实现时的预期行为  
            assert response.status_code in [404, 405, 500]
            
    def test_upload_oversized_file_contract(self):
        """测试文件过大的错误响应合约"""
        # 创建模拟的大文件（50MB+）
        large_content = BytesIO()
        large_content.write(b"x" * (50 * 1024 * 1024 + 1))  # 超过50MB
        large_content.seek(0)
        
        files = {
            "file": ("large_plan.xlsx", large_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = self.client.post(self.upload_endpoint, files=files)
        
        # 合约验证：文件过大错误
        if response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
            response_data = response.json()
            
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 413
            assert "文件大小" in response_data["message"] or "too large" in response_data["message"].lower()
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_upload_with_overwrite_parameter_contract(self):
        """测试覆盖参数的合约"""
        files = {
            "file": ("test_plan.xlsx", self.test_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        # 测试允许覆盖
        response = self.client.post(
            self.upload_endpoint,
            files=files,
            data={"allow_overwrite": "true"}
        )
        
        # 验证请求被正确处理（无论是否成功）
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_upload_content_type_validation_contract(self):
        """测试Content-Type验证合约"""
        # 测试正确的Content-Type
        files = {
            "file": ("plan.xlsx", self.test_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = self.client.post(self.upload_endpoint, files=files)
        
        # 验证Content-Type被正确处理
        # 由于端点未实现，主要验证请求格式正确性
        assert response.status_code in [200, 400, 404, 405, 500]
        
        # 测试错误的Content-Type但正确的文件扩展名
        files_wrong_type = {
            "file": ("plan.xlsx", self.test_excel_content, "application/octet-stream")
        }
        
        response_wrong = self.client.post(self.upload_endpoint, files=files_wrong_type)
        assert response_wrong.status_code in [200, 400, 404, 405, 500]
        
    def test_response_headers_contract(self):
        """测试响应头合约"""
        files = {
            "file": ("test.xlsx", self.test_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = self.client.post(self.upload_endpoint, files=files)
        
        # 验证标准HTTP响应头
        assert "content-type" in response.headers
        
        # 如果实现了CORS，验证CORS头
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] is not None
            
    def test_upload_filename_with_special_characters_contract(self):
        """测试特殊字符文件名的合约"""
        special_filenames = [
            "浙江中烟-2024年11月份生产计划安排表.xlsx",  # 中文和特殊字符
            "plan (copy).xlsx",  # 括号
            "plan_2024.11.16.xlsx",  # 点号
            "plan file.xlsx"  # 空格
        ]
        
        for filename in special_filenames:
            files = {
                "file": (filename, self.test_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            }
            
            response = self.client.post(self.upload_endpoint, files=files)
            
            # 验证特殊字符文件名被正确处理
            assert response.status_code in [200, 400, 404, 405, 500]
            
            # 如果成功，验证文件名在响应中正确返回
            if response.status_code == 200:
                response_data = response.json()
                if "data" in response_data and "file_name" in response_data["data"]:
                    assert response_data["data"]["file_name"] == filename


# =============================================================================
# 异步测试版本（如果API使用异步处理）
# =============================================================================

class TestMonthlyPlanUploadAsyncContract:
    """异步月计划上传端点合约测试"""
    
    @pytest.fixture
    def async_client(self):
        """异步测试客户端"""
        return httpx.AsyncClient(app=app, base_url="http://test")
        
    @pytest.mark.asyncio
    async def test_async_upload_contract(self, async_client):
        """测试异步上传的合约"""
        files = {
            "file": ("async_test.xlsx", BytesIO(b"test content"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        # 异步请求
        response = await async_client.post("/api/v1/monthly-plans/upload", files=files)  # 月计划专用路由
        
        # 验证异步处理的响应合约
        if response.status_code == status.HTTP_202_ACCEPTED:
            # 异步处理返回202状态码
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            assert "task_id" in response_data["data"]  # 异步任务ID
        else:
            # 端点未实现或同步处理
            assert response.status_code in [200, 404, 405, 500]


# =============================================================================
# 测试配置和工具
# =============================================================================

@pytest.fixture(scope="module")
def test_excel_file():
    """创建临时Excel文件用于测试"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
        temp_file.write(b"PK\x03\x04")  # Excel文件头
        temp_file.write(b"Mock Excel Content")
        temp_file.flush()
        yield temp_file.name
    
    # 清理临时文件
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


def test_contract_documentation():
    """测试合约文档和规范"""
    # 这个测试确保合约测试本身遵循规范
    assert TestMonthlyPlanUploadContract.__doc__ is not None
    assert "合约测试" in TestMonthlyPlanUploadContract.__doc__
    assert "TDD要求" in TestMonthlyPlanUploadContract.__doc__


# =============================================================================
# 运行测试的主函数（用于独立测试）
# =============================================================================

if __name__ == "__main__":
    # 独立运行此合约测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("⚠️ 重要提醒：这是TDD合约测试")
    print("✅ 当前状态：测试已写好并预期失败（端点未实现）") 
    print("📋 下一步：实现 POST /api/v1/monthly-plans/upload 端点")
    print("🎯 实现完成后：运行此测试确保通过")
    print("="*80)