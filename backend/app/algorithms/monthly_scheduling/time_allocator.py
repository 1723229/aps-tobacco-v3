"""
智能时间分配算法 (ALG-006, ALG-009, ALG-005增强版)

本模块实现智能的时间分配和调度逻辑：
1. ALG-006: 时间分配算法 - 从月初开始按优先级分配时间段
2. ALG-009: 时间窗口算法 - 确保时间窗口无冲突
3. ALG-005: 班次约束算法 - 生产时间必须在班次范围内
4. ALG-004: 维修约束算法 - 避开维护时间
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.monthly_plan_models import MonthlyPlan

logger = logging.getLogger(__name__)


class MonthlyTimeAllocator:
    """智能时间分配算法 - 处理时间窗口和冲突"""
    
    def __init__(self):
        # 默认班次配置（从数据验证中获取实际配置）
        self.default_shift_configs = [
            {"name": "早班", "start": "06:40", "end": "15:40", "hours": 9.0},
            {"name": "中班", "start": "15:40", "end": "00:00", "hours": 8.33}
        ]
        
        # 时间分配配置
        self.allocation_configs = {
            "min_allocation_unit": 0.5,    # 最小分配单位（小时）
            "max_continuous_hours": 16.0,  # 最大连续工作时间
            "buffer_time": 0.1,           # 缓冲时间（小时）
            "priority_gap": 0.25          # 优先级间隔时间（小时）
        }
    
    async def allocate_production_time(
        self,
        plan: MonthlyPlan,
        machine_combination: Dict[str, Any],
        time_calculation: Dict[str, Any],
        work_calendar: Dict[str, Any],
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]] = None,
        priority_level: int = 1
    ) -> Dict[str, Any]:
        """
        分配生产时间窗口
        
        Args:
            plan: 月度计划
            machine_combination: 机台组合信息
            time_calculation: 时间计算结果
            work_calendar: 工作日历
            existing_allocations: 已分配时间跟踪
            maintenance_plans: 维护计划
            priority_level: 优先级等级
        
        Returns:
            时间分配结果
        """
        allocation_result = {
            "success": False,
            "scheduled_start_time": None,
            "scheduled_end_time": None,
            "allocated_shifts": [],
            "time_windows": [],
            "conflicts": [],
            "warnings": [],
            "allocation_strategy": "single_day",  # single_day, multi_day, fragmented
            "utilization_info": {}
        }
        
        try:
            required_hours = time_calculation.get("rounded_time_hours", 0)
            maker_code = machine_combination["maker_code"]
            feeder_code = machine_combination["feeder_code"]
            
            logger.info(f"开始为产品 {plan.article_nr} 分配时间: "
                       f"需要 {required_hours}h，机台 {maker_code}-{feeder_code}")
            
            if required_hours <= 0:
                allocation_result["warnings"].append("所需时间为0，无需分配")
                return allocation_result
            
            # 1. 获取工作日和班次配置
            work_days = self._get_available_work_days(work_calendar)
            shift_configs = work_calendar.get("shift_configs", self.default_shift_configs)
            
            if not work_days:
                allocation_result["warnings"].append("无可用工作日")
                return allocation_result
            
            # 2. 尝试单日分配
            single_day_result = await self._try_single_day_allocation(
                required_hours, work_days, shift_configs, 
                maker_code, feeder_code, existing_allocations, maintenance_plans
            )
            
            if single_day_result["success"]:
                allocation_result.update(single_day_result)
                allocation_result["allocation_strategy"] = "single_day"
                logger.info(f"产品 {plan.article_nr} 单日分配成功")
                return allocation_result
            
            # 3. 尝试多日连续分配
            multi_day_result = await self._try_multi_day_allocation(
                required_hours, work_days, shift_configs,
                maker_code, feeder_code, existing_allocations, maintenance_plans
            )
            
            if multi_day_result["success"]:
                allocation_result.update(multi_day_result)
                allocation_result["allocation_strategy"] = "multi_day"
                logger.info(f"产品 {plan.article_nr} 多日分配成功")
                return allocation_result
            
            # 4. 尝试碎片化分配
            fragmented_result = await self._try_fragmented_allocation(
                required_hours, work_days, shift_configs,
                maker_code, feeder_code, existing_allocations, maintenance_plans
            )
            
            if fragmented_result["success"]:
                allocation_result.update(fragmented_result)
                allocation_result["allocation_strategy"] = "fragmented"
                allocation_result["warnings"].append("使用碎片化时间分配，可能影响生产效率")
                logger.info(f"产品 {plan.article_nr} 碎片化分配成功")
                return allocation_result
            
            # 5. 分配失败
            allocation_result["warnings"].append("所有分配策略均失败，可能需要调整计划或增加产能")
            
        except Exception as e:
            logger.error(f"时间分配失败: {str(e)}")
            allocation_result["warnings"].append(f"时间分配异常: {str(e)}")
        
        return allocation_result
    
    def _get_available_work_days(self, work_calendar: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取可用工作日"""
        calendar_days = work_calendar.get("calendar", [])
        return [day for day in calendar_days if day.get("is_working", False)]
    
    async def _try_single_day_allocation(
        self,
        required_hours: float,
        work_days: List[Dict[str, Any]],
        shift_configs: List[Dict[str, Any]],
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """尝试单日分配"""
        
        result = {"success": False, "reason": ""}
        
        # 计算单日最大可用时间
        daily_max_hours = sum(shift["hours"] for shift in shift_configs)
        
        if required_hours > daily_max_hours:
            result["reason"] = f"所需时间 {required_hours}h 超过单日最大时间 {daily_max_hours}h"
            return result
        
        # 按时间顺序遍历工作日
        for work_day in work_days:
            day_date = work_day["date"]
            if isinstance(day_date, str):
                day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
            
            # 获取该日期的可用时间窗口
            available_windows = await self._get_daily_available_windows(
                day_date, shift_configs, maker_code, feeder_code, 
                existing_allocations, maintenance_plans
            )
            
            # 尝试在可用窗口中分配时间
            allocation = self._allocate_in_windows(available_windows, required_hours)
            
            if allocation["success"]:
                result.update({
                    "success": True,
                    "scheduled_start_time": allocation["start_time"],
                    "scheduled_end_time": allocation["end_time"],
                    "allocated_shifts": allocation["allocated_shifts"],
                    "time_windows": allocation["time_windows"],
                    "single_day": True,
                    "allocation_date": day_date
                })
                return result
        
        result["reason"] = "未找到合适的单日时间窗口"
        return result
    
    async def _try_multi_day_allocation(
        self,
        required_hours: float,
        work_days: List[Dict[str, Any]],
        shift_configs: List[Dict[str, Any]],
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """尝试多日连续分配"""
        
        result = {"success": False, "reason": ""}
        
        remaining_hours = required_hours
        allocated_shifts = []
        all_time_windows = []
        start_time = None
        end_time = None
        
        for work_day in work_days:
            if remaining_hours <= 0:
                break
            
            day_date = work_day["date"]
            if isinstance(day_date, str):
                day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
            
            # 获取该日期的可用时间窗口
            available_windows = await self._get_daily_available_windows(
                day_date, shift_configs, maker_code, feeder_code,
                existing_allocations, maintenance_plans
            )
            
            # 在该日分配尽可能多的时间
            daily_allocation = self._allocate_max_in_windows(available_windows, remaining_hours)
            
            if daily_allocation["allocated_hours"] > 0:
                allocated_shifts.extend(daily_allocation["allocated_shifts"])
                all_time_windows.extend(daily_allocation["time_windows"])
                
                if start_time is None:
                    start_time = daily_allocation["start_time"]
                end_time = daily_allocation["end_time"]
                
                remaining_hours -= daily_allocation["allocated_hours"]
        
        if remaining_hours <= 0.1:  # 允许小量误差
            result.update({
                "success": True,
                "scheduled_start_time": start_time,
                "scheduled_end_time": end_time,
                "allocated_shifts": allocated_shifts,
                "time_windows": all_time_windows,
                "multi_day": True,
                "days_used": len(set(shift["date"] for shift in allocated_shifts))
            })
        else:
            result["reason"] = f"多日分配后仍缺少 {remaining_hours:.1f} 小时"
        
        return result
    
    async def _try_fragmented_allocation(
        self,
        required_hours: float,
        work_days: List[Dict[str, Any]],
        shift_configs: List[Dict[str, Any]],
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """尝试碎片化分配（使用所有可用的时间片段）"""
        
        result = {"success": False, "reason": ""}
        
        # 收集所有可用的时间片段
        all_fragments = []
        
        for work_day in work_days:
            day_date = work_day["date"]
            if isinstance(day_date, str):
                day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
            
            available_windows = await self._get_daily_available_windows(
                day_date, shift_configs, maker_code, feeder_code,
                existing_allocations, maintenance_plans
            )
            
            # 将每个可用窗口作为一个片段
            for window in available_windows:
                if window["duration"] >= self.allocation_configs["min_allocation_unit"]:
                    all_fragments.append(window)
        
        if not all_fragments:
            result["reason"] = "无可用时间片段"
            return result
        
        # 按开始时间排序
        all_fragments.sort(key=lambda x: x["start_time"])
        
        # 分配时间到片段
        remaining_hours = required_hours
        allocated_shifts = []
        used_fragments = []
        
        for fragment in all_fragments:
            if remaining_hours <= 0:
                break
            
            fragment_hours = min(fragment["duration"], remaining_hours)
            
            if fragment_hours >= self.allocation_configs["min_allocation_unit"]:
                # 使用这个片段
                fragment_end = fragment["start_time"] + timedelta(hours=fragment_hours)
                
                allocated_shifts.append({
                    "date": fragment["date"],
                    "shift_name": fragment.get("shift_name", "未知班次"),
                    "start_time": fragment["start_time"],
                    "end_time": fragment_end,
                    "allocated_hours": fragment_hours,
                    "fragment": True
                })
                
                used_fragments.append(fragment)
                remaining_hours -= fragment_hours
        
        if remaining_hours <= 0.1:  # 允许小量误差
            result.update({
                "success": True,
                "scheduled_start_time": allocated_shifts[0]["start_time"] if allocated_shifts else None,
                "scheduled_end_time": allocated_shifts[-1]["end_time"] if allocated_shifts else None,
                "allocated_shifts": allocated_shifts,
                "time_windows": used_fragments,
                "fragmented": True,
                "fragments_used": len(used_fragments)
            })
        else:
            result["reason"] = f"碎片化分配后仍缺少 {remaining_hours:.1f} 小时"
        
        return result
    
    async def _get_daily_available_windows(
        self,
        day_date: date,
        shift_configs: List[Dict[str, Any]],
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取指定日期的可用时间窗口"""
        
        available_windows = []
        
        for shift in shift_configs:
            # 构建班次时间段
            start_time = datetime.combine(day_date, time.fromisoformat(shift["start"]))
            
            # 处理跨日班次
            if shift["end"] == "00:00":
                end_time = datetime.combine(day_date + timedelta(days=1), time.fromisoformat("00:00"))
            else:
                end_time = datetime.combine(day_date, time.fromisoformat(shift["end"]))
            
            # 检查机台冲突 (ALG-009: 时间窗口算法)
            if self._has_machine_conflict(start_time, end_time, maker_code, existing_allocations):
                continue
            if self._has_machine_conflict(start_time, end_time, feeder_code, existing_allocations):
                continue
            
            # 检查维护冲突 (ALG-004: 维修约束算法)
            if self._has_maintenance_conflict(start_time, end_time, [maker_code, feeder_code], maintenance_plans):
                continue
            
            # 计算实际可用时间（排除已占用的时间段）
            actual_windows = self._subtract_occupied_time(
                start_time, end_time, maker_code, feeder_code, existing_allocations
            )
            
            for window in actual_windows:
                if window["duration"] >= self.allocation_configs["min_allocation_unit"]:
                    window.update({
                        "date": day_date,
                        "shift_name": shift["name"],
                        "original_shift": shift
                    })
                    available_windows.append(window)
        
        return available_windows
    
    def _has_machine_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        machine_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]]
    ) -> bool:
        """检查机台时间冲突"""
        
        if machine_code not in existing_allocations:
            return False
        
        for existing_start, existing_end in existing_allocations[machine_code]:
            # 检查时间重叠
            if start_time < existing_end and end_time > existing_start:
                return True
        
        return False
    
    def _has_maintenance_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        machine_codes: List[str],
        maintenance_plans: List[Dict[str, Any]] = None
    ) -> bool:
        """检查维护时间冲突"""
        
        if not maintenance_plans:
            return False
        
        for plan in maintenance_plans:
            if plan.get("machine_code") not in machine_codes:
                continue
            
            maint_start = plan.get("maintenance_start")
            maint_end = plan.get("maintenance_end")
            
            if not maint_start or not maint_end:
                continue
            
            # 确保时间格式一致
            if isinstance(maint_start, str):
                maint_start = datetime.fromisoformat(maint_start)
            if isinstance(maint_end, str):
                maint_end = datetime.fromisoformat(maint_end)
            
            # 检查时间重叠
            if start_time < maint_end and end_time > maint_start:
                return True
        
        return False
    
    def _subtract_occupied_time(
        self,
        start_time: datetime,
        end_time: datetime,
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]]
    ) -> List[Dict[str, Any]]:
        """从时间段中减去已占用的时间，返回可用时间片段"""
        
        # 收集所有相关机台的占用时间
        occupied_periods = []
        
        for machine_code in [maker_code, feeder_code]:
            if machine_code in existing_allocations:
                for occ_start, occ_end in existing_allocations[machine_code]:
                    # 只考虑与当前时间段重叠的占用时间
                    if occ_start < end_time and occ_end > start_time:
                        overlap_start = max(start_time, occ_start)
                        overlap_end = min(end_time, occ_end)
                        occupied_periods.append((overlap_start, overlap_end))
        
        if not occupied_periods:
            # 没有占用时间，整个时间段都可用
            duration = (end_time - start_time).total_seconds() / 3600
            return [{
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration
            }]
        
        # 合并重叠的占用时间段
        occupied_periods.sort()
        merged_occupied = []
        
        for occ_start, occ_end in occupied_periods:
            if merged_occupied and occ_start <= merged_occupied[-1][1]:
                # 重叠，合并
                merged_occupied[-1] = (merged_occupied[-1][0], max(merged_occupied[-1][1], occ_end))
            else:
                merged_occupied.append((occ_start, occ_end))
        
        # 计算可用时间片段
        available_fragments = []
        current_time = start_time
        
        for occ_start, occ_end in merged_occupied:
            # 在占用时间之前的可用时间
            if current_time < occ_start:
                duration = (occ_start - current_time).total_seconds() / 3600
                if duration >= self.allocation_configs["min_allocation_unit"]:
                    available_fragments.append({
                        "start_time": current_time,
                        "end_time": occ_start,
                        "duration": duration
                    })
            current_time = max(current_time, occ_end)
        
        # 最后一段可用时间
        if current_time < end_time:
            duration = (end_time - current_time).total_seconds() / 3600
            if duration >= self.allocation_configs["min_allocation_unit"]:
                available_fragments.append({
                    "start_time": current_time,
                    "end_time": end_time,
                    "duration": duration
                })
        
        return available_fragments
    
    def _allocate_in_windows(
        self,
        available_windows: List[Dict[str, Any]],
        required_hours: float
    ) -> Dict[str, Any]:
        """在可用窗口中分配指定时间"""
        
        result = {"success": False}
        
        total_available = sum(w["duration"] for w in available_windows)
        
        if total_available < required_hours:
            result["reason"] = f"可用时间不足: {total_available:.1f}h < {required_hours:.1f}h"
            return result
        
        # 尝试使用连续的时间段
        allocated_shifts = []
        time_windows = []
        remaining_hours = required_hours
        
        for window in available_windows:
            if remaining_hours <= 0:
                break
            
            if window["duration"] >= remaining_hours:
                # 当前窗口可以满足剩余需求
                end_time = window["start_time"] + timedelta(hours=remaining_hours)
                
                allocated_shifts.append({
                    "date": window["date"],
                    "shift_name": window["shift_name"],
                    "start_time": window["start_time"],
                    "end_time": end_time,
                    "allocated_hours": remaining_hours
                })
                
                time_windows.append(window)
                remaining_hours = 0
            else:
                # 使用整个窗口
                allocated_shifts.append({
                    "date": window["date"],
                    "shift_name": window["shift_name"],
                    "start_time": window["start_time"],
                    "end_time": window["end_time"],
                    "allocated_hours": window["duration"]
                })
                
                time_windows.append(window)
                remaining_hours -= window["duration"]
        
        if remaining_hours <= 0.01:  # 允许极小误差
            result.update({
                "success": True,
                "start_time": allocated_shifts[0]["start_time"],
                "end_time": allocated_shifts[-1]["end_time"],
                "allocated_shifts": allocated_shifts,
                "time_windows": time_windows
            })
        else:
            result["reason"] = f"窗口分配失败，仍需 {remaining_hours:.1f}h"
        
        return result
    
    def _allocate_max_in_windows(
        self,
        available_windows: List[Dict[str, Any]],
        max_hours: float
    ) -> Dict[str, Any]:
        """在可用窗口中分配尽可能多的时间（最多max_hours）"""
        
        allocated_shifts = []
        time_windows = []
        total_allocated = 0.0
        
        for window in available_windows:
            if total_allocated >= max_hours:
                break
            
            available_in_window = min(window["duration"], max_hours - total_allocated)
            
            if available_in_window >= self.allocation_configs["min_allocation_unit"]:
                end_time = window["start_time"] + timedelta(hours=available_in_window)
                
                allocated_shifts.append({
                    "date": window["date"],
                    "shift_name": window["shift_name"],
                    "start_time": window["start_time"],
                    "end_time": end_time,
                    "allocated_hours": available_in_window
                })
                
                time_windows.append(window)
                total_allocated += available_in_window
        
        return {
            "allocated_hours": total_allocated,
            "start_time": allocated_shifts[0]["start_time"] if allocated_shifts else None,
            "end_time": allocated_shifts[-1]["end_time"] if allocated_shifts else None,
            "allocated_shifts": allocated_shifts,
            "time_windows": time_windows
        }
    
    def calculate_allocation_efficiency(
        self,
        allocation_result: Dict[str, Any],
        required_hours: float
    ) -> Dict[str, Any]:
        """计算时间分配效率"""
        
        efficiency_result = {
            "time_efficiency": 0.0,
            "fragmentation_index": 0.0,
            "continuity_score": 0.0,
            "overall_score": 0.0,
            "analysis": {}
        }
        
        if not allocation_result.get("success"):
            return efficiency_result
        
        allocated_shifts = allocation_result.get("allocated_shifts", [])
        
        if not allocated_shifts:
            return efficiency_result
        
        try:
            # 1. 时间效率：实际分配时间 vs 所需时间
            total_allocated = sum(shift["allocated_hours"] for shift in allocated_shifts)
            time_efficiency = min(required_hours / total_allocated, 1.0) if total_allocated > 0 else 0
            
            # 2. 碎片化指数：时间段数量的倒数
            num_fragments = len(allocated_shifts)
            fragmentation_index = 1.0 / num_fragments if num_fragments > 0 else 0
            
            # 3. 连续性评分：考虑时间段之间的间隔
            continuity_score = self._calculate_continuity_score(allocated_shifts)
            
            # 4. 综合评分
            overall_score = (time_efficiency * 0.4 + 
                           fragmentation_index * 0.3 + 
                           continuity_score * 0.3)
            
            efficiency_result.update({
                "time_efficiency": time_efficiency,
                "fragmentation_index": fragmentation_index,
                "continuity_score": continuity_score,
                "overall_score": overall_score,
                "analysis": {
                    "total_allocated_hours": total_allocated,
                    "required_hours": required_hours,
                    "time_fragments": num_fragments,
                    "allocation_strategy": allocation_result.get("allocation_strategy", "unknown"),
                    "efficiency_rating": self._get_efficiency_rating(overall_score)
                }
            })
            
        except Exception as e:
            logger.error(f"分配效率计算失败: {str(e)}")
            efficiency_result["error"] = str(e)
        
        return efficiency_result
    
    def _calculate_continuity_score(self, allocated_shifts: List[Dict[str, Any]]) -> float:
        """计算时间连续性评分"""
        
        if len(allocated_shifts) <= 1:
            return 1.0
        
        # 按开始时间排序
        sorted_shifts = sorted(allocated_shifts, key=lambda x: x["start_time"])
        
        total_gaps = 0.0
        total_time = 0.0
        
        for i in range(len(sorted_shifts) - 1):
            current_end = sorted_shifts[i]["end_time"]
            next_start = sorted_shifts[i + 1]["start_time"]
            
            gap_hours = (next_start - current_end).total_seconds() / 3600
            total_gaps += max(0, gap_hours)
            total_time += sorted_shifts[i]["allocated_hours"]
        
        # 最后一个时间段
        total_time += sorted_shifts[-1]["allocated_hours"]
        
        if total_time <= 0:
            return 0.0
        
        # 连续性评分：间隔时间越少分数越高
        gap_ratio = total_gaps / total_time
        continuity_score = max(0, 1.0 - gap_ratio)
        
        return continuity_score
    
    def _get_efficiency_rating(self, score: float) -> str:
        """获取效率评级"""
        if score >= 0.9:
            return "优秀"
        elif score >= 0.8:
            return "良好"
        elif score >= 0.7:
            return "一般"
        elif score >= 0.6:
            return "较差"
        else:
            return "很差"
