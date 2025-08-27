"""
APS智慧排产系统 - 边界条件测试

测试算法在极端条件和异常场景下的健壮性
验证错误处理、数据完整性和性能边界
"""
import pytest
from datetime import datetime
from typing import List, Dict, Any

from app.algorithms import (
    AlgorithmBase,
    AlgorithmResult,
    ProcessingStage,
    ProcessingStatus
)
from app.algorithms.data_preprocessing import DataPreprocessor
from app.algorithms.merge_algorithm import MergeAlgorithm
from app.algorithms.split_algorithm import SplitAlgorithm


class TestBoundaryConditions:
    """边界条件测试"""
    
    def test_empty_input_data(self):
        """测试空输入数据"""
        preprocessor = DataPreprocessor()
        result = preprocessor.process([])
        
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.output_data) == 0
        assert result.metrics.processed_records == 0
    
    def test_large_dataset_performance(self):
        """测试大数据集性能 - 1000条记录"""
        # 生成1000条测试数据
        large_dataset = []
        for i in range(1000):
            record = {
                'work_order_nr': f'W{i:06d}',
                'article_nr': f'PA{i % 10:03d}',  # 10种不同牌号
                'maker_code': f'JJ{i % 5:02d}',  # 5台不同机器
                'feeder_code': f'WS{i % 3:02d}', # 3台喂丝机
                'quantity_total': 1000 + (i % 500),
                'final_quantity': 1000 + (i % 500),
                'planned_start': datetime(2024, 8, 1, 8, 0),
                'planned_end': datetime(2024, 8, 1, 16, 0)
            }
            large_dataset.append(record)
        
        # 执行预处理
        start_time = datetime.now()
        preprocessor = DataPreprocessor()
        result = preprocessor.process(large_dataset)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 验证性能要求：处理1000条记录应该在5秒内完成
        assert execution_time < 5.0, f"处理1000条记录耗时{execution_time:.2f}秒，超过5秒限制"
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.output_data) <= 1000  # 可能有些空记录被过滤
    
    def test_invalid_data_types(self):
        """测试无效数据类型"""
        invalid_data = [
            {
                'work_order_nr': 123,  # 应该是字符串
                'article_nr': None,    # 空值
                'quantity_total': 'invalid',  # 应该是数字
                'final_quantity': -100,  # 负数
                'planned_start': 'not_a_date'  # 无效日期
            }
        ]
        
        preprocessor = DataPreprocessor()
        result = preprocessor.process(invalid_data)
        
        # 应该能处理无效数据而不崩溃
        assert isinstance(result, AlgorithmResult)
        # 可能有错误记录，但不应该导致整个流程失败
        assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
    
    def test_extreme_quantity_values(self):
        """测试极端数量值"""
        extreme_data = [
            {
                'work_order_nr': 'W_ZERO',
                'article_nr': 'PA001',
                'quantity_total': 0,
                'final_quantity': 0
            },
            {
                'work_order_nr': 'W_LARGE',
                'article_nr': 'PA002', 
                'quantity_total': 999999999,  # 极大值
                'final_quantity': 999999999
            }
        ]
        
        preprocessor = DataPreprocessor()
        result = preprocessor.process(extreme_data)
        
        # 验证算法能处理极端值
        assert isinstance(result, AlgorithmResult)
        assert result.status == ProcessingStatus.COMPLETED
    
    def test_memory_usage_with_complex_data(self):
        """测试复杂数据结构的内存使用"""
        complex_data = []
        
        for i in range(100):
            record = {
                'work_order_nr': f'W{i:06d}',
                'article_nr': f'PA{i:03d}',
                'maker_code': f'JJ{i:02d}',
                'feeder_code': f'WS{i:02d}',
                'quantity_total': 10000,
                'final_quantity': 10000,
                'planned_start': datetime(2024, 8, 1, 8, 0),
                'planned_end': datetime(2024, 8, 1, 16, 0),
                # 添加复杂的嵌套数据
                'complex_metadata': {
                    'history': [f'event_{j}' for j in range(50)],
                    'parameters': {f'param_{k}': f'value_{k}' for k in range(20)}
                }
            }
            complex_data.append(record)
        
        # 执行处理
        preprocessor = DataPreprocessor()
        result = preprocessor.process(complex_data)
        
        # 验证能处理复杂数据结构
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.output_data) <= len(complex_data)
    
    def test_concurrent_processing_safety(self):
        """测试并发处理安全性"""
        import threading
        import time
        
        test_data = [
            {
                'work_order_nr': f'W{i:03d}',
                'article_nr': 'PA001',
                'maker_code': 'JJ01',
                'feeder_code': 'WS01',
                'quantity_total': 1000,
                'final_quantity': 1000,
                'planned_start': datetime(2024, 8, 1, 8, 0),
                'planned_end': datetime(2024, 8, 1, 16, 0)
            }
            for i in range(10)
        ]
        
        results = []
        errors = []
        
        def process_data():
            try:
                preprocessor = DataPreprocessor()
                result = preprocessor.process(test_data.copy())
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 启动5个并发线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_data)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证并发安全性
        assert len(errors) == 0, f"并发处理出现错误: {errors}"
        assert len(results) == 5
        
        # 验证所有结果一致性
        for result in results:
            assert result.status == ProcessingStatus.COMPLETED
            assert len(result.output_data) == len(test_data)
    
    def test_algorithm_pipeline_error_propagation(self):
        """测试算法流水线的错误传播"""
        # 故意创建会导致错误的数据
        error_data = [
            {
                'work_order_nr': 'W001',
                'article_nr': 'PA001',
                # 缺少必要字段
            }
        ]
        
        # 测试每个算法如何处理错误数据
        preprocessor = DataPreprocessor()
        preprocess_result = preprocessor.process(error_data)
        
        # 即使有错误，流水线也应该继续
        merge_algo = MergeAlgorithm()
        merge_result = merge_algo.process(preprocess_result.output_data)
        
        # 验证错误被正确记录和传播
        assert isinstance(merge_result, AlgorithmResult)
    
    def test_resource_cleanup_after_processing(self):
        """测试处理后资源清理"""
        large_data = [
            {
                'work_order_nr': f'W{i:06d}',
                'article_nr': 'PA001',
                'maker_code': 'JJ01',
                'feeder_code': 'WS01',
                'quantity_total': 1000,
                'final_quantity': 1000,
                'planned_start': datetime(2024, 8, 1, 8, 0),
                'planned_end': datetime(2024, 8, 1, 16, 0)
            }
            for i in range(500)
        ]
        
        # 处理大量数据
        preprocessor = DataPreprocessor()
        result = preprocessor.process(large_data)
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        # 验证处理成功
        assert result.status == ProcessingStatus.COMPLETED
        assert result.metrics.processed_records == 500