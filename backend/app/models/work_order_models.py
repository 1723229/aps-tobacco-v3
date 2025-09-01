"""
APS智慧排产系统 - 工单结果数据模型（MES规范重构版）

实现完全符合MES接口规范的卷包机和喂丝机工单数据库模型
支持InputBatch结构和工单序列管理
"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Boolean, Date, DECIMAL, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.connection import Base
import enum


class OrderStatus(enum.Enum):
    """工单状态枚举 - 符合MES接口规范"""
    PLANNED = "PLANNED"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderType(enum.Enum):
    """工单类型枚举"""
    HWS = "HWS"  # 喂丝机工单
    HJB = "HJB"  # 卷包机工单


class FeedingOrder(Base):
    """喂丝机工单表 - 完全符合MES接口规范"""
    __tablename__ = "aps_feeding_order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    
    # MES核心字段（严格按照接口规范）
    plan_id = Column(String(50), nullable=False, unique=True, comment='计划ID，格式:HWS+9位流水号')
    production_line = Column(Text, nullable=False, comment='工序段，多个喂丝机代码逗号分隔')
    batch_code = Column(String(50), comment='批次号（喂丝机通常为空）')
    material_code = Column(String(100), nullable=False, comment='生产的物料代码')
    bom_revision = Column(String(50), comment='版本号')
    quantity = Column(String(20), comment='计划生产量（喂丝机通常为空）')
    plan_start_time = Column(DateTime, nullable=False, comment='计划开始时间')
    plan_end_time = Column(DateTime, nullable=False, comment='计划结束时间')
    sequence = Column(Integer, nullable=False, default=1, comment='执行顺序')
    shift = Column(String(10), comment='班次')
    
    # 工艺控制字段
    is_vaccum = Column(Boolean, default=False, comment='是否真空回潮')
    is_sh93 = Column(Boolean, default=False, comment='是否走SH93')
    is_hdt = Column(Boolean, default=False, comment='是否走HDT')
    is_flavor = Column(Boolean, default=False, comment='是否补香')
    unit = Column(String(20), default='公斤', comment='基本单位')
    plan_date = Column(Date, nullable=False, comment='计划日期')
    plan_output_quantity = Column(String(20), comment='计划产出量')
    is_outsourcing = Column(Boolean, default=False, comment='是否委外')
    is_backup = Column(Boolean, default=False, comment='是否备用工单')
    
    # 系统管理字段
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    order_status = Column(String(20), default='PLANNED', comment='工单状态')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class PackingOrder(Base):
    """卷包机工单表 - 完全符合MES接口规范"""
    __tablename__ = "aps_packing_order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    
    # MES核心字段（严格按照接口规范）
    plan_id = Column(String(50), nullable=False, unique=True, comment='计划ID，格式:HJB+9位流水号')
    production_line = Column(String(50), nullable=False, comment='工序段，单个卷包机代码')
    batch_code = Column(String(50), comment='批次号')
    material_code = Column(String(100), nullable=False, comment='生产的物料代码（牌号）')
    bom_revision = Column(String(50), comment='版本号')
    quantity = Column(Integer, nullable=False, comment='成品烟产量（箱）')
    plan_start_time = Column(DateTime, nullable=False, comment='计划开始时间')
    plan_end_time = Column(DateTime, nullable=False, comment='计划结束时间')
    sequence = Column(Integer, nullable=False, default=1, comment='执行顺序')
    shift = Column(String(10), comment='班次')
    
    # InputBatch前工序批次信息
    input_plan_id = Column(String(50), comment='前工序计划号（喂丝机工单号）')
    input_batch_code = Column(String(50), comment='前工序批次号')
    input_quantity = Column(String(20), comment='投入数量')
    batch_sequence = Column(String(10), comment='批次顺序')
    is_whole_batch = Column(Boolean, comment='是否整批')
    is_main_channel = Column(Boolean, default=True, comment='是否走主通道')
    is_deleted = Column(Boolean, default=False, comment='是否删除')
    is_last_one = Column(Boolean, comment='是否最后一个批次')
    input_material_code = Column(String(100), comment='投入物料代码')
    input_bom_revision = Column(String(50), comment='投入版本号')
    tiled = Column(Boolean, comment='是否平铺')
    
    # 工艺控制字段
    is_vaccum = Column(Boolean, default=False, comment='是否真空回潮')
    is_sh93 = Column(Boolean, default=False, comment='是否走SH93')
    is_hdt = Column(Boolean, default=False, comment='是否走HDT')
    is_flavor = Column(Boolean, default=False, comment='是否补香')
    unit = Column(String(20), default='箱', comment='基本单位')
    plan_date = Column(Date, nullable=False, comment='计划日期')
    plan_output_quantity = Column(String(20), comment='计划产出量')
    is_outsourcing = Column(Boolean, default=False, comment='是否委外')
    is_backup = Column(Boolean, default=False, comment='是否备用工单')
    
    # 系统管理字段
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    order_status = Column(String(20), default='PLANNED', comment='工单状态')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 外键关系（暂时注释掉，避免复杂关系影响甘特图显示）
    # feeding_order = relationship("FeedingOrder", foreign_keys=[input_plan_id], 
    #                             primaryjoin="PackingOrder.input_plan_id == FeedingOrder.plan_id", 
    #                             uselist=False)


class WorkOrderSequence(Base):
    """工单号序列表 - 支持MES规范的工单号生成"""
    __tablename__ = "aps_work_order_sequence"
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    order_type = Column(String(10), nullable=False, comment='工单类型：HWS-喂丝机,HJB-卷包机')
    sequence_date = Column(Date, nullable=False, comment='序列日期')
    current_sequence = Column(Integer, default=0, comment='当前序列号')
    last_plan_id = Column(String(50), comment='最后生成的计划ID')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')


class WorkOrderSchedule(Base):
    """工单机台排程表 - 存储用户示例的数据结构，用于甘特图显示"""
    __tablename__ = "aps_work_order_schedule"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    work_order_nr = Column(String(50), nullable=False, comment='生产订单号')
    article_nr = Column(String(100), nullable=False, comment='成品烟牌号')
    final_quantity = Column(Integer, nullable=False, comment='成品数量（箱）- 算法主要使用此字段')
    quantity_total = Column(Integer, nullable=False, comment='投料总量（箱）')
    maker_code = Column(String(20), nullable=False, comment='卷包机代码')
    feeder_code = Column(String(20), nullable=False, comment='喂丝机代码')
    planned_start = Column(DateTime, nullable=False, comment='计划开始时间')
    planned_end = Column(DateTime, nullable=False, comment='计划结束时间')
    task_id = Column(String(50), nullable=False, comment='排产任务ID')
    schedule_status = Column(String(20), default='PENDING', comment='排程状态')
    sync_group_id = Column(String(50), comment='同步组ID')
    is_backup = Column(Boolean, default=False, comment='是否备用工单')
    backup_reason = Column(String(200), comment='备用原因')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')


class InputBatch(Base):
    """工单输入批次关联表 - 支持MES InputBatch结构"""
    __tablename__ = "aps_input_batch"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    packing_order_id = Column(BigInteger, nullable=False, comment='卷包工单ID')
    input_plan_id = Column(String(50), comment='前工序计划号（喂丝机工单号）')
    input_batch_code = Column(String(50), comment='前工序批次号')
    material_code = Column(String(100), nullable=False, comment='物料代码')
    bom_revision = Column(String(50), comment='版本号')
    quantity = Column(DECIMAL(10,2), comment='数量')
    batch_sequence = Column(Integer, comment='批次顺序')
    is_whole_batch = Column(Boolean, default=False, comment='是否整批')
    is_main_channel = Column(Boolean, default=True, comment='是否走主通道')
    is_deleted = Column(Boolean, default=False, comment='是否删除（用于喂丝机工单取消追加）')
    is_last_one = Column(Boolean, default=False, comment='是否最后一个批次（只有喂丝才需要）')
    is_tiled = Column(Boolean, default=False, comment='是否平铺（只有回用烟丝二才会给出）')
    remark1 = Column(String(200), comment='备注1')
    remark2 = Column(String(200), comment='备注2')
    created_time = Column(DateTime, default=func.now(), comment='创建时间')
    updated_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 外键关系（暂时注释掉避免关系错误）
    # packing_order = relationship("PackingOrder", back_populates="input_batches")
    

# 为PackingOrder添加反向关系（暂时注释掉避免关系错误）
# PackingOrder.input_batches = relationship("InputBatch", back_populates="packing_order", 
#                                          foreign_keys="InputBatch.packing_order_id")


# 便捷的数据访问类
class WorkOrderModelManager:
    """工单模型管理器 - 提供便捷的数据访问方法"""
    
    @staticmethod
    def create_feeding_order(mes_order_data: dict) -> FeedingOrder:
        """创建喂丝机工单"""
        return FeedingOrder(**mes_order_data)
    
    @staticmethod
    def create_packing_order(mes_order_data: dict) -> PackingOrder:
        """创建卷包机工单"""
        return PackingOrder(**mes_order_data)
    
    @staticmethod
    def create_schedule_record(schedule_data: dict) -> WorkOrderSchedule:
        """创建排程记录"""
        return WorkOrderSchedule(**schedule_data)