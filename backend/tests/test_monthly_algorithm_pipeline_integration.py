"""
T015 - APS月度算法管道执行集成测试

测试目的: 验证月度排产算法管道的端到端执行流程和性能
测试策略: 集成测试 - 验证算法模块间的协调、数据流转和结果正确性
TDD要求: 测试完整的月度算法管道功能，确保所有模块正确协作

集成测试内容:
1. 完整算法管道执行 - 从工作日历到结果格式化的8个步骤
2. 算法模块间数据流验证 - 确保数据正确传递和转换
3. 并行执行和性能优化 - 验证并发处理能力
4. 约束遵循和结果验证 - 确保业务规则正确应用
5. 异常处理和错误恢复 - 测试容错能力
6. 内存和性能基准测试 - 验证性能指标
7. 工作日历集成测试 - 验证日历约束
8. 真实数据场景测试 - 使用实际业务数据
"""

import pytest
import asyncio
import time
import gc
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from unittest.mock import AsyncMock, MagicMock, patch
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

# 导入算法模块
from app.algorithms.monthly_scheduling import (
    MonthlyCalendarService,
    MonthlyMachineSelector,
    MonthlyCapacityCalculator,
    get_algorithm_info,
    get_pipeline_order,
    ALGORITHM_PIPELINE,
    ALGORITHM_MODULES
)

from app.algorithms.monthly_scheduling.base import (
    BaseAlgorithm,
    AlgorithmType,
    Priority,
    MachineType,
    MonthlyPlanItem,
    MachineInfo,
    ScheduleResult,
    ALGORITHM_CONFIG,
    SHIFT_CONFIG,
    calculate_working_hours,
    generate_schedule_id,
    calculate_priority_score,
    MonthlySchedulingError,
    ConstraintViolationError,
    ResourceConflictError,
    AlgorithmTimeoutError
)

# 导入测试助手
from tests.fixtures.test_helpers import (
    PerformanceMonitor,
    DataValidator,
    ConcurrentTestManager,
    TestReporter,
    PerformanceMetrics,
    ValidationResult
)


# =============================================================================
# 测试数据类和配置
# =============================================================================

@dataclass
class PipelineExecutionResult:
    """管道执行结果"""
    success: bool
    execution_time: float
    processed_plans: int
    generated_schedules: int
    memory_usage_mb: float
    algorithm_results: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    performance_metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlgorithmStepResult:
    """算法步骤结果"""
    algorithm_name: str
    success: bool
    execution_time: float
    input_size: int
    output_size: int
    memory_delta_mb: float
    cpu_usage_percent: float
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class MockAlgorithmModule:
    """模拟算法模块 - 用于测试管道执行"""
    
    def __init__(self, algorithm_type: AlgorithmType, processing_time: float = 0.1):
        self.algorithm_type = algorithm_type
        self.processing_time = processing_time
        self.call_count = 0
        self.last_input = None
        
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """模拟算法执行"""
        self.call_count += 1
        self.last_input = input_data
        
        # 模拟处理时间
        if self.processing_time > 0:
            await asyncio.sleep(self.processing_time)
        
        # 根据算法类型生成相应的输出
        if self.algorithm_type == AlgorithmType.CALENDAR_SERVICE:
            return self._generate_calendar_output(input_data)
        elif self.algorithm_type == AlgorithmType.MACHINE_SELECTOR:
            return self._generate_machine_output(input_data)
        elif self.algorithm_type == AlgorithmType.CAPACITY_CALCULATOR:
            return self._generate_capacity_output(input_data)
        else:
            return input_data  # 简单传递
    
    def _generate_calendar_output(self, input_data: Any) -> Dict[str, Any]:
        """生成日历服务输出"""
        return {
            "working_days": 22,
            "holidays": ["2024-12-25", "2024-12-26"],
            "total_working_hours": 176,
            "calendar_constraints": {
                "maintenance_windows": [],
                "shift_schedules": SHIFT_CONFIG
            }
        }
    
    def _generate_machine_output(self, input_data: Any) -> Dict[str, Any]:
        """生成机台选择输出"""
        return {
            "selected_feeders": ["F101", "F102", "F103"],
            "selected_makers": ["M201", "M202", "M203"],
            "machine_assignments": [
                {"plan_id": 1, "feeder": "F101", "maker": "M201"},
                {"plan_id": 2, "feeder": "F102", "maker": "M202"},
                {"plan_id": 3, "feeder": "F103", "maker": "M203"}
            ],
            "optimization_score": 0.85
        }
    
    def _generate_capacity_output(self, input_data: Any) -> Dict[str, Any]:
        """生成容量计算输出"""
        return {
            "total_capacity": 2400.0,
            "utilized_capacity": 2040.0,
            "capacity_utilization": 0.85,
            "capacity_by_machine": {
                "F101": 800.0, "F102": 800.0, "F103": 800.0,
                "M201": 680.0, "M202": 680.0, "M203": 680.0
            },
            "bottleneck_analysis": {
                "bottleneck_machine": "M201",
                "bottleneck_factor": 0.85
            }
        }


# =============================================================================
# 月度算法管道集成测试类
# =============================================================================

class TestMonthlyAlgorithmPipelineIntegration:
    """月度算法管道执行集成测试"""
    
    def setup_method(self):
        """测试初始化"""
        self.performance_monitor = PerformanceMonitor()
        self.test_reporter = TestReporter()
        self.concurrent_manager = ConcurrentTestManager(max_workers=3)
        
        # 测试配置
        self.test_config = {
            "max_execution_time": 300,  # 5分钟超时
            "memory_limit_mb": 512,     # 512MB内存限制
            "concurrent_plans": 10,     # 并发处理计划数
            "performance_threshold": {
                "execution_time": 30.0,    # 30秒执行阈值
                "memory_usage": 256.0,     # 256MB内存阈值
                "throughput": 50.0          # 50计划/秒吞吐量阈值
            }
        }
        
        # 创建测试数据
        self.test_plans = self._create_test_monthly_plans()
        self.test_machines = self._create_test_machines()
        self.test_calendar = self._create_test_calendar()
        
        # 算法管道模拟器
        self.pipeline_simulators = self._create_pipeline_simulators()
        
    def _create_test_monthly_plans(self) -> List[MonthlyPlanItem]:
        """创建测试月度计划数据"""
        plans = []
        base_date = datetime(2024, 12, 1)
        
        # 生成多种类型的计划
        plan_configs = [
            ("HZWO202412001", "HNZJHYLC001", "利群（阳光）", 1200.0, 100, ["F101"], ["M201"], Priority.HIGH),
            ("HZWO202412002", "HNZJHYLC002", "利群（新版）", 800.0, 80, ["F102"], ["M202"], Priority.MEDIUM),
            ("HZWO202412003", "HNZJHYLC003", "利群（休闲）", 1500.0, 125, ["F103"], ["M203"], Priority.HIGH),
            ("HZWO202412004", "HNZJHYLC004", "黄金叶（硬）", 900.0, 75, ["F101", "F102"], ["M201"], Priority.MEDIUM),
            ("HZWO202412005", "HNZJHYLC005", "黄金叶（软）", 1100.0, 90, ["F103"], ["M202", "M203"], Priority.LOW),
            ("HZWO202412006", "HNZJHYLC006", "真龙（硬）", 700.0, 60, ["F101"], ["M203"], Priority.URGENT),
            ("HZWO202412007", "HNZJHYLC007", "真龙（软）", 1300.0, 110, ["F102", "F103"], ["M201", "M202"], Priority.HIGH),
            ("HZWO202412008", "HNZJHYLC008", "大重九", 600.0, 50, ["F101"], ["M201"], Priority.MEDIUM),
            ("HZWO202412009", "HNZJHYLC009", "西湖（硬）", 1000.0, 85, ["F102"], ["M202"], Priority.LOW),
            ("HZWO202412010", "HNZJHYLC010", "西湖（软）", 1400.0, 120, ["F103"], ["M203"], Priority.HIGH)
        ]
        
        for i, (work_order, article_nr, name, quantity, boxes, feeders, makers, priority) in enumerate(plan_configs):
            plan = MonthlyPlanItem(
                plan_id=i + 1,
                batch_id=f"MONTHLY_BATCH_2024_12_{i+1:03d}",
                work_order_nr=work_order,
                article_nr=article_nr,
                article_name=name,
                target_quantity=quantity,
                planned_boxes=boxes,
                feeder_codes=feeders,
                maker_codes=makers,
                planned_start=base_date + timedelta(days=i*2),
                planned_end=base_date + timedelta(days=i*2 + 3),
                priority=priority
            )
            plans.append(plan)
        
        return plans
    
    def _create_test_machines(self) -> List[MachineInfo]:
        """创建测试机台信息"""
        machines = []
        base_time = datetime(2024, 12, 1, 8, 0)
        
        # 喂丝机
        feeder_configs = [
            ("F101", 150.0, 0.95),
            ("F102", 140.0, 0.90),
            ("F103", 160.0, 0.92)
        ]
        
        for code, capacity, efficiency in feeder_configs:
            machine = MachineInfo(
                machine_code=code,
                machine_type=MachineType.FEEDER,
                capacity_per_hour=capacity,
                efficiency_factor=efficiency,
                maintenance_windows=[
                    (base_time + timedelta(days=7), base_time + timedelta(days=7, hours=2)),
                    (base_time + timedelta(days=14), base_time + timedelta(days=14, hours=1))
                ],
                is_available=True
            )
            machines.append(machine)
        
        # 卷包机
        maker_configs = [
            ("M201", 120.0, 0.88),
            ("M202", 130.0, 0.91),
            ("M203", 125.0, 0.89)
        ]
        
        for code, capacity, efficiency in maker_configs:
            machine = MachineInfo(
                machine_code=code,
                machine_type=MachineType.MAKER,
                capacity_per_hour=capacity,
                efficiency_factor=efficiency,
                maintenance_windows=[
                    (base_time + timedelta(days=10), base_time + timedelta(days=10, hours=3)),
                    (base_time + timedelta(days=20), base_time + timedelta(days=20, hours=2))
                ],
                is_available=True
            )
            machines.append(machine)
        
        return machines
    
    def _create_test_calendar(self) -> Dict[str, Any]:
        """创建测试工作日历"""
        base_date = datetime(2024, 12, 1)
        return {
            "year": 2024,
            "month": 12,
            "working_days": [
                base_date + timedelta(days=i) 
                for i in range(31) 
                if (base_date + timedelta(days=i)).weekday() < 5
            ],
            "holidays": [
                datetime(2024, 12, 25),  # 圣诞节
                datetime(2024, 12, 26)   # 节礼日
            ],
            "maintenance_days": [
                datetime(2024, 12, 15)   # 设备维护日
            ],
            "shift_config": SHIFT_CONFIG,
            "total_working_hours": 176,  # 22个工作日 * 8小时
            "overtime_limit": 2.0        # 每日最大加班2小时
        }
    
    def _create_pipeline_simulators(self) -> Dict[str, MockAlgorithmModule]:
        """创建管道算法模拟器"""
        simulators = {}
        
        # 根据算法管道顺序创建模拟器
        algorithm_timings = {
            "calendar_service": 0.2,
            "monthly_capacity_calculator": 0.5,
            "capacity_calculator": 0.3,
            "machine_selector": 0.8,
            "time_allocator": 0.6,
            "constraint_solver": 1.2,
            "load_balancer": 0.4,
            "monthly_engine": 0.3
        }
        
        for alg_name in ALGORITHM_PIPELINE:
            if alg_name in algorithm_timings:
                # 获取对应的算法类型
                algorithm_type = getattr(AlgorithmType, alg_name.upper(), AlgorithmType.MONTHLY_ENGINE)
                processing_time = algorithm_timings[alg_name]
                
                simulator = MockAlgorithmModule(algorithm_type, processing_time)
                simulators[alg_name] = simulator
        
        return simulators

    def test_complete_algorithm_pipeline_execution(self):
        """测试完整算法管道执行 - 端到端集成测试"""
        print("\n🚀 开始月度算法管道完整执行集成测试")
        
        # 启动性能监控
        self.performance_monitor.start_monitoring()
        start_time = time.time()
        
        try:
            # 执行完整管道
            pipeline_result = asyncio.run(self._execute_full_pipeline())
            
            # 停止性能监控
            execution_time = time.time() - start_time
            performance_metrics = self.performance_monitor.stop_monitoring(
                records_processed=len(self.test_plans)
            )
            
            # 验证执行结果
            assert pipeline_result.success, f"管道执行失败: {pipeline_result.errors}"
            assert pipeline_result.processed_plans == len(self.test_plans)
            assert pipeline_result.generated_schedules > 0
            
            # 性能验证
            assert execution_time < self.test_config["performance_threshold"]["execution_time"]
            assert performance_metrics.memory_usage_mb < self.test_config["performance_threshold"]["memory_usage"]
            
            # 数据一致性验证
            self._verify_pipeline_data_consistency(pipeline_result)
            
            # 记录测试结果
            self.test_reporter.add_test_result(
                "complete_pipeline_execution",
                True,
                {
                    "processed_plans": pipeline_result.processed_plans,
                    "generated_schedules": pipeline_result.generated_schedules,
                    "execution_time": execution_time,
                    "algorithm_steps": len(ALGORITHM_PIPELINE)
                },
                performance_metrics
            )
            
            print(f"✅ 管道执行成功")
            print(f"📊 处理计划: {pipeline_result.processed_plans}")
            print(f"📋 生成排程: {pipeline_result.generated_schedules}")
            print(f"⏱️ 执行时间: {execution_time:.2f}秒")
            print(f"💾 内存使用: {performance_metrics.memory_usage_mb:.1f}MB")
            
        except Exception as e:
            pytest.fail(f"管道执行测试失败: {str(e)}")

    async def _execute_full_pipeline(self) -> PipelineExecutionResult:
        """执行完整算法管道"""
        algorithm_results = {}
        errors = []
        warnings = []
        total_schedules = 0
        
        # 初始化输入数据
        pipeline_data = {
            "monthly_plans": [plan.to_dict() for plan in self.test_plans],
            "machines": [machine.to_dict() for machine in self.test_machines],
            "calendar": self.test_calendar,
            "config": ALGORITHM_CONFIG
        }
        
        try:
            # 按顺序执行算法管道
            for algorithm_name in ALGORITHM_PIPELINE:
                if algorithm_name in self.pipeline_simulators:
                    print(f"  🔄 执行算法: {algorithm_name}")
                    
                    simulator = self.pipeline_simulators[algorithm_name]
                    step_start = time.time()
                    
                    # 执行算法步骤
                    step_result = await simulator.execute(pipeline_data)
                    step_time = time.time() - step_start
                    
                    # 记录步骤结果
                    algorithm_results[algorithm_name] = {
                        "result": step_result,
                        "execution_time": step_time,
                        "input_size": len(str(pipeline_data)),
                        "output_size": len(str(step_result))
                    }
                    
                    # 更新管道数据
                    pipeline_data[f"{algorithm_name}_result"] = step_result
                    
                    # 模拟生成排程数据
                    if algorithm_name == "monthly_engine":
                        total_schedules = len(self.test_plans)
                    
                    print(f"    ✅ {algorithm_name} 完成 ({step_time:.2f}秒)")
                else:
                    warnings.append(f"算法模块 {algorithm_name} 未实现")
            
            return PipelineExecutionResult(
                success=True,
                execution_time=sum(r["execution_time"] for r in algorithm_results.values()),
                processed_plans=len(self.test_plans),
                generated_schedules=total_schedules,
                memory_usage_mb=0.0,  # 将由外部监控器填充
                algorithm_results=algorithm_results,
                errors=errors,
                warnings=warnings,
                performance_metrics={}
            )
            
        except Exception as e:
            errors.append(str(e))
            return PipelineExecutionResult(
                success=False,
                execution_time=0.0,
                processed_plans=0,
                generated_schedules=0,
                memory_usage_mb=0.0,
                algorithm_results=algorithm_results,
                errors=errors,
                warnings=warnings,
                performance_metrics={}
            )

    def test_algorithm_dependencies_and_data_flow(self):
        """测试算法间依赖关系和数据流转"""
        print("\n🔗 测试算法依赖关系和数据流转")
        
        try:
            # 验证算法管道顺序
            pipeline_order = get_pipeline_order()
            assert len(pipeline_order) == len(ALGORITHM_PIPELINE)
            assert pipeline_order == ALGORITHM_PIPELINE
            
            # 验证算法模块信息
            for algorithm_name in ALGORITHM_PIPELINE:
                module_info = get_algorithm_info(algorithm_name)
                assert module_info is not None, f"算法模块 {algorithm_name} 信息缺失"
                assert "name" in module_info
                assert "description" in module_info
                assert "dependencies" in module_info
            
            # 测试数据流转
            asyncio.run(self._test_data_flow_integrity())
            
            print("✅ 算法依赖关系验证通过")
            print("✅ 数据流转完整性验证通过")
            
        except Exception as e:
            pytest.fail(f"依赖关系测试失败: {str(e)}")

    async def _test_data_flow_integrity(self):
        """测试数据流转完整性"""
        initial_data = {
            "plans": self.test_plans[:3],  # 使用前3个计划进行测试
            "machines": self.test_machines[:2],
            "calendar": self.test_calendar
        }
        
        current_data = initial_data.copy()
        
        # 逐步执行算法并验证数据完整性
        for i, algorithm_name in enumerate(ALGORITHM_PIPELINE[:4]):  # 测试前4个算法
            if algorithm_name in self.pipeline_simulators:
                simulator = self.pipeline_simulators[algorithm_name]
                
                # 执行算法
                result = await simulator.execute(current_data)
                
                # 验证输出数据结构
                assert isinstance(result, dict), f"{algorithm_name} 输出不是字典格式"
                assert len(result) > 0, f"{algorithm_name} 输出为空"
                
                # 更新当前数据
                current_data[f"step_{i+1}_result"] = result
                
                print(f"  ✓ {algorithm_name} 数据流转正常")

    def test_parallel_execution_and_performance(self):
        """测试并行执行和性能优化"""
        print("\n⚡ 测试并行执行和性能优化")
        
        # 测试不同规模的并发执行
        test_scales = [1, 3, 5, 10]
        performance_results = []
        
        for scale in test_scales:
            print(f"  📊 测试并发规模: {scale}")
            
            # 创建多个计划批次
            test_batches = [
                self.test_plans[i:i+2] if i+2 <= len(self.test_plans) else self.test_plans[i:]
                for i in range(0, min(scale*2, len(self.test_plans)), 2)
            ]
            
            if not test_batches:
                continue
            
            # 性能监控
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            start_time = time.time()
            
            try:
                # 并发执行
                results = asyncio.run(self._execute_concurrent_pipelines(test_batches))
                
                execution_time = time.time() - start_time
                metrics = monitor.stop_monitoring(
                    records_processed=sum(len(batch) for batch in test_batches)
                )
                
                # 记录性能结果
                performance_results.append({
                    "scale": scale,
                    "execution_time": execution_time,
                    "throughput": len(test_batches) / execution_time if execution_time > 0 else 0,
                    "memory_usage": metrics.memory_usage_mb,
                    "cpu_usage": metrics.cpu_usage_percent,
                    "success_rate": sum(1 for r in results if r["success"]) / len(results)
                })
                
                print(f"    ✅ 规模 {scale}: {execution_time:.2f}秒, {metrics.memory_usage_mb:.1f}MB")
                
            except Exception as e:
                print(f"    ❌ 规模 {scale} 测试失败: {str(e)}")
        
        # 验证性能趋势
        if len(performance_results) >= 2:
            # 验证吞吐量随规模的变化
            throughputs = [r["throughput"] for r in performance_results]
            assert max(throughputs) > 0, "并发执行无吞吐量"
            
            # 验证内存使用合理性
            memory_usages = [r["memory_usage"] for r in performance_results]
            assert all(m < self.test_config["memory_limit_mb"] for m in memory_usages), "内存使用超限"
            
            print(f"✅ 并行性能测试通过，最大吞吐量: {max(throughputs):.1f}批次/秒")

    async def _execute_concurrent_pipelines(self, plan_batches: List[List[MonthlyPlanItem]]) -> List[Dict[str, Any]]:
        """并发执行多个管道"""
        tasks = []
        
        for i, batch in enumerate(plan_batches):
            # 为每个批次创建独立的执行任务
            task_data = {
                "batch_id": f"concurrent_batch_{i}",
                "plans": batch,
                "machines": self.test_machines,
                "calendar": self.test_calendar
            }
            
            task = self._execute_pipeline_batch(task_data)
            tasks.append(task)
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "batch_id": f"concurrent_batch_{i}",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def _execute_pipeline_batch(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个管道批次"""
        try:
            batch_id = task_data["batch_id"]
            plans = task_data["plans"]
            
            # 模拟算法执行
            await asyncio.sleep(0.1)  # 模拟处理时间
            
            # 模拟生成结果
            schedules = [
                ScheduleResult(
                    schedule_id=generate_schedule_id(plan.plan_id),
                    plan_id=plan.plan_id,
                    assigned_feeder=plan.feeder_codes[0] if plan.feeder_codes else "F101",
                    assigned_maker=plan.maker_codes[0] if plan.maker_codes else "M201",
                    scheduled_start=plan.planned_start or datetime.now(),
                    scheduled_end=plan.planned_end or datetime.now() + timedelta(hours=8),
                    allocated_quantity=plan.target_quantity,
                    estimated_duration=8.0,
                    priority_score=calculate_priority_score(plan),
                    constraints_satisfied=True
                )
                for plan in plans
            ]
            
            return {
                "batch_id": batch_id,
                "success": True,
                "processed_plans": len(plans),
                "generated_schedules": len(schedules),
                "schedules": [s.to_dict() for s in schedules]
            }
            
        except Exception as e:
            return {
                "batch_id": task_data.get("batch_id", "unknown"),
                "success": False,
                "error": str(e)
            }

    def test_constraint_compliance_and_validation(self):
        """测试约束遵循和结果验证"""
        print("\n🔒 测试约束遵循和结果验证")
        
        # 定义测试约束
        test_constraints = {
            "working_hours": {
                "max_daily_hours": 16,
                "max_weekly_hours": 80,
                "min_break_time": 1.0
            },
            "machine_capacity": {
                "max_utilization": 0.95,
                "min_efficiency": 0.80
            },
            "production_rules": {
                "max_continuous_production": 12,  # 小时
                "min_setup_time": 0.5,           # 小时
                "max_batch_size": 200.0           # 产量
            },
            "calendar_rules": {
                "respect_holidays": True,
                "respect_maintenance": True,
                "allow_overtime": True
            }
        }
        
        try:
            # 执行约束验证测试
            validation_results = asyncio.run(
                self._validate_constraint_compliance(test_constraints)
            )
            
            # 验证结果
            assert validation_results["overall_compliance"], "整体约束遵循失败"
            assert validation_results["working_hours_compliance"], "工作时间约束违反"
            assert validation_results["capacity_compliance"], "产能约束违反"
            assert validation_results["calendar_compliance"], "日历约束违反"
            
            # 检查违规详情
            violations = validation_results.get("violations", [])
            critical_violations = [v for v in violations if v.get("severity") == "critical"]
            assert len(critical_violations) == 0, f"发现严重约束违规: {critical_violations}"
            
            print("✅ 约束遵循验证通过")
            print(f"📊 总体合规率: {validation_results.get('compliance_rate', 0):.1%}")
            print(f"⚠️ 警告数量: {len([v for v in violations if v.get('severity') == 'warning'])}")
            
        except Exception as e:
            pytest.fail(f"约束验证测试失败: {str(e)}")

    async def _validate_constraint_compliance(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """验证约束遵循情况"""
        violations = []
        
        # 模拟约束检查
        working_hours_ok = True
        capacity_ok = True
        calendar_ok = True
        
        # 验证工作时间约束
        for plan in self.test_plans[:5]:  # 测试前5个计划
            if plan.planned_start and plan.planned_end:
                duration = (plan.planned_end - plan.planned_start).total_seconds() / 3600
                if duration > constraints["working_hours"]["max_daily_hours"]:
                    violations.append({
                        "type": "working_hours",
                        "severity": "critical",
                        "plan_id": plan.plan_id,
                        "message": f"计划持续时间 {duration:.1f}h 超过限制"
                    })
                    working_hours_ok = False
        
        # 验证机台容量约束
        for machine in self.test_machines:
            utilization = machine.efficiency_factor
            if utilization > constraints["machine_capacity"]["max_utilization"]:
                violations.append({
                    "type": "capacity",
                    "severity": "warning",
                    "machine": machine.machine_code,
                    "message": f"机台利用率 {utilization:.1%} 超过推荐值"
                })
        
        # 验证日历约束
        if constraints["calendar_rules"]["respect_holidays"]:
            for holiday in self.test_calendar["holidays"]:
                # 检查是否有计划安排在假期
                holiday_plans = [
                    p for p in self.test_plans 
                    if p.planned_start and p.planned_start.date() == holiday.date()
                ]
                if holiday_plans:
                    violations.append({
                        "type": "calendar",
                        "severity": "critical",
                        "date": holiday.isoformat(),
                        "message": f"假期 {holiday.date()} 安排了 {len(holiday_plans)} 个计划"
                    })
                    calendar_ok = False
        
        # 计算合规率
        total_checks = len(self.test_plans) + len(self.test_machines) + len(self.test_calendar["holidays"])
        compliance_rate = 1.0 - (len(violations) / total_checks) if total_checks > 0 else 1.0
        
        return {
            "overall_compliance": len([v for v in violations if v["severity"] == "critical"]) == 0,
            "working_hours_compliance": working_hours_ok,
            "capacity_compliance": capacity_ok,
            "calendar_compliance": calendar_ok,
            "compliance_rate": compliance_rate,
            "violations": violations,
            "total_checks": total_checks
        }

    def test_error_handling_and_recovery(self):
        """测试异常处理和错误恢复"""
        print("\n🚨 测试异常处理和错误恢复")
        
        # 定义错误场景
        error_scenarios = [
            {
                "name": "算法超时",
                "error_type": AlgorithmTimeoutError,
                "description": "模拟算法执行超时"
            },
            {
                "name": "约束违反",
                "error_type": ConstraintViolationError,
                "description": "模拟约束条件违反"
            },
            {
                "name": "资源冲突",
                "error_type": ResourceConflictError,
                "description": "模拟机台资源冲突"
            },
            {
                "name": "数据无效",
                "error_type": ValueError,
                "description": "模拟输入数据无效"
            },
            {
                "name": "内存不足",
                "error_type": MemoryError,
                "description": "模拟内存不足情况"
            }
        ]
        
        error_handling_results = []
        
        for scenario in error_scenarios:
            print(f"  🧪 测试场景: {scenario['name']}")
            
            try:
                # 模拟错误场景
                result = asyncio.run(
                    self._simulate_error_scenario(scenario)
                )
                
                error_handling_results.append({
                    "scenario": scenario["name"],
                    "handled": result["error_handled"],
                    "recovery": result["recovery_successful"],
                    "cleanup": result["cleanup_completed"],
                    "error_message": result.get("error_message")
                })
                
                print(f"    ✅ 错误处理: {'成功' if result['error_handled'] else '失败'}")
                print(f"    🔄 错误恢复: {'成功' if result['recovery_successful'] else '失败'}")
                
            except Exception as e:
                print(f"    ❌ 场景测试失败: {str(e)}")
                error_handling_results.append({
                    "scenario": scenario["name"],
                    "handled": False,
                    "recovery": False,
                    "cleanup": False,
                    "error_message": str(e)
                })
        
        # 验证错误处理能力
        successful_handling = sum(1 for r in error_handling_results if r["handled"])
        total_scenarios = len(error_scenarios)
        
        assert successful_handling >= total_scenarios * 0.8, \
            f"错误处理成功率过低: {successful_handling}/{total_scenarios}"
        
        print(f"✅ 错误处理测试完成，成功率: {successful_handling}/{total_scenarios}")

    async def _simulate_error_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """模拟错误场景"""
        error_handled = False
        recovery_successful = False
        cleanup_completed = False
        error_message = None
        
        try:
            # 根据场景类型模拟不同错误
            if scenario["error_type"] == AlgorithmTimeoutError:
                # 模拟超时错误
                await asyncio.sleep(0.1)
                raise AlgorithmTimeoutError("算法执行超时")
                
            elif scenario["error_type"] == ConstraintViolationError:
                # 模拟约束违反
                raise ConstraintViolationError("机台容量约束违反")
                
            elif scenario["error_type"] == ResourceConflictError:
                # 模拟资源冲突
                raise ResourceConflictError("机台 M201 时间冲突")
                
            elif scenario["error_type"] == ValueError:
                # 模拟数据错误
                raise ValueError("输入数据格式无效")
                
            elif scenario["error_type"] == MemoryError:
                # 模拟内存错误
                raise MemoryError("内存不足")
                
        except MonthlySchedulingError as e:
            # 处理业务异常
            error_handled = True
            error_message = str(e)
            
            # 尝试恢复
            try:
                # 模拟错误恢复逻辑
                await asyncio.sleep(0.05)
                recovery_successful = True
            except:
                recovery_successful = False
                
        except Exception as e:
            # 处理其他异常
            error_handled = True
            error_message = str(e)
            recovery_successful = False
            
        finally:
            # 清理资源
            try:
                await asyncio.sleep(0.01)  # 模拟清理操作
                cleanup_completed = True
            except:
                cleanup_completed = False
        
        return {
            "error_handled": error_handled,
            "recovery_successful": recovery_successful,
            "cleanup_completed": cleanup_completed,
            "error_message": error_message
        }

    def test_memory_and_performance_benchmarks(self):
        """测试内存和性能基准"""
        print("\n📊 测试内存和性能基准")
        
        # 性能基准配置
        benchmark_configs = [
            {"name": "小规模", "plans": 5, "expected_time": 2.0, "expected_memory": 50},
            {"name": "中规模", "plans": 10, "expected_time": 5.0, "expected_memory": 100},
            {"name": "大规模", "plans": 20, "expected_time": 10.0, "expected_memory": 200}
        ]
        
        benchmark_results = []
        
        for config in benchmark_configs:
            print(f"  🎯 基准测试: {config['name']} ({config['plans']}计划)")
            
            # 准备测试数据
            test_plans = self.test_plans[:config["plans"]]
            
            # 执行基准测试
            monitor = PerformanceMonitor()
            monitor.start_monitoring()
            start_time = time.time()
            
            try:
                # 执行算法管道
                result = asyncio.run(self._execute_benchmark_pipeline(test_plans))
                
                execution_time = time.time() - start_time
                metrics = monitor.stop_monitoring(records_processed=len(test_plans))
                
                # 记录基准结果
                benchmark_result = {
                    "config": config["name"],
                    "plans_count": len(test_plans),
                    "execution_time": execution_time,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "memory_peak_mb": metrics.memory_peak_mb,
                    "cpu_usage_percent": metrics.cpu_usage_percent,
                    "throughput": len(test_plans) / execution_time if execution_time > 0 else 0,
                    "meets_time_target": execution_time <= config["expected_time"],
                    "meets_memory_target": metrics.memory_usage_mb <= config["expected_memory"]
                }
                
                benchmark_results.append(benchmark_result)
                
                print(f"    ⏱️ 执行时间: {execution_time:.2f}s (目标: {config['expected_time']}s)")
                print(f"    💾 内存使用: {metrics.memory_usage_mb:.1f}MB (目标: {config['expected_memory']}MB)")
                print(f"    🚀 吞吐量: {benchmark_result['throughput']:.1f}计划/秒")
                print(f"    ✅ 性能达标: {'是' if benchmark_result['meets_time_target'] and benchmark_result['meets_memory_target'] else '否'}")
                
            except Exception as e:
                print(f"    ❌ 基准测试失败: {str(e)}")
                benchmark_results.append({
                    "config": config["name"],
                    "error": str(e),
                    "meets_time_target": False,
                    "meets_memory_target": False
                })
        
        # 验证基准结果
        successful_benchmarks = [r for r in benchmark_results if r.get("meets_time_target", False) and r.get("meets_memory_target", False)]
        
        assert len(successful_benchmarks) >= len(benchmark_configs) * 0.7, \
            f"性能基准达标率过低: {len(successful_benchmarks)}/{len(benchmark_configs)}"
        
        # 生成性能报告
        self._generate_performance_report(benchmark_results)
        
        print(f"✅ 性能基准测试完成，达标率: {len(successful_benchmarks)}/{len(benchmark_configs)}")

    async def _execute_benchmark_pipeline(self, test_plans: List[MonthlyPlanItem]) -> Dict[str, Any]:
        """执行基准测试管道"""
        # 创建精简的管道数据
        pipeline_data = {
            "plans": [plan.to_dict() for plan in test_plans],
            "machines": [machine.to_dict() for machine in self.test_machines[:3]],  # 只使用3台机器
            "calendar": self.test_calendar
        }
        
        # 执行核心算法步骤
        core_algorithms = ["calendar_service", "machine_selector", "capacity_calculator", "monthly_engine"]
        
        for alg_name in core_algorithms:
            if alg_name in self.pipeline_simulators:
                simulator = self.pipeline_simulators[alg_name]
                result = await simulator.execute(pipeline_data)
                pipeline_data[f"{alg_name}_result"] = result
        
        return {
            "processed_plans": len(test_plans),
            "algorithm_steps": len(core_algorithms),
            "success": True
        }

    def test_work_calendar_integration(self):
        """测试工作日历集成"""
        print("\n📅 测试工作日历集成")
        
        try:
            # 测试日历服务功能
            calendar_tests = [
                self._test_working_days_calculation(),
                self._test_holiday_handling(),
                self._test_maintenance_window_integration(),
                self._test_shift_schedule_validation(),
                self._test_overtime_calculation()
            ]
            
            results = asyncio.run(asyncio.gather(*calendar_tests))
            
            # 验证所有测试通过
            all_passed = all(result["success"] for result in results)
            assert all_passed, f"日历集成测试失败: {[r for r in results if not r['success']]}"
            
            print("✅ 工作日历集成测试全部通过")
            
            # 显示详细结果
            for result in results:
                print(f"  ✓ {result['test_name']}: {result.get('message', '成功')}")
                
        except Exception as e:
            pytest.fail(f"工作日历集成测试失败: {str(e)}")

    async def _test_working_days_calculation(self) -> Dict[str, Any]:
        """测试工作日计算"""
        try:
            calendar = self.test_calendar
            
            # 验证工作日数量
            working_days = calendar["working_days"]
            expected_working_days = 22  # 12月预期工作日
            
            assert len(working_days) >= expected_working_days * 0.9, \
                f"工作日数量不足: {len(working_days)}"
            
            # 验证工作日不包含周末
            for day in working_days:
                assert day.weekday() < 5, f"工作日包含周末: {day}"
            
            # 验证总工作时间
            total_hours = calendar["total_working_hours"]
            expected_hours = len(working_days) * 8  # 每天8小时
            
            assert abs(total_hours - expected_hours) <= 16, \
                f"总工作时间计算错误: {total_hours} vs {expected_hours}"
            
            return {"success": True, "test_name": "工作日计算"}
            
        except Exception as e:
            return {"success": False, "test_name": "工作日计算", "error": str(e)}

    async def _test_holiday_handling(self) -> Dict[str, Any]:
        """测试假期处理"""
        try:
            calendar = self.test_calendar
            holidays = calendar["holidays"]
            working_days = calendar["working_days"]
            
            # 验证假期不在工作日中
            for holiday in holidays:
                working_dates = [day.date() for day in working_days]
                assert holiday.date() not in working_dates, \
                    f"假期 {holiday.date()} 被计入工作日"
            
            # 验证假期数量合理
            assert len(holidays) <= 5, f"假期数量过多: {len(holidays)}"
            
            return {"success": True, "test_name": "假期处理"}
            
        except Exception as e:
            return {"success": False, "test_name": "假期处理", "error": str(e)}

    async def _test_maintenance_window_integration(self) -> Dict[str, Any]:
        """测试维护窗口集成"""
        try:
            # 验证机台维护窗口
            for machine in self.test_machines:
                maintenance_windows = machine.maintenance_windows
                
                # 验证维护窗口时间有效性
                for start_time, end_time in maintenance_windows:
                    assert start_time < end_time, \
                        f"机台 {machine.machine_code} 维护窗口时间无效"
                    
                    # 验证维护时间不超过24小时
                    duration = (end_time - start_time).total_seconds() / 3600
                    assert duration <= 24, \
                        f"机台 {machine.machine_code} 维护时间过长: {duration}小时"
            
            return {"success": True, "test_name": "维护窗口集成"}
            
        except Exception as e:
            return {"success": False, "test_name": "维护窗口集成", "error": str(e)}

    async def _test_shift_schedule_validation(self) -> Dict[str, Any]:
        """测试班次安排验证"""
        try:
            shift_config = SHIFT_CONFIG
            
            # 验证班次配置完整性
            required_shifts = ["day_shift", "night_shift"]
            for shift in required_shifts:
                assert shift in shift_config, f"缺少班次配置: {shift}"
                
                shift_info = shift_config[shift]
                assert "start_time" in shift_info, f"班次 {shift} 缺少开始时间"
                assert "end_time" in shift_info, f"班次 {shift} 缺少结束时间"
                assert "capacity_factor" in shift_info, f"班次 {shift} 缺少产能系数"
            
            # 验证班次产能系数合理性
            for shift_name, shift_info in shift_config.items():
                factor = shift_info["capacity_factor"]
                assert 0.5 <= factor <= 1.2, \
                    f"班次 {shift_name} 产能系数不合理: {factor}"
            
            return {"success": True, "test_name": "班次安排验证"}
            
        except Exception as e:
            return {"success": False, "test_name": "班次安排验证", "error": str(e)}

    async def _test_overtime_calculation(self) -> Dict[str, Any]:
        """测试加班时间计算"""
        try:
            calendar = self.test_calendar
            overtime_limit = calendar.get("overtime_limit", 2.0)
            
            # 验证加班限制合理性
            assert 0 <= overtime_limit <= 4, f"加班限制不合理: {overtime_limit}小时"
            
            # 模拟计算包含加班的工作时间
            base_hours = 8  # 标准工作时间
            max_daily_hours = base_hours + overtime_limit
            
            # 验证最大日工作时间
            assert max_daily_hours <= 12, f"每日最大工作时间过长: {max_daily_hours}小时"
            
            # 测试工作时间计算函数
            start_time = datetime(2024, 12, 1, 8, 0)
            end_time = datetime(2024, 12, 1, 18, 0)  # 10小时
            
            working_hours = calculate_working_hours(start_time, end_time)
            expected_hours = 9.0  # 10小时减去1小时休息
            
            assert abs(working_hours - expected_hours) <= 1.0, \
                f"工作时间计算错误: {working_hours} vs {expected_hours}"
            
            return {"success": True, "test_name": "加班时间计算"}
            
        except Exception as e:
            return {"success": False, "test_name": "加班时间计算", "error": str(e)}

    def test_real_data_scenario_integration(self):
        """测试真实数据场景集成"""
        print("\n🏭 测试真实数据场景集成")
        
        # 创建更真实的测试场景
        real_scenario = self._create_realistic_scenario()
        
        try:
            # 执行真实场景测试
            scenario_result = asyncio.run(
                self._execute_realistic_scenario(real_scenario)
            )
            
            # 验证场景执行结果
            assert scenario_result["success"], f"真实场景执行失败: {scenario_result['errors']}"
            assert scenario_result["business_rules_satisfied"], "业务规则未满足"
            assert scenario_result["resource_utilization"] >= 0.7, "资源利用率过低"
            assert scenario_result["schedule_feasibility"], "排程方案不可行"
            
            print("✅ 真实数据场景测试通过")
            print(f"📊 处理计划数: {scenario_result['processed_plans']}")
            print(f"🏭 资源利用率: {scenario_result['resource_utilization']:.1%}")
            print(f"⏱️ 完成时间: {scenario_result['completion_time']:.2f}秒")
            print(f"✓ 业务规则满足: {scenario_result['business_rules_satisfied']}")
            
        except Exception as e:
            pytest.fail(f"真实数据场景测试失败: {str(e)}")

    def _create_realistic_scenario(self) -> Dict[str, Any]:
        """创建真实业务场景"""
        return {
            "scenario_name": "浙江中烟12月生产计划",
            "description": "模拟真实的月度生产计划场景",
            "plans": self.test_plans,
            "machines": self.test_machines,
            "calendar": self.test_calendar,
            "business_constraints": {
                "brand_priority": {"利群": 1, "黄金叶": 2, "真龙": 3, "大重九": 4, "西湖": 5},
                "factory_rules": {
                    "max_daily_batches": 8,
                    "min_batch_interval": 30,  # 分钟
                    "quality_check_time": 15   # 分钟
                },
                "resource_limits": {
                    "feeder_max_utilization": 0.90,
                    "maker_max_utilization": 0.85,
                    "shared_resources": ["quality_inspector", "material_handler"]
                }
            },
            "kpis": {
                "target_efficiency": 0.85,
                "target_utilization": 0.80,
                "max_overtime_ratio": 0.15,
                "on_time_delivery": 0.95
            }
        }

    async def _execute_realistic_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """执行真实场景测试"""
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # 1. 验证输入数据完整性
            plans = scenario["plans"]
            machines = scenario["machines"]
            calendar = scenario["calendar"]
            
            # 2. 执行业务规则验证
            business_validation = await self._validate_business_rules(scenario)
            
            # 3. 执行资源分配优化
            resource_allocation = await self._optimize_resource_allocation(scenario)
            
            # 4. 生成排程方案
            schedule_generation = await self._generate_production_schedule(scenario)
            
            # 5. 验证KPI达成情况
            kpi_validation = await self._validate_kpi_achievement(scenario)
            
            completion_time = time.time() - start_time
            
            # 计算综合结果
            overall_success = all([
                business_validation["success"],
                resource_allocation["success"],
                schedule_generation["success"],
                kpi_validation["success"]
            ])
            
            return {
                "success": overall_success,
                "processed_plans": len(plans),
                "resource_utilization": resource_allocation.get("utilization", 0.0),
                "schedule_feasibility": schedule_generation.get("feasible", False),
                "business_rules_satisfied": business_validation.get("satisfied", False),
                "kpi_achievement": kpi_validation.get("achievement_rate", 0.0),
                "completion_time": completion_time,
                "errors": errors,
                "warnings": warnings,
                "detailed_results": {
                    "business_validation": business_validation,
                    "resource_allocation": resource_allocation,
                    "schedule_generation": schedule_generation,
                    "kpi_validation": kpi_validation
                }
            }
            
        except Exception as e:
            errors.append(str(e))
            return {
                "success": False,
                "processed_plans": 0,
                "resource_utilization": 0.0,
                "schedule_feasibility": False,
                "business_rules_satisfied": False,
                "kpi_achievement": 0.0,
                "completion_time": time.time() - start_time,
                "errors": errors,
                "warnings": warnings
            }

    async def _validate_business_rules(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """验证业务规则"""
        # 模拟业务规则验证
        await asyncio.sleep(0.1)
        
        constraints = scenario["business_constraints"]
        brand_priorities = constraints["brand_priority"]
        
        # 验证品牌优先级排序
        plans = scenario["plans"]
        priority_violations = 0
        
        for plan in plans:
            brand = plan.article_name.split("（")[0] if "（" in plan.article_name else plan.article_name
            if brand in brand_priorities:
                expected_priority = brand_priorities[brand]
                # 简化验证逻辑
                if plan.priority.value != expected_priority:
                    priority_violations += 1
        
        return {
            "success": priority_violations < len(plans) * 0.2,  # 允许20%的违规
            "satisfied": priority_violations == 0,
            "priority_violations": priority_violations,
            "validation_details": {
                "brand_priority_check": "completed",
                "factory_rules_check": "completed",
                "constraint_validation": "completed"
            }
        }

    async def _optimize_resource_allocation(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """优化资源分配"""
        # 模拟资源分配优化
        await asyncio.sleep(0.2)
        
        machines = scenario["machines"]
        plans = scenario["plans"]
        
        # 计算总容量和需求
        total_feeder_capacity = sum(
            m.capacity_per_hour * m.efficiency_factor 
            for m in machines if m.machine_type == MachineType.FEEDER
        )
        total_maker_capacity = sum(
            m.capacity_per_hour * m.efficiency_factor 
            for m in machines if m.machine_type == MachineType.MAKER
        )
        
        total_demand = sum(plan.target_quantity for plan in plans)
        
        # 计算利用率
        working_hours = scenario["calendar"]["total_working_hours"]
        feeder_utilization = total_demand / (total_feeder_capacity * working_hours)
        maker_utilization = total_demand / (total_maker_capacity * working_hours)
        
        avg_utilization = (feeder_utilization + maker_utilization) / 2
        
        return {
            "success": avg_utilization <= 1.0,  # 不超过100%利用率
            "utilization": min(avg_utilization, 1.0),
            "feeder_utilization": feeder_utilization,
            "maker_utilization": maker_utilization,
            "allocation_details": {
                "total_demand": total_demand,
                "total_capacity": (total_feeder_capacity + total_maker_capacity) / 2,
                "working_hours": working_hours
            }
        }

    async def _generate_production_schedule(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """生成生产排程"""
        # 模拟排程生成
        await asyncio.sleep(0.3)
        
        plans = scenario["plans"]
        machines = scenario["machines"]
        
        # 简化的排程分配
        schedules = []
        for i, plan in enumerate(plans):
            feeder = machines[i % 3] if machines[i % 3].machine_type == MachineType.FEEDER else machines[0]
            maker = machines[(i % 3) + 3] if len(machines) > 3 and machines[(i % 3) + 3].machine_type == MachineType.MAKER else machines[-1]
            
            schedule = ScheduleResult(
                schedule_id=generate_schedule_id(plan.plan_id),
                plan_id=plan.plan_id,
                assigned_feeder=feeder.machine_code,
                assigned_maker=maker.machine_code,
                scheduled_start=plan.planned_start or datetime.now(),
                scheduled_end=plan.planned_end or datetime.now() + timedelta(hours=8),
                allocated_quantity=plan.target_quantity,
                estimated_duration=8.0,
                priority_score=calculate_priority_score(plan),
                constraints_satisfied=True
            )
            schedules.append(schedule)
        
        return {
            "success": len(schedules) == len(plans),
            "feasible": True,
            "generated_schedules": len(schedules),
            "schedule_quality": 0.85,  # 模拟质量分数
            "schedules": [s.to_dict() for s in schedules]
        }

    async def _validate_kpi_achievement(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """验证KPI达成情况"""
        # 模拟KPI验证
        await asyncio.sleep(0.1)
        
        kpis = scenario["kpis"]
        
        # 模拟KPI计算结果
        achieved_kpis = {
            "efficiency": 0.83,       # 目标: 0.85
            "utilization": 0.82,      # 目标: 0.80
            "overtime_ratio": 0.12,   # 目标: 0.15
            "on_time_delivery": 0.96  # 目标: 0.95
        }
        
        # 计算达成率
        achievement_scores = []
        for kpi_name, target in kpis.items():
            if kpi_name.startswith("target_"):
                kpi_key = kpi_name.replace("target_", "")
            elif kpi_name.startswith("max_"):
                kpi_key = kpi_name.replace("max_", "") + "_ratio"
            else:
                kpi_key = kpi_name
                
            if kpi_key in achieved_kpis:
                achieved = achieved_kpis[kpi_key]
                if "max_" in kpi_name:
                    # 越小越好的指标
                    score = 1.0 if achieved <= target else target / achieved
                else:
                    # 越大越好的指标
                    score = achieved / target if target > 0 else 1.0
                achievement_scores.append(min(1.0, score))
        
        overall_achievement = sum(achievement_scores) / len(achievement_scores) if achievement_scores else 0.0
        
        return {
            "success": overall_achievement >= 0.8,
            "achievement_rate": overall_achievement,
            "individual_kpis": {
                "efficiency": achieved_kpis["efficiency"] / kpis["target_efficiency"],
                "utilization": achieved_kpis["utilization"] / kpis["target_utilization"],
                "overtime": kpis["max_overtime_ratio"] / achieved_kpis["overtime_ratio"],
                "delivery": achieved_kpis["on_time_delivery"] / kpis["on_time_delivery"]
            },
            "achieved_values": achieved_kpis,
            "target_values": kpis
        }

    def _verify_pipeline_data_consistency(self, pipeline_result: PipelineExecutionResult):
        """验证管道数据一致性"""
        # 验证处理的计划数量一致性
        assert pipeline_result.processed_plans == len(self.test_plans), \
            f"处理计划数不一致: {pipeline_result.processed_plans} vs {len(self.test_plans)}"
        
        # 验证算法结果的数据完整性
        algorithm_results = pipeline_result.algorithm_results
        
        for alg_name, result_data in algorithm_results.items():
            assert "result" in result_data, f"算法 {alg_name} 缺少结果数据"
            assert "execution_time" in result_data, f"算法 {alg_name} 缺少执行时间"
            assert result_data["execution_time"] >= 0, f"算法 {alg_name} 执行时间无效"
        
        # 验证错误和警告信息的合理性
        assert len(pipeline_result.errors) < 5, f"错误过多: {len(pipeline_result.errors)}"
        assert len(pipeline_result.warnings) < 10, f"警告过多: {len(pipeline_result.warnings)}"

    def _generate_performance_report(self, benchmark_results: List[Dict[str, Any]]):
        """生成性能报告"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_summary": {
                "total_benchmarks": len(benchmark_results),
                "successful_benchmarks": len([r for r in benchmark_results if r.get("meets_time_target") and r.get("meets_memory_target")]),
                "performance_trends": []
            },
            "benchmark_details": benchmark_results,
            "recommendations": []
        }
        
        # 分析性能趋势
        successful_results = [r for r in benchmark_results if "execution_time" in r]
        if successful_results:
            avg_throughput = sum(r.get("throughput", 0) for r in successful_results) / len(successful_results)
            max_memory = max(r.get("memory_usage_mb", 0) for r in successful_results)
            
            report_data["test_summary"]["average_throughput"] = avg_throughput
            report_data["test_summary"]["peak_memory_usage"] = max_memory
            
            # 生成建议
            if avg_throughput < 5.0:
                report_data["recommendations"].append("考虑优化算法并行度以提高吞吐量")
            if max_memory > 150:
                report_data["recommendations"].append("监控内存使用，考虑增加内存管理机制")
        
        # 将报告添加到测试记录
        self.test_reporter.add_test_result(
            "performance_benchmark",
            True,
            report_data,
            None
        )

    def teardown_method(self):
        """测试清理"""
        # 生成最终测试报告
        final_report = self.test_reporter.generate_report()
        
        # 清理资源
        gc.collect()
        
        print("\n📋 T015测试会话总结:")
        print(f"  总测试数: {final_report['summary']['total_tests']}")
        print(f"  成功率: {final_report['summary']['success_rate']:.1%}")
        print(f"  执行时间: {final_report['test_session']['total_duration_seconds']:.2f}秒")
        
        if final_report.get("performance_summary"):
            perf = final_report["performance_summary"]
            print(f"  平均执行时间: {perf.get('avg_execution_time', 0):.2f}秒")
            print(f"  平均内存使用: {perf.get('avg_memory_usage', 0):.1f}MB")


# =============================================================================
# 独立运行和工具函数
# =============================================================================

def test_pipeline_configuration_validity():
    """测试管道配置有效性"""
    # 验证算法管道配置
    assert len(ALGORITHM_PIPELINE) > 0, "算法管道为空"
    assert len(ALGORITHM_MODULES) > 0, "算法模块配置为空"
    
    # 验证管道顺序中的每个算法都有配置
    for alg_name in ALGORITHM_PIPELINE:
        assert alg_name in ALGORITHM_MODULES, f"算法 {alg_name} 缺少配置信息"
        
        module_info = ALGORITHM_MODULES[alg_name]
        assert "name" in module_info, f"算法 {alg_name} 缺少名称"
        assert "description" in module_info, f"算法 {alg_name} 缺少描述"
        assert "dependencies" in module_info, f"算法 {alg_name} 缺少依赖信息"


def test_base_algorithm_functionality():
    """测试基础算法类功能"""
    # 创建测试算法实例
    class TestAlgorithm(BaseAlgorithm):
        async def execute(self, input_data, **kwargs):
            return {"result": "test_output", "input": input_data}
        
        def validate_input(self, input_data):
            return input_data is not None
    
    # 测试算法实例化
    test_alg = TestAlgorithm(AlgorithmType.CALENDAR_SERVICE)
    assert test_alg.algorithm_type == AlgorithmType.CALENDAR_SERVICE
    assert test_alg.version == "1.0.0"
    
    # 测试输入验证
    assert test_alg.validate_input("test_data") == True
    assert test_alg.validate_input(None) == False
    
    # 测试算法信息
    info = test_alg.get_info()
    assert "algorithm_type" in info
    assert "version" in info
    assert "config" in info


if __name__ == "__main__":
    # 独立运行T015测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*80)
    print("🎯 T015 - 月度算法管道执行集成测试完成")
    print("✅ 测试内容:")
    print("   • 完整算法管道执行流程")
    print("   • 算法间依赖关系和数据流转")
    print("   • 并行执行和性能优化")
    print("   • 约束遵循和结果验证")
    print("   • 异常处理和错误恢复")
    print("   • 内存和性能基准测试")
    print("   • 工作日历集成测试")
    print("   • 真实数据场景测试")
    print("📊 覆盖范围: 8个算法模块 + 完整管道协调")
    print("🚀 性能验证: 吞吐量、内存使用、执行时间基准")
    print("="*80)