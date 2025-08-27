"""
测试算法基类和metrics
"""
import pytest
from app.algorithms.base import AlgorithmMetrics


class TestAlgorithmBase:
    """算法基类测试"""
    
    def test_algorithm_metrics_has_custom_metrics(self):
        """测试AlgorithmMetrics需要custom_metrics属性"""
        metrics = AlgorithmMetrics()
        
        # 这个测试应该失败，因为缺少custom_metrics属性
        assert hasattr(metrics, 'custom_metrics')
        
        # 验证custom_metrics是字典类型
        assert isinstance(metrics.custom_metrics, dict)