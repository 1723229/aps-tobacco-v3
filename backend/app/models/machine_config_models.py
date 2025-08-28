"""
APS智慧排产系统 - 机台配置相关数据模型

实现机台速度、机台关系、班次配置等数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Integer, Time, Boolean, DECIMAL, DateTime, Text
from sqlalchemy.sql import func
from app.db.connection import Base
import enum


class MachineSpeedConfig(Base):
    """机台速度配置表 - 对应 aps_machine_speed_config"""
    __tablename__ = "aps_machine_speed_config"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    machine_type = Column(String(20), nullable=False, comment='机台类型')
    standard_speed = Column(Integer, nullable=False, comment='标准速度（每分钟）')
    max_speed = Column(Integer, nullable=False, comment='最大速度（每分钟）')
    min_speed = Column(Integer, nullable=False, comment='最小速度（每分钟）')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class MachineRelation(Base):
    """机台关系配置表 - 对应 aps_machine_relation"""
    __tablename__ = "aps_machine_relation"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    feeder_code = Column(String(20), nullable=False, comment='喂丝机代码')
    maker_code = Column(String(20), nullable=False, comment='卷包机代码')
    relation_type = Column(String(20), nullable=False, comment='关系类型')
    priority = Column(Integer, nullable=False, comment='优先级')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class MachineSpeed(Base):
    """机台速度表 - 对应 aps_machine_speed"""
    __tablename__ = "aps_machine_speed"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    article_nr = Column(String(100), nullable=False, comment='物料编号')
    speed = Column(DECIMAL(10, 2), nullable=False, comment='标准速度（每分钟）')
    efficiency_rate = Column(DECIMAL(5, 2), nullable=True, default=85.00, comment='效率率（百分比）')
    effective_from = Column(DateTime, nullable=False, comment='生效开始日期')
    effective_to = Column(DateTime, nullable=True, comment='生效结束日期')
    status = Column(String(10), nullable=True, default='ACTIVE', comment='状态')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class MaintenancePlan(Base):
    """维护计划表 - 对应 aps_maintenance_plan"""
    __tablename__ = "aps_maintenance_plan"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    maint_plan_no = Column(String(50), nullable=False, unique=True, comment='维护计划编号')
    schedule_date = Column(DateTime, nullable=False, comment='计划日期')
    shift_code = Column(String(20), nullable=True, comment='班次代码')
    maint_group = Column(String(50), nullable=True, comment='维护组')
    equipment_position = Column(String(50), nullable=False, comment='设备位置')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    maint_start_time = Column(DateTime, nullable=False, comment='维护开始时间')
    maint_end_time = Column(DateTime, nullable=False, comment='维护结束时间')
    estimated_duration = Column(Integer, nullable=True, comment='预计持续时间（分钟）')
    maint_type = Column(String(50), nullable=True, comment='维护类型')
    maint_level = Column(String(50), nullable=True, comment='维护级别')
    maint_description = Column(Text, nullable=True, comment='维护描述')
    plan_status = Column(String(20), default='PLANNED', comment='计划状态')
    sync_from_mes = Column(Boolean, default=True, comment='是否从MES同步')
    sync_time = Column(DateTime, nullable=True, comment='同步时间')
    mes_version = Column(String(50), nullable=True, comment='MES版本')
    planner = Column(String(100), nullable=True, comment='计划员')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class ShiftConfig(Base):
    """班次配置表 - 对应 aps_shift_config"""
    __tablename__ = "aps_shift_config"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    shift_name = Column(String(50), nullable=False, comment='班次名称')
    machine_name = Column(String(50), nullable=False, comment='机台名称')
    start_time = Column(Time, nullable=False, comment='开始时间')
    end_time = Column(Time, nullable=False, comment='结束时间')
    is_ot_needed = Column(Boolean, default=False, comment='是否需要加班')
    max_ot_duration = Column(Time, nullable=True, comment='最大加班时长')
    effective_from = Column(DateTime, nullable=False, comment='生效开始日期')
    effective_to = Column(DateTime, nullable=True, comment='生效结束日期')
    status = Column(String(10), nullable=True, default='ACTIVE', comment='状态')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')