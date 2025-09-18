"""
APS智慧排产系统 - 月度排产结果模型

MonthlyScheduleResult模型实现
存储月度排产算法执行后的机台时间分配结果

关键特性：
- 独立的月度排产结果模型，与现有decade系统完全隔离
- 支持完整的机台时间窗口分配
- 算法决策信息追踪
- 工作日历约束集成
- 排产状态和执行进度管理
- 完整的约束验证和业务规则

依赖：
- SQLAlchemy 2.0.23 异步ORM
- 基于现有 app.db.connection.Base
- 外键关联MonthlyPlan模型
- 符合现有模型命名约定和冲突避免原则
"""

from sqlalchemy import Column, BigInteger, String, Integer, DECIMAL, DateTime, Text, TIMESTAMP, Index, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
import json

# 导入现有数据库基类
from app.db.connection import Base


class MonthlyScheduleResult(Base):
    """
    月度排产结果模型
    
    业务职责：
    - 存储月度排产算法执行后的详细结果
    - 管理机台时间窗口分配
    - 跟踪算法决策过程和优化信息
    - 提供排产状态和执行进度管理
    - 支持工作日历约束的集成验证
    - 为工单生成和甘特图展示提供数据基础
    
    表结构对应：aps_monthly_schedule_result
    冲突避免：使用monthly_前缀，与现有decade系统完全隔离
    """
    __tablename__ = "aps_monthly_schedule_result"
    
    # 主键
    monthly_schedule_id = Column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True, 
        comment='排产结果唯一标识'
    )
    monthly_task_id = Column(
        String(100), 
        nullable=False, 
        comment='排产任务ID'
    )
    
    # 关联月计划记录
    monthly_plan_id = Column(
        BigInteger, 
        ForeignKey('aps_monthly_plan.monthly_plan_id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False, 
        comment='关联的月计划记录ID'
    )
    monthly_batch_id = Column(
        String(100), 
        nullable=False, 
        comment='月度导入批次ID'
    )
    
    # 排产核心信息
    work_order_nr = Column(
        String(100), 
        nullable=False, 
        comment='工单号'
    )
    article_nr = Column(
        String(100), 
        nullable=False, 
        comment='品牌规格代码'
    )
    
    # 分配的机台信息
    assigned_feeder_code = Column(
        String(50), 
        comment='分配的喂丝机代码'
    )
    assigned_maker_code = Column(
        String(50), 
        comment='分配的卷包机代码'
    )
    machine_group = Column(
        String(50), 
        comment='机台组别'
    )
    
    # 时间窗口分配
    scheduled_start_time = Column(
        DateTime, 
        nullable=False, 
        comment='排产开始时间'
    )
    scheduled_end_time = Column(
        DateTime, 
        nullable=False, 
        comment='排产结束时间'
    )
    scheduled_duration_hours = Column(
        DECIMAL(8, 2), 
        comment='排产时长（小时）'
    )
    
    # 产量分配（单位：箱）
    allocated_boxes = Column(
        Integer, 
        nullable=False,
        comment='分配产量（箱）'
    )
    estimated_speed = Column(
        DECIMAL(8, 2), 
        comment='预估速度（箱/小时）'
    )
    
    # 算法决策信息
    algorithm_version = Column(
        String(50), 
        comment='使用的算法版本'
    )
    priority_score = Column(
        DECIMAL(8, 4), 
        comment='优先级分数'
    )
    constraint_violations = Column(
        Text, 
        comment='约束违反记录'
    )
    optimization_notes = Column(
        Text, 
        comment='优化备注'
    )
    
    # 注释：工作日历关联字段暂时不使用
    
    # 状态管理
    schedule_status = Column(
        Enum('SCHEDULED', 'OPTIMIZED', 'CONFIRMED', 'EXECUTED', name='schedule_status_enum'),
        default='SCHEDULED',
        comment='排产状态'
    )
    execution_progress = Column(
        DECIMAL(5, 2), 
        default=0.00, 
        comment='执行进度（百分比）'
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
        default='monthly_algorithm', 
        comment='创建者'
    )
    
    # 关系定义
    monthly_plan = relationship("MonthlyPlan", back_populates="schedule_results")
    
    # 索引配置和约束
    __table_args__ = (
        Index('idx_schedule_batch', 'monthly_batch_id'),
        Index('idx_schedule_plan', 'monthly_plan_id'),
        Index('idx_schedule_order', 'work_order_nr'),
        Index('idx_schedule_time', 'scheduled_start_time', 'scheduled_end_time'),
        Index('idx_schedule_machine', 'assigned_feeder_code', 'assigned_maker_code'),
        Index('idx_schedule_status', 'schedule_status'),
        Index('idx_article', 'article_nr'),
        {'comment': '月度排产结果表-存储算法执行后的排产结果（单位：箱）'}
    )
    
    def __repr__(self):
        """字符串表示"""
        return f"<MonthlyScheduleResult(id={self.monthly_schedule_id}, article={self.article_nr}, machine={self.assigned_maker_code}, start={self.scheduled_start_time}, status={self.schedule_status})>"
    
    # 业务属性和方法
    
    @property
    def duration_hours(self) -> float:
        """获取排产时长（小时）"""
        if self.scheduled_duration_hours:
            return float(self.scheduled_duration_hours)
        
        if self.scheduled_start_time and self.scheduled_end_time:
            delta = self.scheduled_end_time - self.scheduled_start_time
            return delta.total_seconds() / 3600
        
        return 0.0
    
    @property
    def duration_days(self) -> float:
        """获取排产时长（天）"""
        return self.duration_hours / 24.0
    
    @property
    def is_active(self) -> bool:
        """判断排产是否处于活跃状态"""
        return self.schedule_status in ['SCHEDULED', 'EXECUTING']
    
    @property
    def is_completed(self) -> bool:
        """判断排产是否已完成"""
        return self.schedule_status == 'COMPLETED'
    
    @property
    def is_cancelled(self) -> bool:
        """判断排产是否已失败"""
        return self.schedule_status == 'FAILED'
    
    @property
    def progress_percentage(self) -> float:
        """获取执行进度百分比"""
        return float(self.execution_progress or 0.0)
    
    @property
    def estimated_completion_time(self) -> Optional[datetime]:
        """估算完成时间（基于当前进度）"""
        if not self.is_active or self.progress_percentage >= 100.0:
            return None
        
        if self.progress_percentage <= 0.0:
            return self.scheduled_end_time
        
        # 基于当前进度估算剩余时间
        elapsed_hours = self.duration_hours * (self.progress_percentage / 100.0)
        remaining_hours = self.duration_hours - elapsed_hours
        
        return datetime.now() + timedelta(hours=remaining_hours)
    
    def get_machine_codes(self) -> List[str]:
        """
        获取分配的机台代码列表
        
        Returns:
            机台代码列表
        """
        codes = []
        if self.assigned_feeder_code:
            codes.append(self.assigned_feeder_code)
        if self.assigned_maker_code:
            codes.append(self.assigned_maker_code)
        return codes
    
    # 日历约束相关方法已移除
    
    def add_constraint_violation(self, violation: str) -> None:
        """
        添加约束违反记录
        
        Args:
            violation: 违反信息
        """
        if self.constraint_violations:
            self.constraint_violations += f"; {violation}"
        else:
            self.constraint_violations = violation
    
    def clear_constraint_violations(self) -> None:
        """清除约束违反记录"""
        self.constraint_violations = None
    
    def update_progress(self, progress: float) -> None:
        """
        更新执行进度
        
        Args:
            progress: 进度百分比（0-100）
        """
        progress = max(0.0, min(100.0, progress))
        self.execution_progress = Decimal(str(progress))
        
        # 自动更新状态
        if progress >= 100.0:
            self.schedule_status = 'COMPLETED'
        elif progress > 0.0 and self.schedule_status == 'SCHEDULED':
            self.schedule_status = 'EXECUTING'
    
    def calculate_efficiency(self) -> Optional[float]:
        """
        计算排产效率（实际速度 vs 预估速度）
        
        Returns:
            效率比例（1.0 = 100%效率）
        """
        if not self.estimated_speed or not self.is_completed:
            return None
        
        actual_speed = float(self.allocated_quantity) / self.duration_hours
        return actual_speed / float(self.estimated_speed)
    
    def get_time_overlap(self, other: 'MonthlyScheduleResult') -> Optional[timedelta]:
        """
        计算与另一个排产记录的时间重叠
        
        Args:
            other: 另一个排产记录
            
        Returns:
            重叠时长，无重叠返回None
        """
        if not other or not isinstance(other, MonthlyScheduleResult):
            return None
        
        # 检查时间范围重叠
        start_overlap = max(self.scheduled_start_time, other.scheduled_start_time)
        end_overlap = min(self.scheduled_end_time, other.scheduled_end_time)
        
        if start_overlap < end_overlap:
            return end_overlap - start_overlap
        
        return None
    
    def has_machine_conflict(self, other: 'MonthlyScheduleResult') -> bool:
        """
        检查与另一个排产记录是否有机台冲突
        
        Args:
            other: 另一个排产记录
            
        Returns:
            是否有机台冲突
        """
        if not other or not isinstance(other, MonthlyScheduleResult):
            return False
        
        # 检查机台代码重叠
        self_machines = set(self.get_machine_codes())
        other_machines = set(other.get_machine_codes())
        
        return bool(self_machines & other_machines)
    
    def get_gantt_data(self) -> Dict[str, Any]:
        """
        获取甘特图显示数据
        
        Returns:
            甘特图数据字典
        """
        return {
            "id": str(self.monthly_schedule_id),
            "task_id": self.monthly_task_id,
            "work_order": self.monthly_work_order_nr,
            "article": self.monthly_article_nr,
            "machine_feeder": self.assigned_feeder_code,
            "machine_maker": self.assigned_maker_code,
            "start_time": self.scheduled_start_time.isoformat() if self.scheduled_start_time else None,
            "end_time": self.scheduled_end_time.isoformat() if self.scheduled_end_time else None,
            "duration_hours": self.duration_hours,
            "quantity": float(self.allocated_quantity),
            "boxes": self.allocated_boxes,
            "status": self.schedule_status,
            "progress": self.progress_percentage,
            "priority_score": float(self.priority_score) if self.priority_score else None
        }
    
    @classmethod
    def create_schedule_result(
        cls,
        task_id: str,
        plan_id: int,
        batch_id: str,
        work_order_nr: str,
        article_nr: str,
        start_time: datetime,
        end_time: datetime,
        allocated_quantity: Decimal,
        assigned_machines: Dict[str, str],
        algorithm_version: str = "v1.0",
        **kwargs
    ) -> 'MonthlyScheduleResult':
        """
        创建排产结果记录的便捷方法
        
        Args:
            task_id: 任务ID
            plan_id: 月计划ID
            batch_id: 批次ID
            work_order_nr: 工单号
            article_nr: 牌号代码
            start_time: 开始时间
            end_time: 结束时间
            allocated_quantity: 分配产量
            assigned_machines: 分配的机台 {"feeder": "F001", "maker": "M001"}
            algorithm_version: 算法版本
            **kwargs: 其他可选字段
            
        Returns:
            MonthlyScheduleResult实例
        """
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600
        
        instance = cls(
            monthly_task_id=task_id,
            monthly_plan_id=plan_id,
            monthly_batch_id=batch_id,
            work_order_nr=work_order_nr,
            article_nr=article_nr,
            scheduled_start_time=start_time,
            scheduled_end_time=end_time,
            scheduled_duration_hours=Decimal(str(duration_hours)),
            allocated_boxes=int(allocated_quantity) if allocated_quantity else 0,
            assigned_feeder_code=assigned_machines.get('feeder'),
            assigned_maker_code=assigned_machines.get('maker'),
            algorithm_version=algorithm_version
        )
        
        # 设置其他可选字段
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        return instance


# 添加反向关系到MonthlyPlan模型
# 注意：这需要在MonthlyPlan模型中添加相应的relationship定义

# 模型元数据 - 用于文档生成和调试
__model_metadata__ = {
    "name": "MonthlyScheduleResult",
    "table": "aps_monthly_schedule_result",
    "purpose": "月度排产结果和机台时间分配管理",
    "conflict_avoidance": "使用monthly_前缀避免与decade系统冲突",
    "features": [
        "机台时间窗口分配",
        "算法决策信息追踪",
        "工作日历约束集成",
        "排产状态和进度管理",
        "时间冲突检测",
        "甘特图数据支持",
        "效率计算和分析"
    ],
    "indexes": [
        "idx_monthly_task",
        "idx_monthly_schedule_batch", 
        "idx_monthly_schedule_plan",
        "idx_monthly_schedule_article",
        "idx_monthly_schedule_machine",
        "idx_monthly_schedule_time",
        "idx_schedule_status",
        "uk_monthly_schedule_unique (unique)"
    ],
    "relationships": {
        "monthly_plan": "多对一关联MonthlyPlan",
        "work_calendar": "通过时间范围关联MonthlyWorkCalendar"
    }
}