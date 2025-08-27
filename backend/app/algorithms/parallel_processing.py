"""
APS智慧排产系统 - 并行切分算法

实现同工单在多机台的并行处理调度逻辑
确保喂丝机和卷包机的同步协调执行
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class ParallelProcessing(AlgorithmBase):
    """并行切分算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.PARALLEL_PROCESSING)
        
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行并行切分处理
        
        Args:
            input_data: 时间校正后的工单数据
            machine_relations: 机台关系映射 {喂丝机: [卷包机列表]}
            machine_speeds: 机台速度配置 {机台代码: {速度信息}}
            
        Returns:
            AlgorithmResult: 并行切分结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        machine_relations = kwargs.get('machine_relations', {})
        machine_speeds = kwargs.get('machine_speeds', {})
        
        # 按产品和月份分组工单
        grouped_orders = self._group_orders_by_product_month(input_data)
        
        parallel_orders = []
        
        for group_key, orders in grouped_orders.items():
            try:
                # 为每组工单生成并行执行计划
                parallel_group = self._create_parallel_execution_plan(
                    orders, machine_relations, machine_speeds
                )
                parallel_orders.extend(parallel_group)
                
            except Exception as e:
                logger.error(f"并行切分失败 - 组 {group_key}: {str(e)}")
                result.add_error(f"组并行切分失败: {str(e)}", {'group': group_key})
                # 失败时保留原工单
                parallel_orders.extend(orders)
        
        result.output_data = parallel_orders
        
        # 计算并行处理统计
        parallel_groups = len(set(order.get('parallel_group_id') for order in parallel_orders if order.get('parallel_group_id')))
        sync_pairs = sum(1 for order in parallel_orders if order.get('sync_machine_code'))
        
        result.metrics.custom_metrics = {
            'parallel_groups_created': parallel_groups,
            'synchronized_pairs': sync_pairs,
            'parallel_efficiency': sync_pairs / len(input_data) if input_data else 0
        }
        
        logger.info(f"并行切分完成: 创建{parallel_groups}个并行组，{sync_pairs}个同步对")
        return self.finalize_result(result)
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行并行切分
        
        Args:
            input_data: 时间校正后的工单数据
            
        Returns:
            AlgorithmResult: 并行切分结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 从数据库查询机台关系和速度配置
        machine_relations = await DatabaseQueryService.get_machine_relations()
        machine_speeds = await self._get_machine_speeds_from_db()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'machine_relations_count': len(machine_relations),
            'machine_speeds_count': len(machine_speeds)
        }
        
        # 按产品和月份分组工单
        grouped_orders = self._group_orders_by_product_month(input_data)
        
        parallel_orders = []
        
        for group_key, orders in grouped_orders.items():
            try:
                # 为每组工单生成并行执行计划
                parallel_group = self._create_parallel_execution_plan(
                    orders, machine_relations, machine_speeds
                )
                parallel_orders.extend(parallel_group)
                
            except Exception as e:
                logger.error(f"并行切分失败 - 组 {group_key}: {str(e)}")
                result.add_error(f"组并行切分失败: {str(e)}", {'group': group_key})
                parallel_orders.extend(orders)
        
        result.output_data = parallel_orders
        
        # 计算并行处理统计
        parallel_groups = len(set(order.get('parallel_group_id') for order in parallel_orders if order.get('parallel_group_id')))
        sync_pairs = sum(1 for order in parallel_orders if order.get('sync_machine_code'))
        
        result.metrics.custom_metrics.update({
            'parallel_groups_created': parallel_groups,
            'synchronized_pairs': sync_pairs,
            'parallel_efficiency': sync_pairs / len(input_data) if input_data else 0
        })
        
        logger.info(f"并行切分完成(真实数据): 创建{parallel_groups}个并行组，{sync_pairs}个同步对")
        return self.finalize_result(result)
    
    def _group_orders_by_product_month(
        self, 
        orders: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按产品和月份分组工单"""
        groups = {}
        
        for order in orders:
            product_code = order.get('product_code', 'unknown')
            planned_start = order.get('planned_start')
            
            if planned_start:
                month_key = planned_start.strftime('%Y-%m')
            else:
                month_key = 'unknown'
            
            group_key = f"{product_code}_{month_key}"
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(order)
        
        return groups
    
    def _create_parallel_execution_plan(
        self,
        orders: List[Dict[str, Any]],
        machine_relations: Dict[str, List[str]],
        machine_speeds: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        为工单组创建并行执行计划
        
        Args:
            orders: 同组工单列表
            machine_relations: 机台关系映射
            machine_speeds: 机台速度配置
            
        Returns:
            List[Dict]: 带并行信息的工单列表
        """
        if not orders:
            return []
        
        # 生成并行组ID
        parallel_group_id = f"parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(orders)}"
        
        # 按机台类型分离工单
        feeder_orders = [o for o in orders if o.get('machine_type') == 'FEEDER']
        maker_orders = [o for o in orders if o.get('machine_type') == 'MAKER']
        
        result_orders = []
        
        # 处理喂丝机工单
        for feeder_order in feeder_orders:
            feeder_code = feeder_order.get('maker_code')  # 工单中的机台代码
            
            # 查找对应的卷包机
            corresponding_makers = machine_relations.get(feeder_code, [])
            
            if corresponding_makers:
                # 找到匹配的卷包机工单
                matching_maker_orders = [
                    mo for mo in maker_orders
                    if mo.get('maker_code') in corresponding_makers and
                       mo.get('product_code') == feeder_order.get('product_code')
                ]
                
                if matching_maker_orders:
                    # 创建同步对
                    sync_pair = self._create_sync_pair(
                        feeder_order, 
                        matching_maker_orders[0],  # 选择第一个匹配的
                        parallel_group_id,
                        machine_speeds
                    )
                    result_orders.extend(sync_pair)
                    
                    # 从待处理列表中移除已处理的工单
                    if matching_maker_orders[0] in maker_orders:
                        maker_orders.remove(matching_maker_orders[0])
                else:
                    # 没有匹配的卷包机，独立处理
                    standalone_order = self._create_standalone_order(feeder_order, parallel_group_id)
                    result_orders.append(standalone_order)
            else:
                # 没有关联机台，独立处理
                standalone_order = self._create_standalone_order(feeder_order, parallel_group_id)
                result_orders.append(standalone_order)
        
        # 处理剩余的卷包机工单
        for maker_order in maker_orders:
            standalone_order = self._create_standalone_order(maker_order, parallel_group_id)
            result_orders.append(standalone_order)
        
        return result_orders
    
    def _create_sync_pair(
        self,
        feeder_order: Dict[str, Any],
        maker_order: Dict[str, Any], 
        parallel_group_id: str,
        machine_speeds: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        创建同步执行对
        
        Args:
            feeder_order: 喂丝机工单
            maker_order: 卷包机工单
            parallel_group_id: 并行组ID
            machine_speeds: 机台速度配置
            
        Returns:
            List[Dict]: 同步的工单对
        """
        # 计算同步时间
        sync_start, sync_end = self._calculate_sync_time(
            feeder_order, maker_order, machine_speeds
        )
        
        # 创建同步后的喂丝机工单
        synced_feeder = feeder_order.copy()
        synced_feeder.update({
            'parallel_group_id': parallel_group_id,
            'sync_machine_code': maker_order.get('maker_code'),
            'sync_type': 'FEEDER_MAKER_PAIR',
            'original_planned_start': feeder_order.get('planned_start'),
            'original_planned_end': feeder_order.get('planned_end'),
            'planned_start': sync_start,
            'planned_end': sync_end,
            'is_synchronized': True,
            'sync_reason': f"与卷包机{maker_order.get('maker_code')}同步执行"
        })
        
        # 创建同步后的卷包机工单
        synced_maker = maker_order.copy()
        synced_maker.update({
            'parallel_group_id': parallel_group_id,
            'sync_machine_code': feeder_order.get('maker_code'),
            'sync_type': 'FEEDER_MAKER_PAIR',
            'original_planned_start': maker_order.get('planned_start'),
            'original_planned_end': maker_order.get('planned_end'),
            'planned_start': sync_start,
            'planned_end': sync_end,
            'is_synchronized': True,
            'sync_reason': f"与喂丝机{feeder_order.get('maker_code')}同步执行"
        })
        
        return [synced_feeder, synced_maker]
    
    def _create_standalone_order(
        self, 
        order: Dict[str, Any], 
        parallel_group_id: str
    ) -> Dict[str, Any]:
        """创建独立执行工单"""
        standalone_order = order.copy()
        standalone_order.update({
            'parallel_group_id': parallel_group_id,
            'sync_type': 'STANDALONE',
            'is_synchronized': False,
            'sync_reason': "无可匹配的关联机台，独立执行"
        })
        
        return standalone_order
    
    def _calculate_sync_time(
        self,
        feeder_order: Dict[str, Any],
        maker_order: Dict[str, Any],
        machine_speeds: Dict[str, Dict[str, Any]]
    ) -> Tuple[datetime, datetime]:
        """
        计算同步执行时间
        
        Args:
            feeder_order: 喂丝机工单
            maker_order: 卷包机工单
            machine_speeds: 机台速度配置
            
        Returns:
            Tuple[datetime, datetime]: (同步开始时间, 同步结束时间)
        """
        # 获取两个工单的时间范围
        feeder_start = feeder_order.get('planned_start')
        feeder_end = feeder_order.get('planned_end')
        maker_start = maker_order.get('planned_start')
        maker_end = maker_order.get('planned_end')
        
        # 同步开始时间：取较晚的开始时间
        sync_start = max(feeder_start, maker_start) if feeder_start and maker_start else (feeder_start or maker_start)
        
        # 根据速度配比计算同步结束时间
        feeder_code = feeder_order.get('maker_code')
        maker_code = maker_order.get('maker_code')
        
        feeder_speed = machine_speeds.get(feeder_code, {}).get('hourly_capacity', 100)
        maker_speed = machine_speeds.get(maker_code, {}).get('hourly_capacity', 100)
        
        # 计算总产量
        total_quantity = feeder_order.get('plan_quantity', 0) + maker_order.get('plan_quantity', 0)
        
        # 按速度较慢的机台计算时间
        limiting_speed = min(feeder_speed, maker_speed)
        if limiting_speed > 0:
            required_hours = total_quantity / limiting_speed
            sync_end = sync_start + timedelta(hours=required_hours)
        else:
            # 如果没有速度信息，使用较长的原计划时间
            feeder_duration = (feeder_end - feeder_start) if feeder_end and feeder_start else timedelta(hours=8)
            maker_duration = (maker_end - maker_start) if maker_end and maker_start else timedelta(hours=8)
            sync_end = sync_start + max(feeder_duration, maker_duration)
        
        return sync_start, sync_end
    
    async def _get_machine_speeds_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库查询机台速度配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认速度配置
        return {
            'default': {
                'hourly_capacity': 100,
                'efficiency_rate': 0.85,
                'setup_time_minutes': 30
            }
        }


def create_parallel_processing() -> ParallelProcessing:
    """
    创建并行切分算法实例
    
    Returns:
        ParallelProcessing: 并行切分算法实例
    """
    return ParallelProcessing()


def process_parallel_execution(
    work_orders: List[Dict[str, Any]],
    machine_relations: Dict[str, List[str]] = None,
    machine_speeds: Dict[str, Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    快速并行执行处理
    
    Args:
        work_orders: 工单列表
        machine_relations: 机台关系映射
        machine_speeds: 机台速度配置
        
    Returns:
        List[Dict]: 并行处理后的工单列表
    """
    processor = create_parallel_processing()
    
    kwargs = {}
    if machine_relations:
        kwargs['machine_relations'] = machine_relations
    if machine_speeds:
        kwargs['machine_speeds'] = machine_speeds
    
    result = processor.process(work_orders, **kwargs)
    return result.output_data