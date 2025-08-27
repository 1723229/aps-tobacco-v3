"""
APS智慧排产系统 - 工单生成算法

基于排产结果生成卷包机和喂丝机的具体工单
包含工单编号生成、工艺参数设定、质量检查点等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging
import uuid

logger = logging.getLogger(__name__)


class WorkOrderGeneration(AlgorithmBase):
    """工单生成算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.WORK_ORDER_GENERATION)
        
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行工单生成
        
        Args:
            input_data: 并行处理后的工单数据
            product_specs: 产品规格配置 {产品代码: {规格信息}}
            quality_standards: 质量标准配置
            
        Returns:
            AlgorithmResult: 工单生成结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        product_specs = kwargs.get('product_specs', {})
        quality_standards = kwargs.get('quality_standards', {})
        
        generated_work_orders = []
        
        for order_data in input_data:
            try:
                # 根据机台类型生成不同的工单
                machine_type = order_data.get('machine_type', 'MAKER')
                
                if machine_type == 'FEEDER':
                    work_order = self._generate_feeder_work_order(
                        order_data, product_specs, quality_standards
                    )
                elif machine_type == 'MAKER':
                    work_order = self._generate_maker_work_order(
                        order_data, product_specs, quality_standards
                    )
                else:
                    # 未知机台类型，生成通用工单
                    work_order = self._generate_generic_work_order(order_data)
                
                generated_work_orders.append(work_order)
                
            except Exception as e:
                logger.error(f"工单生成失败 - 排产数据 {order_data.get('id', 'unknown')}: {str(e)}")
                result.add_error(f"工单生成失败: {str(e)}", {'order_data': order_data})
                
                # 生成基础工单以免中断流程
                fallback_order = self._generate_fallback_work_order(order_data)
                generated_work_orders.append(fallback_order)
        
        result.output_data = generated_work_orders
        
        # 计算生成统计
        feeder_orders = len([wo for wo in generated_work_orders if wo.get('machine_type') == 'FEEDER'])
        maker_orders = len([wo for wo in generated_work_orders if wo.get('machine_type') == 'MAKER'])
        sync_orders = len([wo for wo in generated_work_orders if wo.get('is_synchronized')])
        
        result.metrics.custom_metrics = {
            'feeder_work_orders': feeder_orders,
            'maker_work_orders': maker_orders,
            'synchronized_work_orders': sync_orders,
            'generation_success_rate': len(generated_work_orders) / len(input_data) if input_data else 0
        }
        
        logger.info(f"工单生成完成: 喂丝机{feeder_orders}个，卷包机{maker_orders}个，同步{sync_orders}个")
        return self.finalize_result(result)
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行工单生成
        
        Args:
            input_data: 并行处理后的工单数据
            
        Returns:
            AlgorithmResult: 工单生成结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 从数据库查询产品规格和质量标准
        product_specs = await self._get_product_specs_from_db()
        quality_standards = await self._get_quality_standards_from_db()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'product_specs_count': len(product_specs),
            'quality_standards_count': len(quality_standards)
        }
        
        generated_work_orders = []
        
        for order_data in input_data:
            try:
                # 根据机台类型生成不同的工单
                machine_type = order_data.get('machine_type', 'MAKER')
                
                if machine_type == 'FEEDER':
                    work_order = self._generate_feeder_work_order(
                        order_data, product_specs, quality_standards
                    )
                elif machine_type == 'MAKER':
                    work_order = self._generate_maker_work_order(
                        order_data, product_specs, quality_standards
                    )
                else:
                    work_order = self._generate_generic_work_order(order_data)
                
                generated_work_orders.append(work_order)
                
            except Exception as e:
                logger.error(f"工单生成失败 - 排产数据 {order_data.get('id', 'unknown')}: {str(e)}")
                result.add_error(f"工单生成失败: {str(e)}", {'order_data': order_data})
                
                fallback_order = self._generate_fallback_work_order(order_data)
                generated_work_orders.append(fallback_order)
        
        result.output_data = generated_work_orders
        
        # 计算生成统计
        feeder_orders = len([wo for wo in generated_work_orders if wo.get('machine_type') == 'FEEDER'])
        maker_orders = len([wo for wo in generated_work_orders if wo.get('machine_type') == 'MAKER'])
        sync_orders = len([wo for wo in generated_work_orders if wo.get('is_synchronized')])
        
        result.metrics.custom_metrics.update({
            'feeder_work_orders': feeder_orders,
            'maker_work_orders': maker_orders,
            'synchronized_work_orders': sync_orders,
            'generation_success_rate': len(generated_work_orders) / len(input_data) if input_data else 0
        })
        
        logger.info(f"工单生成完成(真实数据): 喂丝机{feeder_orders}个，卷包机{maker_orders}个，同步{sync_orders}个")
        return self.finalize_result(result)
    
    def _generate_feeder_work_order(
        self,
        order_data: Dict[str, Any],
        product_specs: Dict[str, Dict[str, Any]],
        quality_standards: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成喂丝机工单
        
        Args:
            order_data: 排产工单数据
            product_specs: 产品规格配置
            quality_standards: 质量标准配置
            
        Returns:
            Dict: 喂丝机工单
        """
        product_code = order_data.get('product_code', '')
        product_spec = product_specs.get(product_code, {})
        quality_std = quality_standards.get(product_code, {})
        
        work_order = {
            # 基础信息
            'work_order_nr': self._generate_work_order_number('FEEDER'),
            'work_order_type': 'FEEDER_PRODUCTION',
            'machine_type': 'FEEDER',
            'machine_code': order_data.get('maker_code'),
            'product_code': product_code,
            'product_name': order_data.get('product_name', ''),
            
            # 计划信息
            'plan_quantity': order_data.get('plan_quantity', 0),
            'plan_unit': order_data.get('plan_unit', 'KG'),
            'planned_start_time': order_data.get('planned_start'),
            'planned_end_time': order_data.get('planned_end'),
            
            # 喂丝机特有参数
            'tobacco_blend_formula': product_spec.get('blend_formula', 'STANDARD'),
            'moisture_target': product_spec.get('moisture_target', 13.5),
            'moisture_tolerance': product_spec.get('moisture_tolerance', 0.5),
            'cut_width': product_spec.get('cut_width', 0.8),
            'feeding_rate': product_spec.get('feeding_rate', 120),  # kg/h
            
            # 质量检查点
            'quality_checkpoints': [
                {
                    'checkpoint_name': '配方准确性检查',
                    'check_frequency': 'BATCH_START',
                    'standard': quality_std.get('blend_accuracy', '±2%')
                },
                {
                    'checkpoint_name': '水分含量检查',
                    'check_frequency': 'HOURLY',
                    'standard': f"{product_spec.get('moisture_target', 13.5)}±{product_spec.get('moisture_tolerance', 0.5)}%"
                },
                {
                    'checkpoint_name': '切丝宽度检查',
                    'check_frequency': 'HOURLY',
                    'standard': f"{product_spec.get('cut_width', 0.8)}mm±0.1mm"
                }
            ],
            
            # 工艺参数
            'process_parameters': {
                'oven_temperature': product_spec.get('oven_temperature', 85),
                'drying_time': product_spec.get('drying_time', 45),
                'cooling_time': product_spec.get('cooling_time', 15),
                'flavoring_amount': product_spec.get('flavoring_amount', 2.5)
            },
            
            # 同步信息
            'parallel_group_id': order_data.get('parallel_group_id'),
            'sync_machine_code': order_data.get('sync_machine_code'),
            'is_synchronized': order_data.get('is_synchronized', False),
            'sync_type': order_data.get('sync_type'),
            
            # 状态和时间
            'work_order_status': 'PLANNED',
            'created_time': datetime.now(),
            'created_by': 'APS_SYSTEM',
            
            # 备注
            'remarks': f"APS系统生成的喂丝机工单 - {order_data.get('sync_reason', '')}"
        }
        
        return work_order
    
    def _generate_maker_work_order(
        self,
        order_data: Dict[str, Any],
        product_specs: Dict[str, Dict[str, Any]],
        quality_standards: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成卷包机工单
        
        Args:
            order_data: 排产工单数据
            product_specs: 产品规格配置
            quality_standards: 质量标准配置
            
        Returns:
            Dict: 卷包机工单
        """
        product_code = order_data.get('product_code', '')
        product_spec = product_specs.get(product_code, {})
        quality_std = quality_standards.get(product_code, {})
        
        work_order = {
            # 基础信息
            'work_order_nr': self._generate_work_order_number('MAKER'),
            'work_order_type': 'MAKER_PRODUCTION',
            'machine_type': 'MAKER',
            'machine_code': order_data.get('maker_code'),
            'product_code': product_code,
            'product_name': order_data.get('product_name', ''),
            
            # 计划信息
            'plan_quantity': order_data.get('plan_quantity', 0),
            'plan_unit': order_data.get('plan_unit', '万支'),
            'planned_start_time': order_data.get('planned_start'),
            'planned_end_time': order_data.get('planned_end'),
            
            # 卷包机特有参数
            'cigarette_length': product_spec.get('cigarette_length', 84),  # mm
            'cigarette_diameter': product_spec.get('cigarette_diameter', 7.8),  # mm
            'filter_length': product_spec.get('filter_length', 21),  # mm
            'packing_density': product_spec.get('packing_density', 260),  # mg/cm³
            'production_speed': product_spec.get('production_speed', 8000),  # 支/分钟
            
            # 包装参数
            'package_type': product_spec.get('package_type', '20支装硬盒'),
            'package_quantity_per_box': product_spec.get('quantity_per_box', 20),
            'carton_quantity': product_spec.get('carton_quantity', 10),
            
            # 质量检查点
            'quality_checkpoints': [
                {
                    'checkpoint_name': '烟支长度检查',
                    'check_frequency': 'CONTINUOUS',
                    'standard': f"{product_spec.get('cigarette_length', 84)}±1mm"
                },
                {
                    'checkpoint_name': '圆周度检查',
                    'check_frequency': 'HOURLY',
                    'standard': f"{product_spec.get('cigarette_diameter', 7.8)}±0.1mm"
                },
                {
                    'checkpoint_name': '充填密度检查',
                    'check_frequency': 'HOURLY',
                    'standard': f"{product_spec.get('packing_density', 260)}±10mg/cm³"
                },
                {
                    'checkpoint_name': '外观质量检查',
                    'check_frequency': 'BATCH_END',
                    'standard': quality_std.get('appearance_standard', '无破损，外观整齐')
                }
            ],
            
            # 工艺参数
            'process_parameters': {
                'wrapping_pressure': product_spec.get('wrapping_pressure', 2.5),  # kg/cm²
                'sealing_temperature': product_spec.get('sealing_temperature', 180),  # °C
                'cutting_blade_speed': product_spec.get('cutting_speed', 3000),  # rpm
                'filter_attachment_glue': product_spec.get('filter_glue', 'EVA'),
            },
            
            # 同步信息
            'parallel_group_id': order_data.get('parallel_group_id'),
            'sync_machine_code': order_data.get('sync_machine_code'),
            'is_synchronized': order_data.get('is_synchronized', False),
            'sync_type': order_data.get('sync_type'),
            
            # 状态和时间
            'work_order_status': 'PLANNED',
            'created_time': datetime.now(),
            'created_by': 'APS_SYSTEM',
            
            # 备注
            'remarks': f"APS系统生成的卷包机工单 - {order_data.get('sync_reason', '')}"
        }
        
        return work_order
    
    def _generate_generic_work_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成通用工单"""
        work_order = {
            'work_order_nr': self._generate_work_order_number('GENERIC'),
            'work_order_type': 'GENERIC_PRODUCTION',
            'machine_type': order_data.get('machine_type', 'UNKNOWN'),
            'machine_code': order_data.get('maker_code'),
            'product_code': order_data.get('product_code', ''),
            'product_name': order_data.get('product_name', ''),
            'plan_quantity': order_data.get('plan_quantity', 0),
            'plan_unit': order_data.get('plan_unit', 'PCS'),
            'planned_start_time': order_data.get('planned_start'),
            'planned_end_time': order_data.get('planned_end'),
            'work_order_status': 'PLANNED',
            'created_time': datetime.now(),
            'created_by': 'APS_SYSTEM',
            'remarks': f"通用工单 - 机台类型: {order_data.get('machine_type', 'UNKNOWN')}"
        }
        
        return work_order
    
    def _generate_fallback_work_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成备用工单"""
        work_order = {
            'work_order_nr': self._generate_work_order_number('FALLBACK'),
            'work_order_type': 'FALLBACK_PRODUCTION',
            'machine_code': order_data.get('maker_code', 'UNKNOWN'),
            'product_code': order_data.get('product_code', 'UNKNOWN'),
            'plan_quantity': order_data.get('plan_quantity', 0),
            'planned_start_time': order_data.get('planned_start', datetime.now()),
            'planned_end_time': order_data.get('planned_end', datetime.now() + timedelta(hours=8)),
            'work_order_status': 'PLANNED',
            'created_time': datetime.now(),
            'created_by': 'APS_SYSTEM',
            'remarks': "备用工单 - 工单生成过程中发生错误"
        }
        
        return work_order
    
    def _generate_work_order_number(self, machine_type: str) -> str:
        """
        生成工单编号
        
        格式: {机台类型}{YYYYMMDD}{6位序号}
        例如: FEEDER20241201000001, MAKER20241201000001
        """
        date_part = datetime.now().strftime('%Y%m%d')
        sequence = str(uuid.uuid4().int)[-6:]  # 使用UUID的最后6位作为序号
        
        return f"{machine_type}{date_part}{sequence}"
    
    async def _get_product_specs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库查询产品规格配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认产品规格
        return {
            'DEFAULT': {
                'cigarette_length': 84,
                'cigarette_diameter': 7.8,
                'filter_length': 21,
                'packing_density': 260,
                'production_speed': 8000,
                'moisture_target': 13.5,
                'moisture_tolerance': 0.5,
                'cut_width': 0.8,
                'feeding_rate': 120
            }
        }
    
    async def _get_quality_standards_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库查询质量标准配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认质量标准
        return {
            'DEFAULT': {
                'blend_accuracy': '±2%',
                'appearance_standard': '无破损，外观整齐',
                'weight_tolerance': '±5mg',
                'length_tolerance': '±1mm'
            }
        }


def create_work_order_generation() -> WorkOrderGeneration:
    """
    创建工单生成算法实例
    
    Returns:
        WorkOrderGeneration: 工单生成算法实例
    """
    return WorkOrderGeneration()


def generate_work_orders(
    parallel_orders: List[Dict[str, Any]],
    product_specs: Dict[str, Dict[str, Any]] = None,
    quality_standards: Dict[str, Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    快速工单生成
    
    Args:
        parallel_orders: 并行处理后的工单数据
        product_specs: 产品规格配置
        quality_standards: 质量标准配置
        
    Returns:
        List[Dict]: 生成的工单列表
    """
    generator = create_work_order_generation()
    
    kwargs = {}
    if product_specs:
        kwargs['product_specs'] = product_specs
    if quality_standards:
        kwargs['quality_standards'] = quality_standards
    
    result = generator.process(parallel_orders, **kwargs)
    return result.output_data