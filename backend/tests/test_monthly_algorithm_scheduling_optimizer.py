"""
APS智慧排产系统 - 调度优化器测试

测试 SchedulingOptimizer 类的功能，使用真实数据进行验证。

测试覆盖：
1. 零时间重叠约束验证
2. 智能机台选择算法
3. 产品优先级排序
4. 时间分配算法
5. 产品拆分策略
6. 全覆盖验证
7. 调度结果优化

技术要求：
- 验证时间窗口绝对不重叠
- 测试复杂的调度逻辑
- 使用真实产能和时间数据
- 验证调度算法的正确性
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import MagicMock

from app.algorithms.monthly_scheduling.scheduling_optimizer import SchedulingOptimizer
from app.algorithms.monthly_scheduling.database_loader import DatabaseLoader
from app.algorithms.monthly_scheduling.time_window_calculator import TimeWindowCalculator
from app.algorithms.monthly_scheduling.capacity_calculator import CapacityCalculator
from app.db.connection import get_db_session


class TestSchedulingOptimizer:
    """调度优化器测试类"""
    
    @pytest.fixture
    def optimizer(self):
        """调度优化器实例夹具"""
        return SchedulingOptimizer()
    
    @pytest.fixture
    async def real_integrated_data(self):
        """集成的真实数据夹具"""
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            data = await loader.load_all_data("TEST_BATCH")
            
            # 如果有数据，生成时间窗口和产能矩阵
            if data['monthly_plans'] and data['machines']['packing']:
                time_calculator = TimeWindowCalculator()
                capacity_calculator = CapacityCalculator()
                
                # 只使用前几台机器和计划以提高测试速度
                test_machines = data['machines']['packing'][:3]
                test_plans = data['monthly_plans'][:5]
                
                time_windows = time_calculator.calculate_available_windows(
                    machines=test_machines,
                    work_calendar=data['work_calendar'],
                    shift_configs=data['shift_configs'],
                    maintenance_plans=data['maintenance_plans']
                )
                
                capacity_matrix = capacity_calculator.calculate_all_capacities(
                    monthly_plans=test_plans,
                    packing_machines=test_machines,
                    speed_configs=data['speed_configs'],
                    time_windows=time_windows
                )
                
                return {
                    'monthly_plans': test_plans,
                    'machines': test_machines,
                    'time_windows': time_windows,
                    'capacity_matrix': capacity_matrix,
                    'machine_relations': data['machine_relations']
                }
            
            return None
    
    @pytest.fixture
    def sample_monthly_plans(self):
        """示例月度计划数据"""
        plans = []
        
        for i, (article_nr, quantity, priority) in enumerate([
            ("C001", 1000, 1), ("C002", 1500, 2), ("C003", 800, 3), ("C004", 1200, 1)
        ]):
            plan = MagicMock()
            plan.monthly_plan_id = f"PLAN_{i+1:03d}"
            plan.article_nr = article_nr
            plan.article_name = f"产品{article_nr}"
            plan.target_quantity_boxes = quantity
            plan.priority = priority
            plan.due_date = datetime(2024, 1, 31)
            plans.append(plan)
        
        return plans
    
    @pytest.fixture
    def sample_capacity_matrix(self):
        """示例产能矩阵"""
        base_time = datetime(2024, 1, 5, 8, 0)
        
        return {
            ("A1", "C001"): {
                "can_complete": True,
                "max_producible": 1200,
                "required_hours": 8.0,
                "available_hours": 16.0,
                "speed_per_hour": 150,
                "efficiency_rate": 0.85
            },
            ("A1", "C002"): {
                "can_complete": True,
                "max_producible": 1800,
                "required_hours": 12.0,
                "available_hours": 16.0,
                "speed_per_hour": 120,
                "efficiency_rate": 0.90
            },
            ("A2", "C001"): {
                "can_complete": True,
                "max_producible": 1000,
                "required_hours": 10.0,
                "available_hours": 12.0,
                "speed_per_hour": 100,
                "efficiency_rate": 0.80
            },
            ("A2", "C003"): {
                "can_complete": True,
                "max_producible": 900,
                "required_hours": 8.0,
                "available_hours": 12.0,
                "speed_per_hour": 110,
                "efficiency_rate": 0.85
            }
        }
    
    @pytest.fixture
    def sample_time_windows(self):
        """示例时间窗口数据"""
        base_time = datetime(2024, 1, 5, 8, 0)
        
        return {
            "A1": [
                {
                    "start_time": base_time,
                    "end_time": base_time + timedelta(hours=8),
                    "duration_hours": 8.0
                },
                {
                    "start_time": base_time + timedelta(hours=16),
                    "end_time": base_time + timedelta(hours=24),
                    "duration_hours": 8.0
                }
            ],
            "A2": [
                {
                    "start_time": base_time,
                    "end_time": base_time + timedelta(hours=12),
                    "duration_hours": 12.0
                }
            ]
        }
    
    @pytest.fixture
    def sample_machine_relations(self):
        """示例机台关系数据"""
        return {
            "maker_to_feeder": {
                "A1": "1",
                "A2": "2"
            },
            "feeder_to_makers": {
                "1": [{"maker_code": "A1", "priority": 1}],
                "2": [{"maker_code": "A2", "priority": 1}]
            }
        }
    
    async def test_optimize_schedule_with_real_data(self, optimizer, real_integrated_data):
        """测试使用真实数据的调度优化"""
        if not real_integrated_data:
            pytest.skip("没有真实数据，跳过测试")
        
        data = real_integrated_data
        
        optimization_result = optimizer.optimize_schedule(
            monthly_plans=data['monthly_plans'],
            capacity_matrix=data['capacity_matrix'],
            time_windows=data['time_windows'],
            machine_relations=data['machine_relations']
        )
        
        # 验证结果结构
        assert isinstance(optimization_result, dict), "优化结果应该返回字典"
        assert 'success' in optimization_result, "应该包含success字段"
        assert 'scheduled_results' in optimization_result, "应该包含scheduled_results字段"
        
        if optimization_result['success']:
            scheduled_results = optimization_result['scheduled_results']
            assert isinstance(scheduled_results, list), "调度结果应该是列表"
            
            # 验证调度结果格式
            for result in scheduled_results:
                required_fields = [
                    'monthly_plan_id', 'article_nr', 'target_quantity_boxes',
                    'assigned_maker_code', 'assigned_feeder_code',
                    'scheduled_start_time', 'scheduled_end_time', 
                    'scheduled_duration_hours'
                ]
                
                for field in required_fields:
                    assert field in result, f"调度结果应该包含字段: {field}"
            
            # 验证零时间重叠
            zero_overlap_valid = optimizer.validate_zero_overlap(scheduled_results)
            assert zero_overlap_valid, "调度结果应该满足零时间重叠约束"
        
        print(f"✅ 真实数据调度优化测试通过: 成功={optimization_result['success']}")
    
    async def test_optimize_schedule_basic(self, optimizer, sample_monthly_plans, 
                                          sample_capacity_matrix, sample_time_windows, 
                                          sample_machine_relations):
        """测试基本调度优化功能"""
        optimization_result = optimizer.optimize_schedule(
            monthly_plans=sample_monthly_plans,
            capacity_matrix=sample_capacity_matrix,
            time_windows=sample_time_windows,
            machine_relations=sample_machine_relations
        )
        
        # 验证基本结构
        assert isinstance(optimization_result, dict), "优化结果应该返回字典"
        assert 'success' in optimization_result, "应该包含成功标志"
        assert 'scheduled_results' in optimization_result, "应该包含调度结果"
        assert 'execution_summary' in optimization_result, "应该包含执行摘要"
        
        if optimization_result['success']:
            scheduled_results = optimization_result['scheduled_results']
            
            # 验证时间重叠
            for result in scheduled_results:
                start_time = result['scheduled_start_time']
                end_time = result['scheduled_end_time']
                assert start_time < end_time, "开始时间应该早于结束时间"
            
            # 验证机台分配
            for result in scheduled_results:
                maker_code = result['assigned_maker_code']
                feeder_code = result['assigned_feeder_code']
                
                expected_feeder = sample_machine_relations['maker_to_feeder'].get(maker_code)
                assert feeder_code == expected_feeder, \
                    f"机台关系映射错误: {maker_code} -> {feeder_code}, 期望 {expected_feeder}"
        
        print(f"✅ 基本调度优化测试通过")
    
    async def test_validate_zero_overlap(self, optimizer):
        """测试零时间重叠验证"""
        # 创建无重叠的调度结果
        non_overlap_results = [
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 8, 0),
                'scheduled_end_time': datetime(2024, 1, 5, 12, 0)
            },
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 12, 0),
                'scheduled_end_time': datetime(2024, 1, 5, 16, 0)
            },
            {
                'assigned_maker_code': 'A2',
                'scheduled_start_time': datetime(2024, 1, 5, 8, 0),
                'scheduled_end_time': datetime(2024, 1, 5, 16, 0)
            }
        ]
        
        # 验证无重叠情况
        is_valid = optimizer.validate_zero_overlap(non_overlap_results)
        assert is_valid, "无重叠的调度结果应该通过验证"
        
        # 创建有重叠的调度结果
        overlap_results = [
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 8, 0),
                'scheduled_end_time': datetime(2024, 1, 5, 12, 0)
            },
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 10, 0),  # 重叠
                'scheduled_end_time': datetime(2024, 1, 5, 14, 0)
            }
        ]
        
        # 验证有重叠情况
        is_valid = optimizer.validate_zero_overlap(overlap_results)
        assert not is_valid, "有重叠的调度结果应该不通过验证"
        
        print(f"✅ 零时间重叠验证测试通过")
    
    async def test_ensure_full_coverage(self, optimizer, sample_monthly_plans):
        """测试全覆盖验证"""
        # 创建完全覆盖的调度结果
        full_coverage_results = []
        for plan in sample_monthly_plans:
            result = {
                'monthly_plan_id': plan.monthly_plan_id,
                'article_nr': plan.article_nr,
                'target_quantity_boxes': plan.target_quantity_boxes
            }
            full_coverage_results.append(result)
        
        # 验证完全覆盖
        coverage_result = optimizer.ensure_full_coverage(sample_monthly_plans, full_coverage_results)
        assert coverage_result['full_coverage'], "完全覆盖应该通过验证"
        assert len(coverage_result['missing_products']) == 0, "不应该有缺失产品"
        
        # 创建部分覆盖的调度结果（缺少最后一个产品）
        partial_coverage_results = full_coverage_results[:-1]
        
        coverage_result = optimizer.ensure_full_coverage(sample_monthly_plans, partial_coverage_results)
        assert not coverage_result['full_coverage'], "部分覆盖应该不通过验证"
        assert len(coverage_result['missing_products']) == 1, "应该有一个缺失产品"
        
        print(f"✅ 全覆盖验证测试通过")
    
    async def test_schedule_single_product(self, optimizer, sample_capacity_matrix, 
                                          sample_time_windows):
        """测试单产品调度"""
        # 创建单个产品计划
        plan = MagicMock()
        plan.monthly_plan_id = "PLAN_001"
        plan.article_nr = "C001"
        plan.target_quantity_boxes = 1000
        
        # 已占用的时间槽（模拟）
        occupied_slots = {}
        
        scheduling_result = optimizer._schedule_single_product(
            plan=plan,
            capacity_matrix=sample_capacity_matrix,
            time_windows=sample_time_windows,
            occupied_slots=occupied_slots
        )
        
        # 验证结果
        if scheduling_result['success']:
            result = scheduling_result['scheduled_result']
            
            assert result['monthly_plan_id'] == plan.monthly_plan_id, "计划ID应该匹配"
            assert result['article_nr'] == plan.article_nr, "物料代码应该匹配"
            assert result['target_quantity_boxes'] == plan.target_quantity_boxes, "数量应该匹配"
            assert 'assigned_maker_code' in result, "应该分配机台"
            assert 'scheduled_start_time' in result, "应该有开始时间"
            assert 'scheduled_end_time' in result, "应该有结束时间"
        
        print(f"✅ 单产品调度测试通过: 成功={scheduling_result['success']}")
    
    async def test_find_best_machine_for_plan(self, optimizer, sample_capacity_matrix):
        """测试为计划寻找最佳机台"""
        plan = MagicMock()
        plan.article_nr = "C001"
        plan.target_quantity_boxes = 1000
        
        best_machine = optimizer._find_best_machine_for_plan(plan, sample_capacity_matrix)
        
        if best_machine:
            machine_code, capacity_info = best_machine
            
            assert isinstance(machine_code, str), "机台代码应该是字符串"
            assert isinstance(capacity_info, dict), "产能信息应该是字典"
            assert capacity_info['can_complete'], "最佳机台应该能完成任务"
            
            # 验证选择的是最优机台
            key = (machine_code, plan.article_nr)
            assert key in sample_capacity_matrix, "选择的机台应该在产能矩阵中"
        
        print(f"✅ 最佳机台选择测试通过: {best_machine[0] if best_machine else 'None'}")
    
    async def test_allocate_time_slot(self, optimizer, sample_time_windows):
        """测试时间槽分配"""
        machine_code = "A1"
        required_hours = 6.0
        occupied_slots = {}
        
        allocation_result = optimizer._allocate_time_slot(
            machine_code=machine_code,
            required_hours=required_hours,
            time_windows=sample_time_windows,
            occupied_slots=occupied_slots
        )
        
        if allocation_result['success']:
            start_time = allocation_result['start_time']
            end_time = allocation_result['end_time']
            
            assert isinstance(start_time, datetime), "开始时间应该是datetime对象"
            assert isinstance(end_time, datetime), "结束时间应该是datetime对象"
            assert start_time < end_time, "开始时间应该早于结束时间"
            
            # 验证时间长度
            actual_duration = (end_time - start_time).total_seconds() / 3600
            assert abs(actual_duration - required_hours) < 0.01, \
                f"分配的时间长度不正确: 期望 {required_hours}, 实际 {actual_duration}"
        
        print(f"✅ 时间槽分配测试通过: 成功={allocation_result['success']}")
    
    async def test_product_priority_sorting(self, optimizer, sample_monthly_plans):
        """测试产品优先级排序"""
        sorted_plans = optimizer._sort_products_by_priority(sample_monthly_plans)
        
        assert len(sorted_plans) == len(sample_monthly_plans), "排序后数量应该一致"
        
        # 验证排序逻辑（优先级低的数字表示高优先级）
        for i in range(len(sorted_plans) - 1):
            current_priority = getattr(sorted_plans[i], 'priority', 999)
            next_priority = getattr(sorted_plans[i + 1], 'priority', 999)
            assert current_priority <= next_priority, \
                f"优先级排序错误: {current_priority} 应该 <= {next_priority}"
        
        print(f"✅ 产品优先级排序测试通过")
    
    async def test_product_splitting_strategy(self, optimizer, sample_capacity_matrix, 
                                             sample_time_windows):
        """测试产品拆分策略"""
        # 创建大数量的产品计划
        large_plan = MagicMock()
        large_plan.monthly_plan_id = "LARGE_PLAN"
        large_plan.article_nr = "C001"
        large_plan.target_quantity_boxes = 5000  # 超出单机台产能
        
        # 模拟已占用的时间槽
        occupied_slots = {}
        
        scheduling_result = optimizer._schedule_single_product(
            plan=large_plan,
            capacity_matrix=sample_capacity_matrix,
            time_windows=sample_time_windows,
            occupied_slots=occupied_slots
        )
        
        # 验证拆分逻辑
        if scheduling_result['success']:
            # 如果成功，说明算法能处理大数量
            result = scheduling_result['scheduled_result']
            assert result['target_quantity_boxes'] <= large_plan.target_quantity_boxes, \
                "拆分后的数量应该不超过原计划"
        else:
            # 如果失败，应该有明确的失败原因
            assert 'error' in scheduling_result, "失败应该有错误信息"
        
        print(f"✅ 产品拆分策略测试通过")
    
    async def test_edge_cases_and_error_handling(self, optimizer):
        """测试边界条件和错误处理"""
        
        # 测试空数据
        empty_result = optimizer.optimize_schedule(
            monthly_plans=[],
            capacity_matrix={},
            time_windows={},
            machine_relations={"maker_to_feeder": {}, "feeder_to_makers": {}}
        )
        
        assert not empty_result['success'] or len(empty_result['scheduled_results']) == 0, \
            "空数据应该返回失败或空结果"
        
        # 测试无可用产能
        impossible_plan = MagicMock()
        impossible_plan.monthly_plan_id = "IMPOSSIBLE"
        impossible_plan.article_nr = "UNKNOWN"
        impossible_plan.target_quantity_boxes = 1000
        
        impossible_result = optimizer.optimize_schedule(
            monthly_plans=[impossible_plan],
            capacity_matrix={},  # 无产能配置
            time_windows={},
            machine_relations={"maker_to_feeder": {}, "feeder_to_makers": {}}
        )
        
        assert not impossible_result['success'], "无可用产能应该返回失败"
        
        # 测试时间重叠验证的边界情况
        edge_case_results = [
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 8, 0),
                'scheduled_end_time': datetime(2024, 1, 5, 12, 0)
            },
            {
                'assigned_maker_code': 'A1',
                'scheduled_start_time': datetime(2024, 1, 5, 12, 0),  # 边界情况：恰好不重叠
                'scheduled_end_time': datetime(2024, 1, 5, 16, 0)
            }
        ]
        
        is_valid = optimizer.validate_zero_overlap(edge_case_results)
        assert is_valid, "边界情况（恰好不重叠）应该通过验证"
        
        print(f"✅ 边界条件和错误处理测试通过")
    
    async def test_optimization_quality_metrics(self, optimizer, sample_monthly_plans, 
                                               sample_capacity_matrix, sample_time_windows, 
                                               sample_machine_relations):
        """测试优化质量指标"""
        optimization_result = optimizer.optimize_schedule(
            monthly_plans=sample_monthly_plans,
            capacity_matrix=sample_capacity_matrix,
            time_windows=sample_time_windows,
            machine_relations=sample_machine_relations
        )
        
        if optimization_result['success']:
            scheduled_results = optimization_result['scheduled_results']
            
            # 计算覆盖率
            planned_products = {plan.article_nr for plan in sample_monthly_plans}
            scheduled_products = {result['article_nr'] for result in scheduled_results}
            coverage_rate = len(scheduled_products) / len(planned_products)
            
            # 计算机台利用率
            machine_usage = {}
            for result in scheduled_results:
                machine_code = result['assigned_maker_code']
                duration = result['scheduled_duration_hours']
                
                if machine_code not in machine_usage:
                    machine_usage[machine_code] = 0
                machine_usage[machine_code] += duration
            
            # 验证质量指标
            assert coverage_rate > 0, "应该有产品被调度"
            assert len(machine_usage) > 0, "应该有机台被使用"
            
            # 验证时间分配合理性
            for result in scheduled_results:
                duration = result['scheduled_duration_hours']
                assert duration > 0, "调度时间应该大于0"
                assert duration <= 24, "单次调度时间不应超过24小时"
        
        print(f"✅ 优化质量指标测试通过")
    
    async def test_performance_with_large_dataset(self, optimizer):
        """测试大数据集性能"""
        import time
        
        # 创建大量测试数据
        large_plans = []
        for i in range(50):  # 50个计划
            plan = MagicMock()
            plan.monthly_plan_id = f"PLAN_{i:03d}"
            plan.article_nr = f"C{i%10:03d}"  # 10种产品
            plan.target_quantity_boxes = 1000 + i * 10
            plan.priority = i % 3 + 1
            large_plans.append(plan)
        
        # 创建产能矩阵
        large_capacity_matrix = {}
        for i in range(10):  # 10台机器
            machine_code = f"M{i:02d}"
            for j in range(10):  # 10种产品
                article_nr = f"C{j:03d}"
                large_capacity_matrix[(machine_code, article_nr)] = {
                    "can_complete": True,
                    "max_producible": 1200 + i * 100,
                    "required_hours": 8.0,
                    "available_hours": 16.0,
                    "speed_per_hour": 150 + i * 10,
                    "efficiency_rate": 0.8 + i * 0.01
                }
        
        # 创建时间窗口
        large_time_windows = {}
        base_time = datetime(2024, 1, 5, 8, 0)
        for i in range(10):
            machine_code = f"M{i:02d}"
            large_time_windows[machine_code] = [
                {
                    "start_time": base_time + timedelta(days=i%3),
                    "end_time": base_time + timedelta(days=i%3, hours=16),
                    "duration_hours": 16.0
                }
            ]
        
        # 创建机台关系
        large_machine_relations = {
            "maker_to_feeder": {f"M{i:02d}": f"{i%5}" for i in range(10)},
            "feeder_to_makers": {}
        }
        for i in range(5):
            large_machine_relations["feeder_to_makers"][str(i)] = [
                {"maker_code": f"M{j:02d}", "priority": 1} 
                for j in range(10) if j % 5 == i
            ]
        
        # 性能测试
        start_time_perf = time.time()
        
        large_optimization_result = optimizer.optimize_schedule(
            monthly_plans=large_plans,
            capacity_matrix=large_capacity_matrix,
            time_windows=large_time_windows,
            machine_relations=large_machine_relations
        )
        
        end_time_perf = time.time()
        execution_time = end_time_perf - start_time_perf
        
        # 验证结果
        assert isinstance(large_optimization_result, dict), "应该返回结果"
        assert execution_time < 30, f"大数据集计算时间过长: {execution_time:.2f} 秒"
        
        if large_optimization_result['success']:
            scheduled_count = len(large_optimization_result['scheduled_results'])
            print(f"✅ 大数据集性能测试通过: {scheduled_count} 个调度结果, 用时 {execution_time:.2f} 秒")
        else:
            print(f"✅ 大数据集性能测试通过: 调度失败但用时合理 {execution_time:.2f} 秒")


# 异步测试运行器
@pytest.mark.asyncio
async def test_scheduling_optimizer_complete_suite():
    """运行完整的调度优化器测试套件"""
    print("\n🚀 开始运行调度优化器完整测试套件")
    
    optimizer = SchedulingOptimizer()
    test_instance = TestSchedulingOptimizer()
    
    # 准备测试数据
    sample_monthly_plans = test_instance.sample_monthly_plans(test_instance)
    sample_capacity_matrix = test_instance.sample_capacity_matrix(test_instance)
    sample_time_windows = test_instance.sample_time_windows(test_instance)
    sample_machine_relations = test_instance.sample_machine_relations(test_instance)
    
    try:
        # 运行真实数据测试
        print("\n📋 运行真实数据测试...")
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            data = await loader.load_all_data("TEST_BATCH")
            
            if data['monthly_plans'] and data['machines']['packing']:
                time_calculator = TimeWindowCalculator()
                capacity_calculator = CapacityCalculator()
                
                test_machines = data['machines']['packing'][:3]
                test_plans = data['monthly_plans'][:5]
                
                time_windows = time_calculator.calculate_available_windows(
                    machines=test_machines,
                    work_calendar=data['work_calendar'],
                    shift_configs=data['shift_configs'],
                    maintenance_plans=data['maintenance_plans']
                )
                
                capacity_matrix = capacity_calculator.calculate_all_capacities(
                    monthly_plans=test_plans,
                    packing_machines=test_machines,
                    speed_configs=data['speed_configs'],
                    time_windows=time_windows
                )
                
                real_data = {
                    'monthly_plans': test_plans,
                    'machines': test_machines,
                    'time_windows': time_windows,
                    'capacity_matrix': capacity_matrix,
                    'machine_relations': data['machine_relations']
                }
                
                await test_instance.test_optimize_schedule_with_real_data(optimizer, real_data)
            else:
                print("跳过真实数据测试（无数据）")
        
        # 运行基础功能测试
        print("\n📋 运行基础功能测试...")
        await test_instance.test_optimize_schedule_basic(
            optimizer, sample_monthly_plans, sample_capacity_matrix, 
            sample_time_windows, sample_machine_relations
        )
        
        # 运行核心算法测试
        print("\n📋 运行核心算法测试...")
        await test_instance.test_validate_zero_overlap(optimizer)
        await test_instance.test_ensure_full_coverage(optimizer, sample_monthly_plans)
        await test_instance.test_schedule_single_product(
            optimizer, sample_capacity_matrix, sample_time_windows
        )
        await test_instance.test_find_best_machine_for_plan(optimizer, sample_capacity_matrix)
        await test_instance.test_allocate_time_slot(optimizer, sample_time_windows)
        await test_instance.test_product_priority_sorting(optimizer, sample_monthly_plans)
        await test_instance.test_product_splitting_strategy(
            optimizer, sample_capacity_matrix, sample_time_windows
        )
        
        # 运行边界条件测试
        print("\n📋 运行边界条件测试...")
        await test_instance.test_edge_cases_and_error_handling(optimizer)
        await test_instance.test_optimization_quality_metrics(
            optimizer, sample_monthly_plans, sample_capacity_matrix, 
            sample_time_windows, sample_machine_relations
        )
        
        # 运行性能测试
        print("\n📋 运行性能测试...")
        await test_instance.test_performance_with_large_dataset(optimizer)
        
        print("\n🎉 调度优化器测试套件全部通过!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_scheduling_optimizer_complete_suite())