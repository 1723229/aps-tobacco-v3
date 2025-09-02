"""
APS智慧排产系统 - 规则拆分算法 (修复版)

将合并后的旬计划拆分为MES系统需要的工单格式：
- 每个卷包机组对应一个卷包工单
- 喂丝机工单对应旬计划内的所有喂丝机
- 处理喂丝机资源冲突和时间调度
- 建立卷包机工单与喂丝机工单的关联关系
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class SplitAlgorithmFixed(AlgorithmBase):
    """
    拆分算法 - 严格按照算法细则执行
    
    将合并后的旬计划拆分为MES系统所需的工单格式：
    1. 按喂丝机分组旬计划
    2. 为每个喂丝机组生成喂丝机工单
    3. 为每个卷包机生成卷包机工单，并关联到对应的喂丝机工单
    4. 处理喂丝机资源冲突
    """
    
    def __init__(self):
        super().__init__(ProcessingStage.RULE_SPLITTING)
        # 喂丝机时间调度表 - 记录每个喂丝机的时间占用情况  
        self.feeder_schedules: Dict[str, List[Dict]] = defaultdict(list)
        # 工单序号计数器
        self.work_order_sequence = 1
    
    async def process(self, input_data: List[Dict[str, Any]]) -> AlgorithmResult:
        """
        执行拆分算法处理
        
        Args:
            input_data: 合并后的旬计划列表
            
        Returns:
            AlgorithmResult: 拆分后的MES工单列表
        """
        logger.info(f"开始执行拆分算法，输入 {len(input_data)} 个旬计划")
        
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
        
        # 第二步：为每个喂丝机组生成MES工单（先喂丝，后卷包，建立关联）
        mes_work_orders = []
        feeder_work_orders = []
        
        for feeder_code, plans in feeder_groups.items():
            # 处理喂丝机资源冲突
            conflict_resolved_plans = self._resolve_feeder_conflicts_for_group(plans)
            
            # 先生成喂丝机工单（每个喂丝机一个工单）
            feeder_order = self._generate_feeder_work_order(conflict_resolved_plans, feeder_code)
            if feeder_order:
                feeder_work_orders.append(feeder_order)
                
                # 获取喂丝机工单的plan_id用于关联
                feeder_plan_id = feeder_order.get('work_order_nr')  # 使用work_order_nr作为plan_id
                
                # 生成卷包机工单并关联到喂丝机工单
                packing_orders = self._generate_packing_work_orders(conflict_resolved_plans, feeder_plan_id)
                mes_work_orders.extend(packing_orders)
            else:
                # 如果没有喂丝机工单，卷包机工单不关联
                packing_orders = self._generate_packing_work_orders(conflict_resolved_plans, None)
                mes_work_orders.extend(packing_orders)
        
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
        
        logger.info(f"🔧 处理喂丝机{feeder_code}的资源冲突，共{len(sorted_plans)}个计划")
        
        for i, plan in enumerate(sorted_plans):
            planned_start = plan.get('planned_start')
            planned_end = plan.get('planned_end')
            
            if not planned_start or not planned_end:
                resolved_plans.append(plan)
                continue
            
            # 字符串时间转换
            if isinstance(planned_start, str):
                planned_start = datetime.fromisoformat(planned_start.replace('Z', '+00:00'))
                plan['planned_start'] = planned_start
            if isinstance(planned_end, str):
                planned_end = datetime.fromisoformat(planned_end.replace('Z', '+00:00'))
                plan['planned_end'] = planned_end
            
            # 按照算法细则：检查喂丝机资源冲突，后续工单必须等待前一个工单完成
            need_adjustment = False
            new_start_time = planned_start
            
            # 检查与已安排的工单是否有时间冲突
            for existing_schedule in self.feeder_schedules[feeder_code]:
                existing_end = existing_schedule['end']
                
                # 如果新工单开始时间早于已有工单结束时间，需要调整
                if new_start_time < existing_end:
                    # 调整到已有工单结束后开始
                    new_start_time = existing_end
                    need_adjustment = True
            
            if need_adjustment:
                # 计算新的结束时间（保持原有工作时长）
                work_duration = planned_end - planned_start
                new_end_time = new_start_time + work_duration
                
                plan['planned_start'] = new_start_time
                plan['planned_end'] = new_end_time
                
                # 标记为已调整
                plan['schedule_adjusted'] = True
                plan['adjustment_reason'] = f"喂丝机{feeder_code}资源冲突调整"
                
                wait_hours = (new_start_time - planned_start).total_seconds() / 3600
                logger.info(f"   ⚠️  冲突调整: {plan.get('work_order_nr')} -> {new_start_time.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"      ⏰ 等待时间: {wait_hours:.1f}小时")
                
                planned_start = plan['planned_start']
                planned_end = plan['planned_end']
            else:
                logger.info(f"   ✅ 无冲突: {plan.get('work_order_nr')} ({planned_start.strftime('%Y-%m-%d %H:%M')})")
            
            # 记录时间安排
            self.feeder_schedules[feeder_code].append({
                'start': planned_start,
                'end': planned_end,
                'work_order_nr': plan.get('work_order_nr', ''),
                'maker_code': plan.get('maker_code', ''),
                'article_nr': plan.get('article_nr', '')
            })
            
            resolved_plans.append(plan)
        
        logger.info(f"✅ 喂丝机{feeder_code}资源冲突解决完成")
        
        return resolved_plans
    
    def _generate_packing_work_orders(self, plans: List[Dict[str, Any]], feeder_plan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        生成卷包机工单 - 严格按照算法细则执行
        
        算法细则要求：
        - 每个卷包机组对应一个卷包工单  
        - 卷包计划的开始结束时间，取旬计划的开始结束时间
        - 数量平均分配
        - 关联到对应的喂丝机工单
        
        Args:
            plans: 旬计划列表
            feeder_plan_id: 关联的喂丝机工单plan_id
            
        Returns:
            List[Dict]: 卷包机工单列表
        """
        packing_orders = []
        
        for plan in plans:
            # 获取卷包机代码列表（可能有多个卷包机）
            maker_codes = self._extract_maker_codes(plan)
            
            if not maker_codes:
                logger.warning(f"旬计划{plan.get('work_order_nr')}缺少卷包机代码")
                continue
            
            # 数量平均分配到每个卷包机
            total_quantity = plan.get('quantity_total', 0)
            total_final_quantity = plan.get('final_quantity', 0)
            
            quantity_per_maker = total_quantity // len(maker_codes) if maker_codes else 0
            final_quantity_per_maker = total_final_quantity // len(maker_codes) if maker_codes else 0
            
            # 处理除不尽的情况，余数分配给第一台机器
            quantity_remainder = total_quantity % len(maker_codes) if maker_codes else 0
            final_quantity_remainder = total_final_quantity % len(maker_codes) if maker_codes else 0
            
            # 为每个卷包机生成一个工单
            for i, maker_code in enumerate(maker_codes):
                packing_order = plan.copy()
                
                # 更新工单类型和编号
                packing_order['work_order_type'] = 'PACKING'  # 卷包工单
                timestamp_suffix = datetime.now().strftime('%H%M%S')
                packing_order['work_order_nr'] = f"PK{datetime.now().strftime('%Y%m%d')}{timestamp_suffix}{self.work_order_sequence:04d}"
                self.work_order_sequence += 1
                
                # 设置单独的卷包机代码
                packing_order['maker_code'] = maker_code
                
                # 数量平均分配（第一台机器承担余数）
                if i == 0:
                    packing_order['quantity_total'] = quantity_per_maker + quantity_remainder
                    packing_order['final_quantity'] = final_quantity_per_maker + final_quantity_remainder
                else:
                    packing_order['quantity_total'] = quantity_per_maker
                    packing_order['final_quantity'] = final_quantity_per_maker
                
                # 时间直接继承旬计划的时间（算法细则要求）
                # planned_start, planned_end 保持不变
                
                # 记录原始计划信息
                packing_order['source_plan'] = plan.get('work_order_nr')
                packing_order['generated_timestamp'] = datetime.now()
                packing_order['split_sequence'] = i + 1
                packing_order['total_makers'] = len(maker_codes)
                
                # ✅ 关联到喂丝机工单 - 这是关键的修复
                packing_order['input_plan_id'] = feeder_plan_id
                
                packing_orders.append(packing_order)
                
                logger.info(f"✅ 生成卷包工单: {packing_order['work_order_nr']}")
                logger.info(f"   🏭 卷包机: {maker_code} (第{i+1}台，共{len(maker_codes)}台)")
                logger.info(f"   📊 分配数量: {packing_order['quantity_total']}箱 -> {packing_order['final_quantity']}箱")
                logger.info(f"   📅 时间: {packing_order.get('planned_start')} - {packing_order.get('planned_end')}")
                if feeder_plan_id:
                    logger.info(f"   🔗 关联喂丝工单: {feeder_plan_id}")
        
        return packing_orders
    
    def _extract_maker_codes(self, plan: Dict[str, Any]) -> List[str]:
        """
        从旬计划中提取卷包机代码列表
        
        支持多种格式：
        - 单个卷包机：'C7' 
        - 多个卷包机：'C7,C8' 或 'C7;C8'
        - 数组格式：['C7', 'C8']
        
        Args:
            plan: 旬计划
            
        Returns:
            List[str]: 卷包机代码列表
        """
        maker_code = plan.get('maker_code', '')
        
        if not maker_code:
            return []
        
        # 如果已经是列表，直接返回
        if isinstance(maker_code, list):
            return [code.strip() for code in maker_code if code.strip()]
        
        # 字符串格式，支持逗号或分号分隔
        if isinstance(maker_code, str):
            # 支持逗号或分号分隔的多个机台
            if ',' in maker_code:
                return [code.strip() for code in maker_code.split(',') if code.strip()]
            elif ';' in maker_code:
                return [code.strip() for code in maker_code.split(';') if code.strip()]
            else:
                # 单个机台
                return [maker_code.strip()]
        
        return []
    
    def _generate_feeder_work_order(self, plans: List[Dict[str, Any]], feeder_code: str) -> Optional[Dict[str, Any]]:
        """
        生成喂丝机工单 - 严格按照算法细则执行
        
        算法细则要求：
        - 喂丝机工单对应旬计划内的所有喂丝机
        - 基于烟丝消耗计算数量  
        - 考虑喂丝机资源冲突
        
        Args:
            plans: 同一喂丝机的旬计划列表
            feeder_code: 喂丝机代码
            
        Returns:
            Dict: 喂丝机工单
        """
        if not plans:
            return None
        
        # 按照算法细则：喂丝机工单基于烟丝消耗计算
        # 喂丝机工单的剩余数量 = 计划数量 - 已创建批次数量
        total_quantity = sum(p.get('quantity_total', 0) for p in plans)
        total_final_quantity = sum(p.get('final_quantity', 0) for p in plans)
        
        # 取最早开始时间和最晚结束时间
        all_starts = [p.get('planned_start') for p in plans if p.get('planned_start')]
        all_ends = [p.get('planned_end') for p in plans if p.get('planned_end')]
        
        # 检查产品一致性（同一喂丝机应该生产相同或兼容的产品）
        articles = list(set(p.get('article_nr', '') for p in plans if p.get('article_nr')))
        if len(articles) > 1:
            logger.warning(f"喂丝机{feeder_code}需要生产多种产品: {articles}")
        
        # 创建喂丝机工单
        timestamp_suffix = datetime.now().strftime('%H%M%S')
        feeder_order = {
            'work_order_type': 'FEEDING',  # 喂丝工单
            'work_order_nr': f"FD{datetime.now().strftime('%Y%m%d')}{timestamp_suffix}{self.work_order_sequence:04d}",
            'feeder_code': feeder_code,
            'article_nr': articles[0] if articles else '',  # 主要产品
            'quantity_total': total_quantity,
            'final_quantity': total_final_quantity,
            'planned_start': min(all_starts) if all_starts else None,
            'planned_end': max(all_ends) if all_ends else None,
            'source_plans': [p.get('work_order_nr') for p in plans],
            'generated_timestamp': datetime.now(),
            
            # 喂丝机特有属性
            'tobacco_consumption_rate': self._calculate_tobacco_consumption_rate(plans),
            'associated_makers': self._get_associated_makers(plans),
            'plan_count': len(plans),
            'remaining_quantity': total_quantity,  # 初始剩余量等于总量
            'created_batches': 0  # 已创建批次数
        }
        
        # 如果有多种产品，记录产品清单
        if len(articles) > 1:
            feeder_order['product_list'] = articles
        
        self.work_order_sequence += 1
        
        logger.info(f"✅ 生成喂丝工单: {feeder_order['work_order_nr']}")
        logger.info(f"   🏭 喂丝机: {feeder_code}")
        logger.info(f"   📦 生产产品: {', '.join(articles) if articles else '未知'}")
        logger.info(f"   📊 总量: {total_quantity}箱 -> {total_final_quantity}箱")
        logger.info(f"   📅 时间: {feeder_order['planned_start']} - {feeder_order['planned_end']}")
        logger.info(f"   🔗 关联卷包机: {', '.join(feeder_order['associated_makers'])}")
        logger.info(f"   📋 来源计划: {len(plans)}个旬计划")
        
        return feeder_order
    
    def _calculate_tobacco_consumption_rate(self, plans: List[Dict[str, Any]]) -> float:
        """
        计算烟丝消耗速度
        
        Args:
            plans: 旬计划列表
            
        Returns:
            float: 烟丝消耗速度（箱/小时）
        """
        if not plans:
            return 0.0
        
        total_quantity = sum(p.get('quantity_total', 0) for p in plans)
        
        # 计算总工作时间（小时）
        total_hours = 0
        for plan in plans:
            start = plan.get('planned_start')
            end = plan.get('planned_end')
            if start and end:
                if isinstance(start, str):
                    start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if isinstance(end, str):
                    end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
                duration = (end - start).total_seconds() / 3600
                total_hours += duration
        
        return total_quantity / total_hours if total_hours > 0 else 0.0
    
    def _get_associated_makers(self, plans: List[Dict[str, Any]]) -> List[str]:
        """
        获取关联的卷包机列表
        
        Args:
            plans: 旬计划列表
            
        Returns:
            List[str]: 关联的卷包机代码列表
        """
        all_makers = set()
        
        for plan in plans:
            maker_codes = self._extract_maker_codes(plan)
            all_makers.update(maker_codes)
        
        return list(all_makers)
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行规则拆分（修复版）
        
        Args:
            input_data: 合并后的计划数据
            
        Returns:
            AlgorithmResult: 拆分结果，包含正确的input_plan_id关联
        """
        logger.info(f"开始执行修复版拆分算法，输入 {len(input_data)} 个合并计划")
        
        # 直接调用主要的process方法
        return await self.process(input_data)
