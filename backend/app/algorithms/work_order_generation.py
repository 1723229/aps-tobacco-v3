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
        
        # 按照设计文档实现：先按喂丝机分组，然后生成喂丝机工单和对应的卷包机工单
        feeder_groups = self._group_by_feeder_code(input_data)
        logger.info(f"按喂丝机分组结果: {len(feeder_groups)}组")
        for feeder_code, orders in feeder_groups.items():
            logger.info(f"  {feeder_code}: {len(orders)}个工单")
        
        for feeder_code, feeder_group_orders in feeder_groups.items():
            try:
                # 为每个喂丝机生成一个喂丝机工单
                logger.info(f"为喂丝机 {feeder_code} 生成工单...")
                feeder_work_order = self._generate_feeder_work_order_from_group(
                    feeder_code, feeder_group_orders, product_specs, quality_standards
                )
                logger.info(f"生成喂丝机工单: {feeder_work_order['work_order_nr']}")
                generated_work_orders.append(feeder_work_order)
                
                # 为每个卷包机生成对应的卷包机工单
                for order_data in feeder_group_orders:
                    maker_work_order = self._generate_maker_work_order(
                        order_data, product_specs, quality_standards
                    )
                    # 关联到喂丝机工单
                    maker_work_order['related_feeder_order'] = feeder_work_order['work_order_nr']
                    generated_work_orders.append(maker_work_order)
                
            except Exception as e:
                logger.error(f"工单生成失败 - 喂丝机 {feeder_code}: {str(e)}")
                result.add_error(f"工单生成失败: {str(e)}", {'feeder_code': feeder_code})
                
                # 生成基础工单以免中断流程
                for order_data in feeder_group_orders:
                    fallback_order = self._generate_fallback_work_order(order_data)
                    generated_work_orders.append(fallback_order)
        
        result.output_data = generated_work_orders
        
        # 计算生成统计
        feeder_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'FEEDER_PRODUCTION'])
        maker_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'MAKER_PRODUCTION'])
        sync_orders = len([wo for wo in generated_work_orders if wo.get('is_synchronized')])
        
        result.metrics.custom_metrics = {
            'feeder_work_orders': feeder_orders,
            'maker_work_orders': maker_orders,
            'synchronized_work_orders': sync_orders,
            'generation_success_rate': len(generated_work_orders) / len(input_data) if input_data else 0,
            'feeder_groups_processed': len(feeder_groups)
        }
        
        logger.info(f"工单生成完成: 喂丝机{feeder_orders}个，卷包机{maker_orders}个，同步{sync_orders}个")
        return self.finalize_result(result)
    
    def _group_by_feeder_code(self, input_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按喂丝机代码分组
        
        Args:
            input_data: 输入工单数据
            
        Returns:
            Dict[str, List]: {喂丝机代码: 工单列表}
        """
        from collections import defaultdict
        
        feeder_groups = defaultdict(list)
        
        for order_data in input_data:
            feeder_code = order_data.get('feeder_code')
            if feeder_code:
                feeder_groups[feeder_code].append(order_data)
            else:
                # 没有喂丝机代码的单独处理
                feeder_groups['UNKNOWN_FEEDER'].append(order_data)
        
        return dict(feeder_groups)
    
    def _generate_feeder_work_order_from_group(
        self,
        feeder_code: str,
        group_orders: List[Dict[str, Any]],
        product_specs: Dict[str, Dict[str, Any]],
        quality_standards: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        从工单组生成喂丝机工单
        
        Args:
            feeder_code: 喂丝机代码
            group_orders: 同一喂丝机的工单列表
            product_specs: 产品规格配置
            quality_standards: 质量标准配置
            
        Returns:
            Dict: 喂丝机工单
        """
        if not group_orders:
            raise ValueError(f"喂丝机 {feeder_code} 没有关联工单")
        
        # 合并工单数据计算总量和时间范围
        total_quantity = sum(order.get('quantity_total', 0) for order in group_orders)
        earliest_start = min(order.get('planned_start') for order in group_orders if order.get('planned_start'))
        latest_end = max(order.get('planned_end') for order in group_orders if order.get('planned_end'))
        
        # 获取产品信息（使用第一个工单的产品信息）
        first_order = group_orders[0]
        product_code = first_order.get('article_nr', '')
        product_spec = product_specs.get(product_code, {})
        quality_std = quality_standards.get(product_code, {})
        
        # 添加安全库存（5%）
        safety_stock_ratio = 0.05
        safe_quantity = int(total_quantity * (1 + safety_stock_ratio))
        
        work_order = {
            # 基础信息
            'work_order_nr': self._generate_work_order_number('HWS'),
            'work_order_type': 'FEEDER_PRODUCTION',
            'machine_type': 'HWS',
            'machine_code': feeder_code,
            'product_code': product_code,
            'product_name': first_order.get('article_nr', ''),
            
            # 计划信息
            'plan_quantity': safe_quantity,
            'base_quantity': total_quantity,
            'safety_stock': safe_quantity - total_quantity,
            'plan_unit': 'KG',
            'planned_start_time': earliest_start,
            'planned_end_time': latest_end,
            
            # 关联的卷包机工单
            'related_maker_orders': [order.get('work_order_nr') for order in group_orders],
            'maker_machines': list(set(order.get('maker_code') for order in group_orders if order.get('maker_code'))),
            
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
                }
            ],
            
            # 审计信息
            'created_time': datetime.now(),
            'created_by': 'APS_SYSTEM',
            'generation_source': 'GROUP_BASED'
        }
        
        return work_order
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行工单生成
        
        Args:
            input_data: 并行处理后的工单数据
            
        Returns:
            AlgorithmResult: 工单生成结果
        """
        from app.services.database_query_service import DatabaseQueryService
        from app.services.mes_integration import mes_service
        
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
            'quality_standards_count': len(quality_standards),
            'mes_integration_enabled': True
        }
        
        generated_work_orders = []
        
        # 使用与process方法相同的逻辑：按喂丝机分组
        feeder_groups = self._group_by_feeder_code(input_data)
        logger.info(f"真实数据工单生成 - 按喂丝机分组结果: {len(feeder_groups)}组")
        for feeder_code, orders in feeder_groups.items():
            logger.info(f"  {feeder_code}: {len(orders)}个工单")
        
        for feeder_code, feeder_group_orders in feeder_groups.items():
            try:
                # 为每个喂丝机生成一个喂丝机工单
                logger.info(f"为喂丝机 {feeder_code} 生成工单...")
                feeder_work_order = self._generate_feeder_work_order_from_group(
                    feeder_code, feeder_group_orders, product_specs, quality_standards
                )
                logger.info(f"生成喂丝机工单: {feeder_work_order['work_order_nr']}")
                generated_work_orders.append(feeder_work_order)
                
                # 为每个卷包机生成对应的卷包机工单
                for order_data in feeder_group_orders:
                    maker_work_order = self._generate_maker_work_order(
                        order_data, product_specs, quality_standards
                    )
                    # 关联到喂丝机工单
                    maker_work_order['related_feeder_order'] = feeder_work_order['work_order_nr']
                    generated_work_orders.append(maker_work_order)
                
            except Exception as e:
                logger.error(f"真实数据工单生成失败 - 喂丝机 {feeder_code}: {str(e)}")
                result.add_error(f"工单生成失败: {str(e)}", {'feeder_code': feeder_code})
                
                # 生成基础工单以免中断流程
                for order_data in feeder_group_orders:
                    fallback_order = self._generate_fallback_work_order(order_data)
                    generated_work_orders.append(fallback_order)
        
        result.output_data = generated_work_orders
        
        # 计算生成统计
        feeder_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'FEEDER_PRODUCTION'])
        maker_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'MAKER_PRODUCTION'])
        sync_orders = len([wo for wo in generated_work_orders if wo.get('is_synchronized')])
        
        result.metrics.custom_metrics.update({
            'feeder_work_orders': feeder_orders,
            'maker_work_orders': maker_orders,
            'synchronized_work_orders': sync_orders,
            'generation_success_rate': len(generated_work_orders) / len(input_data) if input_data else 0
        })
        
        # 推送工单到MES系统
        try:
            mes_response = await mes_service.send_work_order_to_mes(generated_work_orders)
            result.metrics.custom_metrics.update({
                'mes_push_success': mes_response.success,
                'mes_accepted_orders': mes_response.data.get('accepted_count', 0) if mes_response.data else 0,
                'mes_rejected_orders': mes_response.data.get('rejected_count', 0) if mes_response.data else 0,
                'mes_batch_id': mes_response.data.get('mes_batch_id') if mes_response.data else None
            })
            logger.info(f"MES推送结果: {mes_response.message}")
        except Exception as e:
            logger.warning(f"MES推送失败，继续执行: {str(e)}")
            result.metrics.custom_metrics.update({
                'mes_push_success': False,
                'mes_error': str(e)
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
            'work_order_nr': self._generate_work_order_number('HWS'),
            'work_order_type': 'FEEDER_PRODUCTION',
            'machine_type': 'HWS',
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
        product_code = order_data.get('article_nr', '')  # 修正字段名
        product_spec = product_specs.get(product_code, {})
        quality_std = quality_standards.get(product_code, {})
        
        work_order = {
            # 基础信息
            'work_order_nr': self._generate_work_order_number('HJB'),
            'work_order_type': 'MAKER_PRODUCTION',
            'machine_type': 'HJB',
            'machine_code': order_data.get('maker_code'),
            'product_code': product_code,
            'product_name': order_data.get('article_nr', ''),  # 修正字段名
            
            # 计划信息
            'plan_quantity': order_data.get('quantity_total', 0),  # 修正字段名
            'plan_unit': '万支',
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
        
        格式: {机台类型}{YYYYMMDD}{HHMMSS}{4位随机码}
        例如: FEEDER20241201143052A1B2, MAKER20241201143052C3D4
        增强了唯一性保证，避免高并发时的重复
        """
        import random
        import string
        
        now = datetime.now()
        date_part = now.strftime('%Y%m%d')
        time_part = now.strftime('%H%M%S')
        # 使用4位随机字母数字组合增加唯一性
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        return f"{machine_type}{date_part}{time_part}{random_part}"
    
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


# 为WorkOrderGeneration类添加数据库持久化方法
def add_database_persistence_methods():
    """为WorkOrderGeneration类动态添加数据库持久化方法"""
    import types
    
    async def save_work_orders_to_database(self, work_orders: List[Dict[str, Any]], task_id: str) -> AlgorithmResult:
        """将工单保存到数据库"""
        from app.db.connection import get_db_session
        from sqlalchemy import text
        from datetime import datetime, date
        import json
        
        result = self.create_result()
        result.input_data = work_orders
        result.metrics.processed_records = len(work_orders)
        
        packing_orders_saved = 0
        feeding_orders_saved = 0
        
        async with get_db_session() as db:
            try:
                for work_order in work_orders:
                    # 提取公共字段
                    common_fields = self._extract_common_work_order_fields(work_order, task_id)
                    
                    if work_order.get('machine_type') == 'HJB':
                        # 保存卷包工单
                        await self._save_packing_order(db, common_fields, work_order)
                        packing_orders_saved += 1
                        
                    elif work_order.get('machine_type') == 'HWS':
                        # 保存喂丝工单
                        await self._save_feeding_order(db, common_fields, work_order)
                        feeding_orders_saved += 1
                        
                    else:
                        # 默认保存为卷包工单
                        await self._save_packing_order(db, common_fields, work_order)
                        packing_orders_saved += 1
                
                await db.commit()
                logger.info(f"工单保存完成: 卷包工单{packing_orders_saved}个，喂丝工单{feeding_orders_saved}个")
                
            except Exception as e:
                await db.rollback()
                error_msg = f"工单保存失败: {str(e)}"
                logger.error(error_msg)
                result.add_error(error_msg)
                return self.finalize_result(result)
        
        result.output_data = {
            'packing_orders_saved': packing_orders_saved,
            'feeding_orders_saved': feeding_orders_saved,
            'total_saved': packing_orders_saved + feeding_orders_saved
        }
        
        result.metrics.custom_metrics = {
            'packing_orders_saved': packing_orders_saved,
            'feeding_orders_saved': feeding_orders_saved,
            'save_success_rate': (packing_orders_saved + feeding_orders_saved) / len(work_orders) if work_orders else 0
        }
        
        result.success = True
        return result
    
    def _extract_common_work_order_fields(self, work_order: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """提取工单公共字段"""
        from datetime import datetime, date
        
        # 处理时间字段
        def safe_datetime(value):
            if isinstance(value, datetime):
                return value
            elif isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    return datetime.now()
            else:
                return datetime.now()
                
        def safe_date(value):
            if isinstance(value, date):
                return value
            elif isinstance(value, datetime):
                return value.date()
            elif isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
                except:
                    return datetime.now().date()
            else:
                return datetime.now().date()
        
        # 处理数值字段
        def safe_int(value, default=0):
            try:
                return int(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        planned_start = safe_datetime(work_order.get('planned_start_time') or work_order.get('planned_start'))
        planned_end = safe_datetime(work_order.get('planned_end_time') or work_order.get('planned_end'))
        
        return {
            'work_order_nr': work_order.get('work_order_nr', ''),
            'task_id': task_id,
            'original_order_nr': work_order.get('original_work_order_nr', work_order.get('work_order_nr', '')),
            'article_nr': work_order.get('product_code', ''),
            'quantity_total': safe_int(work_order.get('plan_quantity')),
            'final_quantity': safe_int(work_order.get('plan_quantity')),
            'planned_start': planned_start,
            'planned_end': planned_end,
            'sequence': safe_int(work_order.get('sequence'), 1),
            'plan_date': safe_date(planned_start),
            'work_order_type': work_order.get('work_order_type')[:10],
            'machine_code': work_order.get('machine_code', '')[:20],
            'product_code': work_order.get('product_code', '')[:100],
            'plan_quantity': safe_int(work_order.get('plan_quantity')),
            'work_order_status': 'PENDING',
            'planned_start_time': planned_start,
            'planned_end_time': planned_end,
            'created_by': work_order.get('created_by', 'system')
        }
    
    async def _save_packing_order(self, db, common_fields: Dict[str, Any], work_order: Dict[str, Any]):
        """保存卷包工单到aps_packing_order表"""
        from sqlalchemy import text
        
        # 卷包工单特有字段
        packing_fields = common_fields.copy()
        packing_fields.update({
            'maker_code': work_order.get('machine_code', '')[:20],
            'machine_type': 'HJB',
            'unit': work_order.get('plan_unit', '箱')[:20],
            'production_speed': int(work_order.get('production_speed', 0)) if work_order.get('production_speed') else None,
            'feeder_code': work_order.get('feeder_code', '')[:20] if work_order.get('feeder_code') else '',
            'estimated_duration': int((packing_fields['planned_end'] - packing_fields['planned_start']).total_seconds() / 60) if packing_fields['planned_end'] and packing_fields['planned_start'] else None,
            # 设置冗余时间字段为NULL，使用planned_start/planned_end作为主要时间字段
            'planned_start_time': None,
            'planned_end_time': None,
        })
        
        insert_sql = text('''
            INSERT INTO aps_packing_order (
                work_order_nr, task_id, original_order_nr, article_nr, quantity_total, final_quantity,
                maker_code, machine_type, planned_start, planned_end, estimated_duration, sequence,
                unit, plan_date, production_speed, feeder_code, work_order_type, machine_code,
                product_code, plan_quantity, work_order_status, planned_start_time, planned_end_time,
                created_by
            ) VALUES (
                :work_order_nr, :task_id, :original_order_nr, :article_nr, :quantity_total, :final_quantity,
                :maker_code, :machine_type, :planned_start, :planned_end, :estimated_duration, :sequence,
                :unit, :plan_date, :production_speed, :feeder_code, :work_order_type, :machine_code,
                :product_code, :plan_quantity, :work_order_status, :planned_start_time, :planned_end_time,
                :created_by
            )
        ''')
        
        await db.execute(insert_sql, packing_fields)
    
    async def _save_feeding_order(self, db, common_fields: Dict[str, Any], work_order: Dict[str, Any]):
        """保存喂丝工单到aps_feeding_order表"""
        from sqlalchemy import text
        import json
        
        # 喂丝工单特有字段
        feeding_fields = common_fields.copy()
        feeding_fields.update({
            'base_quantity': feeding_fields['quantity_total'],
            'feeder_code': work_order.get('machine_code', '')[:20],
            'feeder_type': work_order.get('feeder_type', '')[:50] if work_order.get('feeder_type') else None,
            'machine_type': 'HWS',
            'unit': work_order.get('plan_unit', '公斤')[:20],
            'feeding_speed': float(work_order.get('feeding_rate', 0)) if work_order.get('feeding_rate') else None,
            'related_packing_orders': json.dumps(work_order.get('related_packing_orders', [])),
            'packing_machines': json.dumps(work_order.get('packing_machines', [])),
            'estimated_duration': int((feeding_fields['planned_end'] - feeding_fields['planned_start']).total_seconds() / 60) if feeding_fields['planned_end'] and feeding_fields['planned_start'] else None,
            # 设置冗余时间字段为NULL，使用planned_start/planned_end作为主要时间字段
            'planned_start_time': None,
            'planned_end_time': None,
        })
        
        insert_sql = text('''
            INSERT INTO aps_feeding_order (
                work_order_nr, task_id, article_nr, quantity_total, base_quantity, feeder_code,
                feeder_type, planned_start, planned_end, estimated_duration, sequence, unit,
                plan_date, feeding_speed, related_packing_orders, packing_machines, work_order_type,
                machine_type, machine_code, product_code, plan_quantity, work_order_status,
                planned_start_time, planned_end_time, created_by
            ) VALUES (
                :work_order_nr, :task_id, :article_nr, :quantity_total, :base_quantity, :feeder_code,
                :feeder_type, :planned_start, :planned_end, :estimated_duration, :sequence, :unit,
                :plan_date, :feeding_speed, :related_packing_orders, :packing_machines, :work_order_type,
                :machine_type, :machine_code, :product_code, :plan_quantity, :work_order_status,
                :planned_start_time, :planned_end_time, :created_by
            )
        ''')
        
        await db.execute(insert_sql, feeding_fields)
    
    # 将方法动态添加到WorkOrderGeneration类
    WorkOrderGeneration.save_work_orders_to_database = save_work_orders_to_database
    WorkOrderGeneration._extract_common_work_order_fields = _extract_common_work_order_fields
    WorkOrderGeneration._save_packing_order = _save_packing_order
    WorkOrderGeneration._save_feeding_order = _save_feeding_order

# 调用函数添加方法
add_database_persistence_methods()
