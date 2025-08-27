"""
测试工单生成算法 - 单个测试方法
"""
import pytest
from app.algorithms.work_order_generation import WorkOrderGeneration


class TestWorkOrderGeneration:
    """工单生成算法测试"""
    
    def test_work_order_generation_creation(self):
        """测试工单生成算法创建"""
        generator = WorkOrderGeneration()
        assert generator is not None
        assert generator.stage.name == 'WORK_ORDER_GENERATION'