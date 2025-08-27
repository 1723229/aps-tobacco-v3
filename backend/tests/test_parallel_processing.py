"""
测试并行处理算法 - 单个测试方法
"""
import pytest
from app.algorithms.parallel_processing import ParallelProcessing


class TestParallelProcessing:
    """并行处理算法测试"""
    
    def test_parallel_processing_creation(self):
        """测试并行处理算法创建"""
        processor = ParallelProcessing()
        assert processor is not None
        assert processor.stage.name == 'PARALLEL_PROCESSING'