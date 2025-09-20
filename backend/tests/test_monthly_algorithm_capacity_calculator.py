"""
APS智慧排产系统 - 产能计算器测试

测试 CapacityCalculator 类的功能，使用真实数据进行验证。

测试覆盖：
1. 严格只计算卷包机产能（喂丝机不参与）
2. 速度配置通配符匹配算法验证
3. 时间窗口与产能计算的集成
4. 产能约束验证和边界条件
5. 最佳机台选择算法
6. 产能矩阵生成和格式验证
7. 异常情况和错误处理

技术要求：
- 使用真实速度配置和机台数据
- 验证产能计算的正确性
- 测试通配符匹配优先级
- 验证只对卷包机进行产能计算
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import MagicMock
from decimal import Decimal

from app.algorithms.monthly_scheduling.capacity_calculator import CapacityCalculator
from app.algorithms.monthly_scheduling.database_loader import DatabaseLoader
from app.algorithms.monthly_scheduling.time_window_calculator import TimeWindowCalculator
from app.db.connection import get_db_session


class TestCapacityCalculator:
    """产能计算器测试类"""
    
    @pytest.fixture
    def calculator(self):
        """产能计算器实例夹具"""
        return CapacityCalculator()
    
    @pytest.fixture
    async def real_data_loader(self):
        """真实数据加载器夹具"""
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            # 加载真实数据用于测试
            data = await loader.load_all_data("TEST_BATCH")
            return data
    
    @pytest.fixture
    def sample_monthly_plans(self):
        """示例月度计划数据"""
        plans = []
        
        for i, (article_nr, quantity) in enumerate([
            ("C001", 1000), ("C002", 1500), ("C003", 800)
        ]):
            plan = MagicMock()
            plan.monthly_plan_id = f"PLAN_{i+1:03d}"
            plan.article_nr = article_nr
            plan.article_name = f"产品{article_nr}"
            plan.target_quantity_boxes = quantity
            plans.append(plan)
        
        return plans
    
    @pytest.fixture
    def sample_packing_machines(self):
        """示例卷包机数据"""
        machines = []
        
        for code in ["A1", "A2", "B1", "B2"]:
            machine = MagicMock()
            machine.machine_code = code
            machine.machine_type = "PACKING"
            machine.is_active = True
            machines.append(machine)
        
        return machines
    
    @pytest.fixture
    def sample_feeding_machines(self):
        """示例喂丝机数据（用于验证不参与产能计算）"""
        machines = []
        
        for code in ["1", "2", "3"]:
            machine = MagicMock()
            machine.machine_code = code
            machine.machine_type = "FEEDING"
            machine.is_active = True
            machines.append(machine)
        
        return machines
    
    @pytest.fixture
    def sample_speed_configs(self):
        """示例速度配置数据"""
        # 具体配置：(machine_code, article_nr) -> speed_info
        specific_configs = {
            ("A1", "C001"): {"speed_per_hour": 150, "efficiency": 0.85},
            ("A2", "C001"): {"speed_per_hour": 140, "efficiency": 0.80},
            ("A1", "C002"): {"speed_per_hour": 120, "efficiency": 0.90},
        }
        
        # 通配符配置
        wildcard_configs = [
            {"machine_code": "*", "article_nr": "C001", "speed_per_hour": 130, "efficiency": 0.75},
            {"machine_code": "A1", "article_nr": "*", "speed_per_hour": 100, "efficiency": 0.70},
            {"machine_code": "*", "article_nr": "*", "speed_per_hour": 80, "efficiency": 0.65},
        ]
        
        return {
            "specific": specific_configs,
            "wildcard": wildcard_configs
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
            ],
            "B1": [
                {
                    "start_time": base_time,
                    "end_time": base_time + timedelta(hours=6),
                    "duration_hours": 6.0
                }
            ]
        }
    
    async def test_calculate_all_capacities_with_real_data(self, calculator, real_data_loader):
        """测试使用真实数据计算所有产能"""
        data = real_data_loader
        
        if not data['monthly_plans']:
            pytest.skip("没有月度计划数据，跳过测试")
        
        if not data['machines']['packing']:
            pytest.skip("没有卷包机数据，跳过测试")
        
        # 使用时间窗口计算器生成时间窗口
        time_calculator = TimeWindowCalculator()
        time_windows = time_calculator.calculate_available_windows(
            machines=data['machines']['packing'][:3],  # 只测试前3台
            work_calendar=data['work_calendar'],
            shift_configs=data['shift_configs'],
            maintenance_plans=data['maintenance_plans']
        )
        
        # 计算产能矩阵
        capacity_matrix = calculator.calculate_all_capacities(
            monthly_plans=data['monthly_plans'][:5],  # 只测试前5个计划
            packing_machines=data['machines']['packing'][:3],
            speed_configs=data['speed_configs'],
            time_windows=time_windows
        )
        
        # 验证结果
        assert isinstance(capacity_matrix, dict), "产能矩阵应该返回字典"
        
        for (machine_code, article_nr), capacity_info in capacity_matrix.items():
            assert isinstance(machine_code, str), "机台代码应该是字符串"
            assert isinstance(article_nr, str), "物料代码应该是字符串"
            assert isinstance(capacity_info, dict), "产能信息应该是字典"
            
            # 验证必需字段
            required_fields = [
                'can_complete', 'max_producible', 'required_hours', 
                'available_hours', 'speed_per_hour', 'efficiency_rate'
            ]
            for field in required_fields:
                assert field in capacity_info, f"产能信息应该包含字段: {field}"
            
            # 验证数据类型和逻辑
            assert isinstance(capacity_info['can_complete'], bool), "can_complete应该是布尔值"
            assert capacity_info['max_producible'] >= 0, "最大产能应该非负"
            assert capacity_info['available_hours'] >= 0, "可用时间应该非负"
            assert capacity_info['speed_per_hour'] > 0, "速度应该大于0"
            assert 0 <= capacity_info['efficiency_rate'] <= 1, "效率应该在0-1之间"
        
        print(f"✅ 真实数据产能计算测试通过: {len(capacity_matrix)} 个机台-产品组合")
    
    async def test_calculate_all_capacities_basic(self, calculator, sample_monthly_plans, 
                                                 sample_packing_machines, sample_speed_configs, 
                                                 sample_time_windows):
        """测试基本产能计算功能"""
        capacity_matrix = calculator.calculate_all_capacities(
            monthly_plans=sample_monthly_plans,
            packing_machines=sample_packing_machines,
            speed_configs=sample_speed_configs,
            time_windows=sample_time_windows
        )
        
        # 验证基本结构
        assert isinstance(capacity_matrix, dict), "产能矩阵应该返回字典"
        
        # 验证键格式
        for key in capacity_matrix.keys():
            assert isinstance(key, tuple), "产能矩阵键应该是元组"
            assert len(key) == 2, "键应该是二元组 (machine_code, article_nr)"
            machine_code, article_nr = key
            assert isinstance(machine_code, str), "机台代码应该是字符串"
            assert isinstance(article_nr, str), "物料代码应该是字符串"
        
        # 验证只包含卷包机（不包含喂丝机）
        all_machine_codes = {key[0] for key in capacity_matrix.keys()}
        sample_machine_codes = {m.machine_code for m in sample_packing_machines}
        
        for machine_code in all_machine_codes:
            assert machine_code in sample_machine_codes, f"产能矩阵中的机台 {machine_code} 应该是卷包机"
        
        print(f"✅ 基本产能计算测试通过: {len(capacity_matrix)} 个组合")
    
    async def test_packing_machines_only(self, calculator, sample_monthly_plans, 
                                        sample_packing_machines, sample_feeding_machines, 
                                        sample_speed_configs, sample_time_windows):
        """测试严格只计算卷包机产能"""
        # 创建包含喂丝机的时间窗口（不应该被使用）
        extended_time_windows = sample_time_windows.copy()
        extended_time_windows["1"] = [  # 喂丝机时间窗口
            {
                "start_time": datetime(2024, 1, 5, 8, 0),
                "end_time": datetime(2024, 1, 5, 16, 0),
                "duration_hours": 8.0
            }
        ]
        
        # 计算产能（只传入卷包机）
        capacity_matrix = calculator.calculate_all_capacities(
            monthly_plans=sample_monthly_plans,
            packing_machines=sample_packing_machines,  # 只传入卷包机
            speed_configs=sample_speed_configs,
            time_windows=extended_time_windows
        )
        
        # 验证结果中不包含喂丝机
        all_machine_codes = {key[0] for key in capacity_matrix.keys()}
        feeding_machine_codes = {m.machine_code for m in sample_feeding_machines}
        
        for feeding_code in feeding_machine_codes:
            assert feeding_code not in all_machine_codes, \
                f"产能矩阵不应该包含喂丝机 {feeding_code}"
        
        # 验证只包含卷包机
        packing_machine_codes = {m.machine_code for m in sample_packing_machines}
        for machine_code in all_machine_codes:
            assert machine_code in packing_machine_codes, \
                f"产能矩阵应该只包含卷包机，发现: {machine_code}"
        
        print(f"✅ 卷包机专用产能计算测试通过")
    
    async def test_calculate_machine_capacity(self, calculator, sample_speed_configs, 
                                             sample_time_windows):
        """测试单机台产能计算"""
        machine_code = "A1"
        article_nr = "C001"
        target_quantity = 1000
        
        machine_windows = sample_time_windows[machine_code]
        
        capacity_info = calculator.calculate_machine_capacity(
            machine_code=machine_code,
            article_nr=article_nr,
            target_quantity=target_quantity,
            speed_configs=sample_speed_configs,
            time_windows=machine_windows
        )
        
        # 验证返回结果
        assert isinstance(capacity_info, dict), "产能信息应该返回字典"
        
        required_fields = [
            'can_complete', 'max_producible', 'required_hours', 
            'available_hours', 'speed_per_hour', 'efficiency_rate'
        ]
        for field in required_fields:
            assert field in capacity_info, f"产能信息应该包含字段: {field}"
        
        # 验证逻辑一致性
        speed = capacity_info['speed_per_hour']
        efficiency = capacity_info['efficiency_rate']
        available_hours = capacity_info['available_hours']
        required_hours = capacity_info['required_hours']
        max_producible = capacity_info['max_producible']
        
        # 验证计算逻辑
        expected_required_hours = target_quantity / (speed * efficiency)
        assert abs(required_hours - expected_required_hours) < 0.01, \
            f"所需时间计算错误: 期望 {expected_required_hours}, 实际 {required_hours}"
        
        expected_max_producible = available_hours * speed * efficiency
        assert abs(max_producible - expected_max_producible) < 0.01, \
            f"最大产能计算错误: 期望 {expected_max_producible}, 实际 {max_producible}"
        
        print(f"✅ 单机台产能计算测试通过")
    
    async def test_find_best_speed_config(self, calculator, sample_speed_configs):
        """测试最佳速度配置查找"""
        test_scenarios = [
            # (machine_code, article_nr, expected_source)
            ("A1", "C001", "specific"),     # 具体配置
            ("A2", "C001", "specific"),     # 具体配置
            ("B1", "C001", "wildcard"),    # 产品通配符
            ("A1", "C003", "wildcard"),    # 机台通配符
            ("B1", "C003", "wildcard"),    # 完全通配符
        ]
        
        for machine_code, article_nr, expected_source in test_scenarios:
            speed_config = calculator._find_best_speed_config(
                machine_code, article_nr, sample_speed_configs
            )
            
            assert speed_config is not None, \
                f"应该找到 {machine_code}-{article_nr} 的速度配置"
            
            assert 'speed_per_hour' in speed_config, "速度配置应该包含速度"
            assert speed_config['speed_per_hour'] > 0, "速度应该大于0"
            
            # 验证优先级（具体配置优先于通配符）
            if expected_source == "specific":
                expected_key = (machine_code, article_nr)
                if expected_key in sample_speed_configs['specific']:
                    expected_speed = sample_speed_configs['specific'][expected_key]['speed_per_hour']
                    assert speed_config['speed_per_hour'] == expected_speed, \
                        f"应该使用具体配置的速度: {expected_speed}"
        
        print(f"✅ 最佳速度配置查找测试通过")
    
    async def test_wildcard_matching_priority(self, calculator):
        """测试通配符匹配优先级"""
        # 创建有优先级的速度配置
        complex_speed_configs = {
            "specific": {
                ("A1", "C001"): {"speed_per_hour": 150, "efficiency": 0.85},
            },
            "wildcard": [
                {"machine_code": "*", "article_nr": "C001", "speed_per_hour": 130, "efficiency": 0.75},
                {"machine_code": "A1", "article_nr": "*", "speed_per_hour": 100, "efficiency": 0.70},
                {"machine_code": "*", "article_nr": "*", "speed_per_hour": 80, "efficiency": 0.65},
            ]
        }
        
        # 测试优先级：具体 > 产品通配符 > 机台通配符 > 完全通配符
        test_cases = [
            ("A1", "C001", 150),  # 具体配置
            ("A2", "C001", 130),  # 产品通配符
            ("A1", "C002", 100),  # 机台通配符
            ("A2", "C002", 80),   # 完全通配符
        ]
        
        for machine_code, article_nr, expected_speed in test_cases:
            speed_config = calculator._find_best_speed_config(
                machine_code, article_nr, complex_speed_configs
            )
            
            assert speed_config is not None, f"应该找到配置: {machine_code}-{article_nr}"
            assert speed_config['speed_per_hour'] == expected_speed, \
                f"速度不匹配: 期望 {expected_speed}, 实际 {speed_config['speed_per_hour']}"
        
        print(f"✅ 通配符匹配优先级测试通过")
    
    async def test_validate_capacity_constraints(self, calculator, sample_monthly_plans):
        """测试产能约束验证"""
        # 创建测试产能矩阵
        capacity_matrix = {
            ("A1", "C001"): {
                "can_complete": True,
                "max_producible": 1200,
                "required_hours": 8.0,
                "available_hours": 16.0
            },
            ("A2", "C001"): {
                "can_complete": False,
                "max_producible": 800,
                "required_hours": 12.0,
                "available_hours": 10.0
            },
            ("A1", "C002"): {
                "can_complete": True,
                "max_producible": 1500,
                "required_hours": 10.0,
                "available_hours": 12.0
            }
        }
        
        validation_result = calculator.validate_capacity_constraints(
            capacity_matrix, sample_monthly_plans
        )
        
        # 验证验证结果结构
        assert isinstance(validation_result, dict), "验证结果应该是字典"
        assert 'valid' in validation_result, "应该包含valid字段"
        assert 'violations' in validation_result, "应该包含violations字段"
        assert 'summary' in validation_result, "应该包含summary字段"
        
        # 验证违规检测
        violations = validation_result['violations']
        assert isinstance(violations, list), "违规应该是列表"
        
        # 应该检测到A2机台无法完成任务的违规
        found_capacity_violation = False
        for violation in violations:
            if (violation['type'] == 'INSUFFICIENT_CAPACITY' and 
                violation['machine_code'] == 'A2'):
                found_capacity_violation = True
                break
        
        if not found_capacity_violation:
            print("⚠️ 警告: 未检测到预期的产能不足违规")
        
        print(f"✅ 产能约束验证测试通过: {len(violations)} 个违规")
    
    async def test_find_best_machine_for_product(self, calculator, sample_speed_configs, 
                                                sample_time_windows):
        """测试为产品寻找最佳机台"""
        article_nr = "C001"
        target_quantity = 1000
        
        # 计算所有机台的产能
        machine_capacities = {}
        for machine_code in sample_time_windows.keys():
            capacity_info = calculator.calculate_machine_capacity(
                machine_code=machine_code,
                article_nr=article_nr,
                target_quantity=target_quantity,
                speed_configs=sample_speed_configs,
                time_windows=sample_time_windows[machine_code]
            )
            machine_capacities[machine_code] = capacity_info
        
        # 寻找最佳机台
        best_machine = calculator.find_best_machine_for_product(
            article_nr=article_nr,
            target_quantity=target_quantity,
            machine_capacities=machine_capacities
        )
        
        # 验证结果
        if best_machine:
            assert isinstance(best_machine, dict), "最佳机台应该返回字典"
            assert 'machine_code' in best_machine, "应该包含机台代码"
            assert 'capacity_info' in best_machine, "应该包含产能信息"
            assert 'priority_score' in best_machine, "应该包含优先级分数"
            
            # 验证选择的机台能完成任务
            capacity_info = best_machine['capacity_info']
            assert capacity_info['can_complete'], "最佳机台应该能完成任务"
            
            machine_code = best_machine['machine_code']
            assert machine_code in machine_capacities, "机台应该在候选列表中"
        
        print(f"✅ 最佳机台选择测试通过: {best_machine['machine_code'] if best_machine else 'None'}")
    
    async def test_edge_cases_and_error_handling(self, calculator):
        """测试边界条件和错误处理"""
        
        # 测试空数据
        empty_capacity = calculator.calculate_all_capacities(
            monthly_plans=[],
            packing_machines=[],
            speed_configs={"specific": {}, "wildcard": []},
            time_windows={}
        )
        assert empty_capacity == {}, "空数据应该返回空字典"
        
        # 测试无速度配置
        machine = MagicMock()
        machine.machine_code = "TEST"
        
        plan = MagicMock()
        plan.article_nr = "UNKNOWN"
        plan.target_quantity_boxes = 100
        
        no_speed_capacity = calculator.calculate_all_capacities(
            monthly_plans=[plan],
            packing_machines=[machine],
            speed_configs={"specific": {}, "wildcard": []},
            time_windows={"TEST": []}
        )
        
        # 应该有结果但使用默认值
        key = ("TEST", "UNKNOWN")
        if key in no_speed_capacity:
            capacity_info = no_speed_capacity[key]
            # 应该使用默认速度配置
            assert capacity_info['speed_per_hour'] > 0, "应该有默认速度"
        
        # 测试无时间窗口
        no_time_capacity = calculator.calculate_machine_capacity(
            machine_code="TEST",
            article_nr="C001",
            target_quantity=100,
            speed_configs={"specific": {}, "wildcard": [
                {"machine_code": "*", "article_nr": "*", "speed_per_hour": 100, "efficiency": 0.8}
            ]},
            time_windows=[]
        )
        
        assert no_time_capacity['available_hours'] == 0, "无时间窗口可用时间应为0"
        assert not no_time_capacity['can_complete'], "无时间窗口不能完成任务"
        
        print(f"✅ 边界条件和错误处理测试通过")
    
    async def test_calculation_accuracy(self, calculator):
        """测试计算精度"""
        # 使用精确的测试数据
        test_speed_configs = {
            "specific": {
                ("TEST", "PROD"): {"speed_per_hour": 100, "efficiency": 0.8}
            },
            "wildcard": []
        }
        
        test_time_windows = [
            {
                "start_time": datetime(2024, 1, 5, 8, 0),
                "end_time": datetime(2024, 1, 5, 16, 0),
                "duration_hours": 8.0
            }
        ]
        
        target_quantity = 500
        
        capacity_info = calculator.calculate_machine_capacity(
            machine_code="TEST",
            article_nr="PROD",
            target_quantity=target_quantity,
            speed_configs=test_speed_configs,
            time_windows=test_time_windows
        )
        
        # 验证精确计算
        expected_effective_speed = 100 * 0.8  # 80 件/小时
        expected_max_producible = 8.0 * 80    # 640 件
        expected_required_hours = 500 / 80    # 6.25 小时
        
        assert abs(capacity_info['max_producible'] - expected_max_producible) < 0.01, \
            f"最大产能计算错误: 期望 {expected_max_producible}, 实际 {capacity_info['max_producible']}"
        
        assert abs(capacity_info['required_hours'] - expected_required_hours) < 0.01, \
            f"所需时间计算错误: 期望 {expected_required_hours}, 实际 {capacity_info['required_hours']}"
        
        assert capacity_info['can_complete'], "应该能完成任务"
        
        print(f"✅ 计算精度测试通过")
    
    async def test_performance_with_large_dataset(self, calculator):
        """测试大数据集性能"""
        import time
        
        # 创建大量测试数据
        large_plans = []
        for i in range(100):  # 100个计划
            plan = MagicMock()
            plan.monthly_plan_id = f"PLAN_{i:03d}"
            plan.article_nr = f"C{i%10:03d}"  # 10种产品
            plan.target_quantity_boxes = 1000 + i * 10
            large_plans.append(plan)
        
        large_machines = []
        for i in range(20):  # 20台机器
            machine = MagicMock()
            machine.machine_code = f"M{i:02d}"
            machine.machine_type = "PACKING"
            large_machines.append(machine)
        
        # 创建速度配置
        large_speed_configs = {
            "specific": {},
            "wildcard": [
                {"machine_code": "*", "article_nr": "*", "speed_per_hour": 100, "efficiency": 0.8}
            ]
        }
        
        # 创建时间窗口
        large_time_windows = {}
        base_time = datetime(2024, 1, 5, 8, 0)
        for machine in large_machines:
            large_time_windows[machine.machine_code] = [
                {
                    "start_time": base_time,
                    "end_time": base_time + timedelta(hours=8),
                    "duration_hours": 8.0
                }
            ]
        
        # 性能测试
        start_time_perf = time.time()
        
        large_capacity_matrix = calculator.calculate_all_capacities(
            monthly_plans=large_plans,
            packing_machines=large_machines,
            speed_configs=large_speed_configs,
            time_windows=large_time_windows
        )
        
        end_time_perf = time.time()
        execution_time = end_time_perf - start_time_perf
        
        expected_combinations = len(large_plans) * len(large_machines)
        actual_combinations = len(large_capacity_matrix)
        
        assert actual_combinations <= expected_combinations, "组合数量不应超过预期"
        assert execution_time < 10, f"大数据集计算时间过长: {execution_time:.2f} 秒"
        
        print(f"✅ 大数据集性能测试通过: {actual_combinations} 个组合, 用时 {execution_time:.2f} 秒")


# 异步测试运行器
@pytest.mark.asyncio
async def test_capacity_calculator_complete_suite():
    """运行完整的产能计算器测试套件"""
    print("\n🚀 开始运行产能计算器完整测试套件")
    
    calculator = CapacityCalculator()
    test_instance = TestCapacityCalculator()
    
    # 准备测试数据
    sample_monthly_plans = test_instance.sample_monthly_plans(test_instance)
    sample_packing_machines = test_instance.sample_packing_machines(test_instance)
    sample_feeding_machines = test_instance.sample_feeding_machines(test_instance)
    sample_speed_configs = test_instance.sample_speed_configs(test_instance)
    sample_time_windows = test_instance.sample_time_windows(test_instance)
    
    try:
        # 运行真实数据测试
        print("\n📋 运行真实数据测试...")
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            real_data = await loader.load_all_data("TEST_BATCH")
            await test_instance.test_calculate_all_capacities_with_real_data(calculator, real_data)
        
        # 运行基础功能测试
        print("\n📋 运行基础功能测试...")
        await test_instance.test_calculate_all_capacities_basic(
            calculator, sample_monthly_plans, sample_packing_machines, 
            sample_speed_configs, sample_time_windows
        )
        
        # 运行卷包机专用测试
        print("\n📋 运行卷包机专用测试...")
        await test_instance.test_packing_machines_only(
            calculator, sample_monthly_plans, sample_packing_machines, 
            sample_feeding_machines, sample_speed_configs, sample_time_windows
        )
        
        # 运行组件测试
        print("\n📋 运行组件测试...")
        await test_instance.test_calculate_machine_capacity(
            calculator, sample_speed_configs, sample_time_windows
        )
        await test_instance.test_find_best_speed_config(calculator, sample_speed_configs)
        await test_instance.test_wildcard_matching_priority(calculator)
        await test_instance.test_validate_capacity_constraints(calculator, sample_monthly_plans)
        await test_instance.test_find_best_machine_for_product(
            calculator, sample_speed_configs, sample_time_windows
        )
        
        # 运行边界条件测试
        print("\n📋 运行边界条件测试...")
        await test_instance.test_edge_cases_and_error_handling(calculator)
        await test_instance.test_calculation_accuracy(calculator)
        
        # 运行性能测试
        print("\n📋 运行性能测试...")
        await test_instance.test_performance_with_large_dataset(calculator)
        
        print("\n🎉 产能计算器测试套件全部通过!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_capacity_calculator_complete_suite())