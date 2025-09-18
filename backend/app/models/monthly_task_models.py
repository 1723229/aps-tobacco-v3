"""
APS智慧排产系统 - 月度排产任务模型

实现月度排产任务管理和处理日志记录的数据库模型
独立于现有decade排产系统，避免外键约束冲突

关键特性：
- 独立的月度排产任务模型，与现有decade_plan完全隔离
- 支持月度批次ID的外键关联到aps_monthly_plan
- 完整的任务状态和进度管理
- 月度特化的算法参数配置
- 执行日志和错误追踪
"""

from sqlalchemy import Column, BigInteger, String, Enum, DateTime, Integer, Text, JSON, Boolean, DECIMAL, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.connection import Base
import enum
from datetime import datetime
from typing import Optional, Dict, Any


class MonthlyTaskStatus(enum.Enum):
    """月度排产任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MonthlyLogLevel(enum.Enum):
    """月度日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class MonthlySchedulingTask(Base):
    """
    月度排产任务表
    
    业务职责：
    - 管理月度排产算法的执行任务
    - 跟踪月度排产进度和状态
    - 存储月度特化的算法配置
    - 提供月度排产结果的任务级管理
    - 支持月度批次的独立任务调度
    
    表结构对应：aps_monthly_scheduling_task
    冲突避免：完全独立的表结构，使用monthly_前缀
    """
    __tablename__ = "aps_monthly_scheduling_task"
    
    # 主键和基本信息
    monthly_task_id = Column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True, 
        comment='月度任务主键ID'
    )
    task_id = Column(
        String(100), 
        nullable=False, 
        unique=True, 
        comment='月度排产任务ID，格式：MONTHLY_TASK_YYYYMMDD_HHMMSS_XXXX'
    )
    monthly_batch_id = Column(
        String(100), 
        nullable=False, 
        comment='关联月度批次ID'
    )
    task_name = Column(
        String(255), 
        nullable=False, 
        comment='任务名称'
    )
    
    # 任务状态和进度
    task_status = Column(
        Enum(MonthlyTaskStatus), 
        default=MonthlyTaskStatus.PENDING, 
        comment='任务状态'
    )
    current_stage = Column(
        String(100), 
        comment='当前执行阶段'
    )
    progress = Column(
        Integer, 
        default=0, 
        comment='进度百分比(0-100)'
    )
    total_records = Column(
        Integer, 
        default=0, 
        comment='总记录数'
    )
    processed_records = Column(
        Integer, 
        default=0, 
        comment='已处理记录数'
    )
    
    # 月度算法配置参数
    optimization_level = Column(
        String(20), 
        default='medium', 
        comment='优化级别：low/medium/high'
    )
    enable_load_balancing = Column(
        Boolean, 
        default=True, 
        comment='是否启用负载均衡'
    )
    max_execution_time = Column(
        Integer, 
        default=300, 
        comment='最大执行时间（秒）'
    )
    target_efficiency = Column(
        DECIMAL(5, 4), 
        default=0.85, 
        comment='目标效率'
    )
    
    # 约束参数（JSON格式存储）
    constraints_config = Column(
        JSON, 
        comment='约束配置参数（JSON格式）'
    )
    algorithm_config = Column(
        JSON, 
        comment='算法配置参数（JSON格式）'
    )
    
    # 执行时间信息
    start_time = Column(
        DateTime, 
        comment='开始时间'
    )
    end_time = Column(
        DateTime, 
        comment='结束时间'
    )
    execution_duration = Column(
        Integer, 
        comment='执行耗时（秒）'
    )
    
    # 结果和错误信息
    error_message = Column(
        Text, 
        comment='错误信息'
    )
    result_summary = Column(
        JSON, 
        comment='结果摘要（JSON格式）'
    )
    algorithm_summary = Column(
        JSON, 
        comment='算法执行摘要（JSON格式）'
    )
    
    # 审计字段
    created_by = Column(
        String(100), 
        default='monthly_system', 
        comment='创建者'
    )
    created_time = Column(
        DateTime, 
        default=func.current_timestamp(), 
        comment='创建时间'
    )
    updated_time = Column(
        DateTime, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    
    # 关系定义 - 关联到月度计划（通过batch_id）
    # 注意：不使用直接外键，而是通过batch_id进行逻辑关联
    
    # 索引配置
    __table_args__ = (
        Index('idx_monthly_task_id', 'task_id'),
        Index('idx_monthly_batch_id', 'monthly_batch_id'),
        Index('idx_monthly_task_status', 'task_status'),
        Index('idx_monthly_created_time', 'created_time'),
        Index('idx_monthly_task_progress', 'task_status', 'progress'),
        {'comment': '月度排产任务表-独立管理月度排产算法执行'}
    )
    
    def __repr__(self):
        """字符串表示"""
        return f"<MonthlySchedulingTask(task_id={self.task_id}, batch_id={self.monthly_batch_id}, status={self.task_status}, progress={self.progress}%)>"
    
    # 业务属性和方法
    
    @property
    def is_running(self) -> bool:
        """判断任务是否正在运行"""
        return self.task_status in [MonthlyTaskStatus.PENDING, MonthlyTaskStatus.RUNNING]
    
    @property
    def is_completed(self) -> bool:
        """判断任务是否已完成"""
        return self.task_status == MonthlyTaskStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """判断任务是否失败"""
        return self.task_status == MonthlyTaskStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """判断任务是否可以重试"""
        return self.task_status in [MonthlyTaskStatus.FAILED, MonthlyTaskStatus.CANCELLED]
    
    @property
    def execution_time_seconds(self) -> Optional[int]:
        """获取实际执行时间（秒）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds())
        return self.execution_duration
    
    def update_progress(self, current: int, total: int, stage: str = None) -> None:
        """
        更新任务进度
        
        Args:
            current: 当前处理数量
            total: 总数量
            stage: 当前阶段描述
        """
        self.processed_records = current
        self.total_records = total
        if total > 0:
            self.progress = min(100, int((current / total) * 100))
        if stage:
            self.current_stage = stage
    
    def start_execution(self) -> None:
        """开始执行任务"""
        self.task_status = MonthlyTaskStatus.RUNNING
        self.start_time = datetime.now()
        self.current_stage = "开始执行"
        self.progress = 0
    
    def complete_execution(self, result_summary: Dict[str, Any] = None) -> None:
        """完成任务执行"""
        self.task_status = MonthlyTaskStatus.COMPLETED
        self.end_time = datetime.now()
        self.current_stage = "执行完成"
        self.progress = 100
        if result_summary:
            self.result_summary = result_summary
        
        # 计算执行时间
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_duration = int(delta.total_seconds())
    
    def fail_execution(self, error_message: str) -> None:
        """任务执行失败"""
        self.task_status = MonthlyTaskStatus.FAILED
        self.end_time = datetime.now()
        self.current_stage = "执行失败"
        self.error_message = error_message
        
        # 计算执行时间
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_duration = int(delta.total_seconds())
    
    def cancel_execution(self) -> None:
        """取消任务执行"""
        self.task_status = MonthlyTaskStatus.CANCELLED
        self.end_time = datetime.now()
        self.current_stage = "任务已取消"
        
        # 计算执行时间
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_duration = int(delta.total_seconds())
    
    def get_algorithm_config(self) -> Dict[str, Any]:
        """获取算法配置"""
        if self.algorithm_config:
            return self.algorithm_config
        
        # 返回默认配置
        return {
            "optimization_level": self.optimization_level or "medium",
            "enable_load_balancing": self.enable_load_balancing if self.enable_load_balancing is not None else True,
            "max_execution_time": self.max_execution_time or 300,
            "target_efficiency": float(self.target_efficiency) if self.target_efficiency else 0.85
        }
    
    def get_constraints_config(self) -> Dict[str, Any]:
        """获取约束配置"""
        if self.constraints_config:
            return self.constraints_config
        
        # 返回默认约束
        return {
            "working_hours_limit": 16,
            "maintenance_windows": [],
            "priority_articles": []
        }
    
    def set_algorithm_config(self, config: Dict[str, Any]) -> None:
        """设置算法配置"""
        self.algorithm_config = config
        
        # 同时更新单独字段（用于索引和查询）
        if "optimization_level" in config:
            self.optimization_level = config["optimization_level"]
        if "enable_load_balancing" in config:
            self.enable_load_balancing = config["enable_load_balancing"]
        if "max_execution_time" in config:
            self.max_execution_time = config["max_execution_time"]
        if "target_efficiency" in config:
            self.target_efficiency = config["target_efficiency"]
    
    def set_constraints_config(self, constraints: Dict[str, Any]) -> None:
        """设置约束配置"""
        self.constraints_config = constraints
    
    @classmethod
    def create_task(
        cls,
        task_id: str,
        monthly_batch_id: str,
        task_name: str,
        algorithm_config: Dict[str, Any] = None,
        constraints: Dict[str, Any] = None,
        created_by: str = "monthly_api_user"
    ) -> 'MonthlySchedulingTask':
        """
        创建月度排产任务的便捷方法
        
        Args:
            task_id: 任务ID
            monthly_batch_id: 月度批次ID
            task_name: 任务名称
            algorithm_config: 算法配置
            constraints: 约束配置
            created_by: 创建者
            
        Returns:
            MonthlySchedulingTask实例
        """
        task = cls(
            task_id=task_id,
            monthly_batch_id=monthly_batch_id,
            task_name=task_name,
            created_by=created_by
        )
        
        if algorithm_config:
            task.set_algorithm_config(algorithm_config)
        
        if constraints:
            task.set_constraints_config(constraints)
        
        return task


class MonthlyProcessingLog(Base):
    """
    月度排产处理日志表
    
    业务职责：
    - 记录月度排产算法执行的详细日志
    - 提供月度排产过程的可追溯性
    - 支持错误诊断和性能分析
    - 独立于decade系统的日志管理
    
    表结构对应：aps_monthly_processing_log
    """
    __tablename__ = "aps_monthly_processing_log"
    
    # 主键
    monthly_log_id = Column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True, 
        comment='月度日志主键ID'
    )
    
    # 关联任务
    task_id = Column(
        String(100), 
        nullable=False, 
        comment='关联的月度任务ID'
    )
    
    # 日志信息
    log_level = Column(
        Enum(MonthlyLogLevel), 
        default=MonthlyLogLevel.INFO, 
        comment='日志级别'
    )
    stage = Column(
        String(100), 
        comment='执行阶段'
    )
    message = Column(
        Text, 
        nullable=False, 
        comment='日志消息'
    )
    details = Column(
        JSON, 
        comment='详细信息（JSON格式）'
    )
    
    # 时间信息
    timestamp = Column(
        DateTime, 
        default=func.current_timestamp(), 
        comment='日志时间戳'
    )
    execution_time_ms = Column(
        Integer, 
        comment='执行耗时（毫秒）'
    )
    
    # 索引配置
    __table_args__ = (
        Index('idx_monthly_log_task_id', 'task_id'),
        Index('idx_monthly_log_level', 'log_level'),
        Index('idx_monthly_log_timestamp', 'timestamp'),
        Index('idx_monthly_log_stage', 'stage'),
        {'comment': '月度排产处理日志表-记录月度排产算法执行过程'}
    )
    
    def __repr__(self):
        """字符串表示"""
        return f"<MonthlyProcessingLog(task_id={self.task_id}, level={self.log_level}, stage={self.stage})>"
    
    @classmethod
    def create_log(
        cls,
        task_id: str,
        level: MonthlyLogLevel,
        message: str,
        stage: str = None,
        details: Dict[str, Any] = None,
        execution_time_ms: int = None
    ) -> 'MonthlyProcessingLog':
        """
        创建月度处理日志的便捷方法
        
        Args:
            task_id: 任务ID
            level: 日志级别
            message: 日志消息
            stage: 执行阶段
            details: 详细信息
            execution_time_ms: 执行耗时（毫秒）
            
        Returns:
            MonthlyProcessingLog实例
        """
        return cls(
            task_id=task_id,
            log_level=level,
            message=message,
            stage=stage,
            details=details,
            execution_time_ms=execution_time_ms
        )


# 模型元数据
__monthly_task_metadata__ = {
    "models": [
        {
            "name": "MonthlySchedulingTask",
            "table": "aps_monthly_scheduling_task",
            "purpose": "月度排产任务管理",
            "features": [
                "独立的月度任务调度",
                "月度特化的算法配置",
                "完整的任务状态管理",
                "执行进度追踪",
                "结果和错误管理"
            ]
        },
        {
            "name": "MonthlyProcessingLog", 
            "table": "aps_monthly_processing_log",
            "purpose": "月度排产处理日志",
            "features": [
                "详细的执行日志记录",
                "多级别日志管理",
                "阶段性进度追踪",
                "性能分析支持"
            ]
        }
    ],
    "conflict_avoidance": "使用monthly_前缀和独立表结构，完全避免与decade系统冲突",
    "database_schema": "需要创建对应的数据库表结构"
}