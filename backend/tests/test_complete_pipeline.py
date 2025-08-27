"""
测试完整算法管道 - 验证所有算法都能使用真实数据库数据
"""
import pytest
from datetime import datetime
from app.algorithms.pipeline import AlgorithmPipeline


class TestCompletePipeline:
    """完整管道测试"""
    
    @pytest.mark.asyncio
    async def test_pipeline_creation(self):
        """测试管道创建"""
        pipeline = AlgorithmPipeline()
        assert pipeline is not None
        assert hasattr(pipeline, 'preprocessor')
        assert hasattr(pipeline, 'merger') 
        assert hasattr(pipeline, 'splitter')
        assert hasattr(pipeline, 'time_corrector')
        assert hasattr(pipeline, 'parallel_processor')
        assert hasattr(pipeline, 'work_order_generator')
    
    @pytest.mark.asyncio
    async def test_all_algorithms_have_real_data_methods(self):
        """测试所有算法都有真实数据处理方法"""
        pipeline = AlgorithmPipeline()
        
        # 验证所有算法都有 process_with_real_data 方法
        assert hasattr(pipeline.preprocessor, 'process_with_real_data')
        assert hasattr(pipeline.merger, 'process_with_real_data')
        assert hasattr(pipeline.splitter, 'process_with_real_data')
        assert hasattr(pipeline.time_corrector, 'process_with_real_data')
        assert hasattr(pipeline.parallel_processor, 'process_with_real_data')
        assert hasattr(pipeline.work_order_generator, 'process_with_real_data')
    
    @pytest.mark.asyncio
    async def test_execute_single_stage(self):
        """测试执行单个阶段"""
        pipeline = AlgorithmPipeline()
        
        test_data = [
            {
                'work_order_nr': 'TEST001',
                'article_nr': 'A001',
                'quantity_total': 1000,
                'planned_start': datetime(2024, 1, 1, 8, 0),
                'planned_end': datetime(2024, 1, 1, 16, 0)
            }
        ]
        
        # 测试数据预处理阶段
        result = await pipeline.execute_single_stage('preprocessing', test_data, use_real_data=True)
        assert result is not None
        assert hasattr(result, 'output_data')
        assert result.metrics.custom_metrics.get('used_real_database_data') == True
    
    def test_validate_pipeline_data(self):
        """测试数据验证"""
        pipeline = AlgorithmPipeline()
        
        valid_data = [
            {
                'work_order_nr': 'WO001',
                'article_nr': 'A001',
                'quantity_total': 1000
            }
        ]
        
        invalid_data = [
            {
                'work_order_nr': 'WO002',
                # 缺少 article_nr 和 quantity_total
            }
        ]
        
        # 测试有效数据
        import asyncio
        valid_result = asyncio.run(pipeline.validate_pipeline_data(valid_data))
        assert valid_result['is_valid'] == True
        assert valid_result['validation_summary']['valid_records'] == 1
        
        # 测试无效数据
        invalid_result = asyncio.run(pipeline.validate_pipeline_data(invalid_data))
        assert invalid_result['is_valid'] == False
        assert len(invalid_result['invalid_records']) == 1