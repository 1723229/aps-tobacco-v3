"""
APS智慧排产系统 - 时间校正算法测试

测试轮保冲突检测和班次时间校正功能
验证算法在各种时间冲突场景下的正确性
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.algorithms.time_correction import TimeCorrection


class TestTimeCorrection:
    """时间校正算法测试"""
    
    def test_no_conflicts_no_correction(self):
        """测试无冲突情况下不进行校正"""
        work_orders = [
            {
                'work_order_nr': 'W001',
                'maker_code': 'JJ01',
                'planned_start': datetime(2024, 8, 1, 8, 0),
                'planned_end': datetime(2024, 8, 1, 16, 0)
            }
        ]
        
        maintenance_plans = [
            {
                'machine_code': 'JJ02',  # 不同机台
                'maint_start_time': datetime(2024, 8, 1, 10, 0),
                'maint_end_time': datetime(2024, 8, 1, 12, 0)
            }
        ]
        
        correction = TimeCorrection()
        result = correction.process(work_orders, maintenance_plans=maintenance_plans)
        
        assert len(result.output_data) == 1
        corrected_order = result.output_data[0]
        
        # 应该没有被校正
        assert not corrected_order.get('time_corrected', False)
        assert corrected_order['planned_start'] == work_orders[0]['planned_start']
        assert corrected_order['planned_end'] == work_orders[0]['planned_end']
    
    def test_maintenance_conflict_resolution(self):
        """测试轮保冲突解决"""
        work_orders = [
            {
                'work_order_nr': 'W001',
                'maker_code': 'JJ01',
                'planned_start': datetime(2024, 8, 1, 10, 0),
                'planned_end': datetime(2024, 8, 1, 18, 0)
            }
        ]
        
        maintenance_plans = [
            {
                'machine_code': 'JJ01',  # 同一机台
                'maint_start_time': datetime(2024, 8, 1, 14, 0),  # 冲突时间
                'maint_end_time': datetime(2024, 8, 1, 16, 0)
            }
        ]
        
        correction = TimeCorrection()
        result = correction.process(work_orders, maintenance_plans=maintenance_plans)
        
        assert len(result.output_data) == 1
        corrected_order = result.output_data[0]
        
        # 应该被校正
        assert corrected_order.get('maintenance_conflict_resolved', False)
        assert corrected_order.get('time_corrected', False)
        
        # 新的开始时间应该是轮保结束时间
        assert corrected_order['planned_start'] == datetime(2024, 8, 1, 16, 0)
        
        # 持续时间应该保持不变（8小时）
        original_duration = work_orders[0]['planned_end'] - work_orders[0]['planned_start']
        new_duration = corrected_order['planned_end'] - corrected_order['planned_start']
        assert original_duration == new_duration
        
        # 应该记录原始时间
        assert corrected_order['original_planned_start'] == work_orders[0]['planned_start']
        assert corrected_order['original_planned_end'] == work_orders[0]['planned_end']