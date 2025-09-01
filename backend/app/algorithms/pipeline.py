"""
APS智慧排产系统 - 算法管道统一入口

实现完整的排产算法流水线，使用真实数据库数据
按照 数据预处理 -> 规则合并 -> 规则拆分 -> 时间校正 -> 并行切分 -> 工单生成 的顺序执行
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .data_preprocessing import DataPreprocessor
from .merge_algorithm import MergeAlgorithm  
from .split_algorithm import SplitAlgorithm
from .time_correction import TimeCorrection
from .parallel_processing import ParallelProcessing
from .work_order_generation import WorkOrderGeneration
from .base import AlgorithmResult

logger = logging.getLogger(__name__)


class AlgorithmPipeline:
    """算法管道统一调度器"""
    
    def __init__(self):
        self.preprocessor = DataPreprocessor()
        self.merger = MergeAlgorithm()
        self.splitter = SplitAlgorithm()
        self.time_corrector = TimeCorrection()
        self.parallel_processor = ParallelProcessing()
        self.work_order_generator = WorkOrderGeneration()
        
    async def execute_full_pipeline_with_batch(
        self,
        import_batch_id: str,
        use_real_data: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整的排产算法流水线 - 从数据库查询旬计划数据
        
        Args:
            import_batch_id: 导入批次ID，从aps_decade_plan表查询数据
            use_real_data: 是否使用真实数据库数据
            
        Returns:
            Dict: 包含每个阶段结果的完整执行结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        pipeline_start_time = datetime.now()
        results = {
            'pipeline_id': f"pipeline_{pipeline_start_time.strftime('%Y%m%d_%H%M%S')}",
            'start_time': pipeline_start_time,
            'import_batch_id': import_batch_id,
            'use_real_data': use_real_data,
            'stages': {}
        }
        
        try:
            # 首先从数据库查询旬计划数据
            logger.info(f"从数据库查询旬计划数据 - 批次ID: {import_batch_id}")
            raw_plan_data = await DatabaseQueryService.get_decade_plans(
                import_batch_id=import_batch_id
            )
            
            if not raw_plan_data:
                logger.warning(f"未找到批次 {import_batch_id} 的旬计划数据")
                results.update({
                    'success': False,
                    'error': f'未找到批次 {import_batch_id} 的旬计划数据',
                    'final_work_orders': []
                })
                return results
            
            logger.info(f"查询到 {len(raw_plan_data)} 条旬计划数据，开始执行算法管道")
            
            # 执行完整管道
            return await self.execute_full_pipeline(raw_plan_data, use_real_data)
            
        except Exception as e:
            logger.error(f"算法管道执行失败: {str(e)}")
            results.update({
                'end_time': datetime.now(),
                'success': False,
                'error': str(e),
                'final_work_orders': []
            })
            return results

    async def execute_full_pipeline(
        self, 
        raw_plan_data: List[Dict[str, Any]], 
        use_real_data: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整的排产算法流水线
        
        Args:
            raw_plan_data: 原始旬计划数据
            use_real_data: 是否使用真实数据库数据
            
        Returns:
            Dict: 包含每个阶段结果的完整执行结果
        """
        pipeline_start_time = datetime.now()
        results = {
            'pipeline_id': f"pipeline_{pipeline_start_time.strftime('%Y%m%d_%H%M%S')}",
            'start_time': pipeline_start_time,
            'use_real_data': use_real_data,
            'stages': {}
        }
        
        try:
            logger.info(f"开始执行算法管道 - 原始数据{len(raw_plan_data)}条，使用真实数据: {use_real_data}")
            
            # 阶段1：数据预处理
            logger.info("执行阶段1: 数据预处理")
            if use_real_data:
                preprocessing_result = await self.preprocessor.process_with_real_data(raw_plan_data)
            else:
                preprocessing_result = await self.preprocessor.process(raw_plan_data)
            
            results['stages']['preprocessing'] = self._extract_stage_summary(preprocessing_result)
            current_data = preprocessing_result.output_data
            
            # 阶段2：规则合并
            logger.info(f"执行阶段2: 规则合并 - 输入{len(current_data)}条")
            if use_real_data:
                merge_result = await self.merger.process_with_real_data(current_data)
            else:
                merge_result = await self.merger.process(current_data)
            
            results['stages']['merging'] = self._extract_stage_summary(merge_result)
            results['merged_plans'] = merge_result.output_data  # 保存合并后的计划数据
            current_data = merge_result.output_data
            
            # 阶段3：规则拆分
            logger.info(f"执行阶段3: 规则拆分 - 输入{len(current_data)}条")
            if use_real_data:
                split_result = await self.splitter.process_with_real_data(current_data)
            else:
                split_result = await self.splitter.process(current_data)
            
            results['stages']['splitting'] = self._extract_stage_summary(split_result)
            current_data = split_result.output_data
            
            # 阶段4：时间校正
            logger.info(f"执行阶段4: 时间校正 - 输入{len(current_data)}条")
            if use_real_data:
                time_correction_result = await self.time_corrector.process_with_real_data(current_data)
            else:
                time_correction_result = await self.time_corrector.process(current_data)
            
            results['stages']['time_correction'] = self._extract_stage_summary(time_correction_result)
            current_data = time_correction_result.output_data
            
            # 阶段5：并行切分
            logger.info(f"执行阶段5: 并行切分 - 输入{len(current_data)}条")
            if use_real_data:
                parallel_result = await self.parallel_processor.process_with_real_data(current_data)
            else:
                parallel_result = await self.parallel_processor.process(current_data)
            
            results['stages']['parallel_processing'] = self._extract_stage_summary(parallel_result)
            current_data = parallel_result.output_data
            
            # 阶段6：工单生成
            logger.info(f"执行阶段6: 工单生成 - 输入{len(current_data)}条")
            if use_real_data:
                work_order_result = await self.work_order_generator.process_with_real_data(current_data)
            else:
                work_order_result = await self.work_order_generator.process(current_data)
            
            results['stages']['work_order_generation'] = self._extract_stage_summary(work_order_result)
            final_work_orders = work_order_result.output_data
            
            # 管道执行完成
            pipeline_end_time = datetime.now()
            execution_duration = (pipeline_end_time - pipeline_start_time).total_seconds()
            
            results.update({
                'end_time': pipeline_end_time,
                'execution_duration_seconds': execution_duration,
                'success': True,
                'final_work_orders': final_work_orders,
                'summary': {
                    'input_records': len(raw_plan_data),
                    'output_work_orders': len(final_work_orders),
                    'processing_rate': len(final_work_orders) / len(raw_plan_data) if raw_plan_data else 0,
                    'total_stages': 6,
                    'average_stage_duration': execution_duration / 6
                }
            })
            
            logger.info(f"算法管道执行完成 - 耗时{execution_duration:.2f}秒，生成{len(final_work_orders)}个工单")
            return results
            
        except Exception as e:
            logger.error(f"算法管道执行失败: {str(e)}")
            results.update({
                'end_time': datetime.now(),
                'success': False,
                'error': str(e),
                'final_work_orders': []
            })
            return results
    
    async def execute_single_stage(
        self, 
        stage_name: str, 
        input_data: List[Dict[str, Any]], 
        use_real_data: bool = True
    ) -> AlgorithmResult:
        """
        执行单个算法阶段
        
        Args:
            stage_name: 阶段名称 ('preprocessing', 'merging', 'splitting', 'time_correction', 'parallel_processing', 'work_order_generation')
            input_data: 输入数据
            use_real_data: 是否使用真实数据库数据
            
        Returns:
            AlgorithmResult: 单个阶段的执行结果
        """
        stage_map = {
            'preprocessing': self.preprocessor,
            'merging': self.merger,
            'splitting': self.splitter,
            'time_correction': self.time_corrector,
            'parallel_processing': self.parallel_processor,
            'work_order_generation': self.work_order_generator
        }
        
        algorithm = stage_map.get(stage_name)
        if not algorithm:
            raise ValueError(f"未知的算法阶段: {stage_name}")
        
        logger.info(f"执行单个阶段: {stage_name} - 输入{len(input_data)}条数据")
        
        if use_real_data and hasattr(algorithm, 'process_with_real_data'):
            result = await algorithm.process_with_real_data(input_data)
        else:
            result = await algorithm.process(input_data)
        
        return result
    
    def _extract_stage_summary(self, result: AlgorithmResult) -> Dict[str, Any]:
        """提取阶段执行摘要"""
        return {
            'stage': result.stage.name if result.stage else 'UNKNOWN',
            'status': result.status.name if result.status else 'UNKNOWN',
            'input_records': len(result.input_data) if result.input_data else 0,
            'output_records': len(result.output_data) if result.output_data else 0,
            'execution_time_seconds': result.metrics.execution_time,
            'error_count': len(result.errors),
            'custom_metrics': result.metrics.custom_metrics,
            'has_errors': len(result.errors) > 0
        }
    
    async def validate_pipeline_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证管道输入数据的完整性
        
        Args:
            data: 待验证的数据
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'record_count': len(data),
            'missing_fields': [],
            'invalid_records': [],
            'validation_summary': {}
        }
        
        required_fields = ['work_order_nr', 'article_nr', 'quantity_total']
        
        for i, record in enumerate(data):
            missing = [field for field in required_fields if not record.get(field)]
            if missing:
                validation_result['missing_fields'].extend(missing)
                validation_result['invalid_records'].append({
                    'index': i,
                    'work_order_nr': record.get('work_order_nr', 'UNKNOWN'),
                    'missing_fields': missing
                })
        
        validation_result['is_valid'] = len(validation_result['invalid_records']) == 0
        validation_result['validation_summary'] = {
            'total_records': len(data),
            'valid_records': len(data) - len(validation_result['invalid_records']),
            'invalid_records': len(validation_result['invalid_records']),
            'validation_rate': (len(data) - len(validation_result['invalid_records'])) / len(data) if data else 1.0
        }
        
        return validation_result


# 便利函数
async def execute_complete_scheduling(
    raw_plan_data: List[Dict[str, Any]], 
    use_real_data: bool = True
) -> Dict[str, Any]:
    """
    执行完整排产流程的便利函数
    
    Args:
        raw_plan_data: 原始计划数据
        use_real_data: 是否使用真实数据库数据
        
    Returns:
        Dict: 完整的执行结果
    """
    pipeline = AlgorithmPipeline()
    return await pipeline.execute_full_pipeline(raw_plan_data, use_real_data)


async def execute_single_algorithm(
    algorithm_name: str,
    input_data: List[Dict[str, Any]],
    use_real_data: bool = True
) -> AlgorithmResult:
    """
    执行单个算法的便利函数
    
    Args:
        algorithm_name: 算法名称
        input_data: 输入数据
        use_real_data: 是否使用真实数据库数据
        
    Returns:
        AlgorithmResult: 算法执行结果
    """
    pipeline = AlgorithmPipeline()
    return await pipeline.execute_single_stage(algorithm_name, input_data, use_real_data)