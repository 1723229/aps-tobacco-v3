"""
APS智慧排产系统 - 调度优化器

核心调度算法，负责实现卷包机时间不重叠的机台分配和时间槽优化。

核心职责：
1. 智能机台选择算法
2. 严格的时间不重叠分配
3. 负载均衡优化
4. 冲突解决策略
5. 确保100%产品覆盖

关键业务规则：
- 同一卷包机的时间窗口绝对不重叠
- 所有aps_monthly_plan中的产品都必须被安排
- 基于产能和时间约束的智能分配
- 优化整体完成时间和资源利用率

算法策略：
- 贪心算法：优先安排大产量、长时间的产品
- 负载均衡：避免单台机台过度使用
- 时间连续性：优化时间窗口的连续使用
- 约束满足：严格遵循所有时间和产能约束

技术特性：
- 高效的时间冲突检测算法
- 智能的机台选择策略
- 完整的调度状态管理
- 灵活的优化参数调整
- 完善的错误恢复机制
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)


class SchedulingOptimizer:
    """
    调度优化器
    
    核心职责：
    1. 执行智能机台选择算法
    2. 实现严格的时间不重叠分配
    3. 优化负载均衡和资源利用率
    4. 解决调度冲突和约束冲突
    5. 确保所有产品都被正确安排
    """
    
    def __init__(self):
        self._scheduling_state = {}
        self._allocated_slots = {}  # {机台代码: [(start, end, product)]}
        self._unassigned_products = []
        self._original_time_windows = {}  # 缓存原始时间窗口
        self._machine_selection_counter = {}  # 机台选择计数器，用于轮换选择
        self._daily_utilization = {}  # 每日利用率统计 {date: {total_hours: float, schedules: int}}
        self._current_task_id = None  # 统一的任务ID，避免重复生成
        
    def optimize_schedule(
        self, 
        monthly_plans: List[Any], 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict],
        work_calendar: Dict[str, Any] = None,
        shift_configs: List[Dict[str, Any]] = None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """
        执行主调度优化算法
        
        Args:
            monthly_plans: 月度计划列表
            capacity_matrix: 产能矩阵
            time_windows: 机台时间窗口
            machine_relations: 机台关系映射
            
        Returns:
            调度结果字典
        """
        logger.info("开始执行调度优化算法")
        
        try:
            # 1. 初始化调度状态
            self._initialize_scheduling_state(monthly_plans, time_windows)
            
            # 设置统一的任务ID，优先使用传入的task_id
            if task_id:
                self._current_task_id = task_id
                logger.info(f"🔑 使用传入的统一任务ID: {self._current_task_id}")
            else:
                import uuid
                self._current_task_id = f"TASK_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
                logger.info(f"🔑 生成新的任务ID: {self._current_task_id}")
            
            # 缓存原始时间窗口和工作日历
            self._original_time_windows = time_windows.copy()
            self._work_calendar = work_calendar or {}
            
            # 2. 计算动态时间参数（从shift_configs获取正确的每日工时）
            time_params = self._calculate_dynamic_time_parameters(work_calendar, time_windows, shift_configs)
            logger.info(f"🕐 动态时间参数: 工作日数={time_params['total_work_days']}, "
                       f"每日工作时长={time_params['daily_work_hours']:.2f}小时（从班次配置计算）, "
                       f"月度总时长={time_params['total_monthly_hours']:.1f}小时")
            
            # 存储时间参数以供后续使用
            self._time_params = time_params
            
            # 3. **强制覆盖模式：通用拆分预处理**
            force_coverage_mode = time_params.get('force_coverage_mode', False)
            
            if force_coverage_mode:
                logger.info("🎯 启用强制覆盖模式：所有产品将拆分以充分利用全部35台机台")
                processed_plans = self._universal_product_splitting(
                    monthly_plans, capacity_matrix, time_params
                )
                logger.info(f"通用拆分完成: {len(processed_plans)} 个工单（原始{len(monthly_plans)}个产品）")
                sorted_plans = processed_plans  # 直接使用拆分后的计划
            else:
                # 原始逻辑
                sorted_plans = self._sort_products_by_priority(monthly_plans, capacity_matrix)
                logger.info(f"产品优先级排序完成: {len(sorted_plans)} 个产品")
            
            # 存储参数 - 确保使用动态计算的阈值，不使用硬编码默认值
            calculated_threshold = time_params.get('large_product_threshold_hours')
            if calculated_threshold is None:
                raise ValueError("large_product_threshold_hours未从时间参数正确计算，检查time_window_calculator")
            self._large_product_threshold = calculated_threshold
            logger.info(f"设置大产品拆分阈值: {self._large_product_threshold:.2f} 小时")
            
            # 4. 主调度循环
            scheduled_results = []
            retry_queue = []
            
            for plan in sorted_plans:
                result_list = self._schedule_single_product(
                    plan, capacity_matrix, time_windows, machine_relations
                )
                
                if result_list:
                    # 扩展结果列表以处理拆分产品
                    scheduled_results.extend(result_list)
                    if len(result_list) == 1:
                        result = result_list[0]
                        logger.debug(f"成功调度产品 {plan.article_nr}: "
                                   f"机台 {result['assigned_maker_code']}, "
                                   f"时间 {result['scheduled_start_time']} - {result['scheduled_end_time']}")
                    else:
                        logger.info(f"成功拆分调度产品 {plan.article_nr}: "
                                  f"{len(result_list)} 个调度结果")
                else:
                    retry_queue.append(plan)
                    logger.warning(f"产品 {plan.article_nr} 初次调度失败，加入重试队列")
            
            # 6. 重试失败的产品（包括失败的大批量产品）
            if retry_queue:
                logger.info(f"开始重试调度: {len(retry_queue)} 个产品")
                retry_results = self._retry_scheduling(
                    retry_queue, capacity_matrix, time_windows, machine_relations
                )
                scheduled_results.extend(retry_results)
            
            # 7. 特殊处理：检查是否有未排产的大批量产品
            unscheduled_products = []
            for plan in monthly_plans:
                if not any(r['article_nr'] == plan.article_nr for r in scheduled_results):
                    unscheduled_products.append(plan)
            
            if unscheduled_products:
                logger.info(f"发现未排产产品: {len(unscheduled_products)} 个")
                for plan in unscheduled_products:
                    logger.info(f"- {plan.article_nr}: {plan.target_quantity_boxes} 箱")
                    
                    # 尝试绝望模式调度
                    desperate_results = self._desperate_large_product_scheduling(
                        plan, capacity_matrix, time_windows, machine_relations, time_params
                    )
                    if desperate_results:
                        scheduled_results.extend(desperate_results)
            
            # 8. 验证调度完整性
            coverage_result = self._validate_full_coverage(monthly_plans, scheduled_results)
            
            # 6. 优化调度结果
            optimized_results = self._optimize_scheduling_results(scheduled_results)
            
            # 7. 生成调度摘要
            scheduling_summary = self._generate_scheduling_summary(
                monthly_plans, optimized_results, coverage_result
            )
            
            logger.info(f"调度优化完成: 成功调度 {len(optimized_results)} 个产品")
            
            return {
                'success': True,
                'scheduled_results': optimized_results,
                'scheduling_summary': scheduling_summary,
                'coverage_result': coverage_result,
                'unassigned_products': self._unassigned_products,
                'allocated_slots': dict(self._allocated_slots)
            }
            
        except Exception as e:
            logger.error(f"调度优化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'scheduled_results': [],
                'unassigned_products': [plan.article_nr for plan in monthly_plans]
            }
    
    def _initialize_scheduling_state(
        self, 
        monthly_plans: List[Any], 
        time_windows: Dict[str, List[Dict]]
    ) -> None:
        """
        初始化调度状态
        
        Args:
            monthly_plans: 月度计划列表
            time_windows: 时间窗口数据
        """
        # 初始化机台分配槽
        for machine_code, windows in time_windows.items():
            self._allocated_slots[machine_code] = []
        
        # 初始化未分配产品列表
        self._unassigned_products = [plan.article_nr for plan in monthly_plans]
        
        # 初始化调度状态
        self._scheduling_state = {
            'total_products': len(monthly_plans),
            'scheduled_products': 0,
            'failed_products': 0,
            'current_time': None,
            'machine_utilization': {mc: 0.0 for mc in time_windows.keys()}
        }
        
        # 初始化机台选择计数器
        self._machine_selection_counter = {}
        self._global_machine_rotation = 0  # 全局机台轮换计数器
        
        # 初始化每日利用率统计
        self._daily_utilization = {}
        
        logger.debug("调度状态初始化完成")
    
    def _sort_products_by_priority(
        self, 
        monthly_plans: List[Any], 
        capacity_matrix: Dict[Tuple[str, str], Dict]
    ) -> List[Any]:
        """
        产品优先级排序
        
        排序策略：
        1. 产量大的产品优先（需要更多时间）
        2. 可选机台少的产品优先（约束更强）
        3. 生产时间长的产品优先（安排更困难）
        
        Args:
            monthly_plans: 月度计划列表
            capacity_matrix: 产能矩阵
            
        Returns:
            排序后的产品列表
        """
        def priority_score(plan):
            article_nr = plan.article_nr
            quantity = plan.target_quantity_boxes
            
            # 计算该产品的可选机台数
            available_machines = [
                machine_code for (machine_code, product_code), info in capacity_matrix.items()
                if product_code == article_nr and info['can_complete']
            ]
            machine_count = len(available_machines)
            
            # 计算平均生产时间
            if available_machines:
                avg_time = sum(
                    capacity_matrix[(mc, article_nr)]['required_hours']
                    for mc in available_machines
                ) / len(available_machines)
            else:
                avg_time = 999  # 无可用机台的产品优先级最高
            
            # 综合优先级分数
            # 产量权重 + 机台稀缺性权重 + 时间权重
            quantity_score = quantity / 1000  # 产量分数
            scarcity_score = (10 - machine_count) if machine_count < 10 else 0  # 稀缺性分数
            time_score = avg_time / 10  # 时间分数
            
            return quantity_score + scarcity_score + time_score
        
        sorted_plans = sorted(monthly_plans, key=priority_score, reverse=True)
        
        logger.debug(f"产品优先级排序: {[p.article_nr for p in sorted_plans[:5]]}")
        return sorted_plans
    
    def _schedule_single_product(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        调度单个产品 - 支持大批量产品的跨日和拆分调度
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            time_windows: 时间窗口
            machine_relations: 机台关系
            
        Returns:
            调度结果列表（单个产品返回单项列表，拆分产品返回多项列表）
        """
        article_nr = plan.article_nr
        target_quantity = plan.target_quantity_boxes
        
        # 1. 获取可用机台列表
        available_machines = self._get_available_machines(article_nr, capacity_matrix)
        if not available_machines:
            logger.warning(f"产品 {article_nr} 没有可用机台")
            return None
        
        # 2. 检查是否为大批量产品需要拆分调度
        min_required_hours = min(info['required_hours'] for _, info in available_machines)
        
        # 使用激进的动态阈值：如果所需时间超过单台机台月度可用时长的5%，则拆分调度
        # 目的：充分利用所有35台机台，提高排产达标率
        time_params = getattr(self, '_time_params', {})
        single_machine_monthly_hours = time_params.get('single_machine_monthly_hours')
        if single_machine_monthly_hours is None:
            raise ValueError("single_machine_monthly_hours未从数据库获取，不允许使用默认值")
        
        # 从时间参数获取配置的拆分阈值比例，默认20%（平衡的拆分策略）
        split_threshold_ratio = time_params.get('split_threshold_ratio', 0.20)  # 20%阈值，避免过度拆分
        large_product_threshold = single_machine_monthly_hours * split_threshold_ratio
        
        if min_required_hours > large_product_threshold:
            logger.info(f"产品 {article_nr} 需要 {min_required_hours:.2f}小时（阈值:{large_product_threshold:.1f}），启用拆分调度")
            split_results = self._schedule_large_product_with_splitting(
                plan, available_machines, capacity_matrix, machine_relations
            )
            return split_results if split_results else None
        
        # 3. 按优先级尝试每台机台(原有逻辑)
        for machine_code, capacity_info in available_machines:
            # 4. 查找可用时间槽 - 修改为支持跨日查找
            time_slot = self._find_available_time_slot_cross_day(
                machine_code, capacity_info['required_hours']
            )
            
            if time_slot:
                # 5. 分配时间槽
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 6. 生成调度结果
                    result = self._create_scheduling_result(
                        plan, machine_code, time_slot, capacity_info, machine_relations
                    )
                    
                    # 7. 更新调度状态和每日利用率
                    self._update_scheduling_state(article_nr, machine_code, capacity_info)
                    self._update_daily_utilization(time_slot)
                    
                    logger.info(f"✅ 成功调度产品 {article_nr} 到机台 {machine_code}")
                    return [result]  # 返回单项列表
            else:
                logger.debug(f"机台 {machine_code} 没有足够的时间槽 (需要 {capacity_info['required_hours']:.2f} 小时)")
        
        # 未能成功调度
        logger.warning(f"产品 {article_nr} 调度失败：无可用时间槽")
        return None
    
    def _get_available_machines(
        self, 
        article_nr: str, 
        capacity_matrix: Dict[Tuple[str, str], Dict]
    ) -> List[Tuple[str, Dict]]:
        """
        获取产品的可用机台列表，使用超激进策略确保所有35台机台被充分利用
        
        策略更新：
        1. 优先使用can_complete=True的机台
        2. 如果机台不足，放宽约束使用can_complete=False的机台（部分产能利用）
        3. 确保每个产品都能获得足够的机台选择
        
        Args:
            article_nr: 产品代码
            capacity_matrix: 产能矩阵
            
        Returns:
            可用机台列表 [(机台代码, 产能信息)]
        """
        # 第一优先级：can_complete=True的机台
        primary_available = []
        # 第二优先级：can_complete=False但有速度配置的机台（用于产能不足时）
        secondary_available = []
        
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            # 支持精确匹配和通配符匹配
            if product_code == article_nr or product_code == '*':
                if capacity_info.get('can_complete', False):
                    primary_available.append((machine_code, capacity_info))
                elif capacity_info.get('actual_speed', 0) > 0:
                    # 修改can_complete状态，允许部分利用
                    modified_info = capacity_info.copy()
                    modified_info['can_complete'] = True  # 强制标记为可用
                    modified_info['partial_capacity'] = True  # 标记为部分产能
                    secondary_available.append((machine_code, modified_info))
        
        # 优先使用第一级机台，如果不足则补充第二级机台
        available = primary_available.copy()
        
        # 根本修复：强制启用所有有效机台，不设置数量限制
        # 确保所有35台机台都能参与大批量产品的排产
        if secondary_available:
            logger.info(f"产品 {article_nr} 可用机台: 主要{len(available)}台, 启用全部部分产能机台{len(secondary_available)}台")
            available.extend(secondary_available)  # 添加所有有效的部分产能机台
        
        # 特别处理大批量产品：确保有足够机台选择
        target_machines = 25  # 大批量产品期望使用25台机台
        if len(available) < target_machines:
            logger.warning(f"产品 {article_nr} 机台数量偏少({len(available)}台)，建议检查速度配置覆盖率")
        
        if not available:
            logger.warning(f"产品 {article_nr} 完全没有可用机台")
            return []
        
        # 极致强制轮换策略：优先选择从未使用的机台
        def extreme_rotation_priority(item):
            machine_code, info = item
            
            # 获取当前使用次数
            usage_count = len(self._allocated_slots.get(machine_code, []))
            
            # 极端优先级权重：
            # - 从未使用过的机台获得最高优先级 (10000分)
            # - 使用1次的机台获得中等优先级 (1000分) 
            # - 使用2次以上的机台获得最低优先级 (100分)
            if usage_count == 0:
                base_priority = 10000  # 从未使用，最高优先级
            elif usage_count == 1:
                base_priority = 1000   # 使用过1次，中等优先级
            else:
                base_priority = 100    # 使用过多次，最低优先级
            
            # 减去使用次数的大额惩罚
            usage_penalty = usage_count * 500
            
            # 性能因素作为次要考虑
            speed = info.get('actual_speed') or info.get('speed_per_hour')
            if speed is None:
                raise ValueError(f"机台速度未从数据库获取，不允许使用默认值")
            performance_bonus = speed * 0.1  # 性能只占很小权重
            
            final_priority = base_priority - usage_penalty + performance_bonus
            
            return final_priority
        
        # 按极致轮换优先级排序
        available.sort(key=extreme_rotation_priority, reverse=True)
        
        # 强制轮换策略：使用全局计数器进一步打散分布
        self._global_machine_rotation += 1
        
        # 更激进的轮换：确保前几个产品分配到不同机台
        num_machines = len(available)
        if self._global_machine_rotation <= num_machines:
            # 前N个产品（N=机台数量）使用固定轮换模式
            target_index = (self._global_machine_rotation - 1) % num_machines
            if target_index < len(available):
                # 将目标机台移到首位
                target_machine = available[target_index]
                available.remove(target_machine)
                available.insert(0, target_machine)
        
        logger.debug(f"产品 {article_nr} 极致轮换机台选择: {[m[0] for m in available[:3]]}... "
                    f"(全局轮换: {self._global_machine_rotation})")
        
        return available
    
    def _find_available_time_slot(
        self, 
        machine_code: str, 
        required_hours: float
    ) -> Optional[Dict]:
        """
        为机台查找可用的时间槽
        
        Args:
            machine_code: 机台代码
            required_hours: 所需时间
            
        Returns:
            可用时间槽信息
        """
        allocated_slots = self._allocated_slots.get(machine_code, [])
        
        # 获取该机台的所有时间窗口
        all_windows = []
        for window in self._get_original_time_windows(machine_code):
            all_windows.append({
                'start': window['start_time'],
                'end': window['end_time'],
                'duration': window['duration_hours']
            })
        
        # 合并连续的时间窗口
        merged_windows = self._merge_continuous_windows(all_windows)
        
        # 在合并后的时间窗口中查找可用槽
        for window in merged_windows:
            available_slots = self._split_window_by_allocated_slots(
                window, allocated_slots
            )
            
            for slot in available_slots:
                if slot['duration'] >= required_hours:
                    return {
                        'start': slot['start'],
                        'end': slot['start'] + timedelta(hours=required_hours),
                        'duration': required_hours,
                        'window_start': window['start'],
                        'window_end': window['end']
                    }
        
        return None
    
    def _get_original_time_windows(self, machine_code: str) -> List[Dict]:
        """
        获取机台的原始时间窗口（从缓存中获取）
        
        Args:
            machine_code: 机台代码
            
        Returns:
            时间窗口列表
        """
        windows = self._original_time_windows.get(machine_code, [])
        logger.debug(f"获取机台 {machine_code} 的时间窗口: {len(windows)} 个")
        return windows
    
    def _merge_continuous_windows(self, windows: List[Dict]) -> List[Dict]:
        """
        合并连续的时间窗口 - 修复版：防止过度合并，保留每日独立调度能力
        
        Args:
            windows: 时间窗口列表
            
        Returns:
            合并后的时间窗口列表
        """
        if not windows:
            return []
        
        # 按开始时间排序
        sorted_windows = sorted(windows, key=lambda x: x['start'])
        
        merged = [sorted_windows[0].copy()]
        
        for window in sorted_windows[1:]:
            last_merged = merged[-1]
            
            # 计算时间间隔
            gap = (window['start'] - last_merged['end']).total_seconds() / 60
            
            # 检查是否为同一天的连续班次
            same_day = (
                last_merged['end'].date() == window['start'].date() or
                (last_merged['end'].date() + timedelta(days=1) == window['start'].date() and 
                 window['start'].hour < 12)  # 跨日班次但在上午
            )
            
            # 只有在同一天且间隔很小时才合并，保持跨日分离
            if same_day and gap <= 5:  # 5分钟内可以合并
                # 合并窗口
                last_merged['end'] = window['end']
                last_merged['duration'] = (
                    last_merged['end'] - last_merged['start']
                ).total_seconds() / 3600
                logger.debug(f"合并时间窗口: {last_merged['start']} - {last_merged['end']}")
            else:
                # 添加新窗口，保持独立
                merged.append(window.copy())
                logger.debug(f"保持独立时间窗口: {window['start']} - {window['end']}")
        
        logger.info(f"时间窗口合并完成: {len(sorted_windows)} -> {len(merged)} 个窗口")
        return merged
    
    def _split_window_by_allocated_slots(
        self, 
        window: Dict, 
        allocated_slots: List[Tuple]
    ) -> List[Dict]:
        """
        根据已分配的时间槽分割时间窗口
        
        Args:
            window: 时间窗口
            allocated_slots: 已分配的时间槽 [(start, end, product)]
            
        Returns:
            可用的时间槽列表
        """
        available_slots = []
        current_start = window['start']
        window_end = window['end']
        
        # 按开始时间排序已分配的槽
        sorted_slots = sorted(allocated_slots, key=lambda x: x[0])
        
        for slot_start, slot_end, _ in sorted_slots:
            # 检查槽是否在当前窗口内
            if slot_end <= current_start or slot_start >= window_end:
                continue  # 不在当前窗口内
            
            # 添加槽前的可用时间 - 根本修复：降低最小时间片要求
            if current_start < slot_start:
                duration = (slot_start - current_start).total_seconds() / 3600
                if duration > 0.1:  # 降低到6分钟，允许更细粒度的时间分配
                    available_slots.append({
                        'start': current_start,
                        'end': slot_start,
                        'duration': duration
                    })
            
            # 更新当前开始时间
            current_start = max(current_start, slot_end)
        
        # 添加最后一段可用时间 - 根本修复：降低最小时间片要求
        if current_start < window_end:
            duration = (window_end - current_start).total_seconds() / 3600
            if duration > 0.1:  # 降低到6分钟，允许更细粒度的时间分配
                available_slots.append({
                    'start': current_start,
                    'end': window_end,
                    'duration': duration
                })
        
        return available_slots
    
    def _allocate_time_slot(
        self, 
        machine_code: str, 
        start_time: datetime, 
        end_time: datetime, 
        article_nr: str
    ) -> bool:
        """
        分配时间槽
        
        Args:
            machine_code: 机台代码
            start_time: 开始时间
            end_time: 结束时间
            article_nr: 产品代码
            
        Returns:
            是否成功分配
        """
        # 检查时间槽是否与已分配的槽重叠
        allocated_slots = self._allocated_slots.get(machine_code, [])
        
        for existing_start, existing_end, _ in allocated_slots:
            if self._time_ranges_overlap(start_time, end_time, existing_start, existing_end):
                logger.error(f"时间槽分配冲突: 机台 {machine_code}, "
                           f"新槽 {start_time}-{end_time}, "
                           f"已存在 {existing_start}-{existing_end}")
                return False
        
        # 分配时间槽
        allocated_slots.append((start_time, end_time, article_nr))
        self._allocated_slots[machine_code] = allocated_slots
        
        logger.debug(f"时间槽分配成功: 机台 {machine_code}, "
                    f"产品 {article_nr}, "
                    f"时间 {start_time} - {end_time}")
        return True
    
    def _time_ranges_overlap(
        self, 
        start1: datetime, 
        end1: datetime, 
        start2: datetime, 
        end2: datetime
    ) -> bool:
        """
        检查两个时间范围是否重叠
        
        Args:
            start1, end1: 第一个时间范围
            start2, end2: 第二个时间范围
            
        Returns:
            是否重叠
        """
        return start1 < end2 and start2 < end1
    
    def _create_scheduling_result(
        self, 
        plan: Any, 
        machine_code: str, 
        time_slot: Dict, 
        capacity_info: Dict, 
        machine_relations: Dict[str, Dict]
    ) -> Dict:
        """
        创建调度结果
        
        Args:
            plan: 月度计划
            machine_code: 分配的机台
            time_slot: 分配的时间槽
            capacity_info: 产能信息
            machine_relations: 机台关系
            
        Returns:
            调度结果字典
        """
        # 查找对应的喂丝机
        feeder_code = machine_relations['maker_to_feeder'].get(machine_code)
        
        # 生成工单号
        work_order_nr = f"WO_{plan.monthly_batch_id}_{plan.article_nr}_{uuid.uuid4().hex[:8].upper()}"
        
        return {
            'monthly_task_id': self._current_task_id,  # 使用统一的任务ID
            'monthly_plan_id': plan.monthly_plan_id,
            'monthly_batch_id': plan.monthly_batch_id,
            'work_order_nr': work_order_nr,
            'article_nr': plan.article_nr,
            'article_name': getattr(plan, 'article_name', plan.article_nr),
            'target_quantity_boxes': plan.target_quantity_boxes,
            'assigned_maker_code': machine_code,
            'assigned_feeder_code': feeder_code,
            'scheduled_start_time': time_slot.get('start') or time_slot.get('scheduled_start_time'),
            'scheduled_end_time': time_slot.get('end') or time_slot.get('scheduled_end_time'),
            'scheduled_duration_hours': time_slot.get('duration') or time_slot.get('scheduled_duration_hours'),
            'estimated_speed': capacity_info.get('actual_speed') or capacity_info.get('speed_per_hour'),
            'efficiency_rate': capacity_info.get('efficiency_rate') or 
                               (capacity_info.get('efficiency', 100) / 100 if capacity_info.get('efficiency') is not None else None),
            'utilization_rate': capacity_info.get('utilization_rate') or 1,
            'algorithm_version': 'v2.0_complete',
            'scheduling_timestamp': datetime.now(),
            'priority_score': self._calculate_priority_score(plan, capacity_info),
            'calculation_details': {
                'base_speed': capacity_info['speed_per_hour'],  # 统一使用speed_per_hour字段
                'actual_speed': capacity_info['actual_speed'],
                'required_hours': capacity_info['required_hours'],
                'available_hours': capacity_info['available_hours'],
                'speed_config_source': capacity_info['speed_config_source']
            }
        }
    
    def _calculate_priority_score(self, plan: Any, capacity_info: Dict) -> float:
        """
        计算优先级分数
        
        Args:
            plan: 月度计划
            capacity_info: 产能信息
            
        Returns:
            优先级分数
        """
        quantity_factor = plan.target_quantity_boxes / 1000
        time_factor = capacity_info['required_hours'] / 10
        efficiency_factor = capacity_info['efficiency_rate'] / 100
        
        return quantity_factor + time_factor + efficiency_factor
    
    def _update_scheduling_state(
        self, 
        article_nr: str, 
        machine_code: str, 
        capacity_info: Dict
    ) -> None:
        """
        更新调度状态
        
        Args:
            article_nr: 产品代码
            machine_code: 机台代码
            capacity_info: 产能信息
        """
        # 更新统计信息
        self._scheduling_state['scheduled_products'] += 1
        
        # 更新机台利用率
        current_util = self._scheduling_state['machine_utilization'].get(machine_code, 0.0)
        self._scheduling_state['machine_utilization'][machine_code] = min(
            current_util + capacity_info.get('utilization_rate', 1.0 ), 1.0
        )
        
        # 从未分配列表中移除
        if article_nr in self._unassigned_products:
            self._unassigned_products.remove(article_nr)
    
    def _update_daily_utilization(self, time_slot: Dict) -> None:
        """
        更新每日利用率统计
        
        Args:
            time_slot: 时间槽信息
        """
        if 'scheduled_date' in time_slot:
            date = time_slot['scheduled_date']
        else:
            date = time_slot['start'].date()
            
        if date not in self._daily_utilization:
            self._daily_utilization[date] = {'total_hours': 0.0, 'schedules': 0}
        
        self._daily_utilization[date]['total_hours'] += time_slot['duration']
        self._daily_utilization[date]['schedules'] += 1
        
        logger.debug(f"更新日期 {date} 利用率: {self._daily_utilization[date]['total_hours']:.2f} 小时, "
                    f"{self._daily_utilization[date]['schedules']} 个排产")
    
    def _retry_scheduling(
        self, 
        retry_queue: List[Any], 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict]
    ) -> List[Dict]:
        """
        重试调度失败的产品 - 使用多种增强策略
        
        采用渐进式重试策略：
        1. 机台轮换重试
        2. 约束放松重试
        3. 强制拆分重试
        4. 绝望模式重试（最大约束放松）
        
        Args:
            retry_queue: 重试产品列表
            capacity_matrix: 产能矩阵
            time_windows: 时间窗口
            machine_relations: 机台关系
            
        Returns:
            重试成功的调度结果
        """
        retry_results = []
        still_failed = []
        
        logger.info(f"开始增强重试调度: {len(retry_queue)} 个产品")
        
        for plan in retry_queue:
            article_nr = plan.article_nr
            logger.info(f"重试产品: {article_nr}")
            
            # 策略1: 机台轮换重试 - 强制尝试所有可能的机台
            result = self._retry_with_machine_rotation(plan, capacity_matrix, machine_relations)
            if result:
                retry_results.extend(result)
                logger.info(f"✅ 产品 {article_nr} 通过机台轮换重试成功")
                continue
            
            # 策略2: 约束放松重试 - 放松时间约束
            result = self._retry_with_relaxed_constraints(plan, capacity_matrix, machine_relations)
            if result:
                retry_results.extend(result)
                logger.info(f"✅ 产品 {article_nr} 通过约束放松重试成功")
                continue
            
            # 策略3: 强制拆分重试 - 即使是中等产品也强制拆分
            result = self._retry_with_forced_splitting(plan, capacity_matrix, machine_relations)
            if result:
                retry_results.extend(result)
                logger.info(f"✅ 产品 {article_nr} 通过强制拆分重试成功")
                continue
            
            # 策略4: 绝望模式重试 - 最大程度放松约束
            result = self._retry_with_desperate_mode(plan, capacity_matrix, machine_relations)
            if result:
                retry_results.extend(result)
                logger.info(f"✅ 产品 {article_nr} 通过绝望模式重试成功")
                continue
            
            # 所有策略都失败
            still_failed.append(plan)
            logger.error(f"❌ 产品 {article_nr} 所有重试策略都失败")
        
        # 更新统计
        for plan in still_failed:
            self._scheduling_state['failed_products'] += 1
            
        logger.info(f"重试调度完成: 成功 {len(retry_results)} 个, 仍失败 {len(still_failed)} 个")
        return retry_results
    
    def _try_product_splitting(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        machine_relations: Dict[str, Dict]
    ) -> List[Dict]:
        """
        尝试产品拆分策略
        
        将大产量产品拆分到多台机台上生产
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            拆分后的调度结果列表
        """
        article_nr = plan.article_nr
        total_quantity = plan.target_quantity_boxes
        
        # 获取所有可用机台及其可生产量
        available_capacity = []
        for (machine_code, product_code), info in capacity_matrix.items():
            if product_code == article_nr:
                # 计算该机台的剩余可用时间
                remaining_slots = self._calculate_remaining_capacity(machine_code, info)
                if remaining_slots > 0:
                    available_capacity.append((machine_code, remaining_slots, info))
        
        if not available_capacity:
            return []
        
        # 按可生产量排序
        available_capacity.sort(key=lambda x: x[1], reverse=True)
        
        # 尝试将产量分配到多台机台
        split_results = []
        remaining_quantity = total_quantity
        
        for machine_code, max_quantity, capacity_info in available_capacity:
            if remaining_quantity <= 0:
                break
            
            # 计算该机台的分配量
            allocated_quantity = min(remaining_quantity, max_quantity)
            allocated_hours = allocated_quantity / capacity_info['actual_speed']
            
            # 查找时间槽
            time_slot = self._find_available_time_slot(machine_code, allocated_hours)
            
            if time_slot:
                # 分配时间槽
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 创建拆分后的计划
                    split_plan = self._create_split_plan(plan, allocated_quantity)
                    
                    # 创建调度结果
                    result = self._create_scheduling_result(
                        split_plan, machine_code, time_slot, capacity_info, machine_relations
                    )
                    
                    split_results.append(result)
                    remaining_quantity -= allocated_quantity
                    
                    logger.debug(f"产品拆分: {article_nr} 在机台 {machine_code} "
                               f"分配 {allocated_quantity} 箱")
        
        # 检查是否完全分配
        if remaining_quantity > 0:
            logger.warning(f"产品 {article_nr} 拆分后仍有 {remaining_quantity} 箱未分配")
            # 回滚已分配的时间槽
            self._rollback_allocations(split_results)
            return []
        
        return split_results
    
    def _calculate_remaining_capacity(self, machine_code: str, capacity_info: Dict) -> float:
        """
        计算机台的剩余可生产量
        
        Args:
            machine_code: 机台代码
            capacity_info: 产能信息
            
        Returns:
            剩余可生产量
        """
        # 计算已分配的时间
        allocated_slots = self._allocated_slots.get(machine_code, [])
        allocated_hours = sum(
            (end - start).total_seconds() / 3600 
            for start, end, _ in allocated_slots
        )
        
        # 计算剩余时间
        total_available = capacity_info['available_hours']
        remaining_hours = max(0, total_available - allocated_hours)
        
        # 计算剩余产能
        actual_speed = capacity_info['actual_speed']
        return remaining_hours * actual_speed
    
    def _create_split_plan(self, original_plan: Any, allocated_quantity: int) -> Any:
        """
        创建拆分后的计划对象
        
        Args:
            original_plan: 原始计划
            allocated_quantity: 分配数量
            
        Returns:
            拆分后的计划对象
        """
        # 创建计划副本
        split_plan = type(original_plan)()
        
        # 复制原始属性
        for attr in ['monthly_plan_id', 'monthly_batch_id', 'article_nr', 
                     'article_name', 'plan_year', 'plan_month']:
            if hasattr(original_plan, attr):
                setattr(split_plan, attr, getattr(original_plan, attr))
        
        # 设置分配数量
        split_plan.target_quantity_boxes = allocated_quantity
        
        return split_plan
    
    def _rollback_allocations(self, results: List[Dict]) -> None:
        """
        回滚已分配的时间槽
        
        Args:
            results: 需要回滚的调度结果
        """
        for result in results:
            machine_code = result['assigned_maker_code']
            start_time = result['scheduled_start_time']
            end_time = result['scheduled_end_time']
            
            # 从分配槽中移除
            allocated_slots = self._allocated_slots.get(machine_code, [])
            self._allocated_slots[machine_code] = [
                slot for slot in allocated_slots 
                if not (slot[0] == start_time and slot[1] == end_time)
            ]
        
        logger.debug(f"回滚 {len(results)} 个时间槽分配")
    
    def _retry_with_machine_rotation(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        机台轮换重试策略 - 强制尝试所有可能的机台
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            调度结果列表
        """
        article_nr = plan.article_nr
        
        # 获取所有可用机台，忽略优先级排序
        all_machines = []
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if product_code == article_nr and capacity_info['can_complete']:
                all_machines.append((machine_code, capacity_info))
        
        # 按当前使用情况排序，优先选择使用较少的机台
        def usage_score(item):
            machine_code, _ = item
            usage_count = len(self._allocated_slots.get(machine_code, []))
            return usage_count
        
        all_machines.sort(key=usage_score)
        
        logger.debug(f"产品 {article_nr} 机台轮换尝试: {[m[0] for m in all_machines]}")
        
        # 逐个尝试所有机台
        for machine_code, capacity_info in all_machines:
            required_hours = capacity_info['required_hours']
            
            # 使用日期感知的时间槽查找
            time_slot = self._find_available_time_slot_cross_day(machine_code, required_hours)
            
            if time_slot:
                # 分配时间槽
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 创建调度结果
                    result = self._create_scheduling_result(
                        plan, machine_code, time_slot, capacity_info, machine_relations
                    )
                    
                    # 更新状态
                    self._update_scheduling_state(article_nr, machine_code, capacity_info)
                    self._update_daily_utilization(time_slot)
                    
                    logger.info(f"机台轮换成功: {article_nr} -> {machine_code}")
                    return [result]
        
        return None
    
    def _retry_with_relaxed_constraints(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        约束放松重试策略 - 放松时间约束寻找更多可能
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            调度结果列表
        """
        article_nr = plan.article_nr
        
        # 获取可用机台
        available_machines = self._get_available_machines(article_nr, capacity_matrix)
        
        for machine_code, capacity_info in available_machines:
            required_hours = capacity_info['required_hours']
            
            # 尝试更小的时间块，允许跨班次调度
            relaxed_hours = max(required_hours * 0.8, 4.0)  # 至少4小时
            
            time_slot = self._find_available_time_slot_cross_day(machine_code, relaxed_hours)
            
            if time_slot:
                # 调整时间槽以匹配实际需求
                actual_end = time_slot['start'] + timedelta(hours=required_hours)
                adjusted_slot = {
                    'start': time_slot['start'],
                    'end': actual_end,
                    'duration': required_hours,
                    'window_start': time_slot['window_start'],
                    'window_end': time_slot['window_end']
                }
                
                # 检查调整后的时间槽是否可行
                if self._is_time_slot_available(machine_code, adjusted_slot['start'], adjusted_slot['end']):
                    success = self._allocate_time_slot(
                        machine_code, adjusted_slot['start'], adjusted_slot['end'], article_nr
                    )
                    
                    if success:
                        result = self._create_scheduling_result(
                            plan, machine_code, adjusted_slot, capacity_info, machine_relations
                        )
                        
                        self._update_scheduling_state(article_nr, machine_code, capacity_info)
                        self._update_daily_utilization(adjusted_slot)
                        
                        logger.info(f"约束放松成功: {article_nr} -> {machine_code}")
                        return [result]
        
        return None
    
    def _retry_with_forced_splitting(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        强制拆分重试策略 - 即使中等产品也强制拆分
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            调度结果列表
        """
        article_nr = plan.article_nr
        target_quantity = plan.target_quantity_boxes
        
        logger.info(f"强制拆分产品 {article_nr}, 目标 {target_quantity} 箱")
        
        # 获取所有可用机台
        available_machines = []
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if product_code == article_nr:
                available_machines.append((machine_code, capacity_info))
        
        # 尝试分配到多台机台
        split_results = []
        remaining_quantity = target_quantity
        
        for machine_code, capacity_info in available_machines:
            if remaining_quantity <= 0:
                break
                
            # 计算该机台可处理的数量（较小的时间块）
            max_hours = 8.0  # 降低单次最大时间
            speed = capacity_info['actual_speed']
            max_quantity = int(speed * max_hours)
            
            allocatable_quantity = min(remaining_quantity, max_quantity)
            required_hours = allocatable_quantity / speed
            
            time_slot = self._find_available_time_slot_cross_day(machine_code, required_hours)
            
            if time_slot:
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 创建拆分后的计划
                    split_plan = self._create_split_plan(plan, allocatable_quantity)
                    
                    result = self._create_scheduling_result(
                        split_plan, machine_code, time_slot, capacity_info, machine_relations
                    )
                    
                    # 添加拆分信息
                    result['split_info'] = {
                        'is_split_product': True,
                        'split_index': len(split_results) + 1,
                        'allocated_quantity': allocatable_quantity
                    }
                    
                    split_results.append(result)
                    remaining_quantity -= allocatable_quantity
                    
                    logger.debug(f"强制拆分分配: {allocatable_quantity} 箱到机台 {machine_code}")
        
        if split_results and remaining_quantity < target_quantity * 0.2:  # 至少80%分配成功
            # 更新状态
            self._update_scheduling_state(article_nr, "MULTIPLE", {})
            for result in split_results:
                time_slot = {
                    'start': result['scheduled_start_time'],
                    'end': result['scheduled_end_time'],
                    'duration': result['scheduled_duration_hours']
                }
                self._update_daily_utilization(time_slot)
            
            logger.info(f"强制拆分成功: {article_nr}, 分配 {len(split_results)} 个机台")
            return split_results
        else:
            # 回滚分配
            self._rollback_allocations(split_results)
            return None
    
    def _retry_with_desperate_mode(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        绝望模式重试策略 - 最大程度放松约束
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            调度结果列表
        """
        article_nr = plan.article_nr
        logger.info(f"绝望模式重试: {article_nr}")
        
        # 获取所有机台，不管是否标记为can_complete
        desperate_machines = []
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if product_code == article_nr:  # 移除can_complete检查
                desperate_machines.append((machine_code, capacity_info))
        
        # 尝试最小可行调度
        for machine_code, capacity_info in desperate_machines:
            # 计算最小可行时间（降低到原需求的60%）
            original_hours = capacity_info.get('required_hours', 8.0)
            desperate_hours = max(original_hours * 0.6, 2.0)  # 至少2小时
            
            time_slot = self._find_available_time_slot_cross_day(machine_code, desperate_hours)
            
            if time_slot:
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 按实际可调度数量调整
                    speed = capacity_info.get('actual_speed', 8.0)
                    desperate_quantity = int(speed * desperate_hours)
                    
                    # 创建绝望模式计划
                    desperate_plan = self._create_split_plan(plan, desperate_quantity)
                    
                    result = self._create_scheduling_result(
                        desperate_plan, machine_code, time_slot, capacity_info, machine_relations
                    )
                    
                    # 标记为绝望模式调度
                    result['desperate_mode'] = True
                    result['original_target'] = plan.target_quantity_boxes
                    result['desperate_ratio'] = desperate_quantity / plan.target_quantity_boxes
                    
                    self._update_scheduling_state(article_nr, machine_code, capacity_info)
                    self._update_daily_utilization(time_slot)
                    
                    logger.warning(f"绝望模式成功: {article_nr} -> {machine_code}, "
                                 f"数量 {desperate_quantity}/{plan.target_quantity_boxes}")
                    return [result]
        
        return None
    
    def _is_time_slot_available(
        self, 
        machine_code: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> bool:
        """
        检查时间槽是否可用（不与已分配槽重叠）
        
        Args:
            machine_code: 机台代码
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            是否可用
        """
        allocated_slots = self._allocated_slots.get(machine_code, [])
        
        for existing_start, existing_end, _ in allocated_slots:
            if self._time_ranges_overlap(start_time, end_time, existing_start, existing_end):
                return False
        
        return True
    
    def _validate_full_coverage(
        self, 
        monthly_plans: List[Any], 
        scheduled_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        验证调度的完整覆盖性
        
        Args:
            monthly_plans: 原始月度计划
            scheduled_results: 调度结果
            
        Returns:
            覆盖性验证结果
        """
        # 统计已调度的产品和数量
        scheduled_quantities = {}
        for result in scheduled_results:
            article_nr = result['article_nr']
            quantity = result['target_quantity_boxes']
            
            if article_nr in scheduled_quantities:
                scheduled_quantities[article_nr] += quantity
            else:
                scheduled_quantities[article_nr] = quantity
        
        # 检查覆盖性
        coverage_result = {
            'full_coverage': True,
            'covered_products': [],
            'partial_products': [],
            'missing_products': [],
            'over_scheduled_products': [],
            'coverage_rate': 0.0
        }
        
        total_planned = 0
        total_scheduled = 0
        
        for plan in monthly_plans:
            article_nr = plan.article_nr
            planned_quantity = plan.target_quantity_boxes
            scheduled_quantity = scheduled_quantities.get(article_nr, 0)
            
            total_planned += planned_quantity
            total_scheduled += scheduled_quantity
            
            if scheduled_quantity == 0:
                coverage_result['missing_products'].append({
                    'article_nr': article_nr,
                    'planned_quantity': planned_quantity
                })
                coverage_result['full_coverage'] = False
            elif scheduled_quantity < planned_quantity:
                coverage_result['partial_products'].append({
                    'article_nr': article_nr,
                    'planned_quantity': planned_quantity,
                    'scheduled_quantity': scheduled_quantity,
                    'shortfall': planned_quantity - scheduled_quantity
                })
                coverage_result['full_coverage'] = False
            elif scheduled_quantity > planned_quantity:
                coverage_result['over_scheduled_products'].append({
                    'article_nr': article_nr,
                    'planned_quantity': planned_quantity,
                    'scheduled_quantity': scheduled_quantity,
                    'excess': scheduled_quantity - planned_quantity
                })
            else:
                coverage_result['covered_products'].append({
                    'article_nr': article_nr,
                    'quantity': planned_quantity
                })
        
        # 计算覆盖率
        coverage_result['coverage_rate'] = (
            total_scheduled / total_planned if total_planned > 0 else 0.0
        )
        
        logger.info(f"调度覆盖性验证: "
                   f"覆盖率 {coverage_result['coverage_rate']:.1%}, "
                   f"完全覆盖 {len(coverage_result['covered_products'])} 个产品, "
                   f"缺失 {len(coverage_result['missing_products'])} 个产品")
        
        return coverage_result
    
    def _optimize_scheduling_results(self, results: List[Dict]) -> List[Dict]:
        """
        优化调度结果
        
        Args:
            results: 原始调度结果
            
        Returns:
            优化后的调度结果
        """
        # 当前简化实现：直接返回结果
        # 未来可以添加更多优化策略，如：
        # - 时间窗口紧缩
        # - 机台负载重新平衡
        # - 连续生产优化
        
        optimized = sorted(results, key=lambda x: x['scheduled_start_time'])
        logger.debug(f"调度结果优化完成: {len(optimized)} 个结果")
        return optimized
    
    def _generate_scheduling_summary(
        self, 
        monthly_plans: List[Any], 
        scheduled_results: List[Dict], 
        coverage_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成调度摘要
        
        Args:
            monthly_plans: 月度计划
            scheduled_results: 调度结果
            coverage_result: 覆盖性结果
            
        Returns:
            调度摘要
        """
        # 计算机台利用率统计
        machine_stats = {}
        for result in scheduled_results:
            machine_code = result['assigned_maker_code']
            duration = result['scheduled_duration_hours']
            
            if machine_code not in machine_stats:
                machine_stats[machine_code] = {
                    'total_hours': 0.0,
                    'product_count': 0,
                    'products': []
                }
            
            machine_stats[machine_code]['total_hours'] += duration
            machine_stats[machine_code]['product_count'] += 1
            machine_stats[machine_code]['products'].append(result['article_nr'])
        
        # 生成摘要
        summary = {
            'total_plans': len(monthly_plans),
            'scheduled_plans': len(scheduled_results),
            'success_rate': len(scheduled_results) / len(monthly_plans) if monthly_plans else 0.0,
            'coverage_rate': coverage_result['coverage_rate'],
            'machine_count': len(machine_stats),
            'machine_utilization': machine_stats,
            'scheduling_duration': 'N/A',  # 需要在外部计算
            'algorithm_version': 'v2.0_complete',
            'optimization_notes': []
        }
        
        # 添加优化建议
        if coverage_result['missing_products']:
            summary['optimization_notes'].append(
                f"{len(coverage_result['missing_products'])} 个产品未能安排生产"
            )
        
        if len(machine_stats) < 3:
            summary['optimization_notes'].append("机台利用数量较少，可能存在产能浪费")
        
        return summary
    
    def ensure_full_coverage(
        self, 
        monthly_plans: List[Any], 
        scheduled_results: List[Dict]
    ) -> bool:
        """
        确保所有产品都被安排
        
        Args:
            monthly_plans: 月度计划
            scheduled_results: 调度结果
            
        Returns:
            是否实现完全覆盖
        """
        coverage_result = self._validate_full_coverage(monthly_plans, scheduled_results)
        return coverage_result['full_coverage']
    
    def validate_zero_overlap(self, scheduled_results: List[Dict]) -> bool:
        """
        验证零时间重叠
        
        Args:
            scheduled_results: 调度结果
            
        Returns:
            是否存在时间重叠
        """
        # 按机台分组
        machine_schedules = {}
        for result in scheduled_results:
            machine_code = result['assigned_maker_code']
            if machine_code not in machine_schedules:
                machine_schedules[machine_code] = []
            machine_schedules[machine_code].append(result)
        
        # 检查每台机台的时间重叠
        has_overlap = False
        for machine_code, schedules in machine_schedules.items():
            # 按开始时间排序
            sorted_schedules = sorted(schedules, key=lambda x: x['scheduled_start_time'])
            
            # 检查相邻调度是否重叠
            for i in range(len(sorted_schedules) - 1):
                current = sorted_schedules[i]
                next_schedule = sorted_schedules[i + 1]
                
                if current['scheduled_end_time'] > next_schedule['scheduled_start_time']:
                    logger.error(f"机台 {machine_code} 存在时间重叠: "
                               f"{current['article_nr']} ({current['scheduled_end_time']}) "
                               f"与 {next_schedule['article_nr']} ({next_schedule['scheduled_start_time']})")
                    has_overlap = True
        
        if not has_overlap:
            logger.info("时间重叠验证通过：所有机台时间窗口无重叠")
        
        return not has_overlap
    
    def _find_available_time_slot_cross_day(
        self, 
        machine_code: str, 
        required_hours: float
    ) -> Optional[Dict]:
        """
        查找可用时间槽 - 支持跨日查找，优先选择利用率低的日期
        
        Args:
            machine_code: 机台代码
            required_hours: 所需时间
            
        Returns:
            可用时间槽信息
        """
        allocated_slots = self._allocated_slots.get(machine_code, [])
        
        # 获取该机台的所有时间窗口并按日期分组
        daily_windows = {}
        for window in self._get_original_time_windows(machine_code):
            window_date = window['start_time'].date()
            if window_date not in daily_windows:
                daily_windows[window_date] = []
            daily_windows[window_date].append({
                'start': window['start_time'],
                'end': window['end_time'],
                'duration': window['duration_hours']
            })
        
        # 计算每日当前利用率
        daily_usage = {}
        for date in daily_windows.keys():
            daily_usage[date] = 0.0
            
        for start_time, end_time, _ in allocated_slots:
            slot_date = start_time.date()
            if slot_date in daily_usage:
                slot_duration = (end_time - start_time).total_seconds() / 3600
                daily_usage[slot_date] += slot_duration
        
        # 按日期利用率排序，优先选择利用率低的日期
        sorted_dates = sorted(daily_usage.keys(), key=lambda d: daily_usage[d])
        
        logger.debug(f"机台 {machine_code} 日期利用率排序: {[(d, daily_usage[d]) for d in sorted_dates[:5]]}")
        
        # 在排序后的日期中查找可用时间槽
        for date in sorted_dates:
            windows_for_date = daily_windows[date]
            
            # 在该日期的所有时间窗口中查找
            for window in windows_for_date:
                available_slots = self._split_window_by_allocated_slots(
                    window, allocated_slots
                )
                
                for slot in available_slots:
                    if slot['duration'] >= required_hours:
                        # 更新每日利用率统计
                        if date not in self._daily_utilization:
                            self._daily_utilization[date] = {'total_hours': 0.0, 'schedules': 0}
                        
                        logger.debug(f"在日期 {date} 找到可用时间槽: {slot['start']} - {slot['start'] + timedelta(hours=required_hours)}")
                        
                        return {
                            'start': slot['start'],
                            'end': slot['start'] + timedelta(hours=required_hours),
                            'duration': required_hours,
                            'window_start': window['start'],
                            'window_end': window['end'],
                            'scheduled_date': date
                        }
        
        logger.debug(f"机台 {machine_code} 未找到 {required_hours:.2f} 小时的可用时间槽")
        return None
    
    def _schedule_large_product_with_splitting(
        self,
        plan: Any,
        available_machines: List[Tuple[str, Dict]],
        capacity_matrix: Dict[Tuple[str, str], Dict],
        machine_relations: Dict[str, Dict]
    ) -> Optional[List[Dict]]:
        """
        大批量产品超激进拆分调度 - 确保充分利用所有可用机台
        
        改进策略：
        1. 更激进的拆分：尝试使用更多机台
        2. 更小的单次分配量：允许更灵活的时间安排
        3. 更高的覆盖目标：力争90%以上的分配成功率
        
        Args:
            plan: 月度计划
            available_machines: 可用机台列表
            capacity_matrix: 产能矩阵
            machine_relations: 机台关系
            
        Returns:
            调度结果列表
        """
        article_nr = plan.article_nr
        target_quantity = plan.target_quantity_boxes
        
        logger.info(f"🚀 启动超激进拆分调度: {article_nr}, 目标 {target_quantity} 箱")
        
        # 获取时间参数
        time_params = getattr(self, '_time_params', {})
        daily_work_hours = time_params.get('daily_work_hours')
        if daily_work_hours is None:
            raise ValueError("每日工作时长未从数据库获取，不允许使用默认值")
        
        # **策略1：计算理想的机台分配数量，避免过度拆分**
        # 基于产品总量和可用机台确定分配策略，增加最小任务规模限制
        total_machines = len(available_machines)
        
        # 根本修复：大幅增加拆分数量，减小任务规模，提高成功率
        max_split_tasks = min(35, total_machines)  # 最多拆分成35个任务（所有机台）
        min_task_size = max(100, int(target_quantity / max_split_tasks))  # 最小任务规模100箱，更细粒度
        
        optimal_machines = min(total_machines, max(3, int(target_quantity / min_task_size)))
        
        logger.info(f"📊 拆分策略: 总量{target_quantity}箱, 最大拆分{max_split_tasks}个任务, 最小任务{min_task_size}箱, 计划使用{optimal_machines}台机台")
        
        logger.info(f"📊 产品分析: 总量{target_quantity}箱, 可用机台{total_machines}台, 计划使用{optimal_machines}台")
        
        # **策略2：按机台能力排序，优先使用高效机台**
        machines_by_efficiency = sorted(
            available_machines, 
            key=lambda x: x[1].get('actual_speed', 0) * x[1].get('available_hours', 0),
            reverse=True
        )
        
        split_results = []
        total_allocated = 0
        
        # **策略3：多轮分配，确保覆盖率**
        for round_num in range(3):  # 最多3轮分配
            if total_allocated >= target_quantity * 0.95:  # 95%覆盖率即可
                break
                
            logger.info(f"🔄 第{round_num + 1}轮分配，已分配: {total_allocated}/{target_quantity}")
            
            machines_used_this_round = 0
            for machine_code, capacity_info in machines_by_efficiency:
                if total_allocated >= target_quantity:
                    break
                
                # 限制单轮使用的机台数量
                if machines_used_this_round >= optimal_machines:
                    break
                
                # **策略4：计算该机台的合理分配量，确保任务规模合理**
                speed = capacity_info['actual_speed']
                remaining_quantity = target_quantity - total_allocated
                
                # 根本修复：充分利用班次时间，提高时间利用率
                shift_hours = daily_work_hours / 2  # 按班次分配，每班次约8-9小时
                
                # 策略1：尽量使用完整班次时间
                full_shift_allocation = int(speed * shift_hours)
                
                # 策略2：允许跨班次分配，最大化时间利用
                max_daily_allocation = int(speed * daily_work_hours * 0.9)  # 90%日利用率
                
                # 策略3：根据剩余量智能分配
                if remaining_quantity >= full_shift_allocation:
                    # 大批量：优先使用完整班次
                    target_allocation = full_shift_allocation
                elif remaining_quantity >= min_task_size:
                    # 中等批量：尽量分配剩余量
                    target_allocation = remaining_quantity
                else:
                    # 小批量：保持最小规模
                    target_allocation = min_task_size
                
                # 最终分配量：不超过机台日产能和剩余数量
                max_allocation = min(target_allocation, max_daily_allocation, remaining_quantity)
                
                logger.info(f"🔧 机台{machine_code}: 班次产能{full_shift_allocation}箱/班次, 目标分配{target_allocation}箱, 实际分配{max_allocation}箱")
                
                # 考虑剩余数量和机台负载平衡
                ideal_allocation = min(remaining_quantity, max_allocation, target_quantity // optimal_machines + 1000)
                
                if ideal_allocation < 100:  # 太小的分配量不值得
                    continue
                
                required_hours = ideal_allocation / speed
                
                # **策略5：确保不超过班次时间，灵活的时间槽查找**
                max_shift_hours = shift_hours * 1.1  # 允许10%超班次，最大化利用
                if required_hours > max_shift_hours:
                    # 如果超过班次时间，调整为班次上限
                    required_hours = max_shift_hours
                    ideal_allocation = int(speed * required_hours)
                    logger.info(f"⚠️ 机台{machine_code}: 时间超限，调整为{required_hours:.1f}小时，{ideal_allocation}箱")
                
                time_slot = self._find_available_time_slot_cross_day(machine_code, required_hours)
                
                if time_slot:
                    success = self._allocate_time_slot(
                        machine_code, time_slot['start'], time_slot['end'], article_nr
                    )
                    
                    if success:
                        # 创建拆分后的计划
                        split_plan = self._create_split_plan(plan, ideal_allocation)
                        
                        # 创建调度结果
                        result = self._create_scheduling_result(
                            split_plan, machine_code, time_slot, capacity_info, machine_relations
                        )
                        
                        split_results.append(result)
                        total_allocated += ideal_allocation
                        machines_used_this_round += 1
                        
                        logger.info(f"✅ 第{round_num + 1}轮-机台{machine_code}: {ideal_allocation}箱 ({required_hours:.1f}h)")
        
        # **策略6：评估分配结果**
        if total_allocated > 0:
            coverage_rate = total_allocated / target_quantity
            
            # 更新调度状态
            self._update_scheduling_state(article_nr, "MULTI_SPLIT", {})
            
            # 为每个结果添加详细的拆分信息
            for i, result in enumerate(split_results):
                result['split_info'] = {
                    'is_split_product': True,
                    'split_strategy': 'aggressive_multi_machine',
                    'split_index': i + 1,
                    'total_splits': len(split_results),
                    'split_total_allocated': total_allocated,
                    'split_target_quantity': target_quantity,
                    'split_coverage_rate': coverage_rate,
                    'machines_utilized': len(split_results)
                }
            
            if coverage_rate >= 0.9:
                logger.info(f"🎯 产品 {article_nr} 超激进拆分成功: 覆盖率{coverage_rate:.1%}, 使用{len(split_results)}台机台")
            else:
                logger.warning(f"⚠️ 产品 {article_nr} 拆分覆盖率偏低: {coverage_rate:.1%}, 已尽最大努力")
            
            return split_results
        else:
            logger.error(f"❌ 产品 {article_nr} 拆分完全失败")
            return None
    
    def _calculate_dynamic_time_parameters(
        self, 
        work_calendar: Dict[str, Any], 
        time_windows: Dict[str, List[Dict]],
        shift_configs: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算动态时间参数 - 优先从班次配置计算每日工时
        
        Args:
            work_calendar: 工作日历数据
            time_windows: 机台时间窗口
            shift_configs: 班次配置列表
            
        Returns:
            动态时间参数字典
        """
        # 从工作日历获取工作日数
        total_work_days = work_calendar.get('total_work_days', 0) if work_calendar else 0
        
        # **核心修正：从班次配置计算每日工作时长**
        daily_work_hours = 0.0
        if shift_configs:
            # 计算所有班次的总时长
            total_shift_hours = 0.0
            for shift in shift_configs:
                shift_duration = shift.get('duration_hours', 0.0)
                total_shift_hours += shift_duration
                logger.debug(f"班次 {shift.get('shift_name', '未知')}: {shift_duration:.2f}小时")
            
            daily_work_hours = total_shift_hours
            logger.info(f"📊 从班次配置计算每日工时: {len(shift_configs)}个班次, 总计{daily_work_hours:.2f}小时/天")
        
        # 如果班次配置无效，回退到时间窗口推算
        if daily_work_hours <= 0 and time_windows:
            # 取第一台机台的时间窗口作为样本
            sample_machine = next(iter(time_windows.keys()))
            sample_windows = time_windows[sample_machine]
            
            if sample_windows:
                # 计算单日的总工作时长
                sample_date = sample_windows[0]['start_time'].date()
                
                daily_hours = sum(
                    w['duration_hours'] for w in sample_windows
                    if w['start_time'].date() == sample_date
                )
                daily_work_hours = daily_hours
                logger.warning(f"从时间窗口推算每日工时: {daily_work_hours:.2f}小时")
        
        # 最后回退：从工作日历获取（不使用monthly_total_hours字段）
        if daily_work_hours <= 0 and work_calendar:
            work_days = work_calendar.get('work_days', [])
            if work_days:
                # 取第一个工作日的工作时长作为参考（但不使用monthly_total_hours）
                first_work_day = next((day for day in work_days if day['is_working']), None)
                if first_work_day and 'total_hours' in first_work_day:
                    daily_work_hours = first_work_day.get('total_hours', 0.0)
                    logger.warning(f"从工作日历获取每日工时: {daily_work_hours:.2f}小时")
        
        # 数据验证 - 不允许默认值
        if total_work_days <= 0:
            raise ValueError("工作日数未从数据库获取或无效，不允许使用默认值")
        if daily_work_hours <= 0:
            raise ValueError("每日工作时长未从班次配置获取或无效，不允许使用默认值")
        
        # **强制覆盖模式：基于正确的17.33小时/天计算产能**
        # 基础产能计算
        base_monthly_hours = total_work_days * daily_work_hours
        # 获取利用率系数从数据库，不使用硬编码
        base_utilization = 1  # 后续需要从配置表获取
        single_machine_base_hours = base_monthly_hours * base_utilization  # 基础利用率
        
        # 验证产能充足性：计算理论总产能vs实际需求
        # 35台机台 × 17.33小时/天 × 20天 × 平均速度
        theoretical_capacity = 35 * daily_work_hours * total_work_days  # 机台工时总量
        
        logger.info(f"📈 产能分析: 35台×{daily_work_hours:.2f}h×{total_work_days}天 = {theoretical_capacity:,.0f}机台小时")
        
        # 强制覆盖策略：确保100%排产
        # 策略1：提高设备利用率至100%
        # 策略2：启用所有35台机台的通用拆分、
        extended_utilization = 1  # 100%利用率 - 需要从数据库获取
        single_machine_extended_hours = base_monthly_hours * extended_utilization
        
        logger.info(f"🎯 强制覆盖模式: 单机可用{single_machine_extended_hours:.0f}h/月, 总产能{35*single_machine_extended_hours:,.0f}机台小时")
        
        return {
            'total_work_days': total_work_days,
            'daily_work_hours': daily_work_hours,
            'total_monthly_hours': base_monthly_hours,
            'single_machine_monthly_hours': single_machine_base_hours,
            'single_machine_extended_hours': single_machine_extended_hours,  # 100%利用率
            'theoretical_total_capacity': theoretical_capacity,
            'split_threshold_ratio': 0.20,  # 20%拆分阈值比例，避免过度拆分
            'large_product_threshold_hours': single_machine_base_hours * 0.20,  # 20%阈值，平衡拆分
            'force_coverage_mode': True,  # 强制覆盖模式标记
            'extended_utilization': extended_utilization,
            'max_machines_for_large_products': 20,  # 大产品最多使用20台机台
            'enable_aggressive_splitting': True,  # 启用激进拆分模式
        }
    
    def _preprocess_large_products(
        self, 
        monthly_plans: List[Any], 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_params: Dict[str, Any]
    ) -> Tuple[List[Any], List[Any]]:
        """
        预处理大批量产品，分离大批量和常规产品
        
        Args:
            monthly_plans: 月度计划列表
            capacity_matrix: 产能矩阵
            time_params: 动态时间参数
            
        Returns:
            (大批量产品列表, 常规产品列表)
        """
        large_products = []
        regular_products = []
        
        large_threshold = time_params['large_product_threshold_hours']
        logger.info(f"大批量产品阈值: {large_threshold:.1f} 小时")
        
        for plan in monthly_plans:
            article_nr = plan.article_nr
            target_quantity = plan.target_quantity_boxes
            
            # 计算该产品的最小所需时间
            min_required_hours = float('inf')
            available_machines = 0
            
            for (machine_code, product_code), capacity_info in capacity_matrix.items():
                if product_code == article_nr and capacity_info.get('can_complete', False):
                    required_hours = capacity_info.get('required_hours', 0)
                    min_required_hours = min(min_required_hours, required_hours)
                    available_machines += 1
            
            # 如果没有可用机台，放入常规处理
            if available_machines == 0:
                regular_products.append(plan)
                logger.warning(f"产品 {article_nr} 无可用机台，放入常规处理")
                continue
            
            # 判断是否为大批量产品
            if min_required_hours > large_threshold:
                large_products.append(plan)
                logger.info(f"大批量产品识别: {article_nr}, 需要 {min_required_hours:.1f} 小时, "
                           f"可用机台 {available_machines} 台")
            else:
                regular_products.append(plan)
        
        return large_products, regular_products
    
    def _schedule_large_products_first(
        self, 
        large_products: List[Any], 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict],
        time_params: Dict[str, Any]
    ) -> List[Dict]:
        """
        优先调度大批量产品 - 预留资源和强制拆分
        
        Args:
            large_products: 大批量产品列表
            capacity_matrix: 产能矩阵
            time_windows: 时间窗口
            machine_relations: 机台关系
            time_params: 动态时间参数
            
        Returns:
            大批量产品的调度结果列表
        """
        large_results = []
        
        # 按需求时间排序，最大的优先
        sorted_large = sorted(
            large_products, 
            key=lambda p: self._calculate_min_required_hours(p, capacity_matrix),
            reverse=True
        )
        
        for plan in sorted_large:
            article_nr = plan.article_nr
            target_quantity = plan.target_quantity_boxes
            
            logger.info(f"开始处理大批量产品: {article_nr}, 目标 {target_quantity} 箱")
            
            # 强制多机台并行拆分调度
            split_results = self._force_parallel_splitting(
                plan, capacity_matrix, time_windows, machine_relations, time_params
            )
            
            if split_results:
                large_results.extend(split_results)
                logger.info(f"✅ 大批量产品 {article_nr} 成功拆分到 {len(split_results)} 台机台")
            else:
                logger.error(f"❌ 大批量产品 {article_nr} 拆分失败")
        
        return large_results
    
    def _calculate_min_required_hours(self, plan: Any, capacity_matrix: Dict) -> float:
        """计算产品的最小所需时间"""
        article_nr = plan.article_nr
        min_hours = float('inf')
        
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if product_code == article_nr and capacity_info.get('can_complete', False):
                required_hours = capacity_info.get('required_hours', 0)
                min_hours = min(min_hours, required_hours)
        
        return min_hours if min_hours != float('inf') else 0
    
    def _force_parallel_splitting(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict],
        time_params: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """
        强制并行拆分大批量产品到多台机台
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            time_windows: 时间窗口
            machine_relations: 机台关系
            time_params: 动态时间参数
            
        Returns:
            拆分后的调度结果列表
        """
        article_nr = plan.article_nr
        target_quantity = plan.target_quantity_boxes
        
        # 获取所有可用机台
        available_machines = []
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if (product_code == article_nr and 
                capacity_info.get('can_complete', False) and 
                capacity_info.get('actual_speed', 0) > 0):
                available_machines.append((machine_code, capacity_info))
        
        if not available_machines:
            return None
        
        # 按速度排序（优先使用高速机台）
        available_machines.sort(key=lambda x: x[1]['actual_speed'], reverse=True)
        
        # 计算需要的机台数量
        single_machine_hours = time_params['single_machine_monthly_hours']
        estimated_total_hours = target_quantity / available_machines[0][1]['actual_speed']
        needed_machines = max(1, int(estimated_total_hours / single_machine_hours) + 1)
        
        logger.info(f"大批量产品 {article_nr}: 预计需要 {estimated_total_hours:.1f} 小时, "
                   f"计划使用 {needed_machines} 台机台")
        
        # 尝试分配到多台机台
        split_results = []
        remaining_quantity = target_quantity
        used_machines = 0
        
        for machine_code, capacity_info in available_machines:
            if remaining_quantity <= 0 or used_machines >= needed_machines:
                break
            
            # 为每台机台分配合理的数量
            machine_max_quantity = int(single_machine_hours * capacity_info['actual_speed'])
            allocatable_quantity = min(remaining_quantity, machine_max_quantity)
            
            if allocatable_quantity <= 0:
                continue
            
            # 计算所需时间
            required_hours = allocatable_quantity / capacity_info['actual_speed']
            
            # 查找可用时间槽（使用时间感知算法）
            time_slot = self._find_time_aware_slot(machine_code, required_hours, time_params)
            
            if time_slot:
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 创建拆分后的计划
                    split_plan = self._create_split_plan(plan, allocatable_quantity)
                    
                    # 确保time_slot有正确的字段结构
                    normalized_time_slot = {
                        'start': time_slot['start'],
                        'end': time_slot['end'], 
                        'duration': time_slot['duration']
                    }
                    
                    result = self._create_scheduling_result(
                        split_plan, machine_code, normalized_time_slot, capacity_info, machine_relations
                    )
                    
                    # 添加拆分信息
                    result['split_info'] = {
                        'is_split_product': True,
                        'split_index': len(split_results) + 1,
                        'total_splits': needed_machines,
                        'allocated_quantity': allocatable_quantity,
                        'split_strategy': 'large_product_parallel'
                    }
                    
                    split_results.append(result)
                    remaining_quantity -= allocatable_quantity
                    used_machines += 1
                    
                    logger.debug(f"分配 {allocatable_quantity} 箱到机台 {machine_code}, "
                               f"剩余 {remaining_quantity} 箱")
        
        # 检查分配成功率
        success_rate = (target_quantity - remaining_quantity) / target_quantity if target_quantity > 0 else 0
        
        if success_rate >= 0.8:  # 至少80%分配成功
            # 更新状态
            self._update_scheduling_state(article_nr, "LARGE_PRODUCT_SPLIT", {
                'split_count': len(split_results),
                'success_rate': success_rate
            })
            
            for result in split_results:
                time_slot = {
                    'start': result['scheduled_start_time'],
                    'end': result['scheduled_end_time'],
                    'duration': result['scheduled_duration_hours']
                }
                self._update_daily_utilization(time_slot)
            
            logger.info(f"大批量产品 {article_nr} 分配成功: {len(split_results)} 台机台, "
                       f"成功率 {success_rate:.1%}")
            return split_results
        else:
            # 回滚分配
            self._rollback_allocations(split_results)
            logger.error(f"大批量产品 {article_nr} 分配失败: 成功率仅 {success_rate:.1%}")
            return None
    
    def _find_time_aware_slot(
        self, 
        machine_code: str, 
        required_hours: float, 
        time_params: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        时间感知的时间槽查找 - 优先填充利用率低的时间段
        
        Args:
            machine_code: 机台代码
            required_hours: 所需时间
            time_params: 动态时间参数
            
        Returns:
            可用时间槽信息
        """
        # 获取该机台的所有时间窗口
        all_windows = self._get_original_time_windows(machine_code)
        if not all_windows:
            return None
        
        # 按日期分组时间窗口
        windows_by_date = {}
        for window in all_windows:
            date = window['start_time'].date()
            if date not in windows_by_date:
                windows_by_date[date] = []
            windows_by_date[date].append(window)
        
        # 计算每日当前利用率
        daily_utilization = {}
        allocated_slots = self._allocated_slots.get(machine_code, [])
        
        for date in windows_by_date:
            daily_utilization[date] = sum(
                (slot[1] - slot[0]).total_seconds() / 3600
                for slot in allocated_slots
                if slot[0].date() == date
            )
        
        # 按利用率排序日期（低利用率优先）
        sorted_dates = sorted(
            windows_by_date.keys(),
            key=lambda d: daily_utilization.get(d, 0)
        )
        
        # 在利用率最低的日期中查找时间槽
        for date in sorted_dates:
            windows = windows_by_date[date]
            
            # 合并当日的时间窗口
            merged_windows = self._merge_continuous_windows(windows)
            
            for window in merged_windows:
                available_slots = self._split_window_by_allocated_slots(
                    window, allocated_slots
                )
                
                for slot in available_slots:
                    if slot['duration'] >= required_hours:
                        end_time = slot['start'] + timedelta(hours=required_hours)
                        return {
                            'start': slot['start'],
                            'end': end_time,
                            'duration': required_hours,
                            'window_start': window['start'],
                            'window_end': window['end'],
                            'utilization_balanced': True,
                            'target_date': date,
                            'scheduled_start_time': slot['start'],
                            'scheduled_end_time': end_time,
                            'scheduled_duration_hours': required_hours
                        }
        
        # 如果时间感知查找失败，回退到原始方法
        return self._find_available_time_slot_cross_day(machine_code, required_hours)
    
    def _desperate_large_product_scheduling(
        self, 
        plan: Any, 
        capacity_matrix: Dict[Tuple[str, str], Dict], 
        time_windows: Dict[str, List[Dict]], 
        machine_relations: Dict[str, Dict],
        time_params: Dict[str, Any]
    ) -> Optional[List[Dict]]:
        """
        绝望模式：尽最大努力调度超大批量产品
        
        策略：
        1. 使用所有可用机台
        2. 尽可能多地分配数量
        3. 接受部分完成
        
        Args:
            plan: 月度计划
            capacity_matrix: 产能矩阵
            time_windows: 时间窗口
            machine_relations: 机台关系
            time_params: 动态时间参数
            
        Returns:
            拆分后的调度结果列表
        """
        article_nr = plan.article_nr
        target_quantity = plan.target_quantity_boxes
        
        logger.info(f"绝望模式调度大批量产品: {article_nr}, 目标 {target_quantity} 箱")
        
        # 获取所有可能的机台（放松can_complete约束）
        available_machines = []
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if (product_code == article_nr and 
                capacity_info.get('actual_speed', 0) > 0):
                available_machines.append((machine_code, capacity_info))
        
        if not available_machines:
            logger.error(f"绝望模式失败：产品 {article_nr} 完全没有可用机台")
            return None
        
        # 按速度排序
        available_machines.sort(key=lambda x: x[1]['actual_speed'], reverse=True)
        
        split_results = []
        remaining_quantity = target_quantity
        
        for machine_code, capacity_info in available_machines:
            if remaining_quantity <= 0:
                break
            
            # 计算该机台最大可处理数量
            total_available_hours = sum(
                w['duration_hours'] for w in self._get_original_time_windows(machine_code)
            )
            
            # 计算已占用时间
            allocated_slots = self._allocated_slots.get(machine_code, [])
            used_hours = sum(
                (slot[1] - slot[0]).total_seconds() / 3600 
                for slot in allocated_slots
            )
            
            available_hours = max(0, total_available_hours - used_hours)
            
            if available_hours < 1.0:  # 至少需要1小时
                continue
            
            # 计算可分配数量
            max_quantity = int(available_hours * capacity_info['actual_speed'])
            allocatable_quantity = min(remaining_quantity, max_quantity)
            
            if allocatable_quantity <= 0:
                continue
            
            # 计算所需时间
            required_hours = allocatable_quantity / capacity_info['actual_speed']
            
            # 查找可用时间槽
            time_slot = self._find_available_time_slot_cross_day(machine_code, required_hours)
            
            if time_slot:
                success = self._allocate_time_slot(
                    machine_code, time_slot['start'], time_slot['end'], article_nr
                )
                
                if success:
                    # 创建拆分后的计划
                    split_plan = self._create_split_plan(plan, allocatable_quantity)
                    
                    # 确保time_slot有正确的字段结构
                    normalized_time_slot = {
                        'start': time_slot['start'],
                        'end': time_slot['end'], 
                        'duration': time_slot['duration']
                    }
                    
                    result = self._create_scheduling_result(
                        split_plan, machine_code, normalized_time_slot, capacity_info, machine_relations
                    )
                    
                    # 添加绝望模式标记
                    result['split_info'] = {
                        'is_split_product': True,
                        'split_index': len(split_results) + 1,
                        'allocated_quantity': allocatable_quantity,
                        'split_strategy': 'desperate_large_product'
                    }
                    
                    split_results.append(result)
                    remaining_quantity -= allocatable_quantity
                    
                    logger.info(f"绝望模式分配: {allocatable_quantity} 箱到机台 {machine_code}, "
                               f"剩余 {remaining_quantity} 箱")
        
        # 即使只完成部分，也认为成功
        if split_results:
            allocated_quantity = target_quantity - remaining_quantity
            success_rate = allocated_quantity / target_quantity if target_quantity > 0 else 0
            
            logger.info(f"绝望模式完成: {article_nr}, 分配 {len(split_results)} 台机台, "
                       f"完成数量 {allocated_quantity}/{target_quantity} 箱 ({success_rate:.1%})")
            
            # 更新状态
            self._update_scheduling_state(article_nr, "DESPERATE_PARTIAL", {
                'split_count': len(split_results),
                'success_rate': success_rate,
                'allocated_quantity': allocated_quantity
            })
            
            for result in split_results:
                time_slot = {
                    'start': result['scheduled_start_time'],
                    'end': result['scheduled_end_time'],
                    'duration': result['scheduled_duration_hours']
                }
                self._update_daily_utilization(time_slot)
            
            return split_results
        else:
            logger.error(f"绝望模式失败：产品 {article_nr} 完全无法分配")
            return None
    
    def _universal_product_splitting(
        self,
        monthly_plans: List[Any],
        capacity_matrix: Dict[Tuple[str, str], Dict],
        time_params: Dict[str, Any]
    ) -> List[Any]:
        """
        **强制覆盖模式：通用产品拆分算法**
        
        策略：
        1. 所有产品强制拆分以充分利用35台机台
        2. 按产品规模智能分配机台数量
        3. 确保每台机台都有工作负载
        4. 实现100%产品覆盖
        
        Args:
            monthly_plans: 原始月度计划
            capacity_matrix: 产能矩阵
            time_params: 动态时间参数
            
        Returns:
            拆分后的工单列表
        """
        logger.info("🔄 启动通用产品拆分算法...")
        
        # 获取所有可用机台
        available_machines = set()
        for (machine_code, product_code), capacity_info in capacity_matrix.items():
            if capacity_info.get('actual_speed', 0) > 0:
                available_machines.add(machine_code)
        
        all_machines = sorted(list(available_machines))
        total_machines = len(all_machines)
        
        logger.info(f"可用机台: {total_machines}台 {all_machines[:5]}...")
        
        # 计算总需求和总产能
        total_demand = sum(plan.target_quantity_boxes for plan in monthly_plans)
        single_machine_hours = time_params.get('single_machine_extended_hours')
        if single_machine_hours is None:
            raise ValueError("single_machine_extended_hours未从时间参数获取，不允许使用默认值")
        
        # 按产品规模分类
        split_plans = []
        machine_index = 0  # 轮换分配机台
        
        for plan in monthly_plans:
            article_nr = plan.article_nr
            target_quantity = plan.target_quantity_boxes
            
            # 计算该产品需要的机台数（基于最快机台速度）
            fastest_speed = 0
            for (machine_code, product_code), capacity_info in capacity_matrix.items():
                if (product_code == article_nr or product_code == '*') and machine_code in all_machines:
                    speed = capacity_info.get('actual_speed', 0)
                    fastest_speed = max(fastest_speed, speed)
            
            if fastest_speed <= 0:
                # 从数据库获取默认速度，不使用硬编码
                logger.warning(f"产品 {article_nr} 未找到速度配置，跳过")
                continue
            
            # 计算需要的总时间和机台数
            total_required_hours = target_quantity / fastest_speed
            base_required_machines = max(1, min(total_machines, int(total_required_hours / single_machine_hours) + 1))
            
            # **更激进的拆分策略 - 充分利用35台机台**
            if target_quantity > 15000:
                # 超大产品：使用70%的机台（24-25台）
                required_machines = max(base_required_machines, min(25, int(total_machines * 0.7)))
            elif target_quantity > 8000:
                # 大产品：使用50%的机台（17-18台）
                required_machines = max(base_required_machines, min(18, int(total_machines * 0.5)))
            elif target_quantity > 3000:
                # 中产品：使用30%的机台（10-11台）
                required_machines = max(base_required_machines, min(11, int(total_machines * 0.3)))
            elif target_quantity > 1000:
                # 小产品：使用15%的机台（5-6台）
                required_machines = max(base_required_machines, min(6, int(total_machines * 0.15)))
            else:
                # 微小产品：至少使用2台机台以提高并行度
                required_machines = max(base_required_machines, 2)
            
            logger.info(f"产品 {article_nr}({target_quantity}箱): 需要{required_machines}台机台")
            
            # 拆分产品到多台机台
            for i in range(required_machines):
                # 轮换选择机台
                assigned_machine = all_machines[machine_index % total_machines]
                machine_index += 1
                
                # 计算分配数量（最后一台机台分配剩余）
                if i == required_machines - 1:
                    # 最后一份：分配剩余数量
                    split_quantity = target_quantity - (target_quantity // required_machines) * i
                else:
                    # 均匀分配
                    split_quantity = target_quantity // required_machines
                
                if split_quantity <= 0:
                    continue
                
                # 创建拆分工单
                split_plan = self._create_split_plan(plan, split_quantity)
                split_plan.assigned_machine_code = assigned_machine  # 预分配机台
                split_plan.split_info = {
                    'is_universal_split': True,
                    'original_quantity': target_quantity,
                    'split_index': i + 1,
                    'total_splits': required_machines,
                    'assigned_machine': assigned_machine
                }
                
                split_plans.append(split_plan)
                
                logger.debug(f"  拆分{i+1}/{required_machines}: {split_quantity}箱 → 机台{assigned_machine}")
        
        logger.info(f"✅ 通用拆分完成: {len(monthly_plans)}个产品 → {len(split_plans)}个工单")
        logger.info(f"平均每台机台: {len(split_plans)/total_machines:.1f}个工单")
        
        return split_plans