"""
精确时间计算算法 (ALG-002, ALG-014增强版)

本模块实现精确的生产时间计算逻辑：
1. ALG-002: 基础时间计算算法
2. ALG-014: 效率计算算法
3. 考虑包装切换、设备启动、清理等时间损失
4. 月产能计算，支持产能拆分算法
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import math
import logging

from app.models.monthly_plan_models import MonthlyPlan

logger = logging.getLogger(__name__)


class MonthlyTimeCalculator:
    """精确时间计算算法"""
    
    def __init__(self):
        # 时间计算配置
        self.time_configs = {
            "setup_time": 0.5,        # 设备启动时间（小时）
            "cleanup_time": 0.3,      # 清理时间（小时）
            "package_switch_time": 0.5,  # 包装切换时间（小时）
            "min_time_unit": 0.5,     # 最小时间单位（小时）
            "maintenance_buffer": 8.0, # 月维护时间缓冲（小时）
            "utilization_rate": 0.90   # 设备利用率
        }
    
    def calculate_production_time(
        self,
        target_quantity: int,
        machine_speed: float,
        efficiency_rate: float,
        package_split: Optional[Dict[str, int]] = None,
        additional_factors: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算生产时间需求 (ALG-002)
        
        Args:
            target_quantity: 目标产量（箱）
            machine_speed: 机台速度（箱/小时）
            efficiency_rate: 效率率（%）
            package_split: 包装分配 {"hard": 500, "soft": 500}
            additional_factors: 额外因素 {"complexity": 1.1, "quality_req": 1.05}
        
        Returns:
            时间计算结果
        """
        calculation_result = {
            "target_quantity": target_quantity,
            "machine_speed": machine_speed,
            "efficiency_rate": efficiency_rate,
            "effective_speed": 0.0,
            "base_time_hours": 0.0,
            "setup_time": self.time_configs["setup_time"],
            "cleanup_time": self.time_configs["cleanup_time"],
            "packaging_overhead": 0.0,
            "quality_overhead": 0.0,
            "total_time_hours": 0.0,
            "rounded_time_hours": 0.0,
            "calculation_details": {}
        }
        
        try:
            logger.debug(f"计算生产时间: 目标产量 {target_quantity} 箱，机台速度 {machine_speed} 箱/小时")
            
            # 1. 计算有效速度 (ALG-014: 效率计算算法)
            effective_speed = machine_speed * (efficiency_rate / 100.0)
            calculation_result["effective_speed"] = effective_speed
            
            if effective_speed <= 0:
                raise ValueError(f"有效速度无效: {effective_speed}")
            
            # 2. 基础时间计算
            base_time_hours = target_quantity / effective_speed
            calculation_result["base_time_hours"] = base_time_hours
            
            # 3. 计算包装切换时间损失
            packaging_overhead = self._calculate_packaging_overhead(package_split)
            calculation_result["packaging_overhead"] = packaging_overhead
            
            # 4. 计算质量和复杂度开销
            quality_overhead = self._calculate_quality_overhead(
                target_quantity, additional_factors
            )
            calculation_result["quality_overhead"] = quality_overhead
            
            # 5. 总时间计算
            total_time = (
                base_time_hours + 
                self.time_configs["setup_time"] + 
                self.time_configs["cleanup_time"] + 
                packaging_overhead + 
                quality_overhead
            )
            calculation_result["total_time_hours"] = total_time
            
            # 6. 向上取整到最小时间单位
            min_unit = self.time_configs["min_time_unit"]
            rounded_time = math.ceil(total_time / min_unit) * min_unit
            calculation_result["rounded_time_hours"] = rounded_time
            
            # 7. 记录计算详情
            calculation_result["calculation_details"] = {
                "base_calculation": f"{target_quantity} ÷ ({machine_speed} × {efficiency_rate}%) = {base_time_hours:.2f}h",
                "overhead_breakdown": {
                    "setup": self.time_configs["setup_time"],
                    "cleanup": self.time_configs["cleanup_time"],
                    "packaging": packaging_overhead,
                    "quality": quality_overhead
                },
                "rounding": f"{total_time:.2f}h → {rounded_time:.2f}h (最小单位 {min_unit}h)"
            }
            
            logger.debug(f"时间计算完成: 基础 {base_time_hours:.2f}h，总计 {rounded_time:.2f}h")
            
        except Exception as e:
            logger.error(f"时间计算失败: {str(e)}")
            calculation_result["error"] = str(e)
        
        return calculation_result
    
    def calculate_monthly_capacity(
        self,
        machine_speed: float,
        efficiency_rate: float,
        work_calendar: Dict[str, Any],
        maintenance_plans: Optional[List[Dict[str, Any]]] = None,
        machine_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算机台月产能
        
        用于ALG-008产能拆分算法
        
        Args:
            machine_speed: 机台速度（箱/小时）
            efficiency_rate: 效率率（%）
            work_calendar: 工作日历
            maintenance_plans: 维护计划列表
            machine_code: 机台代码（用于查找维护计划）
        
        Returns:
            月产能计算结果
        """
        capacity_result = {
            "machine_code": machine_code,
            "machine_speed": machine_speed,
            "efficiency_rate": efficiency_rate,
            "effective_speed": 0.0,
            "total_work_hours": 0.0,
            "maintenance_hours": 0.0,
            "available_hours": 0.0,
            "utilization_rate": self.time_configs["utilization_rate"],
            "effective_hours": 0.0,
            "monthly_capacity_boxes": 0,
            "capacity_details": {}
        }
        
        try:
            # 1. 计算有效速度
            effective_speed = machine_speed * (efficiency_rate / 100.0)
            capacity_result["effective_speed"] = effective_speed
            
            # 2. 获取月总工作时间
            total_work_hours = work_calendar.get("total_work_hours", 0)
            capacity_result["total_work_hours"] = total_work_hours
            
            # 3. 计算维护时间损失
            maintenance_hours = self._calculate_maintenance_hours(
                maintenance_plans, machine_code, work_calendar
            )
            capacity_result["maintenance_hours"] = maintenance_hours
            
            # 4. 计算可用时间
            available_hours = max(0, total_work_hours - maintenance_hours)
            capacity_result["available_hours"] = available_hours
            
            # 5. 考虑设备利用率
            utilization_rate = self.time_configs["utilization_rate"]
            effective_hours = available_hours * utilization_rate
            capacity_result["effective_hours"] = effective_hours
            
            # 6. 月产能计算
            monthly_capacity = effective_hours * effective_speed
            capacity_result["monthly_capacity_boxes"] = int(monthly_capacity)
            
            # 7. 记录详细信息
            capacity_result["capacity_details"] = {
                "calendar_summary": {
                    "work_days": work_calendar.get("total_work_days", 0),
                    "work_hours": total_work_hours
                },
                "time_breakdown": {
                    "total_available": total_work_hours,
                    "maintenance_loss": maintenance_hours,
                    "net_available": available_hours,
                    "utilization_factor": utilization_rate,
                    "effective_production": effective_hours
                },
                "capacity_calculation": f"{effective_hours:.1f}h × {effective_speed:.2f}箱/h = {monthly_capacity:.0f}箱"
            }
            
            logger.debug(f"机台 {machine_code} 月产能: {monthly_capacity:.0f} 箱 "
                        f"(有效时间 {effective_hours:.1f}h × 速度 {effective_speed:.2f}箱/h)")
            
        except Exception as e:
            logger.error(f"月产能计算失败: {str(e)}")
            capacity_result["error"] = str(e)
        
        return capacity_result
    
    def calculate_time_span(
        self,
        required_hours: float,
        work_calendar: Dict[str, Any],
        start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        计算时间跨度
        
        根据工作日历计算生产任务需要的天数
        
        Args:
            required_hours: 所需时间（小时）
            work_calendar: 工作日历
            start_date: 开始日期（可选）
        
        Returns:
            时间跨度计算结果
        """
        span_result = {
            "required_hours": required_hours,
            "start_date": start_date,
            "end_date": None,
            "span_days": 0,
            "work_days_used": 0,
            "daily_breakdown": [],
            "remaining_hours": required_hours
        }
        
        try:
            work_days = [d for d in work_calendar.get("calendar", []) if d["is_working"]]
            
            if not work_days:
                span_result["error"] = "无可用工作日"
                return span_result
            
            # 如果没有指定开始日期，使用第一个工作日
            if not start_date:
                first_work_day = work_days[0]
                start_date = first_work_day["date"]
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            
            span_result["start_date"] = start_date
            
            # 计算时间分配
            remaining_hours = required_hours
            current_day_index = 0
            
            # 找到开始日期对应的工作日索引
            for i, day in enumerate(work_days):
                day_date = day["date"]
                if isinstance(day_date, str):
                    day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
                
                if day_date >= start_date:
                    current_day_index = i
                    break
            
            # 分配时间到工作日
            while remaining_hours > 0 and current_day_index < len(work_days):
                work_day = work_days[current_day_index]
                day_total_hours = work_day.get("total_hours", 0)
                
                allocated_hours = min(remaining_hours, day_total_hours)
                
                day_date = work_day["date"]
                if isinstance(day_date, str):
                    day_date = datetime.strptime(day_date, "%Y-%m-%d").date()
                
                span_result["daily_breakdown"].append({
                    "date": day_date,
                    "allocated_hours": allocated_hours,
                    "total_day_hours": day_total_hours,
                    "utilization": allocated_hours / day_total_hours if day_total_hours > 0 else 0
                })
                
                remaining_hours -= allocated_hours
                current_day_index += 1
            
            if span_result["daily_breakdown"]:
                span_result["end_date"] = span_result["daily_breakdown"][-1]["date"]
                span_result["work_days_used"] = len(span_result["daily_breakdown"])
                
                # 计算总跨度天数
                start = span_result["start_date"]
                end = span_result["end_date"]
                if isinstance(start, str):
                    start = datetime.strptime(start, "%Y-%m-%d").date()
                if isinstance(end, str):
                    end = datetime.strptime(end, "%Y-%m-%d").date()
                
                span_result["span_days"] = (end - start).days + 1
            
            span_result["remaining_hours"] = remaining_hours
            
            logger.debug(f"时间跨度计算: {required_hours}h 需要 {span_result['work_days_used']} 个工作日")
            
        except Exception as e:
            logger.error(f"时间跨度计算失败: {str(e)}")
            span_result["error"] = str(e)
        
        return span_result
    
    def _calculate_packaging_overhead(self, package_split: Optional[Dict[str, int]]) -> float:
        """计算包装切换时间损失"""
        if not package_split:
            return 0.0
        
        # 计算有效包装类型数量（产量大于0的）
        active_packages = len([v for v in package_split.values() if v > 0])
        
        if active_packages <= 1:
            return 0.0
        
        # 每次包装切换需要额外时间
        switches = active_packages - 1
        return switches * self.time_configs["package_switch_time"]
    
    def _calculate_quality_overhead(
        self, 
        target_quantity: int, 
        additional_factors: Optional[Dict[str, Any]]
    ) -> float:
        """计算质量和复杂度开销"""
        overhead = 0.0
        
        if not additional_factors:
            return overhead
        
        # 基础时间（用于计算百分比开销）
        base_time = target_quantity * 0.1  # 简化的基础时间估算
        
        # 复杂度因子
        complexity_factor = additional_factors.get("complexity", 1.0)
        if complexity_factor > 1.0:
            overhead += base_time * (complexity_factor - 1.0) * 0.1
        
        # 质量要求因子
        quality_factor = additional_factors.get("quality_req", 1.0)
        if quality_factor > 1.0:
            overhead += base_time * (quality_factor - 1.0) * 0.05
        
        return overhead
    
    def _calculate_maintenance_hours(
        self,
        maintenance_plans: Optional[List[Dict[str, Any]]],
        machine_code: Optional[str],
        work_calendar: Dict[str, Any]
    ) -> float:
        """计算维护时间损失"""
        
        if not maintenance_plans or not machine_code:
            # 如果没有维护计划，使用默认维护缓冲时间
            return self.time_configs["maintenance_buffer"]
        
        total_maintenance_hours = 0.0
        
        # 获取月份范围
        calendar_dates = work_calendar.get("calendar", [])
        if not calendar_dates:
            return self.time_configs["maintenance_buffer"]
        
        month_start = calendar_dates[0]["date"]
        month_end = calendar_dates[-1]["date"]
        
        if isinstance(month_start, str):
            month_start = datetime.strptime(month_start, "%Y-%m-%d").date()
        if isinstance(month_end, str):
            month_end = datetime.strptime(month_end, "%Y-%m-%d").date()
        
        # 查找该机台在当月的维护计划
        for plan in maintenance_plans:
            if plan.get("machine_code") != machine_code:
                continue
            
            maint_start = plan.get("maintenance_start")
            maint_end = plan.get("maintenance_end")
            
            if not maint_start or not maint_end:
                continue
            
            # 确保日期格式一致
            if isinstance(maint_start, str):
                maint_start = datetime.fromisoformat(maint_start)
            if isinstance(maint_end, str):
                maint_end = datetime.fromisoformat(maint_end)
            
            # 检查维护时间是否与当月重叠
            if (maint_start.date() <= month_end and maint_end.date() >= month_start):
                # 计算重叠时间
                overlap_start = max(maint_start, datetime.combine(month_start, maint_start.time()))
                overlap_end = min(maint_end, datetime.combine(month_end, maint_end.time()))
                
                overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                total_maintenance_hours += max(0, overlap_hours)
        
        # 如果没有找到具体维护计划，使用默认缓冲时间
        if total_maintenance_hours == 0:
            total_maintenance_hours = self.time_configs["maintenance_buffer"]
        
        return total_maintenance_hours
    
    def estimate_completion_probability(
        self,
        required_hours: float,
        available_capacity: Dict[str, Any],
        historical_efficiency: float = 0.85
    ) -> Dict[str, Any]:
        """
        估算完成概率
        
        基于历史效率和可用产能估算任务完成的概率
        """
        probability_result = {
            "required_hours": required_hours,
            "available_capacity_hours": available_capacity.get("effective_hours", 0),
            "historical_efficiency": historical_efficiency,
            "completion_probability": 0.0,
            "risk_level": "HIGH",
            "recommendations": []
        }
        
        try:
            available_hours = available_capacity.get("effective_hours", 0)
            
            if available_hours <= 0:
                probability_result["completion_probability"] = 0.0
                probability_result["risk_level"] = "CRITICAL"
                probability_result["recommendations"].append("无可用产能，需要重新安排")
                return probability_result
            
            # 考虑历史效率的实际可用时间
            realistic_hours = available_hours * historical_efficiency
            
            # 计算完成概率
            if realistic_hours >= required_hours:
                excess_ratio = realistic_hours / required_hours
                if excess_ratio >= 1.5:
                    probability_result["completion_probability"] = 0.95
                    probability_result["risk_level"] = "LOW"
                elif excess_ratio >= 1.2:
                    probability_result["completion_probability"] = 0.85
                    probability_result["risk_level"] = "MEDIUM"
                else:
                    probability_result["completion_probability"] = 0.75
                    probability_result["risk_level"] = "MEDIUM"
            else:
                shortage_ratio = required_hours / realistic_hours
                if shortage_ratio <= 1.1:
                    probability_result["completion_probability"] = 0.60
                    probability_result["risk_level"] = "HIGH"
                elif shortage_ratio <= 1.3:
                    probability_result["completion_probability"] = 0.40
                    probability_result["risk_level"] = "HIGH"
                else:
                    probability_result["completion_probability"] = 0.20
                    probability_result["risk_level"] = "CRITICAL"
            
            # 生成建议
            if probability_result["risk_level"] == "LOW":
                probability_result["recommendations"].append("产能充足，可按计划执行")
            elif probability_result["risk_level"] == "MEDIUM":
                probability_result["recommendations"].append("产能紧张，建议优化生产计划")
            else:
                probability_result["recommendations"].append("产能不足，建议拆分任务或延期执行")
        
        except Exception as e:
            logger.error(f"完成概率估算失败: {str(e)}")
            probability_result["error"] = str(e)
        
        return probability_result
