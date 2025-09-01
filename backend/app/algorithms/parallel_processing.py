"""
APS智慧排产系统 - 并行处理算法（简化重构版）

实现同工单在多机台的同步执行逻辑
核心业务：同一工单的不同机台必须同时开始、同时结束
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class ParallelProcessing(AlgorithmBase):
    """并行处理算法 - 简化版，专注于同工单机台同步"""
    
    def __init__(self):
        super().__init__(ProcessingStage.PARALLEL_PROCESSING)
        
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行并行处理 - 简化版
        
        核心逻辑：
        1. 按work_order_nr分组（相同工单的不同机台）
        2. 每组内同步所有机台的开始和结束时间
        3. 确保同一工单的所有机台同时开始、同时结束
        
        Args:
            input_data: 时间校正后的工单数据
            
        Returns:
            AlgorithmResult: 并行处理结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 按工单号分组
        work_order_groups = self._group_by_work_order(input_data)
        
        synchronized_orders = []
        sync_groups_count = 0
        
        for work_order_nr, orders in work_order_groups.items():
            if len(orders) > 1:
                # 多台机台需要同步
                sync_group = self._synchronize_machines(orders)
                synchronized_orders.extend(sync_group)
                sync_groups_count += 1
                logger.info(f"同步工单{work_order_nr}的{len(orders)}台机台")
            else:
                # 单台机台，直接添加
                order = orders[0].copy()
                order['is_synchronized'] = False
                order['sync_reason'] = '单台机台，无需同步'
                synchronized_orders.append(order)
        
        result.output_data = synchronized_orders
        
        # 更新统计信息
        result.metrics.custom_metrics = {
            'sync_groups_created': sync_groups_count,
            'total_machines_synchronized': sum(len(orders) for orders in work_order_groups.values() if len(orders) > 1),
            'sync_efficiency': sync_groups_count / len(work_order_groups) if work_order_groups else 0
        }
        
        logger.info(f"并行处理完成: 创建{sync_groups_count}个同步组，处理{len(synchronized_orders)}个工单")
        return self.finalize_result(result)
    
    def _group_by_work_order(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按工单号分组
        
        Args:
            orders: 工单列表
            
        Returns:
            Dict: {工单号: [工单列表]}
        """
        groups = defaultdict(list)
        
        for order in orders:
            work_order_nr = order.get('work_order_nr', 'UNKNOWN')
            groups[work_order_nr].append(order)
        
        return dict(groups)
    
    def _synchronize_machines(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        同步一个工单下所有机台的时间
        
        根据用户示例，同一工单的所有机台必须：
        - 同时开始（取最晚的开始时间）
        - 同时结束（取最晚的结束时间）
        
        Args:
            orders: 同一工单的机台订单列表
            
        Returns:
            List[Dict[str, Any]]: 同步后的工单列表
        """
        if not orders:
            return []
        
        # 计算统一的开始和结束时间
        start_times = [order.get('planned_start') for order in orders if order.get('planned_start')]
        end_times = [order.get('planned_end') for order in orders if order.get('planned_end')]
        
        if not start_times or not end_times:
            logger.warning(f"工单{orders[0].get('work_order_nr')}缺少时间信息，跳过同步")
            return orders
        
        # 同时开始：取最晚的开始时间（确保所有前置条件都满足）
        sync_start = max(start_times)
        # 同时结束：取最晚的结束时间（确保所有工作都完成）
        sync_end = max(end_times)
        
        # 生成同步组ID
        sync_group_id = f"SYNC_{orders[0].get('work_order_nr', '')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        synchronized_orders = []
        
        for order in orders:
            sync_order = order.copy()
            
            # 保存原始时间
            sync_order['original_planned_start'] = order.get('planned_start')
            sync_order['original_planned_end'] = order.get('planned_end')
            
            # 设置同步时间
            sync_order['planned_start'] = sync_start
            sync_order['planned_end'] = sync_end
            
            # 添加同步标识
            sync_order['is_synchronized'] = True
            sync_order['sync_group_id'] = sync_group_id
            sync_order['sync_reason'] = '同工单机台同步执行'
            sync_order['sync_timestamp'] = datetime.now()
            sync_order['machine_count'] = len(orders)
            
            # 记录机台信息（用于后续跟踪）
            sync_order['synchronized_machines'] = [
                {
                    'maker_code': o.get('maker_code', ''),
                    'feeder_code': o.get('feeder_code', ''),
                    'original_start': o.get('planned_start'),
                    'original_end': o.get('planned_end')
                }
                for o in orders
            ]
            
            synchronized_orders.append(sync_order)
            
            logger.debug(f"同步机台 {sync_order.get('maker_code', sync_order.get('feeder_code', 'UNKNOWN'))}: "
                        f"{order.get('planned_start')} -> {sync_start}, "
                        f"{order.get('planned_end')} -> {sync_end}")
        
        return synchronized_orders
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行并行处理（简化版）
        
        Args:
            input_data: 时间校正后的工单数据
            
        Returns:
            AlgorithmResult: 并行处理结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True
        }
        
        # 使用相同的简化逻辑
        work_order_groups = self._group_by_work_order(input_data)
        
        synchronized_orders = []
        sync_groups_count = 0
        
        for work_order_nr, orders in work_order_groups.items():
            if len(orders) > 1:
                sync_group = self._synchronize_machines(orders)
                synchronized_orders.extend(sync_group)
                sync_groups_count += 1
                logger.info(f"同步工单{work_order_nr}的{len(orders)}台机台(真实数据)")
            else:
                order = orders[0].copy()
                order['is_synchronized'] = False
                order['sync_reason'] = '单台机台，无需同步'
                synchronized_orders.append(order)
        
        result.output_data = synchronized_orders
        
        # 更新统计信息
        result.metrics.custom_metrics.update({
            'sync_groups_created': sync_groups_count,
            'total_machines_synchronized': sum(len(orders) for orders in work_order_groups.values() if len(orders) > 1),
            'sync_efficiency': sync_groups_count / len(work_order_groups) if work_order_groups else 0
        })
        
        logger.info(f"并行处理完成(真实数据): 创建{sync_groups_count}个同步组，处理{len(synchronized_orders)}个工单")
        return self.finalize_result(result)


def create_parallel_processing() -> ParallelProcessing:
    """
    创建并行处理算法实例
    
    Returns:
        ParallelProcessing: 并行处理算法实例
    """
    return ParallelProcessing()


def process_parallel_execution(work_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    快速并行执行处理（简化版）
    
    Args:
        work_orders: 工单列表
        
    Returns:
        List[Dict]: 并行处理后的工单列表
    """
    processor = create_parallel_processing()
    result = processor.process(work_orders)
    return result.output_data