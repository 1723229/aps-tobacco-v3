"""
APS智慧排产系统 - 月度工作日历模型

MonthlyWorkCalendar模型实现
专用于月计划排产的工作日历管理，与现有decade系统完全独立

关键特性：
- 独立的日历数据模型，避免与现有旬计划冲突
- 支持中国法定节假日、周末、维护日的配置
- 多班次配置支持（JSON格式存储）
- 产能系数调整机制
- 完整的审计字段和索引优化

依赖：
- SQLAlchemy 2.0.23 异步ORM
- 基于现有 app.db.connection.Base
- 符合现有模型命名约定
"""

from sqlalchemy import Column, BigInteger, String, Integer, Date, Enum, Text, DECIMAL, TIMESTAMP, Index, JSON
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import json

# 导入现有数据库基类
from app.db.connection import Base


class MonthlyWorkCalendar(Base):
    """
    月度工作日历模型
    
    业务职责：
    - 管理月度排产专用的工作日历
    - 存储工作日、周末、节假日、维护日信息
    - 支持多班次配置和产能系数调整
    - 为月度排产算法提供时间约束数据
    
    表结构对应：aps_monthly_work_calendar
    冲突避免：使用monthly_前缀，与现有decade系统完全隔离
    """
    __tablename__ = "aps_monthly_work_calendar"
    
    # 主键
    monthly_calendar_id = Column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True, 
        comment='日历记录唯一标识'
    )
    
    # 日期信息
    calendar_date = Column(
        Date, 
        nullable=False, 
        unique=True,
        comment='日历日期'
    )
    calendar_year = Column(
        Integer, 
        nullable=False, 
        comment='年份'
    )
    calendar_month = Column(
        Integer, 
        nullable=False, 
        comment='月份'
    )
    calendar_day = Column(
        Integer, 
        nullable=False, 
        comment='日期'
    )
    calendar_week_day = Column(
        Integer, 
        nullable=False, 
        comment='星期几(1-7, 1=星期一)'
    )
    
    # 工作日类型 - 使用月度特化枚举避免冲突
    monthly_day_type = Column(
        Enum('WORKDAY', 'WEEKEND', 'HOLIDAY', 'MAINTENANCE', name='monthly_day_type_enum'),
        default='WORKDAY',
        comment='日期类型'
    )
    monthly_is_working = Column(
        TINYINT(1), 
        default=1, 
        comment='是否工作日（1=工作，0=非工作）'
    )
    
    # 班次信息（JSON格式支持多班次）
    monthly_shifts = Column(
        JSON,
        comment='班次配置JSON: [{"shift_name":"白班","start":"08:00","end":"16:00","capacity_factor":1.0}]'
    )
    monthly_total_hours = Column(
        DECIMAL(4, 2), 
        default=8.00, 
        comment='当日总工作小时数'
    )
    
    # 容量系数（支持节假日前后、维护日等的产能调整）
    monthly_capacity_factor = Column(
        DECIMAL(4, 3), 
        default=1.000, 
        comment='产能系数（0.0-2.0）'
    )
    
    # 特殊标记
    monthly_holiday_name = Column(
        String(100), 
        comment='节假日名称（如果是节假日）'
    )
    monthly_maintenance_type = Column(
        String(50), 
        comment='维护类型（如果是维护日）'
    )
    monthly_notes = Column(
        Text, 
        comment='备注信息'
    )
    
    # 审计字段
    created_time = Column(
        TIMESTAMP, 
        default=func.current_timestamp(), 
        comment='记录创建时间'
    )
    updated_time = Column(
        TIMESTAMP, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='记录更新时间'
    )
    
    # 索引配置 - 优化月度查询性能
    __table_args__ = (
        Index('uk_monthly_calendar_date', 'calendar_date', unique=True),
        Index('idx_monthly_calendar_ym', 'calendar_year', 'calendar_month'),
        Index('idx_monthly_calendar_working', 'monthly_is_working'),
        Index('idx_monthly_calendar_type', 'monthly_day_type'),
        {'comment': '月度工作日历表-专用于月计划排产的日历管理（独立于decade系统）'}
    )
    
    def __repr__(self):
        """字符串表示"""
        return f"<MonthlyWorkCalendar(date={self.calendar_date}, type={self.monthly_day_type}, working={bool(self.monthly_is_working)})>"
    
    # 业务方法
    
    @property
    def is_working_day(self) -> bool:
        """判断是否为工作日"""
        return bool(self.monthly_is_working)
    
    @property
    def effective_capacity_factor(self) -> float:
        """获取有效产能系数"""
        if not self.is_working_day:
            return 0.0
        return float(self.monthly_capacity_factor or 1.0)
    
    @property
    def effective_working_hours(self) -> float:
        """获取有效工作小时数（考虑产能系数）"""
        base_hours = float(self.monthly_total_hours or 8.0)
        return base_hours * self.effective_capacity_factor
    
    def get_shifts_config(self) -> List[Dict[str, Any]]:
        """
        获取班次配置
        
        Returns:
            班次配置列表，默认返回标准单班次
        """
        if self.monthly_shifts:
            try:
                if isinstance(self.monthly_shifts, str):
                    return json.loads(self.monthly_shifts)
                elif isinstance(self.monthly_shifts, list):
                    return self.monthly_shifts
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 默认单班次配置
        return [{
            "shift_name": "标准班",
            "start": "08:00",
            "end": "16:00",
            "capacity_factor": 1.0
        }]
    
    def set_shifts_config(self, shifts: List[Dict[str, Any]]) -> None:
        """
        设置班次配置
        
        Args:
            shifts: 班次配置列表
        """
        self.monthly_shifts = shifts
        # 重新计算总工作小时数
        total_hours = 0.0
        for shift in shifts:
            try:
                start_time = datetime.strptime(shift["start"], "%H:%M")
                end_time = datetime.strptime(shift["end"], "%H:%M")
                hours = (end_time - start_time).total_seconds() / 3600
                total_hours += hours * shift.get("capacity_factor", 1.0)
            except (ValueError, KeyError):
                continue
        self.monthly_total_hours = total_hours
    
    def is_holiday(self) -> bool:
        """判断是否为节假日"""
        return self.monthly_day_type == 'HOLIDAY'
    
    def is_weekend(self) -> bool:
        """判断是否为周末"""
        return self.monthly_day_type == 'WEEKEND'
    
    def is_maintenance_day(self) -> bool:
        """判断是否为维护日"""
        return self.monthly_day_type == 'MAINTENANCE'
    
    def get_day_type_display(self) -> str:
        """获取日期类型的中文显示"""
        type_map = {
            'WORKDAY': '工作日',
            'WEEKEND': '周末',
            'HOLIDAY': '节假日',
            'MAINTENANCE': '维护日'
        }
        return type_map.get(self.monthly_day_type, '未知')
    
    @classmethod
    def create_workday(
        cls,
        calendar_date: date,
        total_hours: float = 8.0,
        capacity_factor: float = 1.0,
        shifts: Optional[List[Dict[str, Any]]] = None
    ) -> 'MonthlyWorkCalendar':
        """
        创建工作日记录的便捷方法
        
        Args:
            calendar_date: 日历日期
            total_hours: 总工作小时数
            capacity_factor: 产能系数
            shifts: 班次配置
            
        Returns:
            MonthlyWorkCalendar实例
        """
        instance = cls(
            calendar_date=calendar_date,
            calendar_year=calendar_date.year,
            calendar_month=calendar_date.month,
            calendar_day=calendar_date.day,
            calendar_week_day=calendar_date.isoweekday(),
            monthly_day_type='WORKDAY',
            monthly_is_working=1,
            monthly_total_hours=total_hours,
            monthly_capacity_factor=capacity_factor
        )
        
        if shifts:
            instance.set_shifts_config(shifts)
        
        return instance
    
    @classmethod
    def create_holiday(
        cls,
        calendar_date: date,
        holiday_name: str,
        notes: Optional[str] = None
    ) -> 'MonthlyWorkCalendar':
        """
        创建节假日记录的便捷方法
        
        Args:
            calendar_date: 日历日期
            holiday_name: 节假日名称
            notes: 备注信息
            
        Returns:
            MonthlyWorkCalendar实例
        """
        return cls(
            calendar_date=calendar_date,
            calendar_year=calendar_date.year,
            calendar_month=calendar_date.month,
            calendar_day=calendar_date.day,
            calendar_week_day=calendar_date.isoweekday(),
            monthly_day_type='HOLIDAY',
            monthly_is_working=0,
            monthly_total_hours=0.0,
            monthly_capacity_factor=0.0,
            monthly_holiday_name=holiday_name,
            monthly_notes=notes
        )
    
    @classmethod
    def create_maintenance_day(
        cls,
        calendar_date: date,
        maintenance_type: str,
        notes: Optional[str] = None
    ) -> 'MonthlyWorkCalendar':
        """
        创建维护日记录的便捷方法
        
        Args:
            calendar_date: 日历日期
            maintenance_type: 维护类型
            notes: 备注信息
            
        Returns:
            MonthlyWorkCalendar实例
        """
        return cls(
            calendar_date=calendar_date,
            calendar_year=calendar_date.year,
            calendar_month=calendar_date.month,
            calendar_day=calendar_date.day,
            calendar_week_day=calendar_date.isoweekday(),
            monthly_day_type='MAINTENANCE',
            monthly_is_working=0,
            monthly_total_hours=0.0,
            monthly_capacity_factor=0.0,
            monthly_maintenance_type=maintenance_type,
            monthly_notes=notes
        )


# 模型元数据 - 用于文档生成和调试
__model_metadata__ = {
    "name": "MonthlyWorkCalendar",
    "table": "aps_monthly_work_calendar",
    "purpose": "月度工作日历管理",
    "conflict_avoidance": "使用monthly_前缀避免与decade系统冲突",
    "features": [
        "工作日/节假日/维护日管理",
        "多班次JSON配置支持",
        "产能系数调整机制",
        "完整的审计跟踪",
        "便捷的创建方法"
    ],
    "indexes": [
        "uk_monthly_calendar_date (unique)",
        "idx_monthly_calendar_ym",
        "idx_monthly_calendar_working",
        "idx_monthly_calendar_type"
    ]
}