"""
结果处理器测试

测试月度排产结果处理器的所有功能：
- 排产结果处理和验证
- 机台关系映射和验证
- 数据库保存操作
- 结果格式化和优化
- 错误处理和恢复
- 批量操作处理
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.algorithms.monthly_scheduling.result_processor import ResultProcessor
from app.models.monthly_schedule_result_models import MonthlyScheduleResult


class TestResultProcessor:
    """结果处理器测试类"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """创建模拟数据库会话"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.execute = AsyncMock()
        return mock_session
    
    @pytest.fixture
    def result_processor(self, mock_db_session):
        """创建结果处理器实例"""
        return ResultProcessor(mock_db_session)
    
    @pytest.fixture
    def sample_scheduled_results(self):
        """示例排产结果"""
        base_time = datetime(2019, 7, 1, 6, 40, 0)
        
        return [
            {
                'monthly_task_id': 'TASK_20190701_001',
                'monthly_plan_id': 'PLAN_001',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': 'WO_001',
                'article_nr': '利群（软蓝）',
                'article_name': '利群（软蓝）',
                'target_quantity_boxes': 1000,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': base_time,
                'scheduled_end_time': base_time + timedelta(hours=8),
                'scheduled_duration_hours': 8.0,
                'estimated_speed': 125.0,
                'efficiency_rate': 100.0,
                'utilization_rate': 0.8,
                'algorithm_version': 'v2.0_complete',
                'priority_score': 85.5,
                'calculation_details': {
                    'base_speed': 125.0,
                    'actual_speed': 125.0,
                    'required_hours': 8.0,
                    'available_hours': 17.0
                }
            },
            {
                'monthly_task_id': 'TASK_20190701_002',
                'monthly_plan_id': 'PLAN_002',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': 'WO_002',
                'article_nr': '利群（硬蓝）',
                'article_name': '利群（硬蓝）',
                'target_quantity_boxes': 800,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': base_time + timedelta(hours=8),
                'scheduled_end_time': base_time + timedelta(hours=15),
                'scheduled_duration_hours': 7.0,
                'estimated_speed': 114.3,
                'efficiency_rate': 100.0,
                'utilization_rate': 0.8,
                'algorithm_version': 'v2.0_complete',
                'priority_score': 78.2,
                'calculation_details': {
                    'base_speed': 114.3,
                    'actual_speed': 114.3,
                    'required_hours': 7.0,
                    'available_hours': 17.0
                }
            },
            {
                'monthly_task_id': 'TASK_20190701_003',
                'monthly_plan_id': 'PLAN_003',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': 'WO_003',
                'article_nr': '白沙（硬）',
                'article_name': '白沙（硬）',
                'target_quantity_boxes': 1200,
                'assigned_maker_code': 'JBJ02',
                'assigned_feeder_code': 'WSJ02',
                'scheduled_start_time': base_time,
                'scheduled_end_time': base_time + timedelta(hours=10),
                'scheduled_duration_hours': 10.0,
                'estimated_speed': 120.0,
                'efficiency_rate': 100.0,
                'utilization_rate': 0.8,
                'algorithm_version': 'v2.0_complete',
                'priority_score': 92.1,
                'calculation_details': {
                    'base_speed': 120.0,
                    'actual_speed': 120.0,
                    'required_hours': 10.0,
                    'available_hours': 17.0
                }
            }
        ]
    
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
    def sample_validation_result(self):
        """示例验证结果"""
        return {
            'valid': True,
            'total_violations': 0,
            'critical_violations': 0,
            'warning_violations': 0,
            'validation_summary': {
                '时间重叠验证': {'valid': True, 'critical_violations': 0},
                '产能约束验证': {'valid': True, 'critical_violations': 0},
                '机台关系验证': {'valid': True, 'critical_violations': 0}
            },
            'recommendations': ['所有约束验证通过，排产结果符合要求']
        }

    @pytest.mark.asyncio
    async def test_process_scheduling_results_success(self, result_processor, sample_scheduled_results,
                                                    sample_machine_relations, sample_validation_result):
        """测试排产结果处理 - 成功"""
        monthly_batch_id = 'MONTHLY_20190701_001'
        task_id = 'TASK_20190701_001'
        
        result = await result_processor.process_scheduling_results(
            scheduled_results=sample_scheduled_results,
            monthly_batch_id=monthly_batch_id,
            task_id=task_id,
            machine_relations=sample_machine_relations,
            validation_result=sample_validation_result
        )
        
        assert result['success'] is True
        assert len(result['processed_results']) == 3
        assert result['processing_summary']['total_processed'] == 3
        assert result['processing_summary']['successful_saves'] == 3
        assert result['processing_summary']['failed_saves'] == 0

    @pytest.mark.asyncio
    async def test_process_scheduling_results_empty(self, result_processor, sample_machine_relations, sample_validation_result):
        """测试排产结果处理 - 空结果"""
        result = await result_processor.process_scheduling_results(
            scheduled_results=[],
            monthly_batch_id='MONTHLY_20190701_001',
            task_id='TASK_20190701_001',
            machine_relations=sample_machine_relations,
            validation_result=sample_validation_result
        )
        
        assert result['success'] is False
        assert 'error_details' in result
        assert 'no_results_to_process' in result['error_details'][0]['error_type']

    @pytest.mark.asyncio
    async def test_validate_machine_relations_success(self, result_processor, sample_scheduled_results, sample_machine_relations):
        """测试机台关系验证 - 成功"""
        validation_result = await result_processor._validate_machine_relations(
            sample_scheduled_results, sample_machine_relations
        )
        
        assert validation_result['valid'] is True
        assert len(validation_result['invalid_relations']) == 0
        assert validation_result['statistics']['total_validated'] == 3
        assert validation_result['statistics']['valid_relations'] == 3

    @pytest.mark.asyncio
    async def test_validate_machine_relations_invalid(self, result_processor, sample_machine_relations):
        """测试机台关系验证 - 无效关系"""
        # 创建无效的机台关系
        invalid_results = [
            {
                'work_order_nr': 'WO_001',
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ99',  # 无效的喂丝机
                'article_nr': '利群（软蓝）'
            },
            {
                'work_order_nr': 'WO_002',
                'assigned_maker_code': 'JBJ99',  # 无效的卷包机
                'assigned_feeder_code': 'WSJ01',
                'article_nr': '利群（硬蓝）'
            }
        ]
        
        validation_result = await result_processor._validate_machine_relations(
            invalid_results, sample_machine_relations
        )
        
        assert validation_result['valid'] is False
        assert len(validation_result['invalid_relations']) == 2
        assert validation_result['statistics']['valid_relations'] == 0

    @pytest.mark.asyncio
    async def test_format_database_records_success(self, result_processor, sample_scheduled_results):
        """测试数据库记录格式化 - 成功"""
        monthly_batch_id = 'MONTHLY_20190701_001'
        task_id = 'TASK_20190701_001'
        
        formatted_records = await result_processor._format_database_records(
            sample_scheduled_results, monthly_batch_id, task_id
        )
        
        assert len(formatted_records) == 3
        
        # 验证第一条记录的格式
        first_record = formatted_records[0]
        assert first_record.monthly_task_id == task_id
        assert first_record.monthly_plan_id == 'PLAN_001'
        assert first_record.monthly_batch_id == monthly_batch_id
        assert first_record.work_order_nr == 'WO_001'
        assert first_record.article_nr == '利群（软蓝）'
        assert first_record.allocated_quantity == 1000
        assert first_record.assigned_feeder_code == 'WSJ01'
        assert first_record.assigned_maker_code == 'JBJ01'

    @pytest.mark.asyncio
    async def test_format_database_records_missing_fields(self, result_processor):
        """测试数据库记录格式化 - 缺失字段"""
        incomplete_results = [
            {
                'monthly_plan_id': 'PLAN_001',
                'article_nr': '利群（软蓝）',
                # 缺失其他必要字段
            }
        ]
        
        with pytest.raises(KeyError):
            await result_processor._format_database_records(
                incomplete_results, 'MONTHLY_20190701_001', 'TASK_20190701_001'
            )

    @pytest.mark.asyncio
    async def test_save_to_database_success(self, result_processor, sample_scheduled_results):
        """测试数据库保存 - 成功"""
        # 创建模拟的数据库记录
        db_records = []
        for result in sample_scheduled_results:
            record = Mock(spec=MonthlyScheduleResult)
            record.work_order_nr = result['work_order_nr']
            record.article_nr = result['article_nr']
            db_records.append(record)
        
        save_result = await result_processor._save_to_database(db_records)
        
        assert save_result['success'] is True
        assert save_result['saved_count'] == 3
        assert save_result['failed_count'] == 0
        assert len(save_result['failed_records']) == 0
        
        # 验证数据库操作被调用
        assert result_processor.db.add.call_count == 3
        result_processor.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_to_database_partial_failure(self, result_processor):
        """测试数据库保存 - 部分失败"""
        # 模拟部分记录保存失败
        db_records = []
        for i in range(3):
            record = Mock(spec=MonthlyScheduleResult)
            record.work_order_nr = f'WO_{i:03d}'
            record.article_nr = f'产品{i}'
            db_records.append(record)
        
        # 模拟第二条记录保存时出错
        def side_effect(record):
            if record.work_order_nr == 'WO_001':
                raise IntegrityError("Duplicate entry", None, None)
        
        result_processor.db.add.side_effect = side_effect
        
        save_result = await result_processor._save_to_database(db_records)
        
        assert save_result['success'] is False
        assert save_result['saved_count'] == 2
        assert save_result['failed_count'] == 1
        assert len(save_result['failed_records']) == 1
        assert save_result['failed_records'][0]['work_order_nr'] == 'WO_001'

    @pytest.mark.asyncio
    async def test_save_to_database_complete_failure(self, result_processor):
        """测试数据库保存 - 完全失败"""
        db_records = [Mock(spec=MonthlyScheduleResult) for _ in range(3)]
        
        # 模拟数据库提交失败
        result_processor.db.commit.side_effect = Exception("Database connection lost")
        
        save_result = await result_processor._save_to_database(db_records)
        
        assert save_result['success'] is False
        assert save_result['saved_count'] == 0
        assert save_result['failed_count'] == 3
        result_processor.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_processing_summary(self, result_processor, sample_scheduled_results, sample_validation_result):
        """测试处理摘要生成"""
        save_result = {
            'success': True,
            'saved_count': 3,
            'failed_count': 0,
            'failed_records': []
        }
        
        summary = await result_processor._generate_processing_summary(
            sample_scheduled_results, save_result, sample_validation_result
        )
        
        assert summary['total_processed'] == 3
        assert summary['successful_saves'] == 3
        assert summary['failed_saves'] == 0
        assert summary['processing_success_rate'] == 1.0
        assert summary['validation_passed'] is True
        assert 'machine_utilization' in summary
        assert 'time_distribution' in summary

    @pytest.mark.asyncio
    async def test_calculate_machine_utilization(self, result_processor, sample_scheduled_results):
        """测试机台利用率计算"""
        utilization = await result_processor._calculate_machine_utilization(sample_scheduled_results)
        
        assert 'JBJ01' in utilization
        assert 'JBJ02' in utilization
        
        # JBJ01 有两个任务，总计15小时
        jbj01_util = utilization['JBJ01']
        assert jbj01_util['total_hours'] == 15.0
        assert jbj01_util['task_count'] == 2
        assert len(jbj01_util['products']) == 2
        
        # JBJ02 有一个任务，总计10小时
        jbj02_util = utilization['JBJ02']
        assert jbj02_util['total_hours'] == 10.0
        assert jbj02_util['task_count'] == 1
        assert len(jbj02_util['products']) == 1

    @pytest.mark.asyncio
    async def test_calculate_time_distribution(self, result_processor, sample_scheduled_results):
        """测试时间分布计算"""
        distribution = await result_processor._calculate_time_distribution(sample_scheduled_results)
        
        assert 'daily_distribution' in distribution
        assert 'hourly_distribution' in distribution
        assert 'shift_distribution' in distribution
        
        # 验证日期分布
        daily_dist = distribution['daily_distribution']
        assert '2019-07-01' in daily_dist
        assert daily_dist['2019-07-01']['task_count'] == 3
        assert daily_dist['2019-07-01']['total_hours'] == 25.0

    @pytest.mark.asyncio
    async def test_optimize_results_ordering(self, result_processor, sample_scheduled_results):
        """测试结果排序优化"""
        # 打乱顺序
        shuffled_results = sample_scheduled_results[::-1]
        
        optimized_results = await result_processor._optimize_results_ordering(shuffled_results)
        
        # 应该按开始时间排序
        start_times = [result['scheduled_start_time'] for result in optimized_results]
        assert start_times == sorted(start_times)

    @pytest.mark.asyncio
    async def test_validate_result_consistency(self, result_processor, sample_scheduled_results):
        """测试结果一致性验证"""
        validation_result = await result_processor._validate_result_consistency(sample_scheduled_results)
        
        assert validation_result['consistent'] is True
        assert validation_result['issues_found'] == 0
        assert len(validation_result['consistency_errors']) == 0

    @pytest.mark.asyncio
    async def test_validate_result_consistency_with_issues(self, result_processor):
        """测试结果一致性验证 - 有问题"""
        inconsistent_results = [
            {
                'work_order_nr': 'WO_001',
                'monthly_batch_id': 'BATCH_001',
                'scheduled_start_time': datetime(2019, 7, 1, 10, 0, 0),
                'scheduled_end_time': datetime(2019, 7, 1, 8, 0, 0),  # 结束时间早于开始时间
                'target_quantity_boxes': -100,  # 负数量
                'scheduled_duration_hours': 2.0
            }
        ]
        
        validation_result = await result_processor._validate_result_consistency(inconsistent_results)
        
        assert validation_result['consistent'] is False
        assert validation_result['issues_found'] > 0
        assert len(validation_result['consistency_errors']) > 0

    @pytest.mark.asyncio
    async def test_handle_split_product_processing(self, result_processor):
        """测试拆分产品处理"""
        # 创建拆分产品结果
        split_results = [
            {
                'monthly_task_id': 'TASK_001',
                'monthly_plan_id': 'PLAN_001',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': 'WO_001_SPLIT_1',
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 600,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': datetime(2019, 7, 1, 6, 40, 0),
                'scheduled_end_time': datetime(2019, 7, 1, 11, 40, 0),
                'scheduled_duration_hours': 5.0,
                'split_info': {
                    'is_split_product': True,
                    'split_index': 1,
                    'total_splits': 2,
                    'split_total_allocated': 1000,
                    'split_target_quantity': 1000
                }
            },
            {
                'monthly_task_id': 'TASK_002',
                'monthly_plan_id': 'PLAN_001',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': 'WO_001_SPLIT_2',
                'article_nr': '利群（软蓝）',
                'target_quantity_boxes': 400,
                'assigned_maker_code': 'JBJ02',
                'assigned_feeder_code': 'WSJ02',
                'scheduled_start_time': datetime(2019, 7, 1, 6, 40, 0),
                'scheduled_end_time': datetime(2019, 7, 1, 9, 40, 0),
                'scheduled_duration_hours': 3.0,
                'split_info': {
                    'is_split_product': True,
                    'split_index': 2,
                    'total_splits': 2,
                    'split_total_allocated': 1000,
                    'split_target_quantity': 1000
                }
            }
        ]
        
        formatted_records = await result_processor._format_database_records(
            split_results, 'MONTHLY_20190701_001', 'TASK_001'
        )
        
        assert len(formatted_records) == 2
        
        # 验证拆分信息正确保存
        for record in formatted_records:
            assert 'split_info' in record.calculation_details
            split_info = record.calculation_details['split_info']
            assert split_info['is_split_product'] is True
            assert split_info['total_splits'] == 2

    @pytest.mark.asyncio
    async def test_handle_large_batch_processing(self, result_processor):
        """测试大批量处理"""
        # 创建大量排产结果
        large_batch_results = []
        base_time = datetime(2019, 7, 1, 6, 40, 0)
        
        for i in range(100):
            result = {
                'monthly_task_id': f'TASK_{i:03d}',
                'monthly_plan_id': f'PLAN_{i:03d}',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': f'WO_{i:03d}',
                'article_nr': f'产品{i}',
                'article_name': f'产品{i}',
                'target_quantity_boxes': 1000,
                'assigned_maker_code': f'JBJ{(i % 5) + 1:02d}',
                'assigned_feeder_code': f'WSJ{(i % 5) + 1:02d}',
                'scheduled_start_time': base_time + timedelta(hours=i*2),
                'scheduled_end_time': base_time + timedelta(hours=i*2 + 8),
                'scheduled_duration_hours': 8.0,
                'estimated_speed': 125.0,
                'efficiency_rate': 100.0,
                'utilization_rate': 0.8,
                'algorithm_version': 'v2.0_complete',
                'priority_score': 80.0,
                'calculation_details': {
                    'base_speed': 125.0,
                    'actual_speed': 125.0,
                    'required_hours': 8.0,
                    'available_hours': 17.0
                }
            }
            large_batch_results.append(result)
        
        # 处理大批量结果
        machine_relations = {
            'maker_to_feeder': {f'JBJ{i:02d}': f'WSJ{i:02d}' for i in range(1, 6)}
        }
        
        validation_result = {'valid': True, 'recommendations': []}
        
        result = await result_processor.process_scheduling_results(
            scheduled_results=large_batch_results,
            monthly_batch_id='MONTHLY_20190701_001',
            task_id='TASK_001',
            machine_relations=machine_relations,
            validation_result=validation_result
        )
        
        assert result['success'] is True
        assert result['processing_summary']['total_processed'] == 100


class TestResultProcessorErrorHandling:
    """结果处理器错误处理测试"""
    
    @pytest.fixture
    def result_processor_with_failing_db(self):
        """创建带有失败数据库的结果处理器"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add.side_effect = Exception("Database error")
        mock_session.commit.side_effect = Exception("Commit failed")
        return ResultProcessor(mock_session)

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, result_processor_with_failing_db):
        """测试数据库连接失败"""
        sample_results = [{
            'monthly_task_id': 'TASK_001',
            'monthly_plan_id': 'PLAN_001',
            'monthly_batch_id': 'MONTHLY_20190701_001',
            'work_order_nr': 'WO_001',
            'article_nr': '利群（软蓝）',
            'target_quantity_boxes': 1000,
            'assigned_maker_code': 'JBJ01',
            'assigned_feeder_code': 'WSJ01',
            'scheduled_start_time': datetime.now(),
            'scheduled_end_time': datetime.now() + timedelta(hours=8),
            'scheduled_duration_hours': 8.0,
            'estimated_speed': 125.0,
            'efficiency_rate': 100.0,
            'utilization_rate': 0.8,
            'algorithm_version': 'v2.0_complete',
            'priority_score': 80.0,
            'calculation_details': {}
        }]
        
        machine_relations = {'maker_to_feeder': {'JBJ01': 'WSJ01'}}
        validation_result = {'valid': True, 'recommendations': []}
        
        result = await result_processor_with_failing_db.process_scheduling_results(
            scheduled_results=sample_results,
            monthly_batch_id='MONTHLY_20190701_001',
            task_id='TASK_001',
            machine_relations=machine_relations,
            validation_result=validation_result
        )
        
        assert result['success'] is False
        assert 'error_details' in result
        assert len(result['error_details']) > 0

    @pytest.mark.asyncio
    async def test_invalid_data_format_handling(self, result_processor):
        """测试无效数据格式处理"""
        invalid_results = [
            {
                'invalid_field': 'invalid_value',
                # 缺失所有必要字段
            }
        ]
        
        machine_relations = {'maker_to_feeder': {}}
        validation_result = {'valid': True, 'recommendations': []}
        
        result = await result_processor.process_scheduling_results(
            scheduled_results=invalid_results,
            monthly_batch_id='MONTHLY_20190701_001',
            task_id='TASK_001',
            machine_relations=machine_relations,
            validation_result=validation_result
        )
        
        assert result['success'] is False
        assert 'error_details' in result

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, result_processor):
        """测试内存压力处理"""
        # 创建非常大的数据集来模拟内存压力
        huge_results = []
        for i in range(10000):  # 大量数据
            result = {
                'monthly_task_id': f'TASK_{i:05d}',
                'monthly_plan_id': f'PLAN_{i:05d}',
                'monthly_batch_id': 'MONTHLY_20190701_001',
                'work_order_nr': f'WO_{i:05d}',
                'article_nr': f'产品{i}',
                'target_quantity_boxes': 1000,
                'assigned_maker_code': 'JBJ01',
                'assigned_feeder_code': 'WSJ01',
                'scheduled_start_time': datetime.now(),
                'scheduled_end_time': datetime.now() + timedelta(hours=8),
                'scheduled_duration_hours': 8.0,
                'estimated_speed': 125.0,
                'efficiency_rate': 100.0,
                'utilization_rate': 0.8,
                'algorithm_version': 'v2.0_complete',
                'priority_score': 80.0,
                'calculation_details': {'large_data': 'x' * 1000}  # 增加数据大小
            }
            huge_results.append(result)
        
        machine_relations = {'maker_to_feeder': {'JBJ01': 'WSJ01'}}
        validation_result = {'valid': True, 'recommendations': []}
        
        # 这个测试主要验证系统在大数据量下不会崩溃
        try:
            result = await result_processor.process_scheduling_results(
                scheduled_results=huge_results,
                monthly_batch_id='MONTHLY_20190701_001',
                task_id='TASK_001',
                machine_relations=machine_relations,
                validation_result=validation_result
            )
            
            # 无论成功还是失败，都应该有响应
            assert 'success' in result
            
        except MemoryError:
            pytest.skip("系统内存不足，跳过大数据量测试")

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, result_processor):
        """测试错误时的事务回滚"""
        # 模拟在保存过程中发生错误
        result_processor.db.commit.side_effect = Exception("Transaction failed")
        
        sample_results = [{
            'monthly_task_id': 'TASK_001',
            'monthly_plan_id': 'PLAN_001',
            'monthly_batch_id': 'MONTHLY_20190701_001',
            'work_order_nr': 'WO_001',
            'article_nr': '利群（软蓝）',
            'target_quantity_boxes': 1000,
            'assigned_maker_code': 'JBJ01',
            'assigned_feeder_code': 'WSJ01',
            'scheduled_start_time': datetime.now(),
            'scheduled_end_time': datetime.now() + timedelta(hours=8),
            'scheduled_duration_hours': 8.0,
            'estimated_speed': 125.0,
            'efficiency_rate': 100.0,
            'utilization_rate': 0.8,
            'algorithm_version': 'v2.0_complete',
            'priority_score': 80.0,
            'calculation_details': {}
        }]
        
        db_records = await result_processor._format_database_records(
            sample_results, 'MONTHLY_20190701_001', 'TASK_001'
        )
        
        save_result = await result_processor._save_to_database(db_records)
        
        assert save_result['success'] is False
        # 验证回滚被调用
        result_processor.db.rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])