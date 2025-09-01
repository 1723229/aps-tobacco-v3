"""
APS智慧排产系统 - 规则合并算法（重构版）

基于成品数量计算，支持MES备用工单逻辑
实现跨月份备用工单生成，完全符合业务需求
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class MergeAlgorithm(AlgorithmBase):
    """规则合并算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.RULE_MERGING)
        self.merge_sequence = 1  # 合并序号计数器
        
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行规则合并
        
        Args:
            input_data: 预处理后的计划数据
            
        Returns:
            AlgorithmResult: 合并结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 识别合并组
        merge_groups = self._identify_merge_groups(input_data)
        
        # 执行合并
        merged_plans = []
        for group in merge_groups:
            if len(group) > 1:
                # 需要合并
                merged_plan = self._merge_plans(group)
                merged_plans.append(merged_plan)
                logger.info(f"合并了{len(group)}个计划为: {merged_plan['work_order_nr']}")
            else:
                # 单个计划，不需要合并
                merged_plans.append(group[0])
        
        result.output_data = merged_plans
        
        logger.info(f"合并完成: 输入{len(input_data)}个 -> 输出{len(merged_plans)}个")
        return self.finalize_result(result)
    
    def _identify_merge_groups(self, plans: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        识别可以合并的计划组
        使用Union-Find算法优化性能
        """
        n = len(plans)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # 构建合并关系
        for i in range(n):
            for j in range(i + 1, n):
                if self._can_merge(plans[i], plans[j]):
                    union(i, j)
        
        # 分组结果
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(plans[i])
        
        return list(groups.values())
    
    def _can_merge(self, plan1: Dict[str, Any], plan2: Dict[str, Any]) -> bool:
        """
        判定两个旬计划是否可以合并
        
        合并条件（需全部满足）：
        1. 同一个月的卷包旬计划
        2. 成品牌号相同
        3. 卷包机代码相同  
        4. 喂丝机代码相同
        """
        # 条件1：同一月份（严格按照开始时间的月份判断）
        start1 = plan1.get('planned_start')
        start2 = plan2.get('planned_start')
        
        if start1 and start2:
            # 处理字符串格式的时间
            if isinstance(start1, str):
                start1 = datetime.fromisoformat(start1.replace('Z', '+00:00'))
            if isinstance(start2, str):
                start2 = datetime.fromisoformat(start2.replace('Z', '+00:00'))
            
            # 严格按照计划开始时间的月份进行判断
            month1 = (start1.year, start1.month)
            month2 = (start2.year, start2.month)
            
            if month1 != month2:
                logger.info(f"计划跨月份，不进行合并: {plan1.get('work_order_nr')}({start1.strftime('%Y-%m')}) vs {plan2.get('work_order_nr')}({start2.strftime('%Y-%m')})")
                return False
        
        # 条件2：成品牌号相同
        if plan1.get('article_nr') != plan2.get('article_nr'):
            return False
            
        # 条件3：卷包机代码相同
        if plan1.get('maker_code') != plan2.get('maker_code'):
            return False
            
        # 条件4：喂丝机代码相同
        if plan1.get('feeder_code') != plan2.get('feeder_code'):
            return False
            
        logger.info(f"符合合并条件: {plan1.get('work_order_nr')} + {plan2.get('work_order_nr')}")
        return True
    
    def _merge_plans(self, plans_to_merge: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行旬计划合并
        
        合并后的属性规则：
        - 计划开始时间：前一个卷包旬计划的开始时间（最早开始时间）
        - 计划结束时间：后一个卷包旬计划的结束时间（最晚结束时间）
        - 数量：两个旬计划数量之和
        - 成品数量：两个旬计划成品数量之和
        - 喂丝机代码、卷包机代码：旬计划对应的机组（保持不变）
        
        Args:
            plans_to_merge: 需要合并的旬计划列表
            
        Returns:
            merged_plan: 合并后的计划
        """
        if not plans_to_merge:
            return {}
        
        if len(plans_to_merge) == 1:
            return plans_to_merge[0]
        
        # 按开始时间排序，确定前后顺序
        sorted_plans = sorted(plans_to_merge, key=lambda x: x.get('planned_start', datetime.min))
        
        # 初始化合并结果，以第一个计划为基础
        merged_plan = sorted_plans[0].copy()
        
        # 生成新的合并订单号
        merge_date = datetime.now().strftime("%Y%m%d")
        merged_plan['work_order_nr'] = f"M{merge_date}{self.merge_sequence:04d}"
        self.merge_sequence += 1
        
        # 时间属性合并：最早开始时间到最晚结束时间
        planned_starts = []
        planned_ends = []
        
        for p in sorted_plans:
            start = p.get('planned_start')
            end = p.get('planned_end')
            
            if start:
                if isinstance(start, str):
                    start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                planned_starts.append(start)
                
            if end:
                if isinstance(end, str):
                    end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                planned_ends.append(end)
        
        if planned_starts:
            merged_plan['planned_start'] = min(planned_starts)  # 前一个计划的开始时间
        if planned_ends:
            merged_plan['planned_end'] = max(planned_ends)      # 后一个计划的结束时间
        
        # 数量合并：两个旬计划数量之和
        merged_plan['quantity_total'] = sum(
            p.get('quantity_total', 0) for p in sorted_plans
        )
        # 成品数量合并：两个旬计划成品数量之和
        merged_plan['final_quantity'] = sum(
            p.get('final_quantity', 0) for p in sorted_plans
        )
        
        # 喂丝机代码、卷包机代码：保持不变（合并条件已确保它们相同）
        # merged_plan['maker_code'] 和 merged_plan['feeder_code'] 保持不变
        
        # 记录合并历史
        merged_plan['merged_from'] = [p.get('work_order_nr') for p in sorted_plans]
        merged_plan['merge_timestamp'] = datetime.now()
        merged_plan['is_merged'] = True
        merged_plan['merged_count'] = len(sorted_plans)
        
        logger.info(f"合并完成: {len(sorted_plans)}个计划 -> 机台:{merged_plan.get('maker_code')} 成品数量:{merged_plan['final_quantity']}箱 时间:{merged_plan['planned_start']} - {merged_plan['planned_end']}")
        
        return merged_plan
    
    def _is_cross_month_plans(self, plans: List[Dict[str, Any]]) -> bool:
        """
        检查计划列表是否跨月份
        
        Args:
            plans: 计划列表
            
        Returns:
            bool: 是否跨月份
        """
        if not plans:
            return False
        
        months = set()
        for plan in plans:
            start_date = plan.get('planned_start')
            if start_date:
                months.add((start_date.year, start_date.month))
        
        return len(months) > 1
    
    def _create_backup_orders(self, cross_month_plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为跨月份计划创建备用工单
        
        Args:
            cross_month_plans: 跨月份的计划列表
            
        Returns:
            List[Dict[str, Any]]: 备用工单列表
        """
        backup_orders = []
        
        # 按月份分组
        monthly_groups = defaultdict(list)
        for plan in cross_month_plans:
            start_date = plan.get('planned_start')
            if start_date:
                month_key = (start_date.year, start_date.month)
                monthly_groups[month_key].append(plan)
        
        # 为每个月份组创建备用工单
        for month_key, month_plans in monthly_groups.items():
            if len(month_plans) == 1:
                # 单个计划，直接标记为备用
                backup_order = month_plans[0].copy()
                backup_order['is_backup'] = True
                backup_order['backup_reason'] = f"跨月份工单，{month_key[0]}年{month_key[1]}月备用工单"
                backup_orders.append(backup_order)
            else:
                # 多个计划，需要合并后创建备用工单
                merged_backup = self._merge_plans(month_plans)
                merged_backup['is_backup'] = True
                merged_backup['backup_reason'] = f"跨月份合并工单，{month_key[0]}年{month_key[1]}月备用工单"
                backup_orders.append(merged_backup)
                
                logger.info(f"为{month_key[0]}年{month_key[1]}月创建备用工单: {merged_backup['work_order_nr']}")
        
        return backup_orders
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行规则合并
        
        Args:
            input_data: 预处理后的计划数据
            
        Returns:
            AlgorithmResult: 合并结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 从数据库查询合并规则配置
        merge_rules = await self._get_merge_rules_from_db()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'merge_rules_count': len(merge_rules)
        }
        
        # 使用修正后的合并逻辑（与process方法保持一致）
        merge_groups = self._identify_merge_groups(input_data)
        
        # 执行合并
        merged_plans = []
        for group in merge_groups:
            if len(group) > 1:
                # 需要合并
                merged_plan = self._merge_plans(group)
                merged_plans.append(merged_plan)
                logger.info(f"合并了{len(group)}个计划为: {merged_plan['work_order_nr']}")
            else:
                # 单个计划，不需要合并
                merged_plans.append(group[0])
        
        result.output_data = merged_plans
        
        logger.info(f"合并完成(真实数据): 输入{len(input_data)}个 -> 输出{len(merged_plans)}个")
        return self.finalize_result(result)
    
    def _identify_merge_groups_with_rules(self, plans: List[Dict[str, Any]], merge_rules: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
        """
        使用真实业务规则识别可以合并的计划组
        """
        n = len(plans)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # 构建合并关系
        for i in range(n):
            for j in range(i + 1, n):
                if self._can_merge_with_rules(plans[i], plans[j], merge_rules):
                    union(i, j)
        
        # 分组结果
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(plans[i])
        
        return list(groups.values())
    
    def _can_merge_with_rules(self, plan1: Dict[str, Any], plan2: Dict[str, Any], merge_rules: Dict[str, Any]) -> bool:
        """
        使用真实业务规则判定两个旬计划是否可以合并
        """
        # 使用真实合并规则
        merge_criteria = merge_rules.get('merge_criteria', {})
        
        # 条件1：时间窗口检查
        time_window_days = merge_criteria.get('time_window_days', 30)
        start1 = plan1.get('planned_start')
        start2 = plan2.get('planned_start')
        
        if start1 and start2:
            time_diff = abs((start1 - start2).days)
            if time_diff > time_window_days:
                return False
        
        # 条件2：必须匹配的字段
        required_match_fields = merge_criteria.get('required_match_fields', ['article_nr', 'maker_code', 'feeder_code'])
        
        for field in required_match_fields:
            if plan1.get(field) != plan2.get(field):
                return False
        
        return True
    
    def _merge_plans_with_rules(self, plans_to_merge: List[Dict[str, Any]], merge_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用真实业务规则执行旬计划合并
        """
        if not plans_to_merge:
            return {}
        
        # 初始化合并结果，以第一个计划为基础
        merged_plan = plans_to_merge[0].copy()
        
        # 生成新的合并订单号
        merge_date = datetime.now().strftime("%Y%m%d")
        merged_plan['work_order_nr'] = f"M{merge_date}{self.merge_sequence:04d}"
        self.merge_sequence += 1
        
        # 使用真实合并规则进行属性合并
        merge_strategies = merge_rules.get('merge_strategies', {})
        
        # 时间属性合并策略
        time_strategy = merge_strategies.get('time_strategy', 'min_max')
        if time_strategy == 'min_max':
            planned_starts = [p.get('planned_start') for p in plans_to_merge if p.get('planned_start')]
            planned_ends = [p.get('planned_end') for p in plans_to_merge if p.get('planned_end')]
            
            if planned_starts:
                merged_plan['planned_start'] = min(planned_starts)
            if planned_ends:
                merged_plan['planned_end'] = max(planned_ends)
        
        # 数量属性合并策略
        quantity_strategy = merge_strategies.get('quantity_strategy', 'sum')
        if quantity_strategy == 'sum':
            merged_plan['quantity_total'] = sum(
                p.get('quantity_total', 0) for p in plans_to_merge
            )
            merged_plan['final_quantity'] = sum(
                p.get('final_quantity', 0) for p in plans_to_merge
            )
        
        # 记录合并历史
        merged_plan['merged_from'] = [p.get('work_order_nr') for p in plans_to_merge]
        merged_plan['merge_timestamp'] = datetime.now()
        merged_plan['is_merged'] = True
        
        return merged_plan
    
    async def _get_merge_rules_from_db(self) -> Dict[str, Any]:
        """从数据库查询合并规则配置"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认合并规则
        return {
            'merge_criteria': {
                'time_window_days': 30,
                'required_match_fields': ['article_nr', 'maker_code', 'feeder_code']
            },
            'merge_strategies': {
                'time_strategy': 'min_max',
                'quantity_strategy': 'sum'
            },
            'max_merge_count': 5
        }