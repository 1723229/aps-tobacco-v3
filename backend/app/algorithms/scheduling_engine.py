"""
APS智慧排产系统 - 算法流水线管理器

实现完整的排产算法流水线，将所有算法模块组合起来
提供统一的接口来执行完整的排产流程
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .base import AlgorithmBase, AlgorithmResult, ProcessingStage, ProcessingStatus
from .pipeline import AlgorithmPipeline
from .data_preprocessing import DataPreprocessor
from .merge_algorithm import MergeAlgorithm
from .split_algorithm import SplitAlgorithm

logger = logging.getLogger(__name__)


class SchedulingEngine:
    """排产引擎 - 管理完整的排产算法流水线"""
    
    def __init__(self, task_id: Optional[str] = None):
        self.task_id = task_id
        self.pipeline = AlgorithmPipeline()
        self.logger = logging.getLogger(f"{__name__}.SchedulingEngine")
        
        # 构建算法流水线
        self._setup_pipeline()
    
    def _setup_pipeline(self):
        """设置算法流水线"""
        # AlgorithmPipeline 已经在初始化时设置了所有算法
        # 不需要额外设置
        pass
    
    async def execute_scheduling_pipeline(
        self,
        input_data: List[Dict[str, Any]], 
        config: Dict[str, Any] = None
    ) -> AlgorithmResult:
        """
        执行完整的排产算法管道
        
        Args:
            input_data: 输入的计划数据
            config: 算法配置
            
        Returns:
            AlgorithmResult: 管道执行结果
        """
        from .base import AlgorithmResult, ProcessingStage, ProcessingStatus
        
        if config is None:
            config = {}
            
        self.logger.info(f"开始执行排产管道 - 输入{len(input_data)}条数据")
        
        # 使用AlgorithmPipeline执行完整流程
        pipeline_result = await self.pipeline.execute_full_pipeline(
            raw_plan_data=input_data,
            use_real_data=config.get('use_real_data', True)
        )
        
        # 转换为AlgorithmResult格式
        result = AlgorithmResult(
            stage=ProcessingStage.WORK_ORDER_GENERATION,
            status=ProcessingStatus.COMPLETED if pipeline_result['success'] else ProcessingStatus.FAILED
        )
        result.input_data = input_data
        result.output_data = pipeline_result.get('final_work_orders', [])
        result.success = pipeline_result['success']
        
        if not pipeline_result['success']:
            result.add_error(pipeline_result.get('error', '管道执行失败'))
        
        result.metrics.processed_records = len(input_data)
        result.metrics.custom_metrics = pipeline_result.get('summary', {})
        
        self.logger.info(f"排产管道执行完成 - 输出{len(result.output_data)}个工单")
        return result
    
    async def execute_scheduling(
        self, 
        input_data: List[Dict[str, Any]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行完整的排产流程
        
        Args:
            input_data: 原始计划数据
            **kwargs: 算法参数
                - maker_mapping: 喂丝机到卷包机的映射关系
                - maintenance_plans: 轮保计划
                - shift_config: 班次配置
                
        Returns:
            dict: 排产结果摘要
        """
        self.logger.info(f"开始执行排产流程 {self.task_id}, 输入{len(input_data)}条记录")
        
        try:
            # 使用新的异步pipeline接口
            results = await self.pipeline.execute_full_pipeline(
                raw_plan_data=input_data, 
                use_real_data=kwargs.get('use_real_data', True)
            )
            
            self.logger.info(f"排产流程 {self.task_id} 执行完成")
            return results
            
        except Exception as e:
            self.logger.error(f"排产流程 {self.task_id} 执行失败: {str(e)}")
            return {
                'task_id': self.task_id,
                'overall_status': ProcessingStatus.FAILED.value,
                'error_message': str(e),
                'execution_time': datetime.now().isoformat()
            }
    
    def _generate_business_metrics(self, results: List[AlgorithmResult]) -> Dict[str, Any]:
        """生成业务指标"""
        if not results:
            return {}
        
        final_result = results[-1]
        initial_result = results[0] if results else None
        
        # 计算业务指标
        input_count = len(initial_result.input_data) if initial_result else 0
        output_count = len(final_result.output_data)
        
        # 计算数量守恒
        input_total_quantity = 0
        output_total_quantity = 0
        
        if initial_result and initial_result.input_data:
            input_total_quantity = sum(
                r.get('quantity_total', 0) for r in initial_result.input_data
            )
        
        if final_result.output_data:
            output_total_quantity = sum(
                r.get('quantity_total', 0) for r in final_result.output_data  
            )
        
        # 数量守恒检查
        quantity_conservation = abs(input_total_quantity - output_total_quantity) <= 1  # 允许1的舍入误差
        
        return {
            'business_metrics': {
                'input_plan_count': input_count,
                'output_order_count': output_count,
                'input_total_quantity': input_total_quantity,
                'output_total_quantity': output_total_quantity,
                'quantity_conservation': quantity_conservation,
                'processing_ratio': output_count / input_count if input_count > 0 else 0,
                'final_stage': final_result.stage.value,
                'final_status': final_result.status.value
            }
        }
    
    def get_detailed_results(self) -> List[Dict[str, Any]]:
        """获取详细的执行结果"""
        return [result.to_dict() for result in self.pipeline.results]
    
    def validate_input_data(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证输入数据质量
        
        Args:
            input_data: 待验证的输入数据
            
        Returns:
            dict: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'total_records': len(input_data),
            'validation_errors': [],
            'validation_warnings': []
        }
        
        if not input_data:
            validation_result['validation_warnings'].append("输入数据为空")
            return validation_result
        
        required_fields = ['work_order_nr', 'article_nr', 'quantity_total', 'final_quantity']
        
        for i, record in enumerate(input_data):
            # 检查必填字段
            for field in required_fields:
                if field not in record or record[field] is None:
                    validation_result['validation_errors'].append(
                        f"第{i+1}条记录缺少必填字段: {field}"
                    )
                    validation_result['is_valid'] = False
            
            # 检查数据类型
            if 'quantity_total' in record:
                try:
                    int(record['quantity_total'])
                except (ValueError, TypeError):
                    validation_result['validation_errors'].append(
                        f"第{i+1}条记录的quantity_total不是有效数字"
                    )
                    validation_result['is_valid'] = False
        
        return validation_result


def create_scheduling_engine(task_id: Optional[str] = None) -> SchedulingEngine:
    """
    创建排产引擎实例
    
    Args:
        task_id: 可选的任务ID
        
    Returns:
        SchedulingEngine: 排产引擎实例
    """
    return SchedulingEngine(task_id)


async def execute_quick_scheduling(
    input_data: List[Dict[str, Any]], 
    maker_mapping: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    快速执行排产流程
    
    Args:
        input_data: 输入数据
        maker_mapping: 机台映射关系
        
    Returns:
        dict: 排产结果
    """
    engine = create_scheduling_engine()
    
    kwargs = {}
    if maker_mapping:
        kwargs['maker_mapping'] = maker_mapping
        
    return await engine.execute_scheduling(input_data, **kwargs)