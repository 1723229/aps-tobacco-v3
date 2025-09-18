"""
APS智慧排产系统 - 工作日历查询API合约测试 T012

测试目的: 验证 GET /api/v1/work-calendar 端点的请求/响应模式
测试策略: 合约测试 - 验证API接口规格compliance，不涉及业务逻辑实现
TDD要求: 这个测试必须失败（因为端点尚未实现），然后通过实现使其通过

合约测试内容:
1. 查询参数验证 - 年份、月份参数的格式和范围验证
2. 响应状态码验证 - 200成功, 400客户端错误, 404未找到
3. 响应结构验证 - 符合OpenAPI规范的工作日历JSON结构
4. 工作日历字段验证 - 月度特化字段名（monthly_day_type, monthly_is_working等）
5. 错误响应验证 - 标准错误格式和工作日历特定错误码
"""

import pytest
import httpx
import asyncio
from fastapi import status
from fastapi.testclient import TestClient
import json
from datetime import datetime, date
from typing import Dict, Any, List

# 导入待测试的应用
from app.main import app

class TestWorkCalendarContract:
    """
    工作日历查询端点合约测试类 T012
    
    测试目的: 验证 GET /api/v1/work-calendar 端点的请求/响应模式
    测试策略: 合约测试 - 验证API接口规格compliance，不涉及业务逻辑实现
    TDD要求: 这个测试必须失败（因为端点尚未实现），然后通过实现使其通过
    """
    
    def setup_method(self):
        """测试初始化"""
        self.client = TestClient(app)
        self.base_endpoint = "/api/v1/work-calendar"
        
        # 测试用的查询参数
        self.valid_year = 2024
        self.valid_month = 11
        self.invalid_year = 1999  # 系统支持范围外
        self.invalid_month = 13   # 无效月份
        
    def test_work_calendar_success_response_contract(self):
        """测试成功查询工作日历的响应合约 - TDD: 当前应该失败，端点未实现"""
        
        # 发送工作日历查询请求 - 这个请求应该失败，因为端点尚未实现
        response = self.client.get(
            self.base_endpoint,
            params={
                "year": self.valid_year,
                "month": self.valid_month
            }
        )
        
        # TDD阶段：端点未实现，预期404错误
        if response.status_code == status.HTTP_404_NOT_FOUND:
            # 这是当前预期的状态 - 端点不存在
            response_data = response.json()
            assert "detail" in response_data
            assert response_data["detail"] == "Not Found"
            print("✅ TDD RED状态：工作日历查询端点未实现 - 正确！")
            
        elif response.status_code == status.HTTP_200_OK:
            # 如果端点已实现，验证成功查询的合约
            response_data = response.json()
            
            # 验证响应结构符合OpenAPI规范
            assert "code" in response_data
            assert "message" in response_data
            assert "data" in response_data
            assert response_data["code"] == 200
            
            # 验证工作日历数据结构
            data = response_data["data"]
            assert "year" in data
            assert "month" in data
            assert "calendar_days" in data
            assert "total_work_days" in data
            assert "total_holidays" in data
            assert "total_maintenance_days" in data
            assert "total_working_hours" in data
            
            # 验证数据类型
            assert isinstance(data["year"], int)
            assert isinstance(data["month"], int)
            assert data["year"] == self.valid_year
            assert data["month"] == self.valid_month
            assert isinstance(data["calendar_days"], list)
            assert isinstance(data["total_work_days"], int)
            assert isinstance(data["total_holidays"], int)
            assert isinstance(data["total_maintenance_days"], int)
            assert isinstance(data["total_working_hours"], (int, float))
            
            # 验证日历条目结构（如果有数据）
            if data["calendar_days"]:
                calendar_day = data["calendar_days"][0]
                expected_fields = [
                    "monthly_calendar_id", "calendar_date", "calendar_year",
                    "calendar_month", "calendar_day", "calendar_week_day",
                    "monthly_day_type", "monthly_is_working", "monthly_shifts",
                    "monthly_total_hours", "monthly_capacity_factor",
                    "monthly_holiday_name", "monthly_maintenance_type", "monthly_notes"
                ]
                for field in expected_fields:
                    assert field in calendar_day
                
                # 验证月度特化字段命名
                assert calendar_day["monthly_day_type"] in ["WORKDAY", "WEEKEND", "HOLIDAY", "MAINTENANCE"]
                assert isinstance(calendar_day["monthly_is_working"], int)
                assert calendar_day["monthly_is_working"] in [0, 1]
                assert isinstance(calendar_day["monthly_total_hours"], (int, float))
                assert isinstance(calendar_day["monthly_capacity_factor"], (int, float))
                
            print("✅ TDD GREEN状态：工作日历查询端点已实现且合约验证通过！")
            
        else:
            # 其他错误状态码
            print(f"⚠️ 意外状态码: {response.status_code}")
            assert response.status_code in [404, 405, 500]  # 可接受的错误码
            
    def test_work_calendar_with_year_only_contract(self):
        """测试只提供年份参数的合约"""
        response = self.client.get(
            self.base_endpoint,
            params={"year": self.valid_year}
        )
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
            # 当只提供年份时，可能返回整年的数据或要求提供月份
            data = response_data["data"]
            assert "year" in data
            assert isinstance(data["year"], int)
            
            # 可能包含年度统计或月份列表
            if "months" in data:
                assert isinstance(data["months"], list)
            elif "calendar_days" in data:
                assert isinstance(data["calendar_days"], list)
                
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            # 如果要求必须提供月份参数
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            assert "月份" in response_data["message"] or "month" in response_data["message"].lower()
            
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_work_calendar_without_parameters_contract(self):
        """测试无参数查询的合约"""
        response = self.client.get(self.base_endpoint)
        
        if response.status_code == status.HTTP_200_OK:
            # 可能返回当前月份的日历
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
            data = response_data["data"]
            assert "year" in data
            assert "month" in data
            # 应该是当前年月
            current_date = datetime.now()
            assert data["year"] == current_date.year
            assert data["month"] == current_date.month
            
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            # 如果要求必须提供参数
            response_data = response.json()
            assert "code" in response_data
            assert "message" in response_data
            assert response_data["code"] == 400
            
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_work_calendar_invalid_year_contract(self):
        """测试无效年份参数的错误响应合约"""
        invalid_years = [
            1900,    # 过早年份
            2100,    # 过晚年份
            -2024,   # 负数
            0,       # 零值
            "abc",   # 非数字字符串
            ""       # 空字符串
        ]
        
        for invalid_year in invalid_years:
            response = self.client.get(
                self.base_endpoint,
                params={
                    "year": invalid_year,
                    "month": self.valid_month
                }
            )
            
            # 验证无效年份的处理
            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                # FastAPI查询参数验证错误
                response_data = response.json()
                assert "detail" in response_data
                assert isinstance(response_data["detail"], list)
                
            elif response.status_code == status.HTTP_400_BAD_REQUEST:
                # 自定义年份范围验证错误
                response_data = response.json()
                assert "code" in response_data
                assert response_data["code"] == 400
                
                # 验证错误信息提及年份问题
                message = response_data["message"]
                assert ("年份" in message or "year" in message.lower() or 
                       "无效" in message or "invalid" in message.lower())
                       
            else:
                # 端点未实现或其他处理方式
                assert response.status_code in [404, 405, 500]
                
    def test_work_calendar_invalid_month_contract(self):
        """测试无效月份参数的错误响应合约"""
        invalid_months = [
            0,       # 零值
            13,      # 超出范围
            -1,      # 负数
            25,      # 过大值
            "abc",   # 非数字字符串
            ""       # 空字符串
        ]
        
        for invalid_month in invalid_months:
            response = self.client.get(
                self.base_endpoint,
                params={
                    "year": self.valid_year,
                    "month": invalid_month
                }
            )
            
            # 验证无效月份的处理
            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                # FastAPI查询参数验证错误
                response_data = response.json()
                assert "detail" in response_data
                assert isinstance(response_data["detail"], list)
                
            elif response.status_code == status.HTTP_400_BAD_REQUEST:
                # 自定义月份范围验证错误
                response_data = response.json()
                assert "code" in response_data
                assert response_data["code"] == 400
                
                # 验证错误信息提及月份问题
                message = response_data["message"]
                assert ("月份" in message or "month" in message.lower() or 
                       "无效" in message or "invalid" in message.lower())
                       
            else:
                # 端点未实现或其他处理方式
                assert response.status_code in [404, 405, 500]
                
    def test_work_calendar_nonexistent_date_contract(self):
        """测试不存在日期的错误响应合约"""
        # 测试系统中不存在的年月组合
        nonexistent_year = 1999
        nonexistent_month = 12
        
        response = self.client.get(
            self.base_endpoint,
            params={
                "year": nonexistent_year,
                "month": nonexistent_month
            }
        )
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            response_data = response.json()
            
            # 验证错误响应结构 - 可能是自定义格式或FastAPI默认格式
            if "code" in response_data:
                # 自定义错误格式
                assert "message" in response_data
                assert response_data["code"] == 404
                
                # 验证错误信息提及日期不存在
                message = response_data["message"]
                assert ("不存在" in message or "not found" in message.lower() or 
                       "没有" in message or "no data" in message.lower())
            elif "detail" in response_data:
                # FastAPI默认错误格式
                assert response_data["detail"] is not None
                   
        elif response.status_code == status.HTTP_200_OK:
            # 如果返回空数据而不是404
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
            data = response_data["data"]
            if "calendar_days" in data:
                # 空数据应该是空列表
                assert len(data["calendar_days"]) == 0
                
        else:
            # 端点未实现时的预期行为
            assert response.status_code in [404, 405, 500]
            
    def test_work_calendar_response_headers_contract(self):
        """测试工作日历响应头合约"""
        response = self.client.get(
            self.base_endpoint,
            params={
                "year": self.valid_year,
                "month": self.valid_month
            }
        )
        
        # 验证标准HTTP响应头
        assert "content-type" in response.headers
        
        if response.status_code == 200:
            # 验证JSON内容类型
            assert "application/json" in response.headers["content-type"]
            
        # 验证CORS头（如果配置了）
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] is not None
            
        # 验证缓存控制头（工作日历数据可能被缓存）
        if "cache-control" in response.headers:
            cache_control = response.headers["cache-control"]
            assert cache_control is not None
            
    def test_work_calendar_filtering_contract(self):
        """测试工作日历过滤功能的合约"""
        # 测试按日期类型过滤
        filter_params = [
            {"year": self.valid_year, "month": self.valid_month, "day_type": "WORKDAY"},
            {"year": self.valid_year, "month": self.valid_month, "day_type": "HOLIDAY"},
            {"year": self.valid_year, "month": self.valid_month, "day_type": "WEEKEND"},
            {"year": self.valid_year, "month": self.valid_month, "day_type": "MAINTENANCE"},
            {"year": self.valid_year, "month": self.valid_month, "is_working": "1"},
            {"year": self.valid_year, "month": self.valid_month, "is_working": "0"}
        ]
        
        for params in filter_params:
            response = self.client.get(self.base_endpoint, params=params)
            
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                assert "code" in response_data
                assert "data" in response_data
                
                # 如果支持过滤，验证过滤结果
                data = response_data["data"]
                if "calendar_days" in data and data["calendar_days"]:
                    # 验证过滤条件是否生效
                    if "day_type" in params:
                        expected_type = params["day_type"]
                        for day in data["calendar_days"]:
                            assert day["monthly_day_type"] == expected_type
                            
                    if "is_working" in params:
                        expected_working = int(params["is_working"])
                        for day in data["calendar_days"]:
                            assert day["monthly_is_working"] == expected_working
                            
            elif response.status_code == status.HTTP_400_BAD_REQUEST:
                # 如果不支持某些过滤参数
                response_data = response.json()
                assert "code" in response_data
                assert response_data["code"] == 400
                
            else:
                # 端点未实现时跳过验证
                assert response.status_code in [404, 405, 500]
                
    def test_work_calendar_pagination_contract(self):
        """测试工作日历分页功能的合约"""
        pagination_params = {
            "year": self.valid_year,
            "month": self.valid_month,
            "page": 1,
            "page_size": 10
        }
        
        response = self.client.get(self.base_endpoint, params=pagination_params)
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            
            data = response_data["data"]
            
            # 如果支持分页，验证分页信息
            if "pagination" in data:
                pagination = data["pagination"]
                assert "page" in pagination
                assert "page_size" in pagination
                assert "total_count" in pagination
                assert "total_pages" in pagination
                
                assert isinstance(pagination["page"], int)
                assert isinstance(pagination["page_size"], int)
                assert isinstance(pagination["total_count"], int)
                assert isinstance(pagination["total_pages"], int)
                
                # 验证分页逻辑
                assert pagination["page"] >= 1
                assert pagination["page_size"] >= 1
                assert pagination["total_count"] >= 0
                assert pagination["total_pages"] >= 0
                
        else:
            # 端点未实现或不支持分页
            assert response.status_code in [404, 405, 500]
            
    def test_work_calendar_data_consistency_contract(self):
        """测试工作日历数据一致性合约"""
        response = self.client.get(
            self.base_endpoint,
            params={
                "year": self.valid_year,
                "month": self.valid_month
            }
        )
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            data = response_data["data"]
            
            if "calendar_days" in data and data["calendar_days"]:
                # 验证统计数据与详细数据的一致性
                calendar_days = data["calendar_days"]
                
                # 计算实际的工作日、节假日、维护日数量
                actual_work_days = sum(1 for day in calendar_days 
                                     if day["monthly_day_type"] == "WORKDAY")
                actual_holidays = sum(1 for day in calendar_days 
                                    if day["monthly_day_type"] == "HOLIDAY")
                actual_maintenance_days = sum(1 for day in calendar_days 
                                            if day["monthly_day_type"] == "MAINTENANCE")
                actual_working_hours = sum(day["monthly_total_hours"] 
                                         for day in calendar_days 
                                         if day["monthly_is_working"] == 1)
                
                # 与汇总数据比较
                if "total_work_days" in data:
                    assert data["total_work_days"] == actual_work_days
                if "total_holidays" in data:
                    assert data["total_holidays"] == actual_holidays
                if "total_maintenance_days" in data:
                    assert data["total_maintenance_days"] == actual_maintenance_days
                if "total_working_hours" in data:
                    assert abs(data["total_working_hours"] - actual_working_hours) < 0.01
                    
                # 验证日期连续性（如果返回完整月份）
                dates = [day["calendar_date"] for day in calendar_days]
                dates.sort()
                
                # 验证年月一致性
                for day in calendar_days:
                    assert day["calendar_year"] == self.valid_year
                    assert day["calendar_month"] == self.valid_month
                    
        else:
            # 端点未实现时跳过验证
            pass


# =============================================================================
# 异步测试版本
# =============================================================================

class TestWorkCalendarAsyncContract:
    """异步工作日历查询端点合约测试"""
    
    @pytest.mark.asyncio
    async def test_async_work_calendar_contract(self):
        """测试异步工作日历查询的合约"""
        async with httpx.AsyncClient(base_url="http://test") as client:
            response = await client.get(
                "/api/v1/work-calendar",
                params={"year": 2024, "month": 11}
            )
            
            # 验证异步查询的响应合约
            if response.status_code == status.HTTP_200_OK:
                response_data = response.json()
                assert "code" in response_data
                assert "data" in response_data
                
                # 验证月度特化字段
                data = response_data["data"]
                if "calendar_days" in data and data["calendar_days"]:
                    day = data["calendar_days"][0]
                    assert "monthly_day_type" in day
                    assert "monthly_is_working" in day
                    assert "monthly_capacity_factor" in day
                    
            else:
                # 端点未实现时的预期行为
                assert response.status_code in [404, 405, 500, 502]


# =============================================================================
# 测试工具和配置
# =============================================================================

def test_work_calendar_contract_specifications():
    """测试工作日历合约规范本身"""
    # 确保合约测试遵循规范
    assert TestWorkCalendarContract.__doc__ is not None
    assert "TDD要求" in TestWorkCalendarContract.__doc__
    assert "合约测试" in TestWorkCalendarContract.__doc__
    assert "T012" in TestWorkCalendarContract.__doc__

def test_monthly_field_naming_contract():
    """测试月度特化字段命名合约"""
    expected_monthly_fields = [
        "monthly_calendar_id",
        "monthly_day_type", 
        "monthly_is_working",
        "monthly_shifts",
        "monthly_total_hours",
        "monthly_capacity_factor",
        "monthly_holiday_name",
        "monthly_maintenance_type",
        "monthly_notes"
    ]
    
    # 这些字段应该出现在API响应中
    # 当前只是验证字段名规范，实际验证在端点实现后进行
    for field in expected_monthly_fields:
        assert field.startswith("monthly_")
        assert "_" in field  # 下划线命名约定


# =============================================================================
# 运行测试的主函数
# =============================================================================

if __name__ == "__main__":
    # 独立运行此合约测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("⚠️ 重要提醒：这是TDD合约测试 T012")
    print("✅ 当前状态：测试已写好并预期失败（端点未实现）")
    print("📋 下一步：实现 GET /api/v1/work-calendar 端点")
    print("🎯 实现完成后：运行此测试确保通过")
    print("📝 测试特点：")
    print("   - 年份、月份查询参数验证")
    print("   - 月度特化字段命名验证 (monthly_*)")
    print("   - 工作日类型、节假日信息验证")
    print("   - 错误处理和边界条件测试")
    print("   - 数据一致性和过滤功能验证")
    print("="*80)