"""
APS智慧排产系统 - 排产任务和日志数据模型

实现排产任务管理和处理日志记录的数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Enum, DateTime, Integer, Text, JSON, Boolean, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.db.connection import Base
import enum


class SchedulingTaskStatus(enum.Enum):
    """排产任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LogLevel(enum.Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class SchedulingTask(Base):
    """排产任务表 - 对应 aps_scheduling_task"""
    __tablename__ = "aps_scheduling_task"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    task_id = Column(String(50), nullable=False, unique=True, comment='排产任务ID')
    import_batch_id = Column(String(50), nullable=False, comment='关联导入批次ID')
    task_name = Column(String(255), nullable=False, comment='任务名称')
    task_status = Column(Enum(SchedulingTaskStatus), default=SchedulingTaskStatus.PENDING, comment='任务状态')
    current_stage = Column(String(100), comment='当前阶段')
    progress = Column(Integer, default=0, comment='进度百分比(0-100)')
    total_records = Column(Integer, default=0, comment='总记录数')
    processed_records = Column(Integer, default=0, comment='已处理记录数')
    
    # 算法参数配置
    merge_enabled = Column(Boolean, default=True, comment='是否启用合并')
    split_enabled = Column(Boolean, default=True, comment='是否启用拆分')
    correction_enabled = Column(Boolean, default=True, comment='是否启用校正')
    parallel_enabled = Column(Boolean, default=True, comment='是否启用并行')
    
    # 执行时间信息
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    execution_duration = Column(Integer, comment='执行耗时（秒）')
    
    # 结果和错误信息
    error_message = Column(Text, comment='错误信息')
    result_summary = Column(JSON, comment='结果摘要（JSON格式）')
    
    # 审计字段
    created_by = Column(String(100), default='system', comment='创建者')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class ProcessingLog(Base):
    """排产处理日志表 - 对应 aps_processing_log"""
    __tablename__ = "aps_processing_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    stage = Column(String(100), nullable=False, comment='处理阶段')
    step_name = Column(String(200), nullable=False, comment='处理步骤名称')
    log_level = Column(Enum(LogLevel), default=LogLevel.INFO, comment='日志级别')
    log_message = Column(Text, nullable=False, comment='日志消息')
    processing_data = Column(JSON, comment='处理数据（JSON格式）')
    execution_time = Column(DateTime, nullable=False, default=func.now(), comment='执行时间')
    duration_ms = Column(Integer, comment='执行耗时（毫秒）')
    
    # 外键约束
    # 注意：实际部署时可以添加外键约束到 aps_scheduling_task
    # task_fk = Column(String(50), ForeignKey('aps_scheduling_task.task_id'), nullable=False)


class WorkOrderSequence(Base):
    """工单号序列表 - 对应 aps_work_order_sequence"""
    __tablename__ = "aps_work_order_sequence"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    order_type = Column(Enum('HWS', 'HJB', name='order_type_enum'), nullable=False, comment='工单类型：HWS-喂丝机,HJB-卷包机')
    sequence_date = Column(DateTime, nullable=False, comment='序列日期')
    current_sequence = Column(Integer, default=0, comment='当前序列号')
    last_order_nr = Column(String(50), comment='最后生成的工单号')
    
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class SystemConfig(Base):
    """系统参数配置表 - 对应 aps_system_config"""
    __tablename__ = "aps_system_config"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    config_key = Column(String(100), nullable=False, unique=True, comment='配置键')
    config_value = Column(Text, nullable=False, comment='配置值')
    config_type = Column(Enum('STRING', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'JSON', name='config_type_enum'), 
                        default='STRING', comment='配置类型')
    config_group = Column(String(50), comment='配置分组')
    config_description = Column(String(500), comment='配置描述')
    is_encrypted = Column(Boolean, default=False, comment='是否加密')
    status = Column(Enum('ACTIVE', 'INACTIVE', name='config_status_enum'), default='ACTIVE', comment='状态')
    
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')