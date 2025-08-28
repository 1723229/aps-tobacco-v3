"""
APS智慧排产系统 - 工单结果数据模型

实现卷包机和喂丝机工单的数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Enum, DECIMAL, Boolean
from sqlalchemy.sql import func
from app.db.connection import Base
import enum


class WorkOrderStatus(enum.Enum):
    """工单状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PackingOrder(Base):
    """卷包机工单表 - 对应 aps_packing_order"""
    __tablename__ = "aps_packing_order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    work_order_nr = Column(String(50), nullable=False, unique=True, comment='工单号')
    work_order_type = Column(String(10), nullable=False, comment='工单类型')
    machine_type = Column(String(20), nullable=False, comment='机台类型')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    product_code = Column(String(100), nullable=False, comment='产品代码')
    plan_quantity = Column(Integer, nullable=False, comment='计划数量')
    work_order_status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, comment='工单状态')
    
    # 时间字段
    planned_start_time = Column(DateTime, comment='计划开始时间')
    planned_end_time = Column(DateTime, comment='计划结束时间')
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class FeedingOrder(Base):
    """喂丝机工单表 - 对应 aps_feeding_order"""
    __tablename__ = "aps_feeding_order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    work_order_nr = Column(String(50), nullable=False, unique=True, comment='工单号')
    work_order_type = Column(String(10), nullable=False, comment='工单类型')
    machine_type = Column(String(20), nullable=False, comment='机台类型')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    product_code = Column(String(100), nullable=False, comment='产品代码')
    plan_quantity = Column(Integer, nullable=False, comment='计划数量')
    safety_stock = Column(Integer, default=0, comment='安全库存数量')
    work_order_status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, comment='工单状态')
    
    # 时间字段
    planned_start_time = Column(DateTime, comment='计划开始时间')
    planned_end_time = Column(DateTime, comment='计划结束时间')
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')