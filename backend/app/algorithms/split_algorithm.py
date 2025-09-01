"""
APS智慧排产系统 - 规则拆分算法

将合并后的旬计划拆分为MES系统需要的工单格式：
- 每个卷包机组对应一个卷包工单
- 喂丝机工单对应旬计划内的所有喂丝机
- 处理喂丝机资源冲突和时间调度
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class SplitAlgorithm(AlgorithmBase):
    """
    规则拆分算法 - 将旬计划拆分为MES工单
    
    核心功能：
    1. 每个卷包机组对应一个卷包工单
    2. 喂丝机工单对应旬计划内的所有喂丝机
    3. 处理喂丝机资源冲突
    4. 数量平均分配和时间调度
    """
    
    def __init__(self):
        super().__init__(ProcessingStage.RULE_SPLITTING)
        self.feeder_schedules = defaultdict(list)  # 喂丝机时间安排表
        self.work_order_sequence = 1  # 工单序号计数器
        
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行规则拆分 - 将旬计划拆分为MES工单
        
        核心逻辑：
        1. 按喂丝机分组旬计划
        2. 生成卷包机工单（每个卷包机一个工单）
        3. 生成喂丝机工单（每个喂丝机一个工单）
        4. 处理喂丝机资源冲突
        
        Args:
            input_data: 合并后的旬计划数据
            
        Returns:
            AlgorithmResult: 拆分后的MES工单列表
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 清空调度表和序号计数器
        self.feeder_schedules.clear()
        self.work_order_sequence = 1
        
        # 第一步：按喂丝机分组旬计划，识别需要拆分的计划组
        feeder_groups = self._group_plans_by_feeder(input_data)
        
        # 第二步：为每个喂丝机组生成MES工单
        mes_work_orders = []
        feeder_work_orders = []
        
        for feeder_code, plans in feeder_groups.items():
            # 处理喂丝机资源冲突
            conflict_resolved_plans = self._resolve_feeder_conflicts_for_group(plans)
            
            # 生成卷包机工单（每个卷包机一个工单）
            packing_orders = self._generate_packing_work_orders(conflict_resolved_plans)
            mes_work_orders.extend(packing_orders)
            
            # 生成喂丝机工单（每个喂丝机一个工单）
            feeder_order = self._generate_feeder_work_order(conflict_resolved_plans, feeder_code)
            if feeder_order:
                feeder_work_orders.append(feeder_order)
        
        # 合并所有工单
        all_work_orders = mes_work_orders + feeder_work_orders
        result.output_data = all_work_orders
        
        logger.info(f"拆分完成: 输入{len(input_data)}个旬计划 -> 输出{len(mes_work_orders)}个卷包工单 + {len(feeder_work_orders)}个喂丝工单")
        return self.finalize_result(result)
    
    def _group_plans_by_feeder(self, plans: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按喂丝机代码分组旬计划
        
        Args:
            plans: 旬计划列表
            
        Returns:
            Dict[str, List]: 按喂丝机代码分组的计划
        """
        feeder_groups = defaultdict(list)
        
        for plan in plans:
            feeder_code = plan.get('feeder_code', '')
            if feeder_code:
                feeder_groups[feeder_code].append(plan)
            else:
                logger.warning(f"旬计划缺少喂丝机代码: {plan.get('work_order_nr')}")
        
        logger.info(f"按喂丝机分组: {len(feeder_groups)}个喂丝机组，总计划数{len(plans)}")
        return dict(feeder_groups)
    
    def _resolve_feeder_conflicts_for_group(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为单个喂丝机组解决资源冲突
        
        Args:
            plans: 同一喂丝机的旬计划列表
            
        Returns:
            List[Dict]: 解决冲突后的计划列表
        """
        if not plans:
            return []
        
        # 按开始时间排序
        sorted_plans = sorted(plans, key=lambda x: x.get('planned_start', datetime.min))
        
        resolved_plans = []
        feeder_code = plans[0].get('feeder_code', '')
        
        for plan in sorted_plans:
            planned_start = plan.get('planned_start')
            planned_end = plan.get('planned_end')
            
            if not planned_start or not planned_end:
                resolved_plans.append(plan)
                continue
            
            # 检查与已安排的任务是否有冲突
            for existing_schedule in self.feeder_schedules[feeder_code]:
                if self._has_time_overlap(
                    (planned_start, planned_end),
                    (existing_schedule['start'], existing_schedule['end'])
                ):
                    # 调整开始时间到已有任务结束之后
                    new_start = existing_schedule['end']
                    duration = planned_end - planned_start
                    new_end = new_start + duration
                    
                    logger.info(f"调整喂丝机{feeder_code}冲突: {plan['work_order_nr']} {planned_start} -> {new_start}")
                    
                    plan = plan.copy()
                    plan['planned_start'] = new_start
                    plan['planned_end'] = new_end
                    plan['schedule_adjusted'] = True
                    
                    planned_start = new_start
                    planned_end = new_end
                    break
            
            # 记录时间安排
            self.feeder_schedules[feeder_code].append({
                'start': planned_start,
                'end': planned_end,
                'work_order_nr': plan.get('work_order_nr', ''),
                'maker_code': plan.get('maker_code', '')
            })
            
            resolved_plans.append(plan)
        
        return resolved_plans
    
    def _generate_packing_work_orders(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成卷包机工单 - 每个卷包机组对应一个卷包工单
        
        Args:
            plans: 旬计划列表
            
        Returns:
            List[Dict]: 卷包机工单列表
        """
        packing_orders = []
        
        for plan in plans:
            # 每个旬计划生成一个卷包机工单
            packing_order = plan.copy()
            
            # 更新工单类型和编号 - 添加更多唯一性标识符
            packing_order['work_order_type'] = 'PACKING'  # 卷包工单
            timestamp_suffix = datetime.now().strftime('%H%M%S')  # 小时分钟秒
            packing_order['work_order_nr'] = f"PK{datetime.now().strftime('%Y%m%d')}{timestamp_suffix}{self.work_order_sequence:04d}"
            self.work_order_sequence += 1
            
            # 卷包机工单保持原有的开始结束时间和数量
            # planned_start, planned_end, final_quantity, quantity_total 保持不变
            
            # 记录原始计划信息
            packing_order['source_plan'] = plan.get('work_order_nr')
            packing_order['generated_timestamp'] = datetime.now()
            
            packing_orders.append(packing_order)
            
            logger.info(f"生成卷包工单: {packing_order['work_order_nr']} 机台:{packing_order.get('maker_code')} 数量:{packing_order.get('final_quantity')}箱")
        
        return packing_orders
    
    def _generate_feeder_work_order(self, plans: List[Dict[str, Any]], feeder_code: str) -> Optional[Dict[str, Any]]:
        """
        生成喂丝机工单 - 每个喂丝机一个工单，包含该喂丝机的所有计划
        
        Args:
            plans: 同一喂丝机的旬计划列表
            feeder_code: 喂丝机代码
            
        Returns:
            Dict: 喂丝机工单
        """
        if not plans:
            return None
        
        # 计算总量和时间范围
        total_quantity = sum(p.get('quantity_total', 0) for p in plans)
        total_final_quantity = sum(p.get('final_quantity', 0) for p in plans)
        
        # 取最早开始时间和最晚结束时间
        all_starts = [p.get('planned_start') for p in plans if p.get('planned_start')]
        all_ends = [p.get('planned_end') for p in plans if p.get('planned_end')]
        
        # 创建喂丝机工单
        timestamp_suffix = datetime.now().strftime('%H%M%S')  # 小时分钟秒
        feeder_order = {
            'work_order_type': 'FEEDING',  # 喂丝工单
            'work_order_nr': f"FD{datetime.now().strftime('%Y%m%d')}{timestamp_suffix}{self.work_order_sequence:04d}",
            'feeder_code': feeder_code,
            'article_nr': plans[0].get('article_nr'),  # 假设同一喂丝机的产品相同
            'quantity_total': total_quantity,
            'final_quantity': total_final_quantity,
            'planned_start': min(all_starts) if all_starts else None,
            'planned_end': max(all_ends) if all_ends else None,
            'source_plans': [p.get('work_order_nr') for p in plans],
            'generated_timestamp': datetime.now()
        }
        
        self.work_order_sequence += 1
        
        logger.info(f"生成喂丝工单: {feeder_order['work_order_nr']} 喂丝机:{feeder_code} 总量:{total_quantity}箱")
        
        return feeder_order
    
    def _resolve_feeder_conflicts(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解决喂丝机资源冲突（重构版）
        
        核心逻辑：
        1. 按工单号分组相同工单的不同机台
        2. 检测喂丝机时间冲突
        3. 调整后续工单的开始时间以避免冲突
        
        Args:
            orders: 工单列表
            
        Returns:
            List[Dict[str, Any]]: 解决冲突后的工单列表
        """
        if not orders:
            return []
        
        # 按工单号分组
        work_order_groups = defaultdict(list)
        for order in orders:
            work_order_nr = order.get('work_order_nr', '')
            work_order_groups[work_order_nr].append(order)
        
        resolved_orders = []
        
        # 按工单号排序处理（确保W0001在W0002之前）
        for work_order_nr in sorted(work_order_groups.keys()):
            group_orders = work_order_groups[work_order_nr]
            
            # 检查这个工单组的喂丝机冲突
            resolved_group = self._resolve_group_feeder_conflicts(group_orders)
            resolved_orders.extend(resolved_group)
        
        return resolved_orders
    
    def _resolve_group_feeder_conflicts(self, group_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解决单个工单组内的喂丝机冲突
        
        Args:
            group_orders: 同一工单的不同机台订单
            
        Returns:
            List[Dict[str, Any]]: 解决冲突后的订单列表
        """
        if not group_orders:
            return []
        
        resolved_orders = []
        
        for order in group_orders:
            feeder_code = order.get('feeder_code', '')
            planned_start = order.get('planned_start')
            planned_end = order.get('planned_end')
            
            if not feeder_code or not planned_start or not planned_end:
                resolved_orders.append(order)
                continue
            
            # 检查喂丝机是否有时间冲突
            conflict_detected = False
            for existing_schedule in self.feeder_schedules[feeder_code]:
                if self._has_time_overlap(
                    (planned_start, planned_end),
                    (existing_schedule['start'], existing_schedule['end'])
                ):
                    conflict_detected = True
                    # 调整开始时间到最后一个任务结束之后
                    new_start = max(
                        existing_schedule['end'],
                        planned_start
                    )
                    duration = planned_end - planned_start
                    new_end = new_start + duration
                    
                    logger.info(f"检测到喂丝机{feeder_code}冲突，调整工单{order['work_order_nr']}时间: {planned_start} -> {new_start}")
                    
                    order = order.copy()
                    order['planned_start'] = new_start
                    order['planned_end'] = new_end
                    order['schedule_adjusted'] = True
                    order['original_start'] = planned_start
                    order['original_end'] = planned_end
                    
                    planned_start = new_start
                    planned_end = new_end
                    break
            
            # 记录喂丝机时间安排
            self.feeder_schedules[feeder_code].append({
                'start': planned_start,
                'end': planned_end,
                'work_order_nr': order.get('work_order_nr', ''),
                'maker_code': order.get('maker_code', '')
            })
            
            resolved_orders.append(order)
        
        return resolved_orders
    
    def _has_time_overlap(self, time_range1: Tuple[datetime, datetime], time_range2: Tuple[datetime, datetime]) -> bool:
        """
        检查两个时间段是否有重叠
        
        Args:
            time_range1: 时间段1 (开始, 结束)
            time_range2: 时间段2 (开始, 结束)
            
        Returns:
            bool: 是否有重叠
        """
        start1, end1 = time_range1
        start2, end2 = time_range2
        
        # 检查重叠：如果没有重叠，则一个时间段在另一个之前或之后
        return not (end1 <= start2 or end2 <= start1)
    
    def _need_split(self, order: Dict[str, Any]) -> bool:
        """
        判定是否需要拆分工单（重构版）
        
        拆分条件：
        1. 成品数量超过单台机台处理能力
        2. 时间跨度超过单个班次时长
        3. 存在多个可用的卷包机
        
        Args:
            order: 工单数据
            
        Returns:
            bool: 是否需要拆分
        """
        # 条件1：成品数量检查（基于final_quantity）
        final_quantity = order.get('final_quantity', 0)
        if final_quantity > 5000:  # 超过5000箱考虑拆分
            logger.info(f"工单{order.get('work_order_nr')}成品数量{final_quantity}箱，超过阈值，需要拆分")
            return True
            
        # 条件2：时间跨度检查
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        if planned_start and planned_end:
            duration_hours = (planned_end - planned_start).total_seconds() / 3600
            if duration_hours > 8:  # 超过8小时考虑拆分
                logger.info(f"工单{order.get('work_order_nr')}时长{duration_hours:.1f}小时，超过阈值，需要拆分")
                return True
        
        # 条件3：默认不需要拆分（除非有特殊业务需求）
        return False
    
    def _split_work_order(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        执行工单拆分（重构版） - 基于成品数量
        
        Args:
            order: 需要拆分的工单
            
        Returns:
            List[Dict]: 拆分后的工单列表
        """
        # 简单的二分拆分策略（可以根据业务需求扩展为多分）
        split_count = 2
        
        final_quantity = order.get('final_quantity', 0)
        quantity_total = order.get('quantity_total', 0)
        
        # 基于成品数量进行分配
        final_quantity_per_split = final_quantity // split_count
        final_quantity_remainder = final_quantity % split_count
        
        total_quantity_per_split = quantity_total // split_count
        total_quantity_remainder = quantity_total % split_count
        
        split_orders = []
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        
        # 计算每个子工单的时长
        if planned_start and planned_end:
            total_duration = planned_end - planned_start
            duration_per_split = total_duration / split_count
        else:
            duration_per_split = timedelta(hours=4)  # 默认4小时
        
        for i in range(split_count):
            split_order = order.copy()
            
            # 更新工单标识
            split_order['work_order_nr'] = f"{order['work_order_nr']}-S{i+1:02d}"
            
            # 分配成品数量
            split_final_quantity = final_quantity_per_split
            split_total_quantity = total_quantity_per_split
            
            # 余数分配给第一个子工单
            if i == 0:
                split_final_quantity += final_quantity_remainder
                split_total_quantity += total_quantity_remainder
            
            split_order['final_quantity'] = split_final_quantity
            split_order['quantity_total'] = split_total_quantity
            
            # 调整时间
            if planned_start:
                split_start = planned_start + duration_per_split * i
                split_end = split_start + duration_per_split
                
                split_order['planned_start'] = split_start
                split_order['planned_end'] = split_end
            
            # 记录拆分历史
            split_order['split_from'] = order['work_order_nr']
            split_order['split_index'] = i + 1
            split_order['split_count'] = split_count
            split_order['split_timestamp'] = datetime.now()
            split_order['is_split'] = True
            split_order['split_strategy'] = 'quantity_based'
            
            split_orders.append(split_order)
            
            logger.info(f"生成子工单{split_order['work_order_nr']}：成品数量{split_final_quantity}箱")
        
        return split_orders

    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行规则拆分（重构版）
        
        Args:
            input_data: 合并后的计划数据
            
        Returns:
            AlgorithmResult: 拆分结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 从数据库查询拆分规则和机台关系
        split_rules = await self._get_split_rules_from_db()
        machine_relations = await DatabaseQueryService.get_machine_relations()
        machine_speeds = await DatabaseQueryService.get_machine_speeds()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'split_rules_count': len(split_rules),
            'machine_relations_count': len(machine_relations),
            'machine_speeds_count': len(machine_speeds)
        }
        
        # 清空调度表和序号计数器
        self.feeder_schedules.clear()
        self.work_order_sequence = 1
        
        # 使用修正后的拆分逻辑（与process方法保持一致）
        # 第一步：按喂丝机分组旬计划，识别需要拆分的计划组
        feeder_groups = self._group_plans_by_feeder(input_data)
        
        # 第二步：为每个喂丝机组生成MES工单
        mes_work_orders = []
        feeder_work_orders = []
        
        for feeder_code, plans in feeder_groups.items():
            # 处理喂丝机资源冲突
            conflict_resolved_plans = self._resolve_feeder_conflicts_for_group(plans)
            
            # 生成卷包机工单（每个卷包机一个工单）
            packing_orders = self._generate_packing_work_orders(conflict_resolved_plans)
            mes_work_orders.extend(packing_orders)
            
            # 生成喂丝机工单（每个喂丝机一个工单）
            feeder_order = self._generate_feeder_work_order(conflict_resolved_plans, feeder_code)
            if feeder_order:
                feeder_work_orders.append(feeder_order)
        
        # 合并所有工单
        split_orders = mes_work_orders + feeder_work_orders
        
        result.output_data = split_orders
        
        logger.info(f"拆分完成(真实数据): 输入{len(input_data)}个 -> 输出{len(split_orders)}个")
        return self.finalize_result(result)
    
    def _need_split_with_db_rules(self, order: Dict[str, Any], split_rules: Dict[str, Any]) -> bool:
        """
        使用数据库规则判定是否需要拆分工单
        """
        split_criteria = split_rules.get('split_criteria', {})
        
        # 成品数量阈值检查
        final_quantity_threshold = split_criteria.get('final_quantity_threshold', 5000)
        if order.get('final_quantity', 0) > final_quantity_threshold:
            return True
        
        # 时间跨度检查
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        if planned_start and planned_end:
            duration_hours = (planned_end - planned_start).total_seconds() / 3600
            max_duration_hours = split_criteria.get('max_duration_hours', 8)
            if duration_hours > max_duration_hours:
                return True
        
        return False
    
    def _split_work_order_with_db_rules(self, order: Dict[str, Any], split_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用数据库规则执行工单拆分
        """
        allocation_strategy = split_rules.get('allocation_strategy', 'equal_split')
        split_count = split_rules.get('default_split_count', 2)
        
        if allocation_strategy == 'equal_split':
            return self._split_work_order(order)  # 使用重构后的拆分方法
        else:
            # 其他拆分策略可以在这里实现
            return [order]  # 暂时不拆分
    
    async def _get_split_rules_from_db(self) -> Dict[str, Any]:
        """从数据库查询拆分规则配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认拆分规则
        return {
            'split_criteria': {
                'final_quantity_threshold': 5000,  # 成品数量阈值（箱）
                'max_duration_hours': 8  # 最大时长阈值（小时）
            },
            'allocation_strategy': 'equal_split',  # 平均拆分策略
            'default_split_count': 2  # 默认拆分数量
        }
    
    def _resolve_feeder_conflicts_with_relations(
        self, 
        orders: List[Dict[str, Any]], 
        machine_relations: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        基于机台关系配置解决喂丝机资源冲突
        
        Args:
            orders: 工单列表
            machine_relations: 机台关系映射 {喂丝机代码: [卷包机代码列表]}
            
        Returns:
            List[Dict[str, Any]]: 解决冲突后的工单列表
        """
        if not orders:
            return []
        
        # 验证喂丝机-卷包机关系的合法性
        validated_orders = []
        for order in orders:
            feeder_code = order.get('feeder_code', '')
            maker_code = order.get('maker_code', '')
            
            if feeder_code in machine_relations:
                # 检查卷包机是否在允许的关系列表中
                allowed_makers = machine_relations[feeder_code]
                if maker_code not in allowed_makers:
                    logger.warning(f"机台关系配置不匹配: 喂丝机{feeder_code}不支持卷包机{maker_code}，尝试重新分配")
                    # 尝试找到优先级最高的替代卷包机
                    if allowed_makers:
                        suggested_maker = allowed_makers[0]  # 取优先级最高的
                        order = order.copy()
                        order['original_maker_code'] = maker_code
                        order['maker_code'] = suggested_maker
                        order['machine_relation_adjusted'] = True
                        order['adjustment_reason'] = f"根据机台关系配置调整：{feeder_code} -> {suggested_maker}"
                        logger.info(f"机台关系调整: {maker_code} -> {suggested_maker}")
            
            validated_orders.append(order)
        
        # 使用原有的时间冲突解决逻辑
        return self._resolve_feeder_conflicts(validated_orders)
    
    def _validate_machine_relations(
        self, 
        orders: List[Dict[str, Any]], 
        machine_relations: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        验证并修正机台关系配置
        
        Args:
            orders: 工单列表
            machine_relations: 机台关系映射
            
        Returns:
            List[Dict[str, Any]]: 验证后的工单列表
        """
        validated_orders = []
        
        for order in orders:
            feeder_code = order.get('feeder_code', '')
            maker_code = order.get('maker_code', '')
            
            # 检查机台关系是否合法
            if feeder_code and maker_code:
                if feeder_code not in machine_relations:
                    logger.warning(f"喂丝机{feeder_code}未在机台关系配置中找到")
                    order = order.copy()
                    order['machine_relation_warning'] = f"喂丝机{feeder_code}未配置关系"
                elif maker_code not in machine_relations[feeder_code]:
                    logger.warning(f"机台关系配置冲突: 喂丝机{feeder_code}不支持卷包机{maker_code}")
                    order = order.copy()
                    order['machine_relation_conflict'] = True
                    order['allowed_makers'] = machine_relations[feeder_code]
            
            validated_orders.append(order)
            
        return validated_orders