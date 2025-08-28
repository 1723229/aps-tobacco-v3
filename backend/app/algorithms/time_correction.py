"""
APS智慧排产系统 - 时间校正算法

实现轮保冲突检测和班次时间校正功能
解决设备维护时间冲突和跨班次调度问题
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
        
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行时间校正
        
        Args:
            input_data: 拆分后的工单数据
            maintenance_plans: 轮保计划列表 [{'machine_code': str, 'maint_start_time': datetime, 'maint_end_time': datetime}]
            shift_config: 班次配置 {'shifts': [{'start_time': str, 'end_time': str, 'name': str}]}
            
        Returns:
            AlgorithmResult: 校正结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        maintenance_plans = kwargs.get('maintenance_plans', [])
        shift_config = kwargs.get('shift_config', self._get_default_shift_config())
        
        corrected_orders = []
        
        for order in input_data:
            try:
                # 1. 轮保冲突检测和处理
                conflict_resolved_order = self._resolve_maintenance_conflict(
                    order, maintenance_plans
                )
                
                # 2. 班次时间校正
                shift_corrected_order = self._correct_shift_time(
                    conflict_resolved_order, shift_config
                )
                
                corrected_orders.append(shift_corrected_order)
                
            except Exception as e:
                logger.error(f"时间校正失败 - 工单 {order.get('work_order_nr')}: {str(e)}")
                result.add_error(f"工单时间校正失败: {str(e)}", {'order': order})
                # 即使校正失败，也保留原工单
                corrected_orders.append(order)
        
        result.output_data = corrected_orders
        
        # 计算校正统计
        corrected_count = sum(1 for order in corrected_orders if order.get('time_corrected', False))
        conflict_resolved_count = sum(1 for order in corrected_orders if order.get('maintenance_conflict_resolved', False))
        
        result.metrics.custom_metrics = {
            'time_corrected_count': corrected_count,
            'maintenance_conflicts_resolved': conflict_resolved_count,
            'correction_rate': corrected_count / len(input_data) if input_data else 0
        }
        
        logger.info(f"时间校正完成: {corrected_count}/{len(input_data)}个工单被校正")
        return self.finalize_result(result)
    
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
        shift_config = {'shifts': shift_configs_list} if shift_configs_list else self._get_default_shift_config()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'maintenance_plans_count': len(maintenance_plans),
            'shift_configs_count': len(shift_configs_list)
        }
        
        corrected_orders = []
        
        for order in input_data:
            try:
                # 1. 轮保冲突检测和处理
                conflict_resolved_order = self._resolve_maintenance_conflict(order, maintenance_plans)
                
                # 2. 班次时间校正
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
        
        result.metrics.custom_metrics.update({
            'time_corrected_count': corrected_count,
            'maintenance_conflicts_resolved': conflict_resolved_count,
            'correction_rate': corrected_count / len(input_data) if input_data else 0
        })
        
        logger.info(f"时间校正完成(真实数据): {corrected_count}/{len(input_data)}个工单被校正")
        return self.finalize_result(result)
    
    def _resolve_maintenance_conflict(
        self, 
        order: Dict[str, Any], 
        maintenance_plans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        解决轮保冲突
        
        检测工单时间是否与设备轮保时间冲突，如有冲突则调整时间
        """
        machine_code = order.get('maker_code')
        planned_start = order.get('planned_start')
        planned_end = order.get('planned_end')
        
        if not all([machine_code, planned_start, planned_end]):
            return order
        
        # 查找该机台的轮保计划
        machine_maintenances = [
            m for m in maintenance_plans 
            if m.get('machine_code') == machine_code
        ]
        
        if not machine_maintenances:
            return order  # 无轮保计划，直接返回
        
        conflicts = []
        for maintenance in machine_maintenances:
            maint_start = maintenance.get('maint_start_time')
            maint_end = maintenance.get('maint_end_time')
            
            if self._has_time_overlap(planned_start, planned_end, maint_start, maint_end):
                conflicts.append(maintenance)
        
        if not conflicts:
            return order  # 无冲突，直接返回
        
        # 解决冲突
        corrected_order = order.copy()
        corrected_order['maintenance_conflict_resolved'] = True
        corrected_order['original_planned_start'] = planned_start
        corrected_order['original_planned_end'] = planned_end
        corrected_order['conflicts_resolved'] = len(conflicts)
        
        # 冲突解决策略：延后到最近的轮保结束后
        latest_maint_end = max(c['maint_end_time'] for c in conflicts)
        
        # 计算原计划持续时间
        original_duration = planned_end - planned_start
        
        # 调整时间：轮保结束后立即开始
        new_start = latest_maint_end
        new_end = new_start + original_duration
        
        corrected_order['planned_start'] = new_start
        corrected_order['planned_end'] = new_end
        corrected_order['time_corrected'] = True
        corrected_order['correction_reason'] = f"轮保冲突解决，延后到{latest_maint_end.strftime('%Y-%m-%d %H:%M')}"
        
        logger.info(
            f"解决轮保冲突 - 工单 {order['work_order_nr']} "
            f"从 {planned_start.strftime('%H:%M')}-{planned_end.strftime('%H:%M')} "
            f"调整到 {new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')}"
        )
        
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
        
        # 重新计算结束时间，确保不跨班次
        new_start = corrected_order.get('planned_start', planned_start)
        original_duration = planned_end - planned_start
        tentative_end = new_start + original_duration
        
        # 检查是否跨班次
        current_shift = self._get_shift_for_time(new_start, shifts)
        if current_shift:
            shift_end = self._get_shift_end_datetime(new_start, current_shift)
            
            if tentative_end > shift_end:
                # 跨班次，截断到班次结束
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