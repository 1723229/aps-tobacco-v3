"""
APS智慧排产系统 - 月度计划模型

MonthlyPlan模型实现
存储从Excel解析的月度生产计划基础数据

关键特性：
- 独立的月度计划数据模型，与现有decade_plan完全隔离
- 支持浙江中烟月度计划Excel格式的完整字段映射
- 专注于杭州卷烟厂数据处理
- 包含完整的Excel解析元数据追踪
- 数据验证状态管理
- 机台代码列表支持

依赖：
- SQLAlchemy 2.0.23 异步ORM
- 基于现有 app.db.connection.Base
- 符合现有模型命名约定和冲突避免原则
"""

from sqlalchemy import Column, BigInteger, String, Integer, DECIMAL, DateTime, Text, TIMESTAMP, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import json

# 导入现有数据库基类
from app.db.connection import Base


class MonthlyPlan(Base):
    """
    月度计划基础模型
    
    业务职责：
    - 存储从Excel解析的月度生产计划原始数据
    - 管理浙江中烟月度计划的完整信息
    - 提供杭州卷烟厂数据的专用处理逻辑
    - 支持Excel解析过程的完整追踪
    - 为月度排产算法提供基础数据
    
    表结构对应：aps_monthly_plan
    冲突避免：使用monthly_前缀，与现有decade_plan完全隔离
    """
    __tablename__ = "aps_monthly_plan"
    
    # 主键
    monthly_plan_id = Column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True, 
        comment='月计划记录唯一标识'
    )
    monthly_batch_id = Column(
        String(100), 
        nullable=False, 
        comment='月度导入批次ID，格式: MONTHLY_YYYYMMDD_HHMMSS_XXXX'
    )
    
    # Excel解析核心字段（与新表结构对应）
    article_nr = Column(
        String(100), 
        nullable=False, 
        comment='品牌规格代码（如：利群休闲、利群红利等）'
    )
    article_name = Column(
        String(200), 
        nullable=False, 
        comment='品牌规格名称'
    )
    
    # 时间信息（计划所属年月）
    plan_year = Column(
        Integer, 
        nullable=False, 
        comment='计划年份（如：2019）'
    )
    plan_month = Column(
        Integer, 
        nullable=False, 
        comment='计划月份（如：7）'
    )
    
    # 核心数量字段（单位：箱）
    target_quantity_boxes = Column(
        Integer, 
        default=0, 
        comment='原计划目标产量（箱）'
    )
    hard_pack_boxes = Column(
        Integer, 
        default=0, 
        comment='硬包数量（箱）'
    )
    soft_pack_boxes = Column(
        Integer, 
        default=0, 
        comment='软包数量（箱）'
    )
    # Excel解析元数据
    source_file = Column(
        String(500), 
        comment='源Excel文件路径'
    )
    source_row = Column(
        Integer, 
        comment='Excel行号'
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
    created_by = Column(
        String(50), 
        default='system', 
        comment='创建者'
    )
    
    # 关系定义
    schedule_results = relationship(
        "MonthlyScheduleResult", 
        back_populates="monthly_plan", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # 索引配置 - 优化月度查询性能
    __table_args__ = (
        Index('idx_monthly_batch', 'monthly_batch_id'),
        Index('idx_article', 'article_nr'),
        Index('idx_plan_time', 'plan_year', 'plan_month'),
        Index('idx_created', 'created_time'),
        Index('uk_monthly_plan_unique', 'monthly_batch_id', 'article_nr', unique=True),
        {'comment': '月计划基础表-存储Excel解析的杭州厂月度生产计划（品牌规格+原计划+硬包+软包，单位：箱）'}
    )
    
    def __repr__(self):
        """字符串表示"""
        return f"<MonthlyPlan(id={self.monthly_plan_id}, article={self.article_nr}, target_boxes={self.target_quantity_boxes}, year_month={self.plan_year}-{self.plan_month:02d})>"
    
    # 业务属性和方法
    
    @property
    def plan_period(self) -> str:
        """获取计划期间的字符串表示"""
        return f"{self.plan_year}-{self.plan_month:02d}"
    
    @property
    def total_quantity_boxes(self) -> int:
        """获取总数量（原计划+硬包+软包）"""
        total = (self.target_quantity_boxes or 0) + (self.hard_pack_boxes or 0) + (self.soft_pack_boxes or 0)
        return total
    
    @property
    def effective_boxes(self) -> int:
        """获取有效目标箱数"""
        return self.target_quantity_boxes or 0
    
    def is_valid_for_scheduling(self) -> bool:
        """
        判断是否可用于排产
        
        Returns:
            True如果数据有效且数量大于0
        """
        return (self.target_quantity_boxes or 0) > 0 and self.article_nr is not None
    
    @classmethod
    def create_from_excel_row(
        cls,
        batch_id: str,
        article_nr: str,
        article_name: str,
        plan_year: int,
        plan_month: int,
        target_quantity_boxes: int,
        hard_pack_boxes: int = 0,
        soft_pack_boxes: int = 0,
        source_file: str = None,
        source_row: int = None,
        **kwargs
    ) -> 'MonthlyPlan':
        """
        从Excel行数据创建月计划记录的便捷方法
        
        Args:
            batch_id: 批次ID
            article_nr: 品牌规格代码
            article_name: 品牌规格名称
            plan_year: 计划年份
            plan_month: 计划月份
            target_quantity_boxes: 原计划目标产量（箱）
            hard_pack_boxes: 硬包数量（箱）
            soft_pack_boxes: 软包数量（箱）
            source_file: 源文件路径
            source_row: 行号
            **kwargs: 其他可选字段
            
        Returns:
            MonthlyPlan实例
        """
        instance = cls(
            monthly_batch_id=batch_id,
            article_nr=article_nr,
            article_name=article_name,
            plan_year=plan_year,
            plan_month=plan_month,
            target_quantity_boxes=target_quantity_boxes,
            hard_pack_boxes=hard_pack_boxes,
            soft_pack_boxes=soft_pack_boxes,
            source_file=source_file,
            source_row=source_row
        )
        
        # 设置其他可选字段
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        return instance


# 模型元数据 - 用于文档生成和调试
__model_metadata__ = {
    "name": "MonthlyPlan",
    "table": "aps_monthly_plan",
    "purpose": "月度生产计划基础数据管理（杭州厂专用，单位：箱）",
    "features": [
        "Excel解析数据存储",
        "杭州卷烟厂数据专用处理",  
        "品牌规格+原计划+硬包+软包数据",
        "箱为基础单位",
        "简化的Excel元数据追踪"
    ],
    "indexes": [
        "idx_monthly_batch",
        "idx_article", 
        "idx_plan_time",
        "idx_created",
        "uk_monthly_plan_unique (unique)"
    ],
    "relationships": {
        "work_calendar": "通过plan_year/plan_month关联MonthlyWorkCalendar",
        "schedule_results": "一对多关联MonthlyScheduleResult"
    }
}