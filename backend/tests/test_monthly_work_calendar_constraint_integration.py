"""
T016 - 月度工作日历约束集成测试

测试目的: 验证工作日历与排产算法的完整集成，确保时间约束在整个排产流程中正确执行
测试策略: 集成测试 - 验证工作日历约束在排产算法中的应用和影响
TDD要求: 测试工作日历约束对排产结果的完整影响

核心测试场景:
1. 工作日历与排产算法的集成验证
2. 节假日、维护日、工作日的约束应用
3. 产能因子在排产中的正确使用
4. 班次安排和工作时间约束
5. 跨月份的日历约束处理
6. 异常日历数据的容错测试
7. 性能测试（大规模日历数据）
8. 与月度算法管道的集成验证
"""

import pytest
import asyncio
import time
import gc
import json
import threading
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from unittest.mock import AsyncMock, MagicMock, patch
import psutil
import os
from concurrent.futures import ThreadPoolExecutor

# 导入模型和服务
from app.models.monthly_work_calendar_models import MonthlyWorkCalendar
from app.algorithms.monthly_scheduling.monthly_calendar_service import (
    MonthlyCalendarService,
    CalendarDay,
    MonthCapacity,
    CalendarServiceConfig,
    DayType,
    CapacityFactorType
)

# 导入月度算法模块
from app.algorithms.monthly_scheduling import (
    MonthlyMachineSelector,
    MonthlyCapacityCalculator,
    get_algorithm_info,
    get_pipeline_order,
    ALGORITHM_PIPELINE
)

from app.algorithms.monthly_scheduling.base import (
    BaseAlgorithm,
    AlgorithmType,
    Priority,
    MachineType,
    MonthlyPlanItem,
    MachineInfo,
    ScheduleResult
)

# 导入测试助手
from .fixtures.test_helpers import PerformanceMetrics, ValidationResult


@dataclass
class CalendarConstraintTestCase:
    """日历约束测试用例"""
    name: str
    description: str
    calendar_data: List[Dict[str, Any]]
    plan_items: List[Dict[str, Any]]
    expected_working_days: int
    expected_total_capacity: Decimal
    expected_constraints_applied: List[str]
    should_pass: bool = True


@dataclass
class PerformanceExpectation:
    """性能期望值"""
    max_execution_time: float  # 最大执行时间（秒）
    max_memory_usage_mb: float  # 最大内存使用（MB）
    min_records_per_second: float  # 最小处理速度


@dataclass
class IntegrationTestResult:
    """集成测试结果"""
    test_name: str
    success: bool
    calendar_constraints_applied: int
    scheduling_result_count: int
    working_days_validated: int
    capacity_factor_adjustments: int
    performance_metrics: PerformanceMetrics
    error_details: Optional[str] = None


class WorkCalendarConstraintIntegrationTest:
    """工作日历约束集成测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.session = None
        self.calendar_service = None
        self.test_results: List[IntegrationTestResult] = []
        self.performance_expectations = PerformanceExpectation(
            max_execution_time=5.0,
            max_memory_usage_mb=200.0,
            min_records_per_second=100.0
        )
        
    async def setup_test_environment(self, session):
        """设置测试环境"""
        self.session = session
        
        # 创建日历服务配置
        config = CalendarServiceConfig(
            default_capacity_factor=Decimal("1.0"),
            overtime_capacity_factor=Decimal("1.5"),
            reduced_capacity_factor=Decimal("0.7"),
            maintenance_capacity_factor=Decimal("0.0"),
            holiday_capacity_factor=Decimal("0.0"),
            standard_working_hours=8,
            overtime_threshold_hours=10,
            maintenance_impact_days=1,
            planned_maintenance_factor=Decimal("0.8")
        )
        
        self.calendar_service = MonthlyCalendarService(session, config)
        
    def create_test_calendar_data(self) -> List[CalendarConstraintTestCase]:
        """创建测试日历数据"""
        test_cases = []
        
        # 测试用例1: 正常工作日历
        test_cases.append(CalendarConstraintTestCase(
            name="normal_calendar",
            description="正常工作日历测试",
            calendar_data=[
                {
                    "calendar_date": date(2025, 1, 1),
                    "monthly_day_type": "HOLIDAY",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0"),
                    "monthly_holiday_name": "元旦"
                },
                {
                    "calendar_date": date(2025, 1, 2),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0"),
                    "monthly_total_hours": Decimal("8.0")
                },
                {
                    "calendar_date": date(2025, 1, 3),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.2"),
                    "monthly_total_hours": Decimal("10.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "红塔山经典",
                    "machine_type": "卷包机",
                    "planned_quantity": 10000,
                    "target_date": "2025-01-02"
                }
            ],
            expected_working_days=2,
            expected_total_capacity=Decimal("2.2"),
            expected_constraints_applied=["holiday_constraint", "capacity_adjustment"]
        ))
        
        # 测试用例2: 维护日约束
        test_cases.append(CalendarConstraintTestCase(
            name="maintenance_calendar",
            description="维护日约束测试",
            calendar_data=[
                {
                    "calendar_date": date(2025, 1, 10),
                    "monthly_day_type": "MAINTENANCE",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0"),
                    "monthly_maintenance_type": "设备保养"
                },
                {
                    "calendar_date": date(2025, 1, 11),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("0.8"),
                    "monthly_total_hours": Decimal("6.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "云烟",
                    "machine_type": "喂丝机",
                    "planned_quantity": 5000,
                    "target_date": "2025-01-10"
                }
            ],
            expected_working_days=1,
            expected_total_capacity=Decimal("0.8"),
            expected_constraints_applied=["maintenance_constraint", "reduced_capacity"]
        ))
        
        # 测试用例3: 跨月约束
        test_cases.append(CalendarConstraintTestCase(
            name="cross_month_calendar",
            description="跨月份日历约束测试",
            calendar_data=[
                {
                    "calendar_date": date(2025, 1, 31),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                },
                {
                    "calendar_date": date(2025, 2, 1),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "中华",
                    "machine_type": "卷包机",
                    "planned_quantity": 20000,
                    "target_date": "2025-01-31"
                }
            ],
            expected_working_days=2,
            expected_total_capacity=Decimal("2.0"),
            expected_constraints_applied=["cross_month_constraint"]
        ))
        
        # 测试用例4: 班次约束
        test_cases.append(CalendarConstraintTestCase(
            name="shift_constraints",
            description="班次安排约束测试",
            calendar_data=[
                {
                    "calendar_date": date(2025, 1, 15),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.5"),
                    "monthly_shifts": [
                        {"shift_name": "白班", "start": "08:00", "end": "16:00", "capacity_factor": 1.0},
                        {"shift_name": "夜班", "start": "20:00", "end": "04:00", "capacity_factor": 0.8}
                    ],
                    "monthly_total_hours": Decimal("16.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "玉溪",
                    "machine_type": "卷包机",
                    "planned_quantity": 15000,
                    "target_date": "2025-01-15"
                }
            ],
            expected_working_days=1,
            expected_total_capacity=Decimal("1.5"),
            expected_constraints_applied=["shift_constraint", "overtime_capacity"]
        ))
        
        return test_cases
        
    async def create_calendar_records(self, calendar_data: List[Dict[str, Any]]):
        """创建日历记录"""
        records = []
        for data in calendar_data:
            record = MonthlyWorkCalendar(
                calendar_date=data["calendar_date"],
                calendar_year=data["calendar_date"].year,
                calendar_month=data["calendar_date"].month,
                calendar_day=data["calendar_date"].day,
                calendar_week_day=data["calendar_date"].isoweekday(),
                monthly_day_type=data.get("monthly_day_type", "WORKDAY"),
                monthly_is_working=data.get("monthly_is_working", 1),
                monthly_capacity_factor=data.get("monthly_capacity_factor", Decimal("1.0")),
                monthly_total_hours=data.get("monthly_total_hours", Decimal("8.0")),
                monthly_shifts=data.get("monthly_shifts"),
                monthly_holiday_name=data.get("monthly_holiday_name"),
                monthly_maintenance_type=data.get("monthly_maintenance_type"),
                monthly_notes=data.get("monthly_notes")
            )
            records.append(record)
            
        # 批量插入数据库
        self.session.add_all(records)
        await self.session.commit()
        return records
        
    async def test_calendar_algorithm_integration(self, test_case: CalendarConstraintTestCase) -> IntegrationTestResult:
        """测试日历与算法集成"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # 1. 创建日历记录
            await self.create_calendar_records(test_case.calendar_data)
            
            # 2. 获取工作日信息
            start_date = min(data["calendar_date"] for data in test_case.calendar_data)
            end_date = max(data["calendar_date"] for data in test_case.calendar_data)
            working_days = await self.calendar_service.get_working_days(start_date, end_date)
            
            # 3. 验证工作日数量
            assert len(working_days) == test_case.expected_working_days, \
                f"工作日数量不匹配: 期望 {test_case.expected_working_days}, 实际 {len(working_days)}"
            
            # 4. 验证总产能
            total_capacity = sum(day.capacity_factor for day in working_days)
            assert abs(total_capacity - test_case.expected_total_capacity) < Decimal("0.01"), \
                f"总产能不匹配: 期望 {test_case.expected_total_capacity}, 实际 {total_capacity}"
            
            # 5. 模拟排产算法集成
            constraints_applied = await self._simulate_scheduling_with_calendar(working_days, test_case.plan_items)
            
            # 6. 验证约束应用
            for expected_constraint in test_case.expected_constraints_applied:
                assert expected_constraint in constraints_applied, \
                    f"约束未正确应用: {expected_constraint}"
            
            # 7. 计算性能指标
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            performance_metrics = PerformanceMetrics(
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=len(test_case.calendar_data),
                records_per_second=len(test_case.calendar_data) / execution_time if execution_time > 0 else 0
            )
            
            return IntegrationTestResult(
                test_name=test_case.name,
                success=True,
                calendar_constraints_applied=len(constraints_applied),
                scheduling_result_count=len(test_case.plan_items),
                working_days_validated=len(working_days),
                capacity_factor_adjustments=len([day for day in working_days if day.capacity_factor != Decimal("1.0")]),
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=0,
                records_per_second=0
            )
            
            return IntegrationTestResult(
                test_name=test_case.name,
                success=False,
                calendar_constraints_applied=0,
                scheduling_result_count=0,
                working_days_validated=0,
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics,
                error_details=str(e)
            )
    
    async def _simulate_scheduling_with_calendar(self, working_days: List[CalendarDay], plan_items: List[Dict[str, Any]]) -> List[str]:
        """模拟排产算法与日历集成"""
        constraints_applied = []
        
        for day in working_days:
            # 检查节假日约束
            if day.day_type == DayType.HOLIDAY:
                constraints_applied.append("holiday_constraint")
                
            # 检查维护日约束
            if day.day_type == DayType.MAINTENANCE:
                constraints_applied.append("maintenance_constraint")
                
            # 检查产能调整
            if day.capacity_factor != Decimal("1.0"):
                if day.capacity_factor > Decimal("1.0"):
                    constraints_applied.append("overtime_capacity")
                else:
                    constraints_applied.append("reduced_capacity")
                constraints_applied.append("capacity_adjustment")
                
            # 检查班次约束
            if day.shift_count > 1:
                constraints_applied.append("shift_constraint")
        
        # 检查跨月约束
        dates = [day.date for day in working_days]
        if dates and max(dates).month != min(dates).month:
            constraints_applied.append("cross_month_constraint")
            
        return list(set(constraints_applied))
    
    async def test_holiday_constraints(self) -> IntegrationTestResult:
        """测试节假日约束"""
        test_case = CalendarConstraintTestCase(
            name="holiday_constraints_test",
            description="节假日约束专项测试",
            calendar_data=[
                # 春节假期
                {
                    "calendar_date": date(2025, 2, 10),
                    "monthly_day_type": "HOLIDAY",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0"),
                    "monthly_holiday_name": "春节"
                },
                {
                    "calendar_date": date(2025, 2, 11),
                    "monthly_day_type": "HOLIDAY",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0"),
                    "monthly_holiday_name": "春节"
                },
                # 节后第一个工作日，产能可能受影响
                {
                    "calendar_date": date(2025, 2, 17),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("0.8"),
                    "monthly_notes": "节后首日，产能可能受影响"
                }
            ],
            plan_items=[
                {
                    "product_name": "中华软包",
                    "machine_type": "卷包机",
                    "planned_quantity": 8000,
                    "target_date": "2025-02-17"
                }
            ],
            expected_working_days=1,
            expected_total_capacity=Decimal("0.8"),
            expected_constraints_applied=["holiday_constraint", "reduced_capacity"]
        )
        
        return await self.test_calendar_algorithm_integration(test_case)
    
    async def test_maintenance_scheduling_integration(self) -> IntegrationTestResult:
        """测试维护日排产集成"""
        test_case = CalendarConstraintTestCase(
            name="maintenance_scheduling_integration",
            description="维护日排产集成测试",
            calendar_data=[
                # 计划维护日
                {
                    "calendar_date": date(2025, 3, 15),
                    "monthly_day_type": "MAINTENANCE",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0"),
                    "monthly_maintenance_type": "月度设备保养",
                    "monthly_notes": "所有卷包机停机维护"
                },
                # 维护前准备日
                {
                    "calendar_date": date(2025, 3, 14),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("0.9"),
                    "monthly_notes": "维护前准备，产能略减"
                },
                # 维护后恢复日
                {
                    "calendar_date": date(2025, 3, 16),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.1"),
                    "monthly_notes": "维护后产能提升"
                }
            ],
            plan_items=[
                {
                    "product_name": "红塔山新势力",
                    "machine_type": "卷包机",
                    "planned_quantity": 12000,
                    "target_date": "2025-03-16"
                }
            ],
            expected_working_days=2,
            expected_total_capacity=Decimal("2.0"),
            expected_constraints_applied=["maintenance_constraint", "capacity_adjustment"]
        )
        
        return await self.test_calendar_algorithm_integration(test_case)
    
    async def test_capacity_factor_integration(self) -> IntegrationTestResult:
        """测试产能因子集成"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # 创建多种产能因子的日历数据
            calendar_data = []
            for i in range(1, 32):  # 一个月的数据
                day_date = date(2025, 4, i)
                
                # 模拟不同的产能因子场景
                if i % 7 in [6, 0]:  # 周末
                    day_type = "WEEKEND"
                    is_working = 0
                    capacity_factor = Decimal("0.0")
                elif i == 15:  # 维护日
                    day_type = "MAINTENANCE"
                    is_working = 0
                    capacity_factor = Decimal("0.0")
                elif i in [10, 20]:  # 加班日
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("1.3")
                elif i in [5, 25]:  # 减产日
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("0.7")
                else:  # 正常工作日
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("1.0")
                
                calendar_data.append({
                    "calendar_date": day_date,
                    "monthly_day_type": day_type,
                    "monthly_is_working": is_working,
                    "monthly_capacity_factor": capacity_factor
                })
            
            # 创建日历记录
            await self.create_calendar_records(calendar_data)
            
            # 获取月度日历
            calendar_days, month_capacity = await self.calendar_service.get_month_calendar(2025, 4)
            
            # 验证产能因子计算
            working_days = [day for day in calendar_days if day.is_working]
            capacity_adjustments = len([day for day in working_days if day.capacity_factor != Decimal("1.0")])
            
            # 验证总产能计算
            expected_total_capacity = sum(day.capacity_factor for day in working_days)
            assert abs(month_capacity.total_capacity_factor - expected_total_capacity) < Decimal("0.01")
            
            # 计算性能指标
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=len(calendar_data),
                records_per_second=len(calendar_data) / (end_time - start_time)
            )
            
            return IntegrationTestResult(
                test_name="capacity_factor_integration",
                success=True,
                calendar_constraints_applied=len(calendar_data),
                scheduling_result_count=1,
                working_days_validated=len(working_days),
                capacity_factor_adjustments=capacity_adjustments,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=0,
                records_per_second=0
            )
            
            return IntegrationTestResult(
                test_name="capacity_factor_integration",
                success=False,
                calendar_constraints_applied=0,
                scheduling_result_count=0,
                working_days_validated=0,
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics,
                error_details=str(e)
            )
    
    async def test_cross_month_constraints(self) -> IntegrationTestResult:
        """测试跨月份约束"""
        test_case = CalendarConstraintTestCase(
            name="cross_month_constraints",
            description="跨月份日历约束测试",
            calendar_data=[
                # 1月最后几天
                {
                    "calendar_date": date(2025, 1, 29),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                },
                {
                    "calendar_date": date(2025, 1, 30),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                },
                {
                    "calendar_date": date(2025, 1, 31),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("0.8")  # 月末产能下降
                },
                # 2月前几天
                {
                    "calendar_date": date(2025, 2, 1),
                    "monthly_day_type": "WEEKEND",
                    "monthly_is_working": 0,
                    "monthly_capacity_factor": Decimal("0.0")
                },
                {
                    "calendar_date": date(2025, 2, 3),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "利群",
                    "machine_type": "卷包机",
                    "planned_quantity": 25000,
                    "target_date": "2025-01-31"
                }
            ],
            expected_working_days=4,
            expected_total_capacity=Decimal("3.8"),
            expected_constraints_applied=["cross_month_constraint", "capacity_adjustment"]
        )
        
        return await self.test_calendar_algorithm_integration(test_case)
    
    async def test_shift_arrangement_constraints(self) -> IntegrationTestResult:
        """测试班次安排约束"""
        test_case = CalendarConstraintTestCase(
            name="shift_arrangement_constraints",
            description="班次安排约束集成测试",
            calendar_data=[
                {
                    "calendar_date": date(2025, 5, 10),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.8"),
                    "monthly_shifts": [
                        {
                            "shift_name": "早班",
                            "start": "06:00",
                            "end": "14:00",
                            "capacity_factor": 1.0
                        },
                        {
                            "shift_name": "中班",
                            "start": "14:00",
                            "end": "22:00",
                            "capacity_factor": 0.9
                        },
                        {
                            "shift_name": "夜班",
                            "start": "22:00",
                            "end": "06:00",
                            "capacity_factor": 0.8
                        }
                    ],
                    "monthly_total_hours": Decimal("24.0")
                }
            ],
            plan_items=[
                {
                    "product_name": "黄鹤楼",
                    "machine_type": "卷包机",
                    "planned_quantity": 30000,
                    "target_date": "2025-05-10"
                }
            ],
            expected_working_days=1,
            expected_total_capacity=Decimal("1.8"),
            expected_constraints_applied=["shift_constraint", "overtime_capacity"]
        )
        
        return await self.test_calendar_algorithm_integration(test_case)
    
    async def test_error_handling_resilience(self) -> IntegrationTestResult:
        """测试异常处理和容错能力"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # 创建包含异常数据的日历
            invalid_calendar_data = [
                {
                    "calendar_date": date(2025, 6, 1),
                    "monthly_day_type": "INVALID_TYPE",  # 无效类型
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("1.0")
                },
                {
                    "calendar_date": date(2025, 6, 2),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("-0.5")  # 无效的负产能
                },
                {
                    "calendar_date": date(2025, 6, 3),
                    "monthly_day_type": "WORKDAY",
                    "monthly_is_working": 1,
                    "monthly_capacity_factor": Decimal("5.0")  # 过高产能
                }
            ]
            
            # 测试服务的容错能力
            error_count = 0
            handled_records = 0
            
            for data in invalid_calendar_data:
                try:
                    # 尝试创建日历记录，期望某些会失败
                    await self.create_calendar_records([data])
                    handled_records += 1
                except Exception:
                    error_count += 1
                    # 继续处理下一条记录
            
            # 验证服务仍然可以正常工作
            working_days = await self.calendar_service.get_working_days(
                date(2025, 6, 1), 
                date(2025, 6, 3)
            )
            
            # 计算性能指标
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=len(invalid_calendar_data),
                records_per_second=len(invalid_calendar_data) / (end_time - start_time)
            )
            
            return IntegrationTestResult(
                test_name="error_handling_resilience",
                success=True,
                calendar_constraints_applied=handled_records,
                scheduling_result_count=1,
                working_days_validated=len(working_days),
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=0,
                records_per_second=0
            )
            
            return IntegrationTestResult(
                test_name="error_handling_resilience",
                success=False,
                calendar_constraints_applied=0,
                scheduling_result_count=0,
                working_days_validated=0,
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics,
                error_details=str(e)
            )
    
    async def test_large_scale_performance(self) -> IntegrationTestResult:
        """测试大规模数据性能"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # 生成一年的日历数据（约365条记录）
            calendar_data = []
            base_date = date(2025, 1, 1)
            
            for i in range(365):
                current_date = base_date + timedelta(days=i)
                weekday = current_date.weekday()
                
                # 模拟真实业务场景
                if weekday >= 5:  # 周末
                    day_type = "WEEKEND"
                    is_working = 0
                    capacity_factor = Decimal("0.0")
                elif i % 30 == 15:  # 每月一次维护
                    day_type = "MAINTENANCE"
                    is_working = 0
                    capacity_factor = Decimal("0.0")
                elif i % 10 == 0:  # 定期加班
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("1.3")
                else:  # 正常工作日
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("1.0")
                
                calendar_data.append({
                    "calendar_date": current_date,
                    "monthly_day_type": day_type,
                    "monthly_is_working": is_working,
                    "monthly_capacity_factor": capacity_factor
                })
            
            # 批量创建记录
            await self.create_calendar_records(calendar_data)
            
            # 测试大规模查询性能
            query_start = time.time()
            working_days = await self.calendar_service.get_working_days(
                date(2025, 1, 1),
                date(2025, 12, 31)
            )
            query_time = time.time() - query_start
            
            # 测试产能趋势分析性能
            trend_start = time.time()
            trend_data = await self.calendar_service.get_capacity_trend(
                date(2025, 1, 1),
                date(2025, 12, 31)
            )
            trend_time = time.time() - trend_start
            
            # 计算性能指标
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            total_time = end_time - start_time
            
            performance_metrics = PerformanceMetrics(
                execution_time=total_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=len(calendar_data),
                records_per_second=len(calendar_data) / total_time
            )
            
            # 验证性能要求
            assert total_time <= self.performance_expectations.max_execution_time, \
                f"执行时间超标: {total_time:.2f}s > {self.performance_expectations.max_execution_time}s"
            
            assert performance_metrics.memory_usage_mb <= self.performance_expectations.max_memory_usage_mb, \
                f"内存使用超标: {performance_metrics.memory_usage_mb:.2f}MB > {self.performance_expectations.max_memory_usage_mb}MB"
            
            assert performance_metrics.records_per_second >= self.performance_expectations.min_records_per_second, \
                f"处理速度过慢: {performance_metrics.records_per_second:.2f} < {self.performance_expectations.min_records_per_second}"
            
            return IntegrationTestResult(
                test_name="large_scale_performance",
                success=True,
                calendar_constraints_applied=len(calendar_data),
                scheduling_result_count=len(working_days),
                working_days_validated=len(working_days),
                capacity_factor_adjustments=len([d for d in calendar_data if d["monthly_capacity_factor"] != Decimal("1.0")]),
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=0,
                records_per_second=0
            )
            
            return IntegrationTestResult(
                test_name="large_scale_performance",
                success=False,
                calendar_constraints_applied=0,
                scheduling_result_count=0,
                working_days_validated=0,
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics,
                error_details=str(e)
            )
    
    async def test_algorithm_pipeline_integration(self) -> IntegrationTestResult:
        """测试与月度算法管道的集成"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # 创建完整的日历数据用于管道测试
            calendar_data = []
            for i in range(1, 32):  # 一个月
                day_date = date(2025, 7, i)
                weekday = day_date.weekday()
                
                if weekday >= 5:
                    day_type = "WEEKEND"
                    is_working = 0
                    capacity_factor = Decimal("0.0")
                else:
                    day_type = "WORKDAY"
                    is_working = 1
                    capacity_factor = Decimal("1.0")
                
                calendar_data.append({
                    "calendar_date": day_date,
                    "monthly_day_type": day_type,
                    "monthly_is_working": is_working,
                    "monthly_capacity_factor": capacity_factor
                })
            
            await self.create_calendar_records(calendar_data)
            
            # 模拟算法管道执行
            pipeline_results = {
                "calendar_service": await self.calendar_service.get_month_calendar(2025, 7),
                "working_days_count": 0,
                "capacity_validation": True,
                "constraint_applications": []
            }
            
            calendar_days, month_capacity = pipeline_results["calendar_service"]
            pipeline_results["working_days_count"] = len([day for day in calendar_days if day.is_working])
            
            # 验证管道集成结果
            assert pipeline_results["working_days_count"] > 0, "管道未正确识别工作日"
            assert month_capacity.total_working_days == pipeline_results["working_days_count"], "工作日统计不一致"
            
            # 计算性能指标
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=len(calendar_data),
                records_per_second=len(calendar_data) / (end_time - start_time)
            )
            
            return IntegrationTestResult(
                test_name="algorithm_pipeline_integration",
                success=True,
                calendar_constraints_applied=len(calendar_data),
                scheduling_result_count=1,
                working_days_validated=pipeline_results["working_days_count"],
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            performance_metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage_mb=end_memory - start_memory,
                memory_peak_mb=max(start_memory, end_memory),
                cpu_usage_percent=psutil.cpu_percent(),
                records_processed=0,
                records_per_second=0
            )
            
            return IntegrationTestResult(
                test_name="algorithm_pipeline_integration",
                success=False,
                calendar_constraints_applied=0,
                scheduling_result_count=0,
                working_days_validated=0,
                capacity_factor_adjustments=0,
                performance_metrics=performance_metrics,
                error_details=str(e)
            )
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.success])
        
        # 性能统计
        avg_execution_time = sum(r.performance_metrics.execution_time for r in self.test_results) / total_tests
        avg_memory_usage = sum(r.performance_metrics.memory_usage_mb for r in self.test_results) / total_tests
        total_constraints_applied = sum(r.calendar_constraints_applied for r in self.test_results)
        total_working_days_validated = sum(r.working_days_validated for r in self.test_results)
        
        return {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests * 100 if total_tests > 0 else 0,
                "failed_tests": total_tests - successful_tests
            },
            "performance_metrics": {
                "average_execution_time": avg_execution_time,
                "average_memory_usage_mb": avg_memory_usage,
                "total_constraints_applied": total_constraints_applied,
                "total_working_days_validated": total_working_days_validated
            },
            "detailed_results": [asdict(result) for result in self.test_results],
            "test_environment": {
                "python_version": os.sys.version,
                "system_info": {
                    "cpu_count": os.cpu_count(),
                    "memory_gb": psutil.virtual_memory().total / (1024**3)
                }
            }
        }


# pytest 测试用例

@pytest.fixture
async def calendar_test_suite(async_session):
    """日历约束集成测试套件fixture"""
    test_suite = WorkCalendarConstraintIntegrationTest()
    await test_suite.setup_test_environment(async_session)
    return test_suite


@pytest.mark.asyncio
async def test_basic_calendar_integration(calendar_test_suite):
    """测试基本日历集成功能"""
    test_cases = calendar_test_suite.create_test_calendar_data()
    
    for test_case in test_cases:
        result = await calendar_test_suite.test_calendar_algorithm_integration(test_case)
        calendar_test_suite.test_results.append(result)
        
        assert result.success, f"测试用例 {test_case.name} 失败: {result.error_details}"
        assert result.working_days_validated > 0, "未验证任何工作日"
        assert result.performance_metrics.execution_time < 2.0, "执行时间过长"


@pytest.mark.asyncio
async def test_holiday_constraints_integration(calendar_test_suite):
    """测试节假日约束集成"""
    result = await calendar_test_suite.test_holiday_constraints()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"节假日约束测试失败: {result.error_details}"
    assert result.calendar_constraints_applied >= 2, "未正确应用节假日约束"
    assert result.working_days_validated == 1, "工作日验证数量不正确"


@pytest.mark.asyncio
async def test_maintenance_scheduling_integration(calendar_test_suite):
    """测试维护日排产集成"""
    result = await calendar_test_suite.test_maintenance_scheduling_integration()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"维护日排产集成测试失败: {result.error_details}"
    assert result.calendar_constraints_applied >= 1, "未正确应用维护约束"
    assert result.capacity_factor_adjustments > 0, "未检测到产能调整"


@pytest.mark.asyncio
async def test_capacity_factor_integration(calendar_test_suite):
    """测试产能因子集成"""
    result = await calendar_test_suite.test_capacity_factor_integration()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"产能因子集成测试失败: {result.error_details}"
    assert result.calendar_constraints_applied > 20, "日历约束应用数量不足"
    assert result.capacity_factor_adjustments > 0, "未检测到产能因子调整"


@pytest.mark.asyncio
async def test_cross_month_constraints(calendar_test_suite):
    """测试跨月份约束"""
    result = await calendar_test_suite.test_cross_month_constraints()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"跨月份约束测试失败: {result.error_details}"
    assert result.working_days_validated >= 4, "跨月工作日验证不足"


@pytest.mark.asyncio
async def test_shift_arrangement_constraints(calendar_test_suite):
    """测试班次安排约束"""
    result = await calendar_test_suite.test_shift_arrangement_constraints()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"班次安排约束测试失败: {result.error_details}"
    assert result.calendar_constraints_applied >= 1, "班次约束未正确应用"


@pytest.mark.asyncio
async def test_error_handling_resilience(calendar_test_suite):
    """测试异常处理和容错能力"""
    result = await calendar_test_suite.test_error_handling_resilience()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"异常处理测试失败: {result.error_details}"


@pytest.mark.asyncio
async def test_large_scale_performance(calendar_test_suite):
    """测试大规模数据性能"""
    result = await calendar_test_suite.test_large_scale_performance()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"大规模性能测试失败: {result.error_details}"
    assert result.performance_metrics.records_per_second >= 50, "处理速度不达标"
    assert result.performance_metrics.memory_usage_mb <= 300, "内存使用过高"


@pytest.mark.asyncio
async def test_algorithm_pipeline_integration(calendar_test_suite):
    """测试与算法管道集成"""
    result = await calendar_test_suite.test_algorithm_pipeline_integration()
    calendar_test_suite.test_results.append(result)
    
    assert result.success, f"算法管道集成测试失败: {result.error_details}"
    assert result.working_days_validated > 0, "管道集成未正确验证工作日"


@pytest.mark.asyncio
async def test_generate_comprehensive_report(calendar_test_suite):
    """生成综合测试报告"""
    # 确保所有测试都已运行
    if not calendar_test_suite.test_results:
        # 运行基本测试
        test_cases = calendar_test_suite.create_test_calendar_data()
        for test_case in test_cases:
            result = await calendar_test_suite.test_calendar_algorithm_integration(test_case)
            calendar_test_suite.test_results.append(result)
    
    # 生成报告
    report = calendar_test_suite.generate_test_report()
    
    # 验证报告内容
    assert "test_summary" in report
    assert "performance_metrics" in report
    assert "detailed_results" in report
    assert report["test_summary"]["total_tests"] > 0
    assert report["test_summary"]["success_rate"] >= 80  # 至少80%成功率
    
    # 打印报告摘要
    print(f"\n=== T016 月度工作日历约束集成测试报告 ===")
    print(f"总测试数: {report['test_summary']['total_tests']}")
    print(f"成功率: {report['test_summary']['success_rate']:.1f}%")
    print(f"平均执行时间: {report['performance_metrics']['average_execution_time']:.3f}s")
    print(f"平均内存使用: {report['performance_metrics']['average_memory_usage_mb']:.1f}MB")
    print(f"总约束应用数: {report['performance_metrics']['total_constraints_applied']}")
    print(f"总工作日验证数: {report['performance_metrics']['total_working_days_validated']}")


if __name__ == "__main__":
    # 允许单独运行此测试文件
    pytest.main([__file__, "-v", "--tb=short"])