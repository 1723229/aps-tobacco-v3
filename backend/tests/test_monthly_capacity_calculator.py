"""
月度容量计算器测试模块

测试月度生产容量计算和优化算法的各项功能，包括：
- 容量计算的准确性和一致性
- 瓶颈分析的精确性
- 优化建议的质量
- 预测算法的稳定性
- 性能指标的正确性
"""

import asyncio
import pytest
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# 导入被测试的模块
from backend.app.algorithms.monthly_scheduling.monthly_capacity_calculator import (
    MonthlyCapacityCalculator,
    CapacityCalculationMethod,
    BottleneckType,
    CapacityFactors,
    MachineCapacity,
    BottleneckAnalysis,
    OptimizationRecommendation,
    CapacityForecast,
    CapacityReport
)


class TestCapacityFactors:
    """测试容量影响因子类"""
    
    def test_default_factors(self):
        """测试默认影响因子"""
        factors = CapacityFactors()
        
        assert factors.efficiency_factor == 0.85
        assert factors.availability_factor == 0.90
        assert factors.quality_factor == 0.95
        assert factors.maintenance_factor == 0.92
        assert factors.setup_factor == 0.88
        assert factors.operator_factor == 0.93
        assert factors.material_factor == 0.97
    
    def test_overall_factor_calculation(self):
        """测试综合影响因子计算"""
        factors = CapacityFactors()
        overall = factors.overall_factor()
        
        # 计算预期值
        expected = (0.85 * 0.90 * 0.95 * 0.92 * 0.88 * 0.93 * 0.97)
        
        assert abs(overall - expected) < 0.001
        assert 0 < overall < 1
    
    def test_custom_factors(self):
        """测试自定义影响因子"""
        factors = CapacityFactors(
            efficiency_factor=0.9,
            availability_factor=0.95,
            quality_factor=0.98
        )
        
        assert factors.efficiency_factor == 0.9
        assert factors.availability_factor == 0.95
        assert factors.quality_factor == 0.98
        # 其他因子应该保持默认值
        assert factors.maintenance_factor == 0.92


class TestMachineCapacity:
    """测试机台容量数据类"""
    
    def test_machine_capacity_creation(self):
        """测试机台容量对象创建"""
        capacity = MachineCapacity(
            machine_id="JBJ001",
            machine_name="卷包机1号",
            product_type="香烟",
            theoretical_capacity=Decimal("8000"),
            practical_capacity=Decimal("6800"),
            available_hours=Decimal("500"),
            total_monthly_capacity=Decimal("3400000"),
            utilized_capacity=Decimal("2720000"),
            remaining_capacity=Decimal("680000"),
            utilization_rate=0.8,
            efficiency_score=85.0,
            bottleneck_indicators=["高利用率"],
            capacity_factors=CapacityFactors()
        )
        
        assert capacity.machine_id == "JBJ001"
        assert capacity.utilization_rate == 0.8
        assert capacity.efficiency_score == 85.0
        assert "高利用率" in capacity.bottleneck_indicators


class TestMonthlyCapacityCalculator:
    """测试月度容量计算器主类"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return MonthlyCapacityCalculator()
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return AsyncMock()
    
    def test_calculator_initialization(self, calculator):
        """测试计算器初始化"""
        assert calculator.db_session is None
        assert isinstance(calculator.default_factors, CapacityFactors)
        assert calculator.calculation_cache == {}
        assert calculator.performance_metrics['calculations_performed'] == 0
    
    def test_cache_key_generation(self, calculator):
        """测试缓存键生成"""
        cache_key = calculator._generate_cache_key(
            year=2024,
            month=1,
            machine_ids=['JBJ001', 'JBJ002'],
            product_types=['香烟'],
            calculation_method=CapacityCalculationMethod.PRACTICAL
        )
        
        expected = "2024_1_JBJ001,JBJ002_香烟_practical"
        assert cache_key == expected
    
    def test_cache_key_with_none_values(self, calculator):
        """测试空值情况下的缓存键生成"""
        cache_key = calculator._generate_cache_key(
            year=2024,
            month=1,
            machine_ids=None,
            product_types=None,
            calculation_method=CapacityCalculationMethod.THEORETICAL
        )
        
        expected = "2024_1___theoretical"
        assert cache_key == expected
    
    @pytest.mark.asyncio
    async def test_get_work_calendar(self, calculator):
        """测试获取工作日历数据"""
        calendar_data = await calculator._get_work_calendar(2024, 1)
        
        assert calendar_data['year'] == 2024
        assert calendar_data['month'] == 1
        assert calendar_data['working_days'] == 22
        assert calendar_data['working_hours_per_day'] == 24
        assert calendar_data['total_working_hours'] == 528
        assert calendar_data['maintenance_hours'] == 48
        assert calendar_data['available_hours'] == 480
    
    @pytest.mark.asyncio
    async def test_get_machine_configs_all(self, calculator):
        """测试获取所有机台配置"""
        machines = await calculator._get_machine_configs(None)
        
        assert len(machines) == 3
        machine_ids = [m['machine_id'] for m in machines]
        assert 'JBJ001' in machine_ids
        assert 'JBJ002' in machine_ids
        assert 'WSJ001' in machine_ids
    
    @pytest.mark.asyncio
    async def test_get_machine_configs_filtered(self, calculator):
        """测试获取指定机台配置"""
        machines = await calculator._get_machine_configs(['JBJ001'])
        
        assert len(machines) == 1
        assert machines[0]['machine_id'] == 'JBJ001'
        assert machines[0]['machine_name'] == '卷包机1号'
    
    @pytest.mark.asyncio
    async def test_get_monthly_plans(self, calculator):
        """测试获取月度计划"""
        plans = await calculator._get_monthly_plans(2024, 1, None)
        
        assert len(plans) == 2
        plan_ids = [p['plan_id'] for p in plans]
        assert 'MP001' in plan_ids
        assert 'MP002' in plan_ids
    
    @pytest.mark.asyncio
    async def test_get_monthly_plans_filtered(self, calculator):
        """测试获取过滤后的月度计划"""
        plans = await calculator._get_monthly_plans(2024, 1, ['香烟'])
        
        assert len(plans) == 1
        assert plans[0]['product_type'] == '香烟'
    
    @pytest.mark.asyncio
    async def test_calculate_machine_capacity_theoretical(self, calculator):
        """测试理论容量计算"""
        machine = {
            'machine_id': 'JBJ001',
            'machine_name': '卷包机1号',
            'product_type': '香烟',
            'theoretical_speed': 8000,
            'practical_speed': 6800,
            'efficiency_factor': 0.85
        }
        
        work_calendar = {
            'available_hours': 480
        }
        
        monthly_plans = [{
            'plan_id': 'MP001',
            'product_type': '香烟',
            'target_quantity': 500000,
            'allocated_machines': ['JBJ001', 'JBJ002']
        }]
        
        capacity = await calculator._calculate_machine_capacity(
            machine, work_calendar, monthly_plans, CapacityCalculationMethod.THEORETICAL
        )
        
        assert capacity.machine_id == 'JBJ001'
        assert capacity.theoretical_capacity == Decimal('8000')
        assert capacity.practical_capacity == Decimal('8000')  # 理论方法使用theoretical_speed
        assert capacity.available_hours == Decimal('480')
        assert capacity.total_monthly_capacity == Decimal('3840000')  # 8000 * 480
        assert capacity.utilized_capacity == Decimal('250000')  # 500000 / 2 machines
    
    @pytest.mark.asyncio
    async def test_calculate_machine_capacity_practical(self, calculator):
        """测试实际容量计算"""
        machine = {
            'machine_id': 'JBJ001',
            'machine_name': '卷包机1号',
            'product_type': '香烟',
            'theoretical_speed': 8000,
            'practical_speed': 6800,
            'efficiency_factor': 0.85
        }
        
        work_calendar = {
            'available_hours': 480
        }
        
        monthly_plans = []
        
        capacity = await calculator._calculate_machine_capacity(
            machine, work_calendar, monthly_plans, CapacityCalculationMethod.PRACTICAL
        )
        
        assert capacity.practical_capacity == Decimal('6800')  # 实际方法使用practical_speed
        assert capacity.total_monthly_capacity == Decimal('3264000')  # 6800 * 480
        assert capacity.utilized_capacity == Decimal('0')  # 无计划分配
        assert capacity.utilization_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_machine_capacity_optimized(self, calculator):
        """测试优化容量计算"""
        machine = {
            'machine_id': 'JBJ001',
            'machine_name': '卷包机1号',
            'product_type': '香烟',
            'theoretical_speed': 8000,
            'practical_speed': 6800,
            'efficiency_factor': 0.85
        }
        
        work_calendar = {
            'available_hours': 480
        }
        
        monthly_plans = []
        
        capacity = await calculator._calculate_machine_capacity(
            machine, work_calendar, monthly_plans, CapacityCalculationMethod.OPTIMIZED
        )
        
        # 优化方法应该考虑各种影响因子
        factors = CapacityFactors(efficiency_factor=0.85)
        expected_capacity = Decimal('6800') * Decimal(str(factors.overall_factor()))
        
        assert abs(float(capacity.practical_capacity) - float(expected_capacity)) < 1.0
    
    def test_calculate_overall_utilization(self, calculator):
        """测试整体利用率计算"""
        machine_capacities = [
            MachineCapacity(
                machine_id="JBJ001", machine_name="卷包机1号", product_type="香烟",
                theoretical_capacity=Decimal("8000"), practical_capacity=Decimal("6800"),
                available_hours=Decimal("480"), total_monthly_capacity=Decimal("3264000"),
                utilized_capacity=Decimal("2611200"), remaining_capacity=Decimal("652800"),
                utilization_rate=0.8, efficiency_score=85.0, bottleneck_indicators=[],
                capacity_factors=CapacityFactors()
            ),
            MachineCapacity(
                machine_id="JBJ002", machine_name="卷包机2号", product_type="香烟",
                theoretical_capacity=Decimal("8000"), practical_capacity=Decimal("7200"),
                available_hours=Decimal("480"), total_monthly_capacity=Decimal("3456000"),
                utilized_capacity=Decimal("2073600"), remaining_capacity=Decimal("1382400"),
                utilization_rate=0.6, efficiency_score=90.0, bottleneck_indicators=[],
                capacity_factors=CapacityFactors()
            )
        ]
        
        overall_utilization = calculator._calculate_overall_utilization(machine_capacities)
        
        # 预期计算：(2611200 + 2073600) / (3264000 + 3456000) ≈ 0.697
        expected = (2611200 + 2073600) / (3264000 + 3456000)
        assert abs(overall_utilization - expected) < 0.001
    
    def test_calculate_variance(self, calculator):
        """测试方差计算"""
        values = [0.8, 0.6, 0.9, 0.7, 0.85]
        variance = calculator._calculate_variance(values)
        
        # 手动计算方差验证
        mean = sum(values) / len(values)  # 0.78
        expected_variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        assert abs(variance - expected_variance) < 0.001
    
    def test_calculate_variance_edge_cases(self, calculator):
        """测试方差计算边界情况"""
        # 空列表
        assert calculator._calculate_variance([]) == 0.0
        
        # 单个值
        assert calculator._calculate_variance([0.8]) == 0.0
        
        # 相同值
        assert calculator._calculate_variance([0.8, 0.8, 0.8]) == 0.0
    
    def test_calculate_seasonality_factor(self, calculator):
        """测试季节性因子计算"""
        # Q1 (1-3月)
        assert calculator._calculate_seasonality_factor(1) == 0.85  # 1月
        assert calculator._calculate_seasonality_factor(2) == 0.85  # 2月
        assert calculator._calculate_seasonality_factor(3) == 0.85  # 3月
        
        # Q2 (4-6月)
        assert calculator._calculate_seasonality_factor(4) == 0.95  # 4月
        assert calculator._calculate_seasonality_factor(6) == 0.95  # 6月
        
        # Q3 (7-9月)
        assert calculator._calculate_seasonality_factor(7) == 1.05  # 7月
        
        # Q4 (10-12月)
        assert calculator._calculate_seasonality_factor(10) == 1.15  # 10月
        assert calculator._calculate_seasonality_factor(12) == 1.15  # 12月
        
        # 跨年测试
        assert calculator._calculate_seasonality_factor(13) == 0.85  # 13月 = 1月


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])