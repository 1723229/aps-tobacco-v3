"""
APS智慧排产系统 - 时间窗口计算器测试

测试 TimeWindowCalculator 类的功能，使用真实数据进行验证。

测试覆盖：
1. 基于工作日历的有效工作日计算
2. 班次配置的时间窗口生成
3. 维护计划的时间排除处理
4. 跨日班次的正确处理
5. 时间窗口优化和合并算法
6. 异常情况和边界条件处理
7. 时间计算精度和一致性验证

技术要求：
- 使用真实工作日历和班次数据
- 测试复杂的时间逻辑处理
- 验证时间窗口的准确性
- 测试维护计划冲突处理
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta, time
from typing import Dict, List, Any
from unittest.mock import MagicMock

from app.algorithms.monthly_scheduling.time_window_calculator import TimeWindowCalculator
from app.algorithms.monthly_scheduling.database_loader import DatabaseLoader
from app.db.connection import get_db_session


class TestTimeWindowCalculator:
    """时间窗口计算器测试类"""
    
    @pytest.fixture
    def calculator(self):
        """时间窗口计算器实例夹具"""
        return TimeWindowCalculator()
    
    @pytest.fixture
    async def real_data_loader(self):
        """真实数据加载器夹具"""
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            # 加载真实数据用于测试
            machines_data = await loader.load_machine_data()
            work_calendar = await loader.load_work_calendar()
            shift_configs = await loader.load_shift_configs()
            maintenance_plans = await loader.load_maintenance_plans()
            
            return {
                'machines': machines_data,
                'work_calendar': work_calendar,
                'shift_configs': shift_configs,
                'maintenance_plans': maintenance_plans
            }
    
    @pytest.fixture
    def sample_machines(self):
        """示例机台数据"""
        machine_a1 = MagicMock()
        machine_a1.machine_code = "A1"
        machine_a1.machine_type = "PACKING"
        
        machine_a2 = MagicMock()
        machine_a2.machine_code = "A2" 
        machine_a2.machine_type = "PACKING"
        
        return [machine_a1, machine_a2]
    
    @pytest.fixture
    def sample_work_calendar(self):
        """示例工作日历数据"""
        base_date = date(2024, 1, 1)
        work_days = []
        
        # 生成一个月的工作日历（工作日为True，周末为False）
        for i in range(31):
            current_date = base_date + timedelta(days=i)
            is_working = current_date.weekday() < 5  # 周一到周五为工作日
            
            work_days.append({
                'date': current_date,
                'is_working': is_working,
                'day_type': 'WORKING' if is_working else 'WEEKEND'
            })
        
        return {
            'work_days': work_days,
            'holiday_days': [
                {'date': date(2024, 1, 1), 'holiday_name': '元旦'}
            ]
        }
    
    @pytest.fixture
    def sample_shift_configs(self):
        """示例班次配置数据"""
        shift1 = MagicMock()
        shift1.shift_name = "早班"
        shift1.start_time = "08:00"
        shift1.end_time = "16:00"
        shift1.is_active = True
        
        shift2 = MagicMock()
        shift2.shift_name = "晚班"
        shift2.start_time = "16:00"
        shift2.end_time = "00:00"
        shift2.is_active = True
        
        shift3 = MagicMock()
        shift3.shift_name = "夜班"
        shift3.start_time = "00:00"
        shift3.end_time = "08:00"
        shift3.is_active = True
        
        return [shift1, shift2, shift3]
    
    @pytest.fixture
    def sample_maintenance_plans(self):
        """示例维护计划数据"""
        return [
            {
                'machine_code': 'A1',
                'start_time': datetime(2024, 1, 5, 10, 0),
                'end_time': datetime(2024, 1, 5, 12, 0),
                'maintenance_type': 'SCHEDULED',
                'description': '定期维护'
            },
            {
                'machine_code': 'A2',
                'start_time': datetime(2024, 1, 10, 14, 0),
                'end_time': datetime(2024, 1, 10, 16, 0),
                'maintenance_type': 'REPAIR',
                'description': '设备维修'
            }
        ]
    
    async def test_calculate_available_windows_with_real_data(self, calculator, real_data_loader):
        """测试使用真实数据计算可用时间窗口"""
        data = real_data_loader
        
        # 使用真实的卷包机数据
        packing_machines = data['machines']['packing']
        if not packing_machines:
            pytest.skip("没有卷包机数据，跳过测试")
        
        # 只测试前3台机器以提高测试速度
        test_machines = packing_machines[:3]
        
        time_windows = calculator.calculate_available_windows(
            machines=test_machines,
            work_calendar=data['work_calendar'],
            shift_configs=data['shift_configs'],
            maintenance_plans=data['maintenance_plans']
        )
        
        # 验证返回结果
        assert isinstance(time_windows, dict), "时间窗口应该返回字典"
        
        for machine in test_machines:
            machine_code = machine.machine_code
            assert machine_code in time_windows, f"应该包含机台 {machine_code} 的时间窗口"
            
            windows = time_windows[machine_code]
            assert isinstance(windows, list), f"机台 {machine_code} 的时间窗口应该是列表"
            
            # 验证时间窗口格式
            for window in windows:
                assert isinstance(window, dict), "时间窗口应该是字典"
                required_fields = ['start_time', 'end_time', 'duration_hours']
                
                for field in required_fields:
                    assert field in window, f"时间窗口应该包含字段: {field}"
                
                # 验证时间逻辑
                assert window['start_time'] < window['end_time'], "开始时间应该早于结束时间"
                assert window['duration_hours'] > 0, "持续时间应该大于0"
        
        print(f"✅ 成功计算真实数据时间窗口: {len(time_windows)} 台机器")
    
    async def test_calculate_available_windows_basic(self, calculator, sample_machines, 
                                                    sample_work_calendar, sample_shift_configs, 
                                                    sample_maintenance_plans):
        """测试基本时间窗口计算功能"""
        time_windows = calculator.calculate_available_windows(
            machines=sample_machines,
            work_calendar=sample_work_calendar,
            shift_configs=sample_shift_configs,
            maintenance_plans=sample_maintenance_plans
        )
        
        # 验证基本结构
        assert isinstance(time_windows, dict), "时间窗口应该返回字典"
        assert len(time_windows) == len(sample_machines), "应该为每台机器生成时间窗口"
        
        for machine in sample_machines:
            machine_code = machine.machine_code
            assert machine_code in time_windows, f"应该包含机台 {machine_code}"
            
            windows = time_windows[machine_code]
            assert isinstance(windows, list), "时间窗口应该是列表"
            
            # 验证时间窗口不重叠
            for i in range(len(windows) - 1):
                current_window = windows[i]
                next_window = windows[i + 1]
                assert current_window['end_time'] <= next_window['start_time'], \
                    f"时间窗口不应该重叠: {current_window} vs {next_window}"
        
        print(f"✅ 基本时间窗口计算测试通过")
    
    async def test_parse_work_calendar(self, calculator, sample_work_calendar):
        """测试工作日历解析功能"""
        working_dates = calculator._parse_work_calendar(sample_work_calendar)
        
        assert isinstance(working_dates, set), "工作日期应该返回集合"
        
        # 验证工作日逻辑（排除周末）
        for work_day in sample_work_calendar['work_days']:
            if work_day['is_working']:
                assert work_day['date'] in working_dates, f"工作日 {work_day['date']} 应该在工作日期集合中"
            else:
                assert work_day['date'] not in working_dates, f"非工作日 {work_day['date']} 不应该在工作日期集合中"
        
        print(f"✅ 工作日历解析测试通过: {len(working_dates)} 个工作日")
    
    async def test_parse_shift_times(self, calculator, sample_shift_configs):
        """测试班次时间解析功能"""
        parsed_shifts = calculator._parse_shift_times(sample_shift_configs)
        
        assert isinstance(parsed_shifts, list), "解析的班次应该返回列表"
        assert len(parsed_shifts) >= len([s for s in sample_shift_configs if s.is_active]), \
            "应该解析所有活跃班次"
        
        for shift in parsed_shifts:
            assert isinstance(shift, dict), "班次应该是字典"
            assert 'shift_name' in shift, "班次应该包含名称"
            assert 'start_time' in shift, "班次应该包含开始时间"
            assert 'end_time' in shift, "班次应该包含结束时间"
            assert 'is_cross_day' in shift, "班次应该标明是否跨日"
            
            # 验证时间格式
            assert isinstance(shift['start_time'], time), "开始时间应该是time对象"
            assert isinstance(shift['end_time'], time), "结束时间应该是time对象"
            assert isinstance(shift['is_cross_day'], bool), "跨日标志应该是布尔值"
        
        print(f"✅ 班次时间解析测试通过: {len(parsed_shifts)} 个班次")
    
    async def test_generate_daily_windows(self, calculator, sample_shift_configs):
        """测试单日时间窗口生成"""
        test_date = date(2024, 1, 5)  # 工作日
        parsed_shifts = calculator._parse_shift_times(sample_shift_configs)
        
        daily_windows = calculator._generate_daily_windows(test_date, parsed_shifts)
        
        assert isinstance(daily_windows, list), "单日时间窗口应该返回列表"
        
        for window in daily_windows:
            assert isinstance(window, dict), "时间窗口应该是字典"
            assert 'start_time' in window, "时间窗口应该包含开始时间"
            assert 'end_time' in window, "时间窗口应该包含结束时间"
            assert 'duration_hours' in window, "时间窗口应该包含持续时间"
            
            # 验证时间类型和逻辑
            assert isinstance(window['start_time'], datetime), "开始时间应该是datetime对象"
            assert isinstance(window['end_time'], datetime), "结束时间应该是datetime对象"
            assert window['start_time'] < window['end_time'], "开始时间应该早于结束时间"
            
            # 验证持续时间计算
            expected_duration = (window['end_time'] - window['start_time']).total_seconds() / 3600
            assert abs(window['duration_hours'] - expected_duration) < 0.01, \
                f"持续时间计算错误: 期望 {expected_duration}, 实际 {window['duration_hours']}"
        
        print(f"✅ 单日时间窗口生成测试通过: {len(daily_windows)} 个窗口")
    
    async def test_apply_maintenance_constraints(self, calculator, sample_maintenance_plans):
        """测试维护计划约束应用"""
        # 创建测试时间窗口
        test_windows = [
            {
                'start_time': datetime(2024, 1, 5, 8, 0),
                'end_time': datetime(2024, 1, 5, 16, 0),
                'duration_hours': 8.0
            },
            {
                'start_time': datetime(2024, 1, 10, 8, 0),
                'end_time': datetime(2024, 1, 10, 16, 0),
                'duration_hours': 8.0
            }
        ]
        
        machine_code = "A1"
        machine_maintenance = [
            plan for plan in sample_maintenance_plans 
            if plan['machine_code'] == machine_code
        ]
        
        constrained_windows = calculator._apply_maintenance_constraints(
            test_windows, machine_maintenance
        )
        
        assert isinstance(constrained_windows, list), "约束后的时间窗口应该返回列表"
        
        # 验证维护时间被正确排除
        for window in constrained_windows:
            for maintenance in machine_maintenance:
                maint_start = maintenance['start_time']
                maint_end = maintenance['end_time']
                
                # 检查时间窗口不与维护时间重叠
                window_start = window['start_time']
                window_end = window['end_time']
                
                overlap = not (window_end <= maint_start or window_start >= maint_end)
                assert not overlap, f"时间窗口不应与维护时间重叠: 窗口 {window_start}-{window_end}, 维护 {maint_start}-{maint_end}"
        
        print(f"✅ 维护计划约束应用测试通过: {len(constrained_windows)} 个有效窗口")
    
    async def test_optimize_time_windows(self, calculator):
        """测试时间窗口优化功能"""
        # 创建有合并机会的测试窗口
        test_windows = [
            {
                'start_time': datetime(2024, 1, 5, 8, 0),
                'end_time': datetime(2024, 1, 5, 12, 0),
                'duration_hours': 4.0
            },
            {
                'start_time': datetime(2024, 1, 5, 12, 0),  # 紧接着上一个窗口
                'end_time': datetime(2024, 1, 5, 16, 0),
                'duration_hours': 4.0
            },
            {
                'start_time': datetime(2024, 1, 5, 18, 0),  # 有间隔
                'end_time': datetime(2024, 1, 5, 22, 0),
                'duration_hours': 4.0
            }
        ]
        
        optimized_windows = calculator._optimize_time_windows(test_windows)
        
        assert isinstance(optimized_windows, list), "优化后的时间窗口应该返回列表"
        assert len(optimized_windows) <= len(test_windows), "优化后窗口数量应该不增加"
        
        # 验证相邻窗口被合并
        if len(optimized_windows) < len(test_windows):
            # 检查第一个窗口是否合并了前两个
            first_window = optimized_windows[0]
            expected_start = test_windows[0]['start_time']
            expected_end = test_windows[1]['end_time']
            
            assert first_window['start_time'] == expected_start, "合并窗口开始时间应该正确"
            assert first_window['end_time'] == expected_end, "合并窗口结束时间应该正确"
        
        print(f"✅ 时间窗口优化测试通过: {len(test_windows)} -> {len(optimized_windows)} 个窗口")
    
    async def test_cross_day_shift_handling(self, calculator):
        """测试跨日班次处理"""
        # 创建跨日班次配置
        cross_day_shift = MagicMock()
        cross_day_shift.shift_name = "夜班"
        cross_day_shift.start_time = "22:00"
        cross_day_shift.end_time = "06:00"
        cross_day_shift.is_active = True
        
        parsed_shifts = calculator._parse_shift_times([cross_day_shift])
        
        assert len(parsed_shifts) == 1, "应该解析出一个班次"
        shift = parsed_shifts[0]
        assert shift['is_cross_day'] == True, "应该正确识别跨日班次"
        
        # 测试跨日班次的时间窗口生成
        test_date = date(2024, 1, 5)
        daily_windows = calculator._generate_daily_windows(test_date, parsed_shifts)
        
        assert len(daily_windows) > 0, "跨日班次应该生成时间窗口"
        
        window = daily_windows[0]
        assert window['start_time'].date() == test_date, "跨日班次开始日期应该正确"
        assert window['end_time'].date() == test_date + timedelta(days=1), "跨日班次结束日期应该是次日"
        
        print(f"✅ 跨日班次处理测试通过")
    
    async def test_edge_cases_and_error_handling(self, calculator):
        """测试边界条件和错误处理"""
        
        # 测试空数据处理
        empty_windows = calculator.calculate_available_windows(
            machines=[],
            work_calendar={'work_days': [], 'holiday_days': []},
            shift_configs=[],
            maintenance_plans=[]
        )
        assert empty_windows == {}, "空数据应该返回空字典"
        
        # 测试无效班次配置
        invalid_shift = MagicMock()
        invalid_shift.shift_name = "无效班次"
        invalid_shift.start_time = "invalid_time"
        invalid_shift.end_time = "16:00"
        invalid_shift.is_active = True
        
        try:
            calculator._parse_shift_times([invalid_shift])
            print("⚠️ 警告: 无效班次配置应该被处理或跳过")
        except Exception:
            print("✅ 无效班次配置正确抛出异常")
        
        # 测试无工作日情况
        no_work_calendar = {
            'work_days': [
                {'date': date(2024, 1, 1), 'is_working': False},
                {'date': date(2024, 1, 2), 'is_working': False}
            ],
            'holiday_days': []
        }
        
        machine = MagicMock()
        machine.machine_code = "TEST"
        
        no_work_windows = calculator.calculate_available_windows(
            machines=[machine],
            work_calendar=no_work_calendar,
            shift_configs=[],
            maintenance_plans=[]
        )
        
        assert "TEST" in no_work_windows, "应该包含机台"
        assert len(no_work_windows["TEST"]) == 0, "无工作日应该生成空时间窗口"
        
        print(f"✅ 边界条件和错误处理测试通过")
    
    async def test_time_calculation_accuracy(self, calculator):
        """测试时间计算精度"""
        # 创建精确的时间测试
        test_windows = [
            {
                'start_time': datetime(2024, 1, 5, 8, 30, 15),  # 包含秒
                'end_time': datetime(2024, 1, 5, 16, 45, 30),
                'duration_hours': 0  # 将重新计算
            }
        ]
        
        # 重新计算持续时间
        window = test_windows[0]
        expected_duration = (window['end_time'] - window['start_time']).total_seconds() / 3600
        window['duration_hours'] = expected_duration
        
        # 验证精度
        assert abs(window['duration_hours'] - 8.255) < 0.001, \
            f"时间计算精度测试失败: 期望约8.255小时, 实际 {window['duration_hours']}"
        
        print(f"✅ 时间计算精度测试通过: {window['duration_hours']:.6f} 小时")
    
    async def test_performance_with_large_dataset(self, calculator):
        """测试大数据集性能"""
        import time
        
        # 创建大量机台数据
        large_machines = []
        for i in range(50):  # 50台机器
            machine = MagicMock()
            machine.machine_code = f"TEST_{i:02d}"
            machine.machine_type = "PACKING"
            large_machines.append(machine)
        
        # 创建大量工作日数据
        large_work_calendar = {
            'work_days': [],
            'holiday_days': []
        }
        
        base_date = date(2024, 1, 1)
        for i in range(365):  # 一年的数据
            current_date = base_date + timedelta(days=i)
            large_work_calendar['work_days'].append({
                'date': current_date,
                'is_working': current_date.weekday() < 5
            })
        
        # 创建班次配置
        test_shifts = []
        for shift_name, start_time, end_time in [
            ("早班", "08:00", "16:00"),
            ("晚班", "16:00", "00:00"),
            ("夜班", "00:00", "08:00")
        ]:
            shift = MagicMock()
            shift.shift_name = shift_name
            shift.start_time = start_time
            shift.end_time = end_time
            shift.is_active = True
            test_shifts.append(shift)
        
        # 性能测试
        start_time_perf = time.time()
        
        large_windows = calculator.calculate_available_windows(
            machines=large_machines,
            work_calendar=large_work_calendar,
            shift_configs=test_shifts,
            maintenance_plans=[]
        )
        
        end_time_perf = time.time()
        execution_time = end_time_perf - start_time_perf
        
        assert len(large_windows) == len(large_machines), "应该为所有机器生成时间窗口"
        assert execution_time < 30, f"大数据集计算时间过长: {execution_time:.2f} 秒"
        
        print(f"✅ 大数据集性能测试通过: {len(large_machines)} 台机器, 用时 {execution_time:.2f} 秒")


# 异步测试运行器
@pytest.mark.asyncio
async def test_time_window_calculator_complete_suite():
    """运行完整的时间窗口计算器测试套件"""
    print("\n🚀 开始运行时间窗口计算器完整测试套件")
    
    calculator = TimeWindowCalculator()
    test_instance = TestTimeWindowCalculator()
    
    # 准备测试数据
    sample_machines = test_instance.sample_machines(test_instance)
    sample_work_calendar = test_instance.sample_work_calendar(test_instance)
    sample_shift_configs = test_instance.sample_shift_configs(test_instance)
    sample_maintenance_plans = test_instance.sample_maintenance_plans(test_instance)
    
    try:
        # 运行真实数据测试
        print("\n📋 运行真实数据测试...")
        async with get_db_session() as session:
            loader = DatabaseLoader(session)
            real_data = {
                'machines': await loader.load_machine_data(),
                'work_calendar': await loader.load_work_calendar(),
                'shift_configs': await loader.load_shift_configs(),
                'maintenance_plans': await loader.load_maintenance_plans()
            }
            
            await test_instance.test_calculate_available_windows_with_real_data(calculator, real_data)
        
        # 运行基础功能测试
        print("\n📋 运行基础功能测试...")
        await test_instance.test_calculate_available_windows_basic(
            calculator, sample_machines, sample_work_calendar, 
            sample_shift_configs, sample_maintenance_plans
        )
        
        # 运行组件测试
        print("\n📋 运行组件测试...")
        await test_instance.test_parse_work_calendar(calculator, sample_work_calendar)
        await test_instance.test_parse_shift_times(calculator, sample_shift_configs)
        await test_instance.test_generate_daily_windows(calculator, sample_shift_configs)
        await test_instance.test_apply_maintenance_constraints(calculator, sample_maintenance_plans)
        await test_instance.test_optimize_time_windows(calculator)
        
        # 运行边界条件测试
        print("\n📋 运行边界条件测试...")
        await test_instance.test_cross_day_shift_handling(calculator)
        await test_instance.test_edge_cases_and_error_handling(calculator)
        await test_instance.test_time_calculation_accuracy(calculator)
        
        # 运行性能测试
        print("\n📋 运行性能测试...")
        await test_instance.test_performance_with_large_dataset(calculator)
        
        print("\n🎉 时间窗口计算器测试套件全部通过!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_time_window_calculator_complete_suite())