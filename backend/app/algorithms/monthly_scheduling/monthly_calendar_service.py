#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度工作日历集成服务

本模块实现 MonthlyCalendarService 类，提供月度生产计划的工作日历管理功能，
包括工作日查询、产能计算、节假日判断和月度日历生成等核心算法。

主要功能：
- 工作日查询和计算
- 产能因子计算
- 节假日和维护日处理
- 月度日历生成
- CLI 支持

作者: APS Team
创建时间: 2025-01-17
版本: 1.0.0
"""

import argparse
import asyncio
import json
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.models.monthly_work_calendar_models import MonthlyWorkCalendar as APSWorkCalendar
from app.algorithms.base import AlgorithmBase, AlgorithmResult, ProcessingStage


logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class DayType(Enum):
    """日期类型枚举"""
    WORKDAY = "WORKDAY"  # 工作日
    WEEKEND = "WEEKEND"  # 周末
    HOLIDAY = "HOLIDAY"  # 节假日
    MAINTENANCE = "MAINTENANCE"  # 维护日
    SPECIAL_WORKING = "SPECIAL_WORKING"  # 特殊工作日（调休）


class CapacityFactorType(Enum):
    """产能因子类型枚举"""
    NORMAL = "normal"  # 正常产能
    REDUCED = "reduced"  # 减产
    OVERTIME = "overtime"  # 加班
    MAINTENANCE = "maintenance"  # 维护（零产能）
    HOLIDAY = "holiday"  # 节假日（零产能）


@dataclass
class CalendarDay:
    """日历日期信息"""
    date: date
    day_type: DayType
    is_working: bool
    capacity_factor: Decimal
    description: Optional[str] = None
    shift_count: int = 1
    maintenance_hours: int = 0
    overtime_hours: int = 0


@dataclass
class MonthCapacity:
    """月度产能信息"""
    month: str  # YYYY-MM 格式
    total_working_days: int
    total_calendar_days: int
    total_capacity_factor: Decimal
    average_daily_capacity: Decimal
    peak_capacity_days: List[date]
    low_capacity_days: List[date]
    maintenance_days: List[date]


@dataclass
class CalendarServiceConfig:
    """日历服务配置"""
    default_capacity_factor: Decimal = Decimal("1.0")
    overtime_capacity_factor: Decimal = Decimal("1.5")
    reduced_capacity_factor: Decimal = Decimal("0.7")
    maintenance_capacity_factor: Decimal = Decimal("0.0")
    holiday_capacity_factor: Decimal = Decimal("0.0")
    
    # 工作时间配置
    standard_working_hours: int = 8
    overtime_threshold_hours: int = 10
    
    # 维护相关配置
    maintenance_impact_days: int = 1  # 维护影响天数
    planned_maintenance_factor: Decimal = Decimal("0.8")  # 计划维护期间产能因子


class MonthlyCalendarService(AlgorithmBase):
    """
    月度工作日历集成服务
    
    提供月度生产计划的工作日历管理功能，包括工作日查询、产能计算、
    节假日判断和月度日历生成等核心算法。
    
    主要特性：
    - 异步数据库操作
    - 多种日期类型支持
    - 产能因子动态计算
    - 节假日和维护日处理
    - 月度日历缓存优化
    """
    
    def __init__(self, session: AsyncSession, config: Optional[CalendarServiceConfig] = None):
        """
        初始化月度日历服务
        
        Args:
            session: 异步数据库会话
            config: 日历服务配置，如未提供则使用默认配置
        """
        super().__init__(ProcessingStage.DATA_PREPROCESSING)
        self.session = session
        self.config = config or CalendarServiceConfig()
        self._calendar_cache: Dict[str, List[CalendarDay]] = {}
        
        # 设置算法信息
        self.algorithm_name = "月度工作日历集成服务"
        self.version = __version__
        
        logger.info(f"初始化 {self.algorithm_name} v{self.version}")
    
    async def get_working_days(
        self, 
        start_date: Union[str, date], 
        end_date: Union[str, date]
    ) -> List[CalendarDay]:
        """
        获取指定日期范围内的工作日信息
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD 或 date 对象)
            end_date: 结束日期 (YYYY-MM-DD 或 date 对象)
            
        Returns:
            工作日信息列表
            
        Raises:
            ValueError: 当日期格式不正确或范围无效时
        """
        try:
            # 标准化日期输入
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start_date > end_date:
                raise ValueError("开始日期不能晚于结束日期")
            
            logger.info(f"查询工作日信息：{start_date} 至 {end_date}")
            
            # 查询数据库中的日历信息
            stmt = select(APSWorkCalendar).where(
                and_(
                    APSWorkCalendar.calendar_date >= start_date,
                    APSWorkCalendar.calendar_date <= end_date
                )
            ).order_by(APSWorkCalendar.calendar_date)
            
            result = await self.session.execute(stmt)
            calendar_records = result.scalars().all()
            
            # 构建日历映射
            calendar_map = {record.calendar_date: record for record in calendar_records}
            
            # 生成日期范围内的所有日期
            working_days = []
            current_date = start_date
            
            while current_date <= end_date:
                calendar_day = await self._build_calendar_day(current_date, calendar_map)
                if calendar_day.is_working:
                    working_days.append(calendar_day)
                current_date += timedelta(days=1)
            
            logger.info(f"找到 {len(working_days)} 个工作日")
            return working_days
            
        except Exception as e:
            logger.error(f"获取工作日信息失败: {e}")
            raise
    
    async def calculate_capacity(
        self, 
        target_date: Union[str, date],
        base_capacity: Decimal = Decimal("1.0")
    ) -> Tuple[Decimal, CalendarDay]:
        """
        计算指定日期的产能因子
        
        Args:
            target_date: 目标日期
            base_capacity: 基础产能
            
        Returns:
            元组包含 (实际产能因子, 日历日期信息)
        """
        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            
            # 查询日历信息
            stmt = select(APSWorkCalendar).where(APSWorkCalendar.calendar_date == target_date)
            result = await self.session.execute(stmt)
            calendar_record = result.scalars().first()
            
            # 构建日历日期信息
            calendar_day = await self._build_calendar_day(target_date, {target_date: calendar_record})
            
            # 计算实际产能
            actual_capacity = base_capacity * calendar_day.capacity_factor
            
            logger.debug(f"日期 {target_date} 产能计算: 基础={base_capacity}, 因子={calendar_day.capacity_factor}, 实际={actual_capacity}")
            
            return actual_capacity, calendar_day
            
        except Exception as e:
            logger.error(f"计算产能失败: {e}")
            raise
    
    async def is_working_day(self, target_date: Union[str, date]) -> bool:
        """
        判断指定日期是否为工作日
        
        Args:
            target_date: 目标日期
            
        Returns:
            True 如果是工作日，False 否则
        """
        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            
            # 查询日历信息
            stmt = select(APSWorkCalendar).where(APSWorkCalendar.calendar_date == target_date)
            result = await self.session.execute(stmt)
            calendar_record = result.scalars().first()
            
            if calendar_record:
                return calendar_record.is_working_day
            
            # 如果数据库中没有记录，根据星期判断
            weekday = target_date.weekday()
            return weekday < 5  # 周一到周五为工作日
            
        except Exception as e:
            logger.error(f"判断工作日失败: {e}")
            return False
    
    async def get_month_calendar(self, year: int, month: int) -> Tuple[List[CalendarDay], MonthCapacity]:
        """
        获取指定月份的完整日历信息和产能统计
        
        Args:
            year: 年份
            month: 月份 (1-12)
            
        Returns:
            元组包含 (日历日期列表, 月度产能信息)
        """
        try:
            # 验证输入
            if not (1 <= month <= 12):
                raise ValueError("月份必须在 1-12 之间")
            
            month_key = f"{year:04d}-{month:02d}"
            
            # 检查缓存
            if month_key in self._calendar_cache:
                logger.debug(f"使用缓存的月度日历: {month_key}")
                calendar_days = self._calendar_cache[month_key]
            else:
                # 计算月份的开始和结束日期
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                
                logger.info(f"生成月度日历: {month_key} ({start_date} 至 {end_date})")
                
                # 查询月度日历配置
                calendar_days = await self._build_month_calendar(start_date, end_date)
                
                # 缓存结果
                self._calendar_cache[month_key] = calendar_days
            
            # 计算月度产能统计
            month_capacity = await self._calculate_month_capacity(calendar_days, month_key)
            
            return calendar_days, month_capacity
            
        except Exception as e:
            logger.error(f"获取月度日历失败: {e}")
            raise
    
    async def get_capacity_trend(
        self, 
        start_date: Union[str, date], 
        end_date: Union[str, date]
    ) -> Dict[str, Any]:
        """
        获取指定时间范围的产能趋势分析
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            产能趋势分析结果
        """
        try:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            # 获取日期范围内的所有日期信息
            all_days = []
            current_date = start_date
            
            while current_date <= end_date:
                stmt = select(APSWorkCalendar).where(APSWorkCalendar.date == current_date)
                result = await self.session.execute(stmt)
                calendar_record = result.scalars().first()
                
                calendar_day = await self._build_calendar_day(current_date, {current_date: calendar_record})
                all_days.append(calendar_day)
                current_date += timedelta(days=1)
            
            # 计算趋势统计
            working_days = [day for day in all_days if day.is_working]
            total_capacity = sum(day.capacity_factor for day in working_days)
            avg_capacity = total_capacity / len(working_days) if working_days else Decimal("0")
            
            # 按月分组统计
            monthly_stats = {}
            for day in all_days:
                month_key = day.date.strftime("%Y-%m")
                if month_key not in monthly_stats:
                    monthly_stats[month_key] = {
                        "working_days": 0,
                        "total_capacity": Decimal("0"),
                        "days": []
                    }
                
                monthly_stats[month_key]["days"].append(day)
                if day.is_working:
                    monthly_stats[month_key]["working_days"] += 1
                    monthly_stats[month_key]["total_capacity"] += day.capacity_factor
            
            return {
                "period": f"{start_date} 至 {end_date}",
                "total_days": len(all_days),
                "working_days": len(working_days),
                "average_capacity_factor": float(avg_capacity),
                "total_capacity_factor": float(total_capacity),
                "monthly_breakdown": {
                    month: {
                        "working_days": stats["working_days"],
                        "average_capacity": float(stats["total_capacity"] / stats["working_days"]) if stats["working_days"] > 0 else 0,
                        "total_capacity": float(stats["total_capacity"])
                    }
                    for month, stats in monthly_stats.items()
                }
            }
            
        except Exception as e:
            logger.error(f"获取产能趋势失败: {e}")
            raise
    
    async def _build_calendar_day(
        self, 
        target_date: date, 
        calendar_map: Dict[date, APSWorkCalendar]
    ) -> CalendarDay:
        """
        构建日历日期信息
        
        Args:
            target_date: 目标日期
            calendar_map: 日历记录映射
            
        Returns:
            日历日期信息
        """
        calendar_record = calendar_map.get(target_date)
        
        if calendar_record:
            # 使用数据库记录
            return CalendarDay(
                date=target_date,
                day_type=DayType(calendar_record.monthly_day_type),
                is_working=calendar_record.is_working_day,
                capacity_factor=Decimal(str(calendar_record.monthly_capacity_factor or "1.0")),
                description=calendar_record.monthly_notes,
                shift_count=len(calendar_record.get_shifts_config()) if calendar_record.monthly_shifts else 1,
                maintenance_hours=0,  # 可以从维护类型推导
                overtime_hours=0  # 可以从班次配置计算
            )
        else:
            # 使用默认规则
            weekday = target_date.weekday()
            is_weekend = weekday >= 5
            
            if is_weekend:
                day_type = DayType.WEEKEND
                is_working = False
                capacity_factor = self.config.holiday_capacity_factor
            else:
                day_type = DayType.WORKDAY
                is_working = True
                capacity_factor = self.config.default_capacity_factor
            
            return CalendarDay(
                date=target_date,
                day_type=day_type,
                is_working=is_working,
                capacity_factor=capacity_factor,
                description="系统默认" if not is_weekend else "周末"
            )
    
    async def _build_month_calendar(self, start_date: date, end_date: date) -> List[CalendarDay]:
        """
        构建月度日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            日历日期列表
        """
        # 查询数据库中的日历信息
        stmt = select(APSWorkCalendar).where(
            and_(
                APSWorkCalendar.calendar_date >= start_date,
                APSWorkCalendar.calendar_date <= end_date
            )
        ).order_by(APSWorkCalendar.calendar_date)
        
        result = await self.session.execute(stmt)
        calendar_records = result.scalars().all()
        
        # 构建日历映射
        calendar_map = {record.calendar_date: record for record in calendar_records}
        
        # 生成日期范围内的所有日期
        calendar_days = []
        current_date = start_date
        
        while current_date <= end_date:
            calendar_day = await self._build_calendar_day(current_date, calendar_map)
            calendar_days.append(calendar_day)
            current_date += timedelta(days=1)
        
        return calendar_days
    
    async def _calculate_month_capacity(self, calendar_days: List[CalendarDay], month_key: str) -> MonthCapacity:
        """
        计算月度产能统计
        
        Args:
            calendar_days: 日历日期列表
            month_key: 月份键 (YYYY-MM)
            
        Returns:
            月度产能信息
        """
        working_days = [day for day in calendar_days if day.is_working]
        total_capacity = sum(day.capacity_factor for day in working_days)
        avg_capacity = total_capacity / len(working_days) if working_days else Decimal("0")
        
        # 识别特殊日期
        peak_capacity_days = [day.date for day in working_days 
                             if day.capacity_factor >= self.config.overtime_capacity_factor]
        low_capacity_days = [day.date for day in working_days 
                            if day.capacity_factor <= self.config.reduced_capacity_factor]
        maintenance_days = [day.date for day in calendar_days 
                           if day.day_type == DayType.MAINTENANCE]
        
        return MonthCapacity(
            month=month_key,
            total_working_days=len(working_days),
            total_calendar_days=len(calendar_days),
            total_capacity_factor=total_capacity,
            average_daily_capacity=avg_capacity,
            peak_capacity_days=peak_capacity_days,
            low_capacity_days=low_capacity_days,
            maintenance_days=maintenance_days
        )
    
    async def process(self, input_data: Dict[str, Any]) -> AlgorithmResult:
        """
        处理算法请求
        
        Args:
            input_data: 输入数据
            
        Returns:
            算法处理结果
        """
        try:
            operation = input_data.get("operation", "get_month_calendar")
            
            if operation == "get_working_days":
                start_date = input_data["start_date"]
                end_date = input_data["end_date"]
                working_days = await self.get_working_days(start_date, end_date)
                
                return AlgorithmResult(
                    success=True,
                    data={
                        "working_days": [asdict(day) for day in working_days],
                        "count": len(working_days)
                    },
                    message=f"成功获取 {len(working_days)} 个工作日"
                )
            
            elif operation == "get_month_calendar":
                year = input_data["year"]
                month = input_data["month"]
                calendar_days, month_capacity = await self.get_month_calendar(year, month)
                
                return AlgorithmResult(
                    success=True,
                    data={
                        "calendar_days": [asdict(day) for day in calendar_days],
                        "month_capacity": asdict(month_capacity)
                    },
                    message=f"成功生成 {year}-{month:02d} 月度日历"
                )
            
            elif operation == "calculate_capacity":
                target_date = input_data["target_date"]
                base_capacity = Decimal(str(input_data.get("base_capacity", "1.0")))
                actual_capacity, calendar_day = await self.calculate_capacity(target_date, base_capacity)
                
                return AlgorithmResult(
                    success=True,
                    data={
                        "actual_capacity": float(actual_capacity),
                        "calendar_day": asdict(calendar_day)
                    },
                    message=f"成功计算日期 {target_date} 的产能"
                )
            
            elif operation == "capacity_trend":
                start_date = input_data["start_date"]
                end_date = input_data["end_date"]
                trend_data = await self.get_capacity_trend(start_date, end_date)
                
                return AlgorithmResult(
                    success=True,
                    data=trend_data,
                    message=f"成功分析产能趋势: {start_date} 至 {end_date}"
                )
            
            else:
                return AlgorithmResult(
                    success=False,
                    message=f"不支持的操作: {operation}"
                )
                
        except Exception as e:
            logger.error(f"算法处理失败: {e}")
            return AlgorithmResult(
                success=False,
                message=f"算法处理失败: {str(e)}"
            )


async def create_calendar_service(session: Optional[AsyncSession] = None) -> MonthlyCalendarService:
    """
    创建月度日历服务实例
    
    Args:
        session: 可选的数据库会话，如未提供则创建新会话
        
    Returns:
        月度日历服务实例
    """
    if session is None:
        session = await get_async_session().__anext__()
    
    return MonthlyCalendarService(session)


# CLI 支持
def create_cli_parser() -> argparse.ArgumentParser:
    """创建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        description="月度工作日历集成服务 - 提供工作日查询、产能计算等功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --working-days 2025-01-01 2025-01-31    # 获取工作日
  %(prog)s --month-calendar 2025 1                 # 获取月度日历
  %(prog)s --capacity 2025-01-15                   # 计算产能
  %(prog)s --capacity-trend 2025-01-01 2025-03-31  # 产能趋势
        """
    )
    
    parser.add_argument("--version", action="version", version=f"月度日历服务 v{__version__}")
    
    # 输出格式选项
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--format", choices=["table", "csv", "json"], default="table", 
                       help="输出格式 (默认: table)")
    
    # 功能选项
    parser.add_argument("--working-days", nargs=2, metavar=("START_DATE", "END_DATE"),
                       help="获取工作日信息 (格式: YYYY-MM-DD)")
    parser.add_argument("--month-calendar", nargs=2, type=int, metavar=("YEAR", "MONTH"),
                       help="获取月度日历 (例: 2025 1)")
    parser.add_argument("--capacity", metavar="DATE", help="计算指定日期产能 (格式: YYYY-MM-DD)")
    parser.add_argument("--capacity-trend", nargs=2, metavar=("START_DATE", "END_DATE"),
                       help="分析产能趋势 (格式: YYYY-MM-DD)")
    parser.add_argument("--is-working", metavar="DATE", help="判断是否工作日 (格式: YYYY-MM-DD)")
    
    return parser


async def main():
    """CLI 主函数"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    try:
        # 创建服务实例
        service = await create_calendar_service()
        
        # 处理不同的命令
        if args.working_days:
            start_date, end_date = args.working_days
            working_days = await service.get_working_days(start_date, end_date)
            
            if args.json or args.format == "json":
                result = [asdict(day) for day in working_days]
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            else:
                print(f"工作日信息 ({start_date} 至 {end_date}):")
                print("-" * 60)
                for day in working_days:
                    print(f"{day.date} | {day.day_type.value} | 产能因子: {day.capacity_factor}")
        
        elif args.month_calendar:
            year, month = args.month_calendar
            calendar_days, month_capacity = await service.get_month_calendar(year, month)
            
            if args.json or args.format == "json":
                result = {
                    "calendar_days": [asdict(day) for day in calendar_days],
                    "month_capacity": asdict(month_capacity)
                }
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            else:
                print(f"{year}-{month:02d} 月度日历:")
                print("-" * 80)
                print(f"总天数: {month_capacity.total_calendar_days}")
                print(f"工作日: {month_capacity.total_working_days}")
                print(f"平均产能: {month_capacity.average_daily_capacity}")
                print(f"总产能因子: {month_capacity.total_capacity_factor}")
        
        elif args.capacity:
            target_date = args.capacity
            actual_capacity, calendar_day = await service.calculate_capacity(target_date)
            
            if args.json or args.format == "json":
                result = {
                    "date": target_date,
                    "actual_capacity": float(actual_capacity),
                    "calendar_day": asdict(calendar_day)
                }
                print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            else:
                print(f"日期: {target_date}")
                print(f"日期类型: {calendar_day.day_type.value}")
                print(f"是否工作日: {'是' if calendar_day.is_working else '否'}")
                print(f"产能因子: {calendar_day.capacity_factor}")
                print(f"实际产能: {actual_capacity}")
        
        elif args.capacity_trend:
            start_date, end_date = args.capacity_trend
            trend_data = await service.get_capacity_trend(start_date, end_date)
            
            if args.json or args.format == "json":
                print(json.dumps(trend_data, ensure_ascii=False, indent=2, default=str))
            else:
                print(f"产能趋势分析 ({start_date} 至 {end_date}):")
                print("-" * 60)
                print(f"总天数: {trend_data['total_days']}")
                print(f"工作日: {trend_data['working_days']}")
                print(f"平均产能因子: {trend_data['average_capacity_factor']:.2f}")
                print(f"总产能因子: {trend_data['total_capacity_factor']:.2f}")
        
        elif args.is_working:
            target_date = args.is_working
            is_working = await service.is_working_day(target_date)
            
            if args.json or args.format == "json":
                result = {"date": target_date, "is_working_day": is_working}
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"{target_date}: {'工作日' if is_working else '非工作日'}")
        
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"CLI 执行失败: {e}")
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))