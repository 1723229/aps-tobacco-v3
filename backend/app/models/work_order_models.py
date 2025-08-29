"""
APS智慧排产系统 - 工单结果数据模型

实现卷包机和喂丝机工单的数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Enum, DECIMAL, Boolean, Date, JSON, Text
from sqlalchemy.sql import func
from app.db.connection import Base
import enum


class WorkOrderStatus(enum.Enum):
    """工单状态枚举"""
    PENDING = "PENDING"
    PLANNED = "PLANNED"  # 添加 PLANNED 状态以兼容现有数据
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderStatus(enum.Enum):
    """订单状态枚举"""
    PLANNED = "PLANNED"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PackingOrder(Base):
    """卷包机工单表 - 对应 aps_packing_order"""
    __tablename__ = "aps_packing_order"
    
    # 基础字段
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    work_order_nr = Column(String(50), nullable=False, unique=True, comment='工单号')
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    original_order_nr = Column(String(50), comment='原始订单号')
    article_nr = Column(String(100), nullable=False, comment='成品烟牌号')
    quantity_total = Column(Integer, nullable=False, comment='投料总量（箱）')
    final_quantity = Column(Integer, nullable=False, comment='成品数量（箱）')
    maker_code = Column(String(20), nullable=False, comment='卷包机代码')
    machine_type = Column(String(50), comment='机台型号')
    
    # 时间和计划字段
    planned_start = Column(DateTime, nullable=False, comment='计划开始时间')
    planned_end = Column(DateTime, nullable=False, comment='计划结束时间')
    estimated_duration = Column(Integer, comment='预计耗时（分钟）')
    sequence = Column(Integer, nullable=False, comment='执行顺序（同一天内从1开始）')
    unit = Column(String(20), nullable=False, default='箱', comment='基本单位')
    plan_date = Column(Date, nullable=False, comment='计划日期（YYYY-MM-DD）')
    production_speed = Column(Integer, comment='生产速度（支/分钟）')
    working_shifts = Column(JSON, comment='工作班次信息（JSON）')
    feeder_code = Column(String(20), nullable=False, comment='对应喂丝机代码')
    related_feeder_order = Column(String(50), comment='关联喂丝机工单号')
    
    # 状态和控制字段
    order_status = Column(Enum(OrderStatus), default=OrderStatus.PLANNED, comment='工单状态')
    priority = Column(Integer, default=5, comment='优先级（1-10，数值越小优先级越高）')
    is_split_order = Column(Boolean, default=False, comment='是否为拆分工单')
    split_from = Column(String(50), comment='拆分来源工单号')
    split_index = Column(Integer, comment='拆分序号')
    is_merged_order = Column(Boolean, default=False, comment='是否为合并工单')
    merged_from = Column(JSON, comment='合并来源工单列表（JSON）')
    is_backup_order = Column(Boolean, default=False, comment='是否为备用工单')
    backup_reason = Column(String(200), comment='备用原因')
    processing_history = Column(JSON, comment='处理历史记录（JSON）')
    created_by = Column(String(100), default='system', comment='创建者')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 兼容字段（为了保持向后兼容）
    work_order_type = Column(String(10), nullable=False, comment='工单类型')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    product_code = Column(String(100), nullable=False, comment='产品代码')
    plan_quantity = Column(Integer, nullable=False, comment='计划数量')
    work_order_status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, comment='工单状态')
    planned_start_time = Column(DateTime, comment='计划开始时间')
    planned_end_time = Column(DateTime, comment='计划结束时间')
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')


class FeedingOrder(Base):
    """喂丝机工单表 - 对应 aps_feeding_order"""
    __tablename__ = "aps_feeding_order"
    
    # 基础字段
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    work_order_nr = Column(String(50), nullable=False, unique=True, comment='工单号')
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    article_nr = Column(String(100), nullable=False, comment='成品烟牌号')
    quantity_total = Column(Integer, nullable=False, comment='总供料量（箱）')
    base_quantity = Column(Integer, nullable=False, comment='基础需求量（箱）')
    safety_stock = Column(Integer, default=0, comment='安全库存（箱）')
    feeder_code = Column(String(20), nullable=False, comment='喂丝机代码')
    feeder_type = Column(String(50), comment='喂丝机型号')
    production_lines = Column(Text, comment='生产线列表（支持多机台，逗号分隔）')
    
    # 时间和计划字段
    planned_start = Column(DateTime, nullable=False, comment='计划开始时间')
    planned_end = Column(DateTime, nullable=False, comment='计划结束时间')
    estimated_duration = Column(Integer, comment='预计耗时（分钟）')
    sequence = Column(Integer, nullable=False, comment='执行顺序（同一天内从1开始）')
    unit = Column(String(20), nullable=False, default='公斤', comment='基本单位')
    plan_date = Column(Date, nullable=False, comment='计划日期（YYYY-MM-DD）')
    feeding_speed = Column(DECIMAL(10,2), comment='喂丝速度（箱/小时）')
    material_consumption = Column(JSON, comment='物料消耗信息（JSON）')
    related_packing_orders = Column(JSON, nullable=False, comment='关联卷包机工单列表（JSON）')
    packing_machines = Column(JSON, nullable=False, comment='对应卷包机列表（JSON）')
    
    # 状态和控制字段
    order_status = Column(Enum(OrderStatus), default=OrderStatus.PLANNED, comment='工单状态')
    priority = Column(Integer, default=5, comment='优先级（1-10，数值越小优先级越高）')
    created_by = Column(String(100), default='system', comment='创建者')
    
    # 审计字段
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 兼容字段（为了保持向后兼容）
    work_order_type = Column(String(10), nullable=False, comment='工单类型')
    machine_type = Column(String(20), nullable=False, comment='机台类型')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    product_code = Column(String(100), nullable=False, comment='产品代码')
    plan_quantity = Column(Integer, nullable=False, comment='计划数量')
    work_order_status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, comment='工单状态')
    planned_start_time = Column(DateTime, comment='计划开始时间')
    planned_end_time = Column(DateTime, comment='计划结束时间')
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')