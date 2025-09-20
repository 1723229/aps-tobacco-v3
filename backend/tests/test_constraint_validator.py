"""
约束验证器测试

测试月度排产约束验证器的所有功能：
- 时间重叠验证
- 产能约束验证
- 机台关系验证
- 维护计划冲突验证
- 工作日历合规性验证
- 全覆盖验证
- 数据完整性验证
- 部分成功评估
"""

import pytest
from datetime import datetime, timedelta, time
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any
import uuid

from app.algorithms.monthly_scheduling.constraint_validator import (
    ConstraintValidator, 
    ValidationLevel
)


class TestConstraintValidator:
    """约束验证器测试类"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return ConstraintValidator()
    
    @pytest.fixture
    def sample_scheduled_results(self):
        """示例排产结果"""
        base_time = datetime(2019, 7, 1, 6, 40, 0)
        
        return [
            {
                'monthly_task_id': 'TASK_001',
                'monthly_plan_id': 'PLAN_001',
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 1000,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': base_time,
                'scheduled_end_time': base_time + timedelta(hours=8),
                'scheduled_duration_hours': 8.0
            },
            {
                'monthly_task_id': 'TASK_002',
                'monthly_plan_id': 'PLAN_002',
                'article_nr': '利群（硬蓝）',
                'target_quantity_boxes': 800,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': base_time + timedelta(hours=8),
                'scheduled_end_time': base_time + timedelta(hours=15),
                'scheduled_duration_hours': 7.0
            },
            {
                'monthly_task_id': 'TASK_003',
                'monthly_plan_id': 'PLAN_003',
                'article_nr': '白沙（硬）',
                'target_quantity_boxes': 1200,
                'assigned_maker_code': 'JBJ02',
                'assigned_feeder_code': 'WSJ02',
                'scheduled_start_time': base_time,
                'scheduled_end_time': base_time + timedelta(hours=10),
                'scheduled_duration_hours': 10.0
            }
        ]
    
    @pytest.fixture
    def sample_monthly_plans(self):
        """示例月度计划"""
        plans = []
        for i, article in enumerate(['利群（软蓝）', '利群（硬蓝）', '白沙（硬）'], 1):
            plan = Mock()
            plan.monthly_plan_id = f'PLAN_{i:03d}'
            plan.article_nr = article
            plan.target_quantity_boxes = [1000, 800, 1200][i-1]
            plans.append(plan)
        return plans
    
    @pytest.fixture
    def sample_machines_data(self):
        """示例机台数据"""
        packing_machines = []
        feeding_machines = []
        
        for i in range(1, 4):
            packing = Mock()
            packing.machine_code = f'JBJ{i:02d}'
            packing.machine_name = f'卷包机{i}'
            packing_machines.append(packing)
            
            feeding = Mock()
            feeding.machine_code = f'WSJ{i:02d}'
            feeding.machine_name = f'喂丝机{i}'
            feeding_machines.append(feeding)
        
        return {
            'packing': packing_machines,
            'feeding': feeding_machines
        }
    
    @pytest.fixture
    def sample_machine_relations(self):
        """示例机台关系"""
        return {
            'maker_to_feeder': {
                'JBJ01': 'WSJ01',
                'JBJ02': 'WSJ02',
                'JBJ03': 'WSJ03'
            },
            'feeder_to_makers': {
                'WSJ01': ['JBJ01'],
                'WSJ02': ['JBJ02'],
                'WSJ03': ['JBJ03']
            }
        }
    
    @pytest.fixture
    def sample_capacity_matrix(self):
        """示例产能矩阵"""
        return {
            ('JBJ01', '利群（软蓝）'): {
                'can_complete': True,
                'required_hours': 8.0,
                'available_hours': 17.0,
                'speed_per_hour': 125.0,
                'actual_speed': 125.0,
                'utilization_rate': 0.8
            },
            ('JBJ01', '利群（硬蓝）'): {
                'can_complete': True,
                'required_hours': 7.0,
                'available_hours': 17.0,
                'speed_per_hour': 114.3,
                'actual_speed': 114.3,
                'utilization_rate': 0.8
            },
            ('JBJ02', '白沙（硬）'): {
                'can_complete': True,
                'required_hours': 10.0,
                'available_hours': 17.0,
                'speed_per_hour': 120.0,
                'actual_speed': 120.0,
                'utilization_rate': 0.8
            }
        }
    
    @pytest.fixture
    def sample_work_calendar(self):
        """示例工作日历"""
        work_days = []
        start_date = datetime(2019, 7, 1).date()
        
        for i in range(31):  # 7月份31天
            current_date = start_date + timedelta(days=i)
            # 假设周一到周五为工作日
            is_working = current_date.weekday() < 5
            
            work_days.append({
                'date': current_date,
                'is_working': is_working,
                'holiday_name': None if is_working else '周末'
            })
        
        return {
            'work_days': work_days,
            'statistics': {
                'total_days': 31,
                'working_days': sum(1 for day in work_days if day['is_working']),
                'holidays': sum(1 for day in work_days if not day['is_working'])
            }
        }
    
    @pytest.fixture
    def sample_time_windows(self):
        """示例时间窗口"""
        windows = {}
        machines = ['JBJ01', 'JBJ02', 'JBJ03']
        
        for machine_code in machines:
            machine_windows = []
            start_date = datetime(2019, 7, 1)
            
            # 为每个工作日生成两个班次
            for day in range(20):  # 假设20个工作日
                current_date = start_date + timedelta(days=day)
                
                # 早班：6:40-15:40
                machine_windows.append({
                    'start_time': current_date.replace(hour=6, minute=40),
                    'end_time': current_date.replace(hour=15, minute=40),
                    'duration_hours': 9.0,
                    'shift_name': '早班'
                })
                
                # 中班：15:40-24:00
                machine_windows.append({
                    'start_time': current_date.replace(hour=15, minute=40),
                    'end_time': current_date.replace(hour=23, minute=59),
                    'duration_hours': 8.33,
                    'shift_name': '中班'
                })
            
            windows[machine_code] = machine_windows
        
        return windows
    
    @pytest.fixture
    def sample_maintenance_plans(self):
        """示例维护计划"""
        return [
            {
                'machine_code': 'JBJ01',
                'start_time': datetime(2019, 7, 15, 12, 0, 0),
                'end_time': datetime(2019, 7, 15, 14, 0, 0),
                'maintenance_type': '例行维护',
                'description': '卷包机例行维护'
            },
            {
                'machine_code': 'JBJ02',
                'start_time': datetime(2019, 7, 20, 10, 0, 0),
                'end_time': datetime(2019, 7, 20, 12, 0, 0),
                'maintenance_type': '预防维护',
                'description': '预防性维护'
            }
        ]

    def test_validate_time_overlap_no_conflicts(self, validator, sample_scheduled_results):
        """测试时间重叠验证 - 无冲突"""
        result = validator._validate_time_overlap(sample_scheduled_results)
        
        assert result['valid'] is True
        assert len(result['violations']) == 0
        assert result['statistics']['overlap_conflicts'] == 0
        assert result['statistics']['machines_checked'] == 2  # JBJ01和JBJ02

    def test_validate_time_overlap_with_conflicts(self, validator):
        """测试时间重叠验证 - 有冲突"""
        base_time = datetime(2019, 7, 1, 6, 40, 0)
        
        # 创建重叠的排产结果
        conflicting_results = [
            {
                'monthly_task_id': 'TASK_001',
                'article_nr': '利群（软蓝）',
                'assigned_maker_code': 'JBJ01',
                'scheduled_start_time': base_time,
                'scheduled_end_time': base_time + timedelta(hours=8)
            },
            {
                'monthly_task_id': 'TASK_002',
                'article_nr': '利群（硬蓝）',
                'assigned_maker_code': 'JBJ01',
                'scheduled_start_time': base_time + timedelta(hours=6),  # 重叠2小时
                'scheduled_end_time': base_time + timedelta(hours=14)
            }
        ]
        
        result = validator._validate_time_overlap(conflicting_results)
        
        assert result['valid'] is False
        assert len(result['violations']) == 1
        assert result['violations'][0]['level'] == ValidationLevel.CRITICAL
        assert result['violations'][0]['type'] == 'TIME_OVERLAP'
        assert result['statistics']['overlap_conflicts'] == 1

    def test_validate_capacity_constraints_success(self, validator, sample_scheduled_results, sample_capacity_matrix):
        """测试产能约束验证 - 成功"""
        result = validator._validate_capacity_constraints(sample_scheduled_results, sample_capacity_matrix)
        
        assert result['valid'] is True
        assert result['statistics']['capacity_violations'] == 0

    def test_validate_capacity_constraints_exceeded(self, validator, sample_capacity_matrix):
        """测试产能约束验证 - 超出产能"""
        # 修改产能矩阵使其不可完成
        capacity_matrix = sample_capacity_matrix.copy()
        capacity_matrix[('JBJ01', '利群（软蓝）')]['can_complete'] = False
        
        scheduled_results = [{
            'article_nr': '利群（软蓝）',
            'assigned_maker_code': 'JBJ01',
            'target_quantity_boxes': 1000,
            'scheduled_duration_hours': 8.0
        }]
        
        result = validator._validate_capacity_constraints(scheduled_results, capacity_matrix)
        
        assert result['valid'] is False
        assert result['statistics']['capacity_violations'] == 1
        assert any(v['type'] == 'CAPACITY_EXCEEDED' for v in result['violations'])

    def test_validate_machine_relations_success(self, validator, sample_scheduled_results, 
                                              sample_machine_relations, sample_machines_data):
        """测试机台关系验证 - 成功"""
        result = validator._validate_machine_relations(
            sample_scheduled_results, sample_machine_relations, sample_machines_data
        )
        
        assert result['valid'] is True
        assert result['statistics']['relation_violations'] == 0

    def test_validate_machine_relations_incorrect_mapping(self, validator, sample_machine_relations, sample_machines_data):
        """测试机台关系验证 - 错误映射"""
        # 创建错误的机台映射
        wrong_results = [{
            'article_nr': '利群（软蓝）',
            'assigned_maker_code': 'JBJ01',
            'assigned_feeder_code': 'WSJ02',  # 错误的喂丝机
        }]
        
        result = validator._validate_machine_relations(
            wrong_results, sample_machine_relations, sample_machines_data
        )
        
        assert len(result['violations']) > 0
        assert any(v['type'] == 'INCORRECT_FEEDER_MAPPING' for v in result['violations'])

    def test_validate_maintenance_conflicts_no_conflict(self, validator, sample_scheduled_results, sample_maintenance_plans):
        """测试维护计划冲突验证 - 无冲突"""
        result = validator._validate_maintenance_conflicts(sample_scheduled_results, sample_maintenance_plans)
        
        assert result['valid'] is True
        assert result['statistics']['maintenance_conflicts'] == 0

    def test_validate_maintenance_conflicts_with_conflict(self, validator, sample_maintenance_plans):
        """测试维护计划冲突验证 - 有冲突"""
        # 创建与维护计划冲突的排产
        conflicting_results = [{
            'article_nr': '利群（软蓝）',
            'assigned_maker_code': 'JBJ01',
            'scheduled_start_time': datetime(2019, 7, 15, 11, 0, 0),  # 与维护时间重叠
            'scheduled_end_time': datetime(2019, 7, 15, 15, 0, 0)
        }]
        
        result = validator._validate_maintenance_conflicts(conflicting_results, sample_maintenance_plans)
        
        assert result['valid'] is False
        assert result['statistics']['maintenance_conflicts'] == 1
        assert any(v['type'] == 'MAINTENANCE_CONFLICT' for v in result['violations'])

    def test_validate_work_calendar_compliance_success(self, validator, sample_scheduled_results, 
                                                     sample_work_calendar, sample_time_windows):
        """测试工作日历合规性验证 - 成功"""
        result = validator._validate_work_calendar_compliance(
            sample_scheduled_results, sample_work_calendar, sample_time_windows
        )
        
        assert result['valid'] is True
        assert result['statistics']['calendar_violations'] == 0

    def test_validate_work_calendar_compliance_non_working_day(self, validator, sample_work_calendar, sample_time_windows):
        """测试工作日历合规性验证 - 非工作日"""
        # 创建在非工作日的排产
        non_working_results = [{
            'article_nr': '利群（软蓝）',
            'assigned_maker_code': 'JBJ01',
            'scheduled_start_time': datetime(2019, 7, 6, 8, 0, 0),  # 7月6日是周六
            'scheduled_end_time': datetime(2019, 7, 6, 16, 0, 0)
        }]
        
        result = validator._validate_work_calendar_compliance(
            non_working_results, sample_work_calendar, sample_time_windows
        )
        
        assert result['valid'] is False
        assert result['statistics']['calendar_violations'] == 1
        assert any(v['type'] == 'NON_WORKING_DAY' for v in result['violations'])

    def test_validate_full_coverage_success(self, validator, sample_scheduled_results, sample_monthly_plans):
        """测试全覆盖验证 - 成功"""
        result = validator._validate_full_coverage(sample_scheduled_results, sample_monthly_plans)
        
        assert result['valid'] is True
        assert len(result['statistics']['missing_products']) == 0
        assert len(result['statistics']['covered_products']) == 3

    def test_validate_full_coverage_missing_products(self, validator, sample_monthly_plans):
        """测试全覆盖验证 - 缺失产品"""
        # 只有部分产品的排产结果
        partial_results = [{
            'article_nr': '利群（软蓝）',
            'target_quantity_boxes': 1000
        }]
        
        result = validator._validate_full_coverage(partial_results, sample_monthly_plans)
        
        assert len(result['statistics']['missing_products']) == 2  # 缺失2个产品
        assert len(result['statistics']['covered_products']) == 1

    def test_validate_full_coverage_quantity_mismatch(self, validator, sample_monthly_plans):
        """测试全覆盖验证 - 数量不匹配"""
        # 数量不匹配的排产结果
        mismatched_results = [
            {
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 800  # 计划1000，实际800
            },
            {
                'article_nr': '利群（硬蓝）',
                'target_quantity_boxes': 800  # 正确
            },
            {
                'article_nr': '白沙（硬）',
                'target_quantity_boxes': 1500  # 计划1200，实际1500
            }
        ]
        
        result = validator._validate_full_coverage(mismatched_results, sample_monthly_plans)
        
        assert len(result['statistics']['quantity_mismatches']) == 2
        assert len(result['statistics']['over_scheduled_products']) == 1

    def test_validate_data_integrity_success(self, validator, sample_scheduled_results):
        """测试数据完整性验证 - 成功"""
        result = validator._validate_data_integrity(sample_scheduled_results)
        
        assert result['valid'] is True
        assert result['statistics']['integrity_issues'] == 0

    def test_validate_data_integrity_missing_fields(self, validator):
        """测试数据完整性验证 - 缺失字段"""
        incomplete_results = [{
            'article_nr': '利群（软蓝）',
            'assigned_maker_code': 'JBJ01',
            # 缺失 assigned_feeder_code
            'scheduled_start_time': datetime.now(),
            'scheduled_end_time': datetime.now() + timedelta(hours=8)
        }]
        
        result = validator._validate_data_integrity(incomplete_results)
        
        assert result['statistics']['integrity_issues'] > 0
        assert any(v['type'] == 'MISSING_REQUIRED_FIELD' for v in result['violations'])

    def test_validate_data_integrity_invalid_quantity(self, validator):
        """测试数据完整性验证 - 无效数量"""
        invalid_results = [{
            'monthly_plan_id': 'PLAN_001',
            'article_nr': '利群（软蓝）',
            'target_quantity_boxes': -100,  # 无效数量
            'assigned_maker_code': 'JBJ01',
            'assigned_feeder_code': 'WSJ01',
            'scheduled_start_time': datetime.now(),
            'scheduled_end_time': datetime.now() + timedelta(hours=8),
            'scheduled_duration_hours': 8.0
        }]
        
        result = validator._validate_data_integrity(invalid_results)
        
        assert result['valid'] is False
        assert any(v['type'] == 'INVALID_QUANTITY' for v in result['violations'])

    def test_validate_data_integrity_invalid_time_range(self, validator):
        """测试数据完整性验证 - 无效时间范围"""
        base_time = datetime.now()
        invalid_results = [{
            'monthly_plan_id': 'PLAN_001',
            'article_nr': '利群（软蓝）',
            'target_quantity_boxes': 1000,
            'assigned_maker_code': 'JBJ01',
            'assigned_feeder_code': 'WSJ01',
            'scheduled_start_time': base_time,
            'scheduled_end_time': base_time - timedelta(hours=1),  # 结束时间早于开始时间
            'scheduled_duration_hours': 8.0
        }]
        
        result = validator._validate_data_integrity(invalid_results)
        
        assert result['valid'] is False
        assert any(v['type'] == 'INVALID_TIME_RANGE' for v in result['violations'])

    def test_evaluate_partial_success_monthly_mode(self, validator, sample_scheduled_results, sample_monthly_plans):
        """测试部分成功评估 - 月度模式"""
        # 设置月度模式
        validator._validation_config['monthly_mode'] = True
        
        validation_result = {
            'valid': False,
            'critical_violations': 5,
            'violation_details': []
        }
        
        # 月度模式下应该通过部分成功评估
        result = validator._evaluate_partial_success(
            validation_result, sample_scheduled_results, sample_monthly_plans
        )
        
        assert result is True

    def test_evaluate_partial_success_no_results(self, validator, sample_monthly_plans):
        """测试部分成功评估 - 无排产结果"""
        validator._validation_config['monthly_mode'] = True
        
        validation_result = {
            'valid': False,
            'critical_violations': 0,
            'violation_details': []
        }
        
        result = validator._evaluate_partial_success(
            validation_result, [], sample_monthly_plans
        )
        
        assert result is False

    def test_evaluate_partial_success_blocking_errors(self, validator, sample_scheduled_results, sample_monthly_plans):
        """测试部分成功评估 - 阻塞性错误"""
        validator._validation_config['monthly_mode'] = True
        
        validation_result = {
            'valid': False,
            'critical_violations': 1,
            'violation_details': [{
                'type': 'TIME_OVERLAP',
                'level': ValidationLevel.CRITICAL
            }]
        }
        
        result = validator._evaluate_partial_success(
            validation_result, sample_scheduled_results, sample_monthly_plans
        )
        
        assert result is False

    def test_complete_validation_pipeline(self, validator, sample_scheduled_results, sample_monthly_plans,
                                        sample_machines_data, sample_machine_relations, sample_time_windows,
                                        sample_capacity_matrix, sample_work_calendar, sample_maintenance_plans):
        """测试完整的验证管道"""
        result = validator.validate_scheduling_results(
            scheduled_results=sample_scheduled_results,
            monthly_plans=sample_monthly_plans,
            machines_data=sample_machines_data,
            machine_relations=sample_machine_relations,
            time_windows=sample_time_windows,
            capacity_matrix=sample_capacity_matrix,
            work_calendar=sample_work_calendar,
            maintenance_plans=sample_maintenance_plans,
            validation_config={
                'strict_mode': False,
                'monthly_mode': True
            }
        )
        
        assert 'valid' in result
        assert 'total_violations' in result
        assert 'critical_violations' in result
        assert 'warning_violations' in result
        assert 'validation_summary' in result
        assert 'violation_details' in result
        assert 'recommendations' in result

    def test_validation_summary_generation(self, validator, sample_scheduled_results, sample_monthly_plans,
                                         sample_machines_data, sample_machine_relations, sample_time_windows,
                                         sample_capacity_matrix, sample_work_calendar, sample_maintenance_plans):
        """测试验证摘要生成"""
        result = validator.validate_scheduling_results(
            scheduled_results=sample_scheduled_results,
            monthly_plans=sample_monthly_plans,
            machines_data=sample_machines_data,
            machine_relations=sample_machine_relations,
            time_windows=sample_time_windows,
            capacity_matrix=sample_capacity_matrix,
            work_calendar=sample_work_calendar,
            maintenance_plans=sample_maintenance_plans
        )
        
        summary = validator.get_validation_summary(result)
        
        assert "=== 约束验证摘要报告 ===" in summary
        assert "验证状态:" in summary
        assert "总违规数:" in summary
        assert "优化建议" in summary or "所有约束验证通过" in summary

    def test_violation_report_export(self, validator, sample_scheduled_results, sample_monthly_plans,
                                   sample_machines_data, sample_machine_relations, sample_time_windows,
                                   sample_capacity_matrix, sample_work_calendar, sample_maintenance_plans):
        """测试违规报告导出"""
        result = validator.validate_scheduling_results(
            scheduled_results=sample_scheduled_results,
            monthly_plans=sample_monthly_plans,
            machines_data=sample_machines_data,
            machine_relations=sample_machine_relations,
            time_windows=sample_time_windows,
            capacity_matrix=sample_capacity_matrix,
            work_calendar=sample_work_calendar,
            maintenance_plans=sample_maintenance_plans
        )
        
        report = validator.export_violation_report(result)
        
        assert 'report_timestamp' in report
        assert 'validation_status' in report
        assert 'summary_statistics' in report
        assert 'validation_details' in report
        assert 'violation_list' in report
        assert 'recommendations' in report
        assert 'validation_config' in report

    def test_time_ranges_overlap_utility(self, validator):
        """测试时间范围重叠工具函数"""
        start1 = datetime(2019, 7, 1, 8, 0, 0)
        end1 = datetime(2019, 7, 1, 16, 0, 0)
        
        start2 = datetime(2019, 7, 1, 14, 0, 0)  # 重叠
        end2 = datetime(2019, 7, 1, 22, 0, 0)
        
        assert validator._time_ranges_overlap(start1, end1, start2, end2) is True
        
        start3 = datetime(2019, 7, 1, 16, 0, 0)  # 不重叠
        end3 = datetime(2019, 7, 1, 24, 0, 0)
        
        assert validator._time_ranges_overlap(start1, end1, start3, end3) is False

    def test_validation_config_update(self, validator):
        """测试验证配置更新"""
        original_config = validator._validation_config.copy()
        
        new_config = {
            'strict_mode': True,
            'tolerance_minutes': 10,
            'monthly_mode': False
        }
        
        # 通过验证调用更新配置
        validator.validate_scheduling_results(
            scheduled_results=[],
            monthly_plans=[],
            machines_data={'packing': [], 'feeding': []},
            machine_relations={'maker_to_feeder': {}},
            time_windows={},
            capacity_matrix={},
            work_calendar={'work_days': []},
            maintenance_plans=[],
            validation_config=new_config
        )
        
        # 验证配置已更新
        assert validator._validation_config['strict_mode'] is True
        assert validator._validation_config['tolerance_minutes'] == 10
        assert validator._validation_config['monthly_mode'] is False

    def test_split_product_quantity_aggregation(self, validator, sample_monthly_plans):
        """测试拆分产品的数量聚合"""
        # 创建拆分产品的排产结果
        split_results = [
            {
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 600,  # 第一部分
                'split_info': {'is_split_product': True, 'split_index': 1}
            },
            {
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 400,  # 第二部分
                'split_info': {'is_split_product': True, 'split_index': 2}
            },
            {
                'article_nr': '利群（硬蓝）',
                'target_quantity_boxes': 800,  # 正常产品
            }
        ]
        
        result = validator._validate_full_coverage(split_results, sample_monthly_plans)
        
        # 验证数量正确聚合：利群（软蓝）应该是600+400=1000
        covered_products = result['statistics']['covered_products']
        luqun_soft = next((p for p in covered_products if p['article_nr'] == '利群（软蓝）'), None)
        
        assert luqun_soft is not None
        assert len(result['statistics']['missing_products']) == 1  # 只有白沙（硬）缺失


class TestConstraintValidatorErrorHandling:
    """约束验证器错误处理测试"""
    
    def test_validation_with_empty_data(self):
        """测试空数据验证"""
        validator = ConstraintValidator()
        
        result = validator.validate_scheduling_results(
            scheduled_results=[],
            monthly_plans=[],
            machines_data={'packing': [], 'feeding': []},
            machine_relations={'maker_to_feeder': {}},
            time_windows={},
            capacity_matrix={},
            work_calendar={'work_days': []},
            maintenance_plans=[]
        )
        
        assert 'valid' in result
        assert result['total_violations'] == 0

    def test_validation_with_malformed_data(self):
        """测试格式错误数据验证"""
        validator = ConstraintValidator()
        
        # 创建格式错误的排产结果
        malformed_results = [
            {
                'article_nr': '利群（软蓝）',
                # 缺失必要字段
            }
        ]
        
        try:
            result = validator.validate_scheduling_results(
                scheduled_results=malformed_results,
                monthly_plans=[],
                machines_data={'packing': [], 'feeding': []},
                machine_relations={'maker_to_feeder': {}},
                time_windows={},
                capacity_matrix={},
                work_calendar={'work_days': []},
                maintenance_plans=[]
            )
            
            # 应该能够处理格式错误而不崩溃
            assert 'valid' in result
            
        except Exception as e:
            pytest.fail(f"验证器应该能够处理格式错误的数据，但抛出了异常: {str(e)}")

    def test_validation_exception_handling(self, mocker):
        """测试验证过程中的异常处理"""
        validator = ConstraintValidator()
        
        # 模拟时间重叠验证抛出异常
        mocker.patch.object(validator, '_validate_time_overlap', side_effect=Exception("模拟错误"))
        
        result = validator.validate_scheduling_results(
            scheduled_results=[],
            monthly_plans=[],
            machines_data={'packing': [], 'feeding': []},
            machine_relations={'maker_to_feeder': {}},
            time_windows={},
            capacity_matrix={},
            work_calendar={'work_days': []},
            maintenance_plans=[]
        )
        
        assert result['valid'] is False
        assert 'error' in result
        assert "模拟错误" in result['error']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])