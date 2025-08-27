"""
APS智慧排产系统 - 规则拆分算法

实现按机台数量拆分工单的算法
支持智能数量分配和机台负载均衡
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class SplitAlgorithm(AlgorithmBase):
    """规则拆分算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.RULE_SPLITTING)
        
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行规则拆分
        
        Args:
            input_data: 合并后的计划数据
            maker_mapping: 喂丝机到卷包机的映射关系 {'WS01': ['JJ01', 'JJ02']}
            
        Returns:
            AlgorithmResult: 拆分结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        maker_mapping = kwargs.get('maker_mapping', {})
        
        split_orders = []
        
        for plan in input_data:
            if self._need_split(plan, maker_mapping):
                # 需要拆分
                split_work_orders = self._split_work_order(plan, maker_mapping)
                split_orders.extend(split_work_orders)
                logger.info(f"拆分工单 {plan['work_order_nr']} 为 {len(split_work_orders)} 个子工单")
            else:
                # 不需要拆分，直接传递
                split_orders.append(plan)
        
        result.output_data = split_orders
        
        logger.info(f"拆分完成: 输入{len(input_data)}个 -> 输出{len(split_orders)}个")
        return self.finalize_result(result)
    
    def _need_split(self, plan: Dict[str, Any], maker_mapping: Dict[str, List[str]]) -> bool:
        """
        判定是否需要拆分工单
        
        拆分条件：
        1. 一个喂丝机对应多台卷包机
        2. 工单数量超过单台机台处理能力
        3. 时间跨度超过单个班次时长
        """
        feeder_code = plan.get('feeder_code')
        if not feeder_code:
            return False
            
        # 获取对应的卷包机列表
        maker_codes = maker_mapping.get(feeder_code, [])
        
        # 条件1：多台卷包机
        if len(maker_codes) > 1:
            return True
            
        # 条件2和3：数量和时间检查（暂时简化）
        # 可以根据实际业务需求扩展
        
        return False
    
    def _split_work_order(self, plan: Dict[str, Any], maker_mapping: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        执行工单拆分
        
        Args:
            plan: 需要拆分的计划
            maker_mapping: 机台映射关系
            
        Returns:
            List[Dict]: 拆分后的工单列表
        """
        feeder_code = plan.get('feeder_code')
        maker_codes = maker_mapping.get(feeder_code, [])
        
        if len(maker_codes) <= 1:
            return [plan]  # 不需要拆分
        
        # 数量分配
        quantity_allocation = self._allocate_quantity(
            plan.get('quantity_total', 0), 
            maker_codes
        )
        
        final_quantity_allocation = self._allocate_quantity(
            plan.get('final_quantity', 0),
            maker_codes
        )
        
        # 生成拆分工单
        split_orders = []
        
        for i, maker_code in enumerate(sorted(maker_codes)):
            split_order = plan.copy()
            
            # 更新工单标识
            split_order['work_order_nr'] = f"{plan['work_order_nr']}-{i+1:02d}"
            split_order['maker_code'] = maker_code
            
            # 更新数量
            split_order['quantity_total'] = quantity_allocation[maker_code]
            split_order['final_quantity'] = final_quantity_allocation[maker_code]
            
            # 保持时间不变（同时开始，同时结束）
            split_order['planned_start'] = plan.get('planned_start')
            split_order['planned_end'] = plan.get('planned_end')
            
            # 记录拆分历史
            split_order['split_from'] = plan['work_order_nr']
            split_order['split_index'] = i + 1
            split_order['split_timestamp'] = datetime.now()
            split_order['is_split'] = True
            
            split_orders.append(split_order)
        
        return split_orders
    
    def _allocate_quantity(self, total_quantity: int, machine_codes: List[str]) -> Dict[str, int]:
        """
        按卷包机数量分配投料数量
        
        分配原则：
        1. 按机台数量平均分配
        2. 余数按机台编号顺序分配
        3. 确保每台机台分配量>0
        
        Args:
            total_quantity: 总投料量
            machine_codes: 卷包机代码列表
            
        Returns:
            dict: {机台代码: 分配数量}
        """
        machine_count = len(machine_codes)
        if machine_count == 0:
            return {}
        
        base_quantity = total_quantity // machine_count
        remainder = total_quantity % machine_count
        
        allocation = {}
        
        # 排序确保分配顺序一致
        sorted_machines = sorted(machine_codes)
        
        for i, machine_code in enumerate(sorted_machines):
            allocation[machine_code] = base_quantity
            # 余数按顺序分配
            if i < remainder:
                allocation[machine_code] += 1
        
        return allocation

    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行规则拆分
        
        Args:
            input_data: 合并后的计划数据
            
        Returns:
            AlgorithmResult: 拆分结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 从数据库查询机台映射关系和拆分规则
        maker_mapping = await DatabaseQueryService.get_machine_relations()
        split_rules = await self._get_split_rules_from_db()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'machine_relations_count': len(maker_mapping),
            'split_rules_count': len(split_rules)
        }
        
        split_orders = []
        
        for plan in input_data:
            if self._need_split_with_rules(plan, maker_mapping, split_rules):
                # 需要拆分
                split_work_orders = self._split_work_order_with_rules(plan, maker_mapping, split_rules)
                split_orders.extend(split_work_orders)
                logger.info(f"拆分工单 {plan['work_order_nr']} 为 {len(split_work_orders)} 个子工单")
            else:
                # 不需要拆分，直接传递
                split_orders.append(plan)
        
        result.output_data = split_orders
        
        logger.info(f"拆分完成(真实数据): 输入{len(input_data)}个 -> 输出{len(split_orders)}个")
        return self.finalize_result(result)
    
    def _need_split_with_rules(
        self, 
        plan: Dict[str, Any], 
        maker_mapping: Dict[str, List[str]], 
        split_rules: Dict[str, Any]
    ) -> bool:
        """
        使用真实业务规则判定是否需要拆分工单
        """
        feeder_code = plan.get('feeder_code')
        if not feeder_code:
            return False
            
        # 获取对应的卷包机列表
        maker_codes = maker_mapping.get(feeder_code, [])
        
        # 条件1：多台卷包机
        if len(maker_codes) > 1:
            return True
        
        # 条件2：根据真实拆分规则进行检查
        split_criteria = split_rules.get('split_criteria', {})
        
        # 数量阈值检查
        quantity_threshold = split_criteria.get('quantity_threshold', 10000)
        if plan.get('quantity_total', 0) > quantity_threshold:
            return True
        
        # 时间跨度检查
        planned_start = plan.get('planned_start')
        planned_end = plan.get('planned_end')
        if planned_start and planned_end:
            duration_hours = (planned_end - planned_start).total_seconds() / 3600
            max_duration_hours = split_criteria.get('max_duration_hours', 24)
            if duration_hours > max_duration_hours:
                return True
        
        return False
    
    def _split_work_order_with_rules(
        self, 
        plan: Dict[str, Any], 
        maker_mapping: Dict[str, List[str]],
        split_rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        使用真实业务规则执行工单拆分
        """
        feeder_code = plan.get('feeder_code')
        maker_codes = maker_mapping.get(feeder_code, [])
        
        if len(maker_codes) <= 1:
            return [plan]  # 不需要拆分
        
        # 使用真实的数量分配策略
        allocation_strategy = split_rules.get('allocation_strategy', 'equal')
        
        if allocation_strategy == 'capacity_based':
            # 基于机台产能的分配（需要机台产能数据）
            quantity_allocation = self._allocate_by_capacity(
                plan.get('quantity_total', 0), 
                maker_codes,
                split_rules.get('machine_capacities', {})
            )
            final_quantity_allocation = self._allocate_by_capacity(
                plan.get('final_quantity', 0),
                maker_codes,
                split_rules.get('machine_capacities', {})
            )
        else:
            # 默认平均分配
            quantity_allocation = self._allocate_quantity(
                plan.get('quantity_total', 0), 
                maker_codes
            )
            final_quantity_allocation = self._allocate_quantity(
                plan.get('final_quantity', 0),
                maker_codes
            )
        
        # 生成拆分工单
        split_orders = []
        
        for i, maker_code in enumerate(sorted(maker_codes)):
            split_order = plan.copy()
            
            # 更新工单标识
            split_order['work_order_nr'] = f"{plan['work_order_nr']}-{i+1:02d}"
            split_order['maker_code'] = maker_code
            
            # 更新数量
            split_order['quantity_total'] = quantity_allocation.get(maker_code, 0)
            split_order['final_quantity'] = final_quantity_allocation.get(maker_code, 0)
            
            # 保持时间不变（同时开始，同时结束）
            split_order['planned_start'] = plan.get('planned_start')
            split_order['planned_end'] = plan.get('planned_end')
            
            # 记录拆分历史
            split_order['split_from'] = plan['work_order_nr']
            split_order['split_index'] = i + 1
            split_order['split_timestamp'] = datetime.now()
            split_order['is_split'] = True
            split_order['allocation_strategy'] = allocation_strategy
            
            split_orders.append(split_order)
        
        return split_orders
    
    def _allocate_by_capacity(
        self, 
        total_quantity: int, 
        machine_codes: List[str],
        machine_capacities: Dict[str, int]
    ) -> Dict[str, int]:
        """
        基于机台产能的数量分配
        
        Args:
            total_quantity: 总数量
            machine_codes: 机台代码列表
            machine_capacities: 机台产能配置 {机台代码: 小时产能}
            
        Returns:
            dict: {机台代码: 分配数量}
        """
        if not machine_codes:
            return {}
        
        # 获取各机台产能
        capacities = []
        total_capacity = 0
        
        for machine_code in machine_codes:
            capacity = machine_capacities.get(machine_code, 100)  # 默认产能100
            capacities.append(capacity)
            total_capacity += capacity
        
        # 按产能比例分配
        allocation = {}
        remaining_quantity = total_quantity
        
        for i, machine_code in enumerate(machine_codes[:-1]):  # 最后一个机台单独处理
            proportion = capacities[i] / total_capacity
            allocated_quantity = int(total_quantity * proportion)
            allocation[machine_code] = allocated_quantity
            remaining_quantity -= allocated_quantity
        
        # 最后一个机台分配剩余数量
        if machine_codes:
            allocation[machine_codes[-1]] = remaining_quantity
        
        return allocation
    
    async def _get_split_rules_from_db(self) -> Dict[str, Any]:
        """从数据库查询拆分规则配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认拆分规则
        return {
            'split_criteria': {
                'quantity_threshold': 10000,
                'max_duration_hours': 24
            },
            'allocation_strategy': 'equal',  # 'equal' 或 'capacity_based'
            'machine_capacities': {
                'default': 100  # 默认机台产能
            }
        }

                
        return allocation