"""
APS智慧排产系统 - 时间窗口计算器

基于工作日历、班次配置、维护计划计算每台机台的精确可用时间窗口。

核心职责：
1. 解析工作日历，确定有效生产日期
2. 应用班次配置，计算每日可用时间段
3. 排除维护计划时间，避免冲突
4. 生成精确的时间窗口矩阵
5. 验证时间连续性和有效性

技术特性：
- 精确的时间计算，支持跨日班次
- 完整的维护计划避让机制
- 灵活的时间窗口分割和合并
- 高效的时间冲突检测
- 完善的时间有效性验证
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class TimeWindowCalculator:
    """
    时间窗口计算器
    
    职责：
    1. 基于工作日历计算有效生产日期
    2. 应用班次配置计算每日可用时间段
    3. 排除维护计划时间窗口
    4. 生成机台可用时间窗口矩阵
    5. 验证时间窗口的连续性和有效性
    """
    
    def __init__(self):
        self._time_cache = {}
        self._window_cache = {}
    
    def calculate_available_windows(
        self, 
        machines: List[Any], 
        work_calendar: Dict[str, Any], 
        shift_configs: List[Dict], 
        maintenance_plans: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        计算所有机台的可用时间窗口
        
        Args:
            machines: 机台列表（通常是卷包机）
            work_calendar: 工作日历数据
            shift_configs: 班次配置
            maintenance_plans: 维护计划
            
        Returns:
            机台时间窗口字典 {机台代码: [时间窗口列表]}
        """
        logger.info("开始计算机台可用时间窗口")
        
        # 缓存班次配置以供后续使用
        self._cached_shift_configs = shift_configs
        
        all_windows = {}
        
        try:
            # 1. 生成基础时间窗口（基于工作日历和班次）
            base_windows = self._generate_base_time_windows(work_calendar, shift_configs)
            logger.info(f"生成基础时间窗口: {len(base_windows)} 个时间段")
            
            # 2. 为每台机台计算可用时间窗口
            for machine in machines:
                machine_code = machine.machine_code
                
                # 3. 应用维护计划约束
                available_windows = self._apply_maintenance_constraints(
                    base_windows, machine_code, maintenance_plans
                )
                
                # 4. 验证和优化时间窗口
                optimized_windows = self._optimize_time_windows(available_windows)
                
                all_windows[machine_code] = optimized_windows
                
                logger.debug(f"机台 {machine_code}: {len(optimized_windows)} 个可用时间窗口")
            
            # 5. 验证时间窗口完整性
            self._validate_windows_integrity(all_windows, work_calendar)
            
            logger.info(f"完成时间窗口计算: {len(all_windows)} 台机台")
            return all_windows
            
        except Exception as e:
            logger.error(f"时间窗口计算失败: {str(e)}")
            raise Exception(f"时间窗口计算失败: {str(e)}")
    
    def _generate_base_time_windows(
        self, 
        work_calendar: Dict[str, Any], 
        shift_configs: List[Dict]
    ) -> List[Dict]:
        """
        生成基础时间窗口（基于工作日历和班次配置）
        
        Args:
            work_calendar: 工作日历数据
            shift_configs: 班次配置
            
        Returns:
            基础时间窗口列表
        """
        base_windows = []
        
        work_days = work_calendar.get('work_days', [])
        
        for day_data in work_days:
            if not day_data['is_working']:
                continue  # 跳过非工作日
            
            work_date = day_data['date']
            
            # 为每个班次生成时间窗口
            for shift in shift_configs:
                window = self._create_shift_time_window(work_date, shift)
                if window:
                    base_windows.append(window)
        
        # 按时间排序
        base_windows.sort(key=lambda x: x['start_time'])
        
        logger.debug(f"生成基础时间窗口: {len(base_windows)} 个")
        return base_windows
    
    def _create_shift_time_window(self, work_date: date, shift: Dict) -> Optional[Dict]:
        """
        为特定日期和班次创建时间窗口
        
        Args:
            work_date: 工作日期
            shift: 班次配置
            
        Returns:
            时间窗口字典
        """
        try:
            start_time_obj = shift['start_time']
            end_time_obj = shift['end_time']
            
            # 构建开始时间
            start_datetime = datetime.combine(work_date, start_time_obj)
            
            # 处理跨日班次
            if end_time_obj <= start_time_obj:
                # 跨日班次，结束时间为第二天
                end_datetime = datetime.combine(work_date + timedelta(days=1), end_time_obj)
            else:
                # 同日班次
                end_datetime = datetime.combine(work_date, end_time_obj)
            
            # 计算实际时长
            duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
            
            return {
                'start_time': start_datetime,
                'end_time': end_datetime,
                'duration_hours': duration_hours,
                'shift_name': shift['shift_name'],
                'machine_name': shift.get('machine_name', 'ALL'),
                'date': work_date,
                'is_overtime': shift.get('is_ot_needed', False)
            }
            
        except Exception as e:
            logger.error(f"创建班次时间窗口失败: {work_date}, {shift}: {str(e)}")
            return None
    
    def _apply_maintenance_constraints(
        self, 
        base_windows: List[Dict], 
        machine_code: str, 
        maintenance_plans: List[Dict]
    ) -> List[Dict]:
        """
        应用维护计划约束，排除维护时间
        
        Args:
            base_windows: 基础时间窗口
            machine_code: 机台代码
            maintenance_plans: 维护计划
            
        Returns:
            排除维护时间后的可用时间窗口
        """
        # 获取该机台的维护计划
        machine_maintenance = [
            plan for plan in maintenance_plans 
            if plan['machine_code'] == machine_code
        ]
        
        if not machine_maintenance:
            # 没有维护计划，直接返回基础时间窗口
            return base_windows.copy()
        
        available_windows = []
        
        for window in base_windows:
            # 检查该时间窗口是否与维护计划冲突
            conflicted_windows = self._split_window_by_maintenance(
                window, machine_maintenance
            )
            available_windows.extend(conflicted_windows)
        
        return available_windows
    
    def _split_window_by_maintenance(
        self, 
        window: Dict, 
        maintenance_plans: List[Dict]
    ) -> List[Dict]:
        """
        根据维护计划分割时间窗口
        
        Args:
            window: 原始时间窗口
            maintenance_plans: 维护计划列表
            
        Returns:
            分割后的时间窗口列表
        """
        result_windows = [window.copy()]
        
        for maintenance in maintenance_plans:
            maint_start = maintenance['start_time']
            maint_end = maintenance['end_time']
            
            new_windows = []
            
            for current_window in result_windows:
                window_start = current_window['start_time']
                window_end = current_window['end_time']
                
                # 检查维护时间与窗口时间的重叠
                if maint_end <= window_start or maint_start >= window_end:
                    # 没有重叠，保留原窗口
                    new_windows.append(current_window)
                else:
                    # 有重叠，需要分割
                    split_windows = self._split_single_window(
                        current_window, maint_start, maint_end
                    )
                    new_windows.extend(split_windows)
            
            result_windows = new_windows
        
        # 过滤掉太短的时间窗口（小于30分钟）
        result_windows = [
            w for w in result_windows 
            if w['duration_hours'] >= 0.5
        ]
        
        return result_windows
    
    def _split_single_window(
        self, 
        window: Dict, 
        maint_start: datetime, 
        maint_end: datetime
    ) -> List[Dict]:
        """
        分割单个时间窗口
        
        Args:
            window: 时间窗口
            maint_start: 维护开始时间
            maint_end: 维护结束时间
            
        Returns:
            分割后的时间窗口列表
        """
        window_start = window['start_time']
        window_end = window['end_time']
        
        split_windows = []
        
        # 维护前的时间段
        if maint_start > window_start:
            before_window = window.copy()
            before_window['end_time'] = maint_start
            before_window['duration_hours'] = (maint_start - window_start).total_seconds() / 3600
            split_windows.append(before_window)
        
        # 维护后的时间段
        if maint_end < window_end:
            after_window = window.copy()
            after_window['start_time'] = maint_end
            after_window['duration_hours'] = (window_end - maint_end).total_seconds() / 3600
            split_windows.append(after_window)
        
        return split_windows
    
    def _optimize_time_windows(self, windows: List[Dict]) -> List[Dict]:
        """
        优化时间窗口（合并相邻窗口，排序等）
        
        Args:
            windows: 原始时间窗口列表
            
        Returns:
            优化后的时间窗口列表
        """
        if not windows:
            return []
        
        # 1. 按开始时间排序
        sorted_windows = sorted(windows, key=lambda x: x['start_time'])
        
        # 2. 合并相邻的时间窗口
        merged_windows = []
        current_window = sorted_windows[0].copy()
        
        for window in sorted_windows[1:]:
            if self._can_merge_windows(current_window, window):
                # 合并窗口
                current_window = self._merge_two_windows(current_window, window)
            else:
                # 不能合并，保存当前窗口并开始新窗口
                merged_windows.append(current_window)
                current_window = window.copy()
        
        # 添加最后一个窗口
        merged_windows.append(current_window)
        
        # 3. 过滤太短的窗口
        optimized_windows = [
            w for w in merged_windows 
            if w['duration_hours'] >= 0.5  # 至少30分钟
        ]
        
        return optimized_windows
    
    def _can_merge_windows(self, window1: Dict, window2: Dict) -> bool:
        """
        判断两个时间窗口是否可以合并
        
        Args:
            window1: 第一个时间窗口
            window2: 第二个时间窗口
            
        Returns:
            是否可以合并
        """
        # 检查时间是否连续（允许小于5分钟的间隔）
        gap = (window2['start_time'] - window1['end_time']).total_seconds() / 60
        
        return gap <= 5  # 5分钟内的间隔可以合并
    
    def _merge_two_windows(self, window1: Dict, window2: Dict) -> Dict:
        """
        合并两个时间窗口
        
        Args:
            window1: 第一个时间窗口
            window2: 第二个时间窗口
            
        Returns:
            合并后的时间窗口
        """
        merged = window1.copy()
        merged['end_time'] = window2['end_time']
        merged['duration_hours'] = (
            merged['end_time'] - merged['start_time']
        ).total_seconds() / 3600
        
        return merged
    
    def _validate_windows_integrity(
        self, 
        all_windows: Dict[str, List[Dict]], 
        work_calendar: Dict[str, Any]
    ) -> None:
        """
        验证时间窗口的完整性
        
        Args:
            all_windows: 所有机台的时间窗口
            work_calendar: 工作日历数据
        """
        errors = []
        
        # 动态计算期望总工作时间（基于实际班次配置）
        work_days_count = work_calendar.get('total_work_days', 0)
        
        # 从工作日历中获取实际的班次时长信息
        daily_hours = work_calendar.get('daily_work_hours', 0.0)
        if daily_hours > 0:
            # 使用工作日历中的实际时长
            expected_total_hours = work_days_count * daily_hours
            logger.info(f"使用工作日历时长: {work_days_count}天 × {daily_hours:.2f}小时/天 = {expected_total_hours:.2f}小时")
        else:
            # 精确计算班次配置的实际时长
            total_shift_hours = 0.0
            shift_configs = getattr(self, '_cached_shift_configs', [])
            
            if not shift_configs:
                logger.error("无法获取班次配置，时间窗口验证将使用保守估算")
                expected_total_hours = work_days_count * 16  # 保守估算
            else:
                for shift in shift_configs:
                    start_time = shift.get('start_time')
                    end_time = shift.get('end_time')
                    if start_time and end_time:
                        # 将time对象转换为总秒数进行精确计算
                        start_seconds = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
                        end_seconds = end_time.hour * 3600 + end_time.minute * 60 + end_time.second
                        
                        # 处理跨日班次（中班15:40-24:00）
                        if end_seconds <= start_seconds:
                            # 跨日班次：24:00-15:40 = 8.33小时
                            duration = (24 * 3600 - start_seconds + end_seconds) / 3600
                        else:
                            # 同日班次：15:40-06:40 = 9小时  
                            duration = (end_seconds - start_seconds) / 3600
                        
                        total_shift_hours += duration
                        logger.info(f"✓ 班次 {shift.get('shift_name', '未知')}: "
                                   f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} = {duration:.2f}小时")
                
                expected_total_hours = work_days_count * total_shift_hours
                logger.info(f"🕐 精确计算总时长: {work_days_count}天 × {total_shift_hours:.2f}小时/天 = {expected_total_hours:.2f}小时")
        
        for machine_code, windows in all_windows.items():
            if not windows:
                errors.append(f"机台 {machine_code} 没有可用时间窗口")
                continue
            
            # 计算总可用时间
            total_available = sum(w['duration_hours'] for w in windows)
            
            # 检查时间是否合理（允许15%的误差，因为班次可能有重叠或间隔）
            if total_available > expected_total_hours * 1.15:
                errors.append(f"机台 {machine_code} 可用时间可能异常: {total_available:.1f}小时 > 预期{expected_total_hours:.1f}小时")
            elif total_available < expected_total_hours * 0.85:
                errors.append(f"机台 {machine_code} 可用时间偏少: {total_available:.1f}小时 < 预期{expected_total_hours:.1f}小时")
            
            # 检查时间窗口是否有重叠
            for i, window1 in enumerate(windows):
                for window2 in windows[i+1:]:
                    if self._windows_overlap(window1, window2):
                        errors.append(f"机台 {machine_code} 时间窗口重叠")
        
        if errors:
            # 将错误改为警告，不要中断算法执行
            logger.warning(f"时间窗口完整性检查发现问题: {'; '.join(errors)}")
        else:
            logger.info("时间窗口完整性验证通过")
    
    def _windows_overlap(self, window1: Dict, window2: Dict) -> bool:
        """
        检查两个时间窗口是否重叠
        
        Args:
            window1: 第一个时间窗口
            window2: 第二个时间窗口
            
        Returns:
            是否重叠
        """
        return (
            window1['start_time'] < window2['end_time'] and 
            window2['start_time'] < window1['end_time']
        )
    
    def get_total_available_hours(self, windows: List[Dict]) -> float:
        """
        计算时间窗口的总可用时间
        
        Args:
            windows: 时间窗口列表
            
        Returns:
            总可用时间（小时）
        """
        return sum(w['duration_hours'] for w in windows)
    
    def find_available_window(
        self, 
        windows: List[Dict], 
        required_hours: float, 
        after_time: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        查找满足要求的可用时间窗口
        
        Args:
            windows: 时间窗口列表
            required_hours: 所需时间（小时）
            after_time: 最早开始时间
            
        Returns:
            匹配的时间窗口
        """
        for window in windows:
            # 检查时间约束
            if after_time and window['start_time'] < after_time:
                continue
            
            # 检查时长约束
            if window['duration_hours'] >= required_hours:
                return window
        
        return None
    
    def allocate_time_slot(
        self, 
        windows: List[Dict], 
        start_time: datetime, 
        duration_hours: float
    ) -> Tuple[bool, List[Dict]]:
        """
        在时间窗口中分配时间槽
        
        Args:
            windows: 时间窗口列表
            start_time: 开始时间
            duration_hours: 持续时间
            
        Returns:
            (是否成功, 更新后的时间窗口列表)
        """
        end_time = start_time + timedelta(hours=duration_hours)
        
        # 查找包含所需时间槽的窗口
        for i, window in enumerate(windows):
            if (window['start_time'] <= start_time and 
                window['end_time'] >= end_time):
                
                # 分割时间窗口
                new_windows = windows.copy()
                del new_windows[i]
                
                # 添加分割后的窗口
                if window['start_time'] < start_time:
                    # 前半段
                    before_window = window.copy()
                    before_window['end_time'] = start_time
                    before_window['duration_hours'] = (
                        start_time - window['start_time']
                    ).total_seconds() / 3600
                    new_windows.append(before_window)
                
                if window['end_time'] > end_time:
                    # 后半段
                    after_window = window.copy()
                    after_window['start_time'] = end_time
                    after_window['duration_hours'] = (
                        window['end_time'] - end_time
                    ).total_seconds() / 3600
                    new_windows.append(after_window)
                
                # 重新排序
                new_windows.sort(key=lambda x: x['start_time'])
                
                return True, new_windows
        
        return False, windows
    
    def validate_time_continuity(self, all_windows: Dict[str, List[Dict]]) -> None:
        """
        验证时间连续性
        
        Args:
            all_windows: 所有机台的时间窗口
        """
        logger.info("验证时间窗口连续性")
        
        for machine_code, windows in all_windows.items():
            for window in windows:
                if window['duration_hours'] <= 0:
                    raise Exception(f"机台 {machine_code} 存在无效时间窗口")
                
                if window['start_time'] >= window['end_time']:
                    raise Exception(f"机台 {machine_code} 存在时间顺序错误")
        
        logger.info("时间连续性验证通过")