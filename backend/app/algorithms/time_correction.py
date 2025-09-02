"""
APS智慧排产系统 - 时间校正算法（算法细则增强版）

实现综合时间校正功能：
1. 机台轮保时间检测和调整（aps_maintenance_plan表）
2. 班次时间校正（aps_shift_config表）
3. 机台速度差异计算（aps_machine_speed表）
4. 避免非工作时间排产
5. 处理跨班次、跨天的工单

算法细则要求：
- 不同卷包机台加工不同成品烟时的速度差异
- 卷包机台的工作日历（开机班次、停机时间、轮保时间等）
- 卷包机台轮保时间有MES提供
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class TimeCorrection(AlgorithmBase):
    """时间校正算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.TIME_CORRECTION)
        
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行时间校正 - 按照算法细则增强版
        
        按照算法细则执行：
        1. 机台速度差异重新计算工期
        2. 轮保冲突检测和处理
        3. 班次时间校正和工作日历检查
        4. 避免非工作时间排产
        
        Args:
            input_data: 拆分后的工单数据
            maintenance_plans: 轮保计划列表（可选，从数据库查询）
            shift_config: 班次配置（可选，从数据库查询）
            machine_speeds: 机台速度配置（可选，从数据库查询）
            
        Returns:
            AlgorithmResult: 校正结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        logger.info(f"⏰ 开始时间校正，处理{len(input_data)}个工单")
        
        # 获取配置数据（优先使用传入参数，否则使用默认值）
        maintenance_plans = kwargs.get('maintenance_plans', [])
        shift_config = kwargs.get('shift_config', self._get_default_shift_config())
        machine_speeds = kwargs.get('machine_speeds', {})
        
        corrected_orders = []
        correction_stats = {
            'speed_adjusted': 0,
            'maintenance_adjusted': 0,
            'shift_adjusted': 0,
            'total_adjustments': 0
        }
        
        for order in input_data:
            try:
                # 1. 机台速度差异校正（根据算法细则要求）
                speed_corrected_order = self._correct_machine_speed(
                    order, machine_speeds
                )
                if speed_corrected_order.get('speed_adjusted'):
                    correction_stats['speed_adjusted'] += 1
                
                # 2. 轮保冲突检测和处理
                conflict_resolved_order = self._resolve_maintenance_conflict(
                    speed_corrected_order, maintenance_plans
                )
                if conflict_resolved_order.get('maintenance_adjusted'):
                    correction_stats['maintenance_adjusted'] += 1
                
                # 3. 班次时间校正和工作日历检查
                shift_corrected_order = self._correct_shift_time(
                    conflict_resolved_order, shift_config
                )
                if shift_corrected_order.get('shift_adjusted'):
                    correction_stats['shift_adjusted'] += 1
                
                # 记录最终调整标记
                if (speed_corrected_order.get('speed_adjusted') or 
                    conflict_resolved_order.get('maintenance_adjusted') or 
                    shift_corrected_order.get('shift_adjusted')):
                    correction_stats['total_adjustments'] += 1
                    shift_corrected_order['time_corrected'] = True
                    shift_corrected_order['correction_timestamp'] = datetime.now()
                
                corrected_orders.append(shift_corrected_order)
                
            except Exception as e:
                logger.error(f"时间校正失败: {order.get('work_order_nr', 'UNKNOWN')} - {str(e)}")
                result.errors.append(f"工单{order.get('work_order_nr', 'UNKNOWN')}时间校正失败: {str(e)}")
                # 即使校正失败，也保留原工单
                order['time_correction_failed'] = True
                order['correction_error'] = str(e)
                corrected_orders.append(order)
        
        result.output_data = corrected_orders
        result.metrics.custom_metrics = correction_stats
        
        logger.info(f"✅ 时间校正完成:")
        logger.info(f"   🏃 速度调整: {correction_stats['speed_adjusted']}个工单")
        logger.info(f"   🔧 轮保调整: {correction_stats['maintenance_adjusted']}个工单")
        logger.info(f"   ⏰ 班次调整: {correction_stats['shift_adjusted']}个工单")
        logger.info(f"   📊 总调整: {correction_stats['total_adjustments']}/{len(input_data)}个工单")
        
        return self.finalize_result(result)
    
    def _correct_machine_speed(self, order: Dict[str, Any], machine_speeds: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据机台速度差异重新计算工期
        
        算法细则要求：不同卷包机台加工不同成品烟时的速度差异
        
        Args:
            order: 工单数据
            machine_speeds: 机台速度配置 {machine_code: {article_nr: speed_per_hour}}
            
        Returns:
            Dict: 速度校正后的工单
        """
        corrected_order = order.copy()
        
        machine_code = order.get('maker_code') or order.get('feeder_code')
        article_nr = order.get('article_nr', '')
        quantity = order.get('final_quantity', 0)
        
        if not machine_code or not article_nr or not quantity:
            return corrected_order
        
        # 查找机台速度配置
        machine_speed_config = machine_speeds.get(machine_code, {})
        speed_per_hour = machine_speed_config.get(article_nr)
        
        if speed_per_hour and speed_per_hour > 0:
            # 重新计算工期
            required_hours = quantity / speed_per_hour
            
            planned_start = order.get('planned_start')
            if isinstance(planned_start, str):
                planned_start = datetime.fromisoformat(planned_start.replace('Z', '+00:00'))
            
            if planned_start:
                # 计算新的结束时间
                new_planned_end = planned_start + timedelta(hours=required_hours)
                original_end = order.get('planned_end')
                
                if isinstance(original_end, str):
                    original_end = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
                
                # 如果时间有显著差异，进行调整
                if original_end:
                    time_diff_hours = abs((new_planned_end - original_end).total_seconds() / 3600)
                    
                    if time_diff_hours > 0.5:  # 超过30分钟差异才调整
                        corrected_order['planned_end'] = new_planned_end
                        corrected_order['speed_adjusted'] = True
                        corrected_order['original_planned_end'] = original_end
                        corrected_order['speed_adjustment_hours'] = (new_planned_end - original_end).total_seconds() / 3600
                        corrected_order['used_speed_per_hour'] = speed_per_hour
                        corrected_order['calculated_hours'] = required_hours
                        
                        logger.info(f"   🏃 速度调整: {order.get('work_order_nr')} 机台{machine_code}")
                        logger.info(f"      📦 产品: {article_nr}")
                        logger.info(f"      🚄 速度: {speed_per_hour}箱/小时")
                        logger.info(f"      📊 数量: {quantity}箱 -> 预计{required_hours:.1f}小时")
                        logger.info(f"      📅 调整: {original_end.strftime('%H:%M')} -> {new_planned_end.strftime('%H:%M')}")
        
        return corrected_order
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行时间校正
        
        Args:
            input_data: 拆分后的工单数据
            
        Returns:
            AlgorithmResult: 校正结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 从数据库查询真实的轮保计划和班次配置
        machine_codes = list(set(order.get('maker_code') for order in input_data if order.get('maker_code')))
        
        # 查询轮保计划
        maintenance_plans = await DatabaseQueryService.get_maintenance_plans(machine_codes=machine_codes)
        
        # 查询班次配置 
        shift_configs_list = await DatabaseQueryService.get_shift_config()
        # 查询机台速度配置
        machine_speeds = await DatabaseQueryService.get_machine_speeds()
        
        shift_config = {'shifts': shift_configs_list} if shift_configs_list else self._get_default_shift_config()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'maintenance_plans_count': len(maintenance_plans),
            'shift_configs_count': len(shift_configs_list),
            'machine_speeds_count': len(machine_speeds)
        }
        
        corrected_orders = []
        
        for order in input_data:
            try:
                # 1. 基于机台速度重新计算生产时间
                speed_corrected_order = self._recalculate_production_time_with_speed(order, machine_speeds)
                
                # 2. 轮保冲突检测和处理
                conflict_resolved_order = self._resolve_maintenance_conflict(speed_corrected_order, maintenance_plans)
                
                # 3. 班次时间校正
                shift_corrected_order = self._correct_shift_time(conflict_resolved_order, shift_config)
                
                corrected_orders.append(shift_corrected_order)
                
            except Exception as e:
                logger.error(f"时间校正失败 - 工单 {order.get('work_order_nr')}: {str(e)}")
                result.add_error(f"工单时间校正失败: {str(e)}", {'order': order})
                corrected_orders.append(order)
        
        result.output_data = corrected_orders
        
        # 计算校正统计
        corrected_count = sum(1 for order in corrected_orders if order.get('time_corrected', False))
        conflict_resolved_count = sum(1 for order in corrected_orders if order.get('maintenance_conflict_resolved', False))
        speed_recalculated_count = sum(1 for order in corrected_orders if order.get('time_recalculated', False))
        
        result.metrics.custom_metrics.update({
            'time_corrected_count': corrected_count,
            'maintenance_conflicts_resolved': conflict_resolved_count,
            'speed_recalculated_count': speed_recalculated_count,
            'correction_rate': corrected_count / len(input_data) if input_data else 0,
            'speed_recalculation_rate': speed_recalculated_count / len(input_data) if input_data else 0
        })
        
        logger.info(f"时间校正完成(真实数据): {corrected_count}/{len(input_data)}个工单被校正")
        return self.finalize_result(result)
    
    def _recalculate_production_time_with_speed(
        self, 
        order: Dict[str, Any], 
        machine_speeds: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基于机台速度配置重新计算生产时间
        
        Args:
            order: 工单数据
            machine_speeds: 机台速度配置
            
        Returns:
            Dict[str, Any]: 时间计算后的工单
        """
        maker_code = order.get('maker_code')
        article_nr = order.get('article_nr', '')
        final_quantity = order.get('final_quantity', 0)
        planned_start = order.get('planned_start')
        
        # 如果没有相关信息，返回原工单
        if not all([maker_code, final_quantity, planned_start]):
            return order
        
        # 查找机台速度配置
        speed_config = None
        if maker_code in machine_speeds:
            speed_config = machine_speeds[maker_code]
        elif '*' in machine_speeds:
            # 使用默认配置
            speed_config = machine_speeds['*']
            logger.info(f"机台{maker_code}使用默认速度配置")
        else:
            logger.warning(f"机台{maker_code}的速度配置未找到（包括默认配置），使用原时间")
            return order
        
        # 获取针对性速度或默认速度
        if article_nr in speed_config.get('product_speeds', {}):
            product_speed = speed_config['product_speeds'][article_nr]
            hourly_capacity = product_speed['hourly_capacity']
            efficiency_rate = product_speed['efficiency_rate']
            logger.info(f"使用产品针对性速度: {maker_code}-{article_nr} = {hourly_capacity}箱/小时")
        else:
            hourly_capacity = speed_config.get('hourly_capacity', 100)
            efficiency_rate = speed_config.get('efficiency_rate', 1)
            logger.info(f"使用机台默认速度: {maker_code} = {hourly_capacity}箱/小时")
        
        # 计算实际生产时间（考虑效率）
        # 确保效率系数为小数（如果>1则转换为百分比）
        if efficiency_rate > 1:
            efficiency_rate = efficiency_rate / 100.0
        effective_capacity = hourly_capacity * efficiency_rate
        
        if effective_capacity <= 0:
            logger.warning(f"机台{maker_code}的有效产能为0，使用原时间")
            return order
        
        # 计算理论生产时间（小时）
        production_hours = final_quantity / effective_capacity
        
        # 转换为时间差
        production_duration = timedelta(hours=production_hours)
        
        # 加上设备准备时间
        setup_minutes = speed_config.get('setup_time_minutes', 30)
        changeover_minutes = speed_config.get('changeover_time_minutes', 15)
        total_setup_time = timedelta(minutes=setup_minutes + changeover_minutes)
        
        # 计算新的结束时间
        calculated_end = planned_start + production_duration + total_setup_time
        
        # 创建新的工单对象
        speed_corrected_order = order.copy()
        
        # 保存原始时间信息
        speed_corrected_order['original_planned_end'] = order.get('planned_end')
        speed_corrected_order['calculated_planned_end'] = calculated_end
        
        # 检查时间是否需要调整
        original_end = order.get('planned_end')
        if original_end and abs((calculated_end - original_end).total_seconds()) > 1800:  # 30分钟误差
            speed_corrected_order['planned_end'] = calculated_end
            speed_corrected_order['time_recalculated'] = True
            speed_corrected_order['recalculation_reason'] = f"基于机台速度重新计算: {effective_capacity:.1f}箱/小时"
            speed_corrected_order['production_hours'] = round(production_hours, 2)
            speed_corrected_order['effective_capacity'] = effective_capacity
            
            logger.info(
                f"时间重新计算 - 工单{order.get('work_order_nr')} "
                f"(数量: {final_quantity}箱, 速度: {effective_capacity:.1f}箱/小时) "
                f"结束时间: {original_end} -> {calculated_end}"
            )
        else:
            speed_corrected_order['time_recalculated'] = False
            speed_corrected_order['time_calculation_accurate'] = True
        
        return speed_corrected_order
    
    def _resolve_maintenance_conflict(
        self, 
        order: Dict[str, Any], 
        maintenance_plans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        解决轮保冲突 - 按照算法细则增强版
        
        算法细则要求：
        - 卷包机台轮保时间有MES提供
        - 卷包机1对卷包机2结束阶段为轮保时的处理
        - 可以认为3个卷包机台的开始时间为卷包机3的开始时间，给1，3调整后的时间
        
        Args:
            order: 工单数据
            maintenance_plans: 轮保计划列表
            
        Returns:
            Dict: 轮保冲突解决后的工单
        """
        corrected_order = order.copy()
        
        machine_code = order.get('maker_code') or order.get('feeder_code')
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        
        if not machine_code or not planned_start or not planned_end:
            return corrected_order
        
        # 时间格式标准化
        if isinstance(planned_start, str):
            planned_start = datetime.fromisoformat(planned_start.replace('Z', '+00:00'))
        if isinstance(planned_end, str):
            planned_end = datetime.fromisoformat(planned_end.replace('Z', '+00:00'))
        
        # 查找该机台的轮保计划
        machine_maintenances = [
            m for m in maintenance_plans 
            if m.get('machine_code') == machine_code
        ]
        
        if not machine_maintenances:
            return corrected_order  # 无轮保计划，直接返回
        
        logger.info(f"   🔧 检查机台{machine_code}轮保冲突，共{len(machine_maintenances)}个轮保计划")
        
        conflicts = []
        for maintenance in machine_maintenances:
            maint_start = maintenance.get('maint_start_time')
            maint_end = maintenance.get('maint_end_time')
            
            # 时间格式标准化
            if isinstance(maint_start, str):
                maint_start = datetime.fromisoformat(maint_start.replace('Z', '+00:00'))
            if isinstance(maint_end, str):
                maint_end = datetime.fromisoformat(maint_end.replace('Z', '+00:00'))
            
            if self._has_time_overlap(planned_start, planned_end, maint_start, maint_end):
                conflicts.append({
                    'maintenance': maintenance,
                    'maint_start': maint_start,
                    'maint_end': maint_end
                })
        
        if not conflicts:
            return corrected_order  # 无冲突，直接返回
        
        # 解决冲突 - 按照算法细则策略
        logger.info(f"      ⚠️ 发现{len(conflicts)}个轮保冲突，开始解决")
        
        # 策略1：如果工单在轮保期间，延后到轮保结束
        # 策略2：如果轮保期间较短，可以考虑提前完成
        
        adjustment_made = False
        original_start = planned_start
        original_end = planned_end
        
        for conflict in conflicts:
            maint_start = conflict['maint_start']
            maint_end = conflict['maint_end']
            maint_type = conflict['maintenance'].get('maintenance_type', 'routine')
            
            logger.info(f"         📅 轮保冲突: {maint_start.strftime('%m-%d %H:%M')} - {maint_end.strftime('%m-%d %H:%M')} ({maint_type})")
            
            # 计算工单持续时间
            work_duration = planned_end - planned_start
            
            # 策略选择：根据轮保类型和时间情况
            if maint_type in ['major', 'overhaul']:
                # 重大轮保，必须避开，延后到轮保结束
                new_start = maint_end
                new_end = new_start + work_duration
                
                logger.info(f"         🔧 重大轮保延后: {planned_start.strftime('%m-%d %H:%M')} -> {new_start.strftime('%m-%d %H:%M')}")
                
            elif planned_start < maint_start and planned_end > maint_start:
                # 工单开始于轮保前但延续到轮保期间，尝试提前完成
                if (maint_start - planned_start) >= timedelta(hours=2):  # 至少2小时工作时间
                    new_start = planned_start
                    new_end = maint_start
                    
                    logger.info(f"         ⏰ 提前完成避开轮保: 结束时间 {planned_end.strftime('%H:%M')} -> {new_end.strftime('%H:%M')}")
                else:
                    # 时间不足，延后到轮保结束
                    new_start = maint_end
                    new_end = new_start + work_duration
                    
                    logger.info(f"         🔧 时间不足，延后到轮保结束: {planned_start.strftime('%m-%d %H:%M')} -> {new_start.strftime('%m-%d %H:%M')}")
                    
            else:
                # 其他情况，延后到轮保结束
                new_start = maint_end
                new_end = new_start + work_duration
                
                logger.info(f"         🔧 延后到轮保结束: {planned_start.strftime('%m-%d %H:%M')} -> {new_start.strftime('%m-%d %H:%M')}")
            
            # 更新计划时间
            planned_start = new_start
            planned_end = new_end
            adjustment_made = True
        
        if adjustment_made:
            corrected_order['planned_start'] = planned_start
            corrected_order['planned_end'] = planned_end
            corrected_order['maintenance_adjusted'] = True
            corrected_order['original_maintenance_start'] = original_start
            corrected_order['original_maintenance_end'] = original_end
            corrected_order['maintenance_conflicts_resolved'] = len(conflicts)
            corrected_order['maintenance_adjustment_hours'] = (planned_start - original_start).total_seconds() / 3600
            
            logger.info(f"      ✅ 轮保冲突解决完成，调整{corrected_order['maintenance_adjustment_hours']:.1f}小时")
        
        return corrected_order
    
    def _correct_shift_time(
        self, 
        order: Dict[str, Any], 
        shift_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        班次时间校正
        
        确保工单时间符合班次规定，处理跨班次问题
        """
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        
        if not all([planned_start, planned_end]):
            return order
        
        shifts = shift_config.get('shifts', [])
        if not shifts:
            return order
        
        # 检查是否需要班次校正
        start_shift = self._get_shift_for_time(planned_start, shifts)
        end_shift = self._get_shift_for_time(planned_end, shifts)
        
        # 如果开始和结束在同一班次内，且时间合理，无需校正
        if (start_shift and end_shift and 
            start_shift['name'] == end_shift['name'] and
            not self._is_cross_shift(planned_start, planned_end, start_shift)):
            return order
        
        # 需要校正
        corrected_order = order.copy()
        
        if not start_shift:
            # 开始时间不在班次内，调整到最近班次开始
            nearest_shift = self._get_nearest_shift(planned_start, shifts)
            if nearest_shift:
                corrected_start = self._get_shift_start_datetime(planned_start, nearest_shift)
                corrected_order['planned_start'] = corrected_start
                corrected_order['shift_corrected'] = True
                corrected_order['time_corrected'] = True
        
        # 重新计算结束时间，使用校正后的时间
        new_start = corrected_order.get('planned_start', planned_start)
        
        # 使用校正后的结束时间，而不是原始时间
        corrected_end = corrected_order.get('planned_end', planned_end)
        tentative_end = corrected_end if isinstance(corrected_end, datetime) else planned_end
        
        # 检查是否跨班次
        current_shift = self._get_shift_for_time(new_start, shifts)
        if current_shift:
            shift_end = self._get_shift_end_datetime(new_start, current_shift)
            
            if tentative_end > shift_end:
                # 检查是否为长时间生产工单（超过24小时）
                duration_hours = (tentative_end - new_start).total_seconds() / 3600
                
                logger.info(
                    f"班次时间校正 - 工单 {order['work_order_nr']} "
                    f"时长: {duration_hours:.1f}小时, 从 {new_start} 到 {tentative_end}"
                )
                
                if duration_hours > 24:
                    # 长时间工单，允许跨班次生产，不截断
                    corrected_order['planned_end'] = tentative_end
                    corrected_order['cross_shift_allowed'] = True
                    corrected_order['production_duration_hours'] = duration_hours
                    
                    logger.info(
                        f"班次时间校正 - 工单 {order['work_order_nr']} "
                        f"长时间生产({duration_hours:.1f}小时)，允许跨班次执行"
                    )
                else:
                    # 短时间工单，截断到班次结束
                    corrected_order['planned_end'] = shift_end
                    corrected_order['shift_corrected'] = True
                    corrected_order['time_corrected'] = True
                    corrected_order['duration_adjusted'] = True
                    corrected_order['correction_reason'] = f"班次时间校正，限制在{current_shift['name']}班次内"
                    
                    logger.info(
                        f"班次时间校正 - 工单 {order['work_order_nr']} "
                        f"结束时间从 {tentative_end.strftime('%H:%M')} "
                        f"调整到 {shift_end.strftime('%H:%M')}"
                    )
            else:
                corrected_order['planned_end'] = tentative_end
        
        return corrected_order
    
    def _has_time_overlap(
        self, 
        start1: datetime, end1: datetime, 
        start2: datetime, end2: datetime
    ) -> bool:
        """检查两个时间段是否重叠"""
        return start1 < end2 and start2 < end1
    
    def _get_shift_for_time(
        self, 
        time: datetime, 
        shifts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取时间所属的班次"""
        time_str = time.strftime('%H:%M')
        
        # 优先匹配开始时间，避免边界时间冲突
        for shift in shifts:
            start_time = shift.get('start_time')
            if start_time == time_str:
                return shift
        
        # 再匹配时间范围
        for shift in shifts:
            start_time = shift.get('start_time')
            end_time = shift.get('end_time')
            
            if self._time_in_range(time_str, start_time, end_time):
                return shift
        
        return None
    
    def _time_in_range(self, time_str: str, start_time: str, end_time: str) -> bool:
        """检查时间是否在范围内"""
        if start_time <= end_time:
            # 同一天内的班次
            return start_time <= time_str <= end_time
        else:
            # 跨天的班次（如夜班 22:00-06:00）
            return time_str >= start_time or time_str <= end_time
    
    def _is_cross_shift(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        shift: Dict[str, Any]
    ) -> bool:
        """检查时间段是否跨越班次边界"""
        shift_end = self._get_shift_end_datetime(start_time, shift)
        return end_time > shift_end
    
    def _get_nearest_shift(
        self, 
        time: datetime, 
        shifts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取最近的班次"""
        if not shifts:
            return None
        
        # 简化实现：返回第一个班次
        return shifts[0]
    
    def _get_shift_start_datetime(self, ref_date: datetime, shift: Dict[str, Any]) -> datetime:
        """获取班次开始时间的完整datetime"""
        start_time_str = shift.get('start_time', '08:00')
        hour, minute = map(int, start_time_str.split(':'))
        
        return ref_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    def _get_shift_end_datetime(self, ref_date: datetime, shift: Dict[str, Any]) -> datetime:
        """获取班次结束时间的完整datetime"""
        end_time_str = shift.get('end_time', '16:00')
        
        # 处理24:00这样的特殊时间格式
        if end_time_str == '24:00':
            hour, minute = 0, 0
            end_date = ref_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            end_date += timedelta(days=1)  # 24:00表示第二天的0:00
        else:
            hour, minute = map(int, end_time_str.split(':'))
            end_date = ref_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 处理跨天的班次
        start_time_str = shift.get('start_time', '08:00')
        if end_time_str != '24:00' and end_time_str <= start_time_str:
            end_date += timedelta(days=1)
        
        return end_date
    
    def _get_default_shift_config(self) -> Dict[str, Any]:
        """获取默认班次配置"""
        return {
            'shifts': [
                {'name': '白班', 'start_time': '08:00', 'end_time': '16:00'},
                {'name': '夜班', 'start_time': '16:00', 'end_time': '00:00'},
                {'name': '早班', 'start_time': '00:00', 'end_time': '08:00'}
            ]
        }


def create_time_correction() -> TimeCorrection:
    """
    创建时间校正算法实例
    
    Returns:
        TimeCorrection: 时间校正算法实例
    """
    return TimeCorrection()


def correct_work_order_times(
    work_orders: List[Dict[str, Any]],
    maintenance_plans: List[Dict[str, Any]] = None,
    shift_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    快速校正工单时间
    
    Args:
        work_orders: 工单列表
        maintenance_plans: 轮保计划
        shift_config: 班次配置
        
    Returns:
        List[Dict]: 校正后的工单列表
    """
    correction = create_time_correction()
    
    kwargs = {}
    if maintenance_plans:
        kwargs['maintenance_plans'] = maintenance_plans
    if shift_config:
        kwargs['shift_config'] = shift_config
    
    result = correction.process(work_orders, **kwargs)
    return result.output_data