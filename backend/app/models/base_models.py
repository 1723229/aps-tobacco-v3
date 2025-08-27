"""
APS智慧排产系统 - 基础数据模型

实现基础数据表的SQLAlchemy模型
包含机台信息、物料信息、速度配置等核心业务数据
"""
from sqlalchemy import Column, BigInteger, String, Enum, DateTime, Text, Index, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.connection import Base


class Machine(Base):
    """机台基础信息表 - 对应技术设计文档2.1.1"""
    __tablename__ = "aps_machine"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    machine_code = Column(String(20), nullable=False, unique=True, comment='机台代码')
    machine_name = Column(String(100), nullable=False, comment='机台名称')
    machine_type = Column(
        Enum('PACKING', 'FEEDING', name='machine_type_enum'), 
        nullable=False, 
        comment='机台类型：卷包机/喂丝机'
    )
    equipment_type = Column(String(50), comment='设备型号(如PROTOS70, M8)')
    production_line = Column(String(50), comment='生产线')
    status = Column(
        Enum('ACTIVE', 'INACTIVE', 'MAINTENANCE', name='machine_status_enum'),
        default='ACTIVE',
        comment='机台状态'
    )
    created_time = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    updated_time = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    
    # 索引
    __table_args__ = (
        Index('idx_machine_type', 'machine_type'),
        Index('idx_status', 'status'),
        {'comment': '机台基础信息表'}
    )


class Material(Base):
    """物料基础信息表 - 对应技术设计文档2.1.2"""
    __tablename__ = "aps_material"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    article_nr = Column(String(100), nullable=False, unique=True, comment='物料编号')
    article_name = Column(String(200), nullable=False, comment='物料名称')
    material_type = Column(
        Enum('FINISHED_PRODUCT', 'TOBACCO_SILK', 'RAW_MATERIAL', name='material_type_enum'),
        nullable=False,
        comment='物料类型'
    )
    package_type = Column(String(50), comment='包装类型（软包/硬包）')
    specification = Column(String(50), comment='规格（长嘴/短嘴/超长嘴/中支/细支）')
    unit = Column(String(20), default='箱', comment='计量单位')
    conversion_rate = Column(String(10), default='1.0000', comment='转换比率')  # 使用String避免Decimal配置复杂性
    status = Column(
        Enum('ACTIVE', 'INACTIVE', name='material_status_enum'),
        default='ACTIVE',
        comment='状态'
    )
    created_time = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    updated_time = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    
    # 索引
    __table_args__ = (
        Index('idx_material_type', 'material_type'),
        Index('idx_status', 'status'),
        {'comment': '物料基础信息表'}
    )


class ImportPlan(Base):
    """导入计划表 - 对应技术设计文档2.2.1"""
    __tablename__ = "aps_import_plan"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    import_batch_id = Column(String(50), nullable=False, unique=True, comment='导入批次ID')
    file_name = Column(String(255), nullable=False, comment='文件名')
    file_path = Column(String(500), comment='文件路径')
    file_size = Column(BigInteger, comment='文件大小（字节）')
    total_records = Column(BigInteger, default=0, comment='总记录数')
    valid_records = Column(BigInteger, default=0, comment='有效记录数')
    error_records = Column(BigInteger, default=0, comment='错误记录数')
    import_status = Column(
        Enum('UPLOADING', 'PARSING', 'COMPLETED', 'FAILED', name='import_status_enum'),
        default='UPLOADING',
        comment='导入状态'
    )
    import_start_time = Column(DateTime, comment='导入开始时间')
    import_end_time = Column(DateTime, comment='导入结束时间')
    error_message = Column(Text, comment='错误信息')
    created_by = Column(String(100), default='system', comment='创建者')
    created_time = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    updated_time = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    
class DecadePlan(Base):
    """原始旬计划表 - 存储解析后的生产作业计划数据"""
    __tablename__ = "aps_decade_plan"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    import_batch_id = Column(String(50), nullable=False, comment='导入批次ID')
    work_order_nr = Column(String(50), nullable=False, comment='生产订单号')
    article_nr = Column(String(100), nullable=False, comment='成品烟牌号')
    package_type = Column(String(50), comment='包装类型（软包/硬包）')
    specification = Column(String(50), comment='规格（长嘴/短嘴等）')
    quantity_total = Column(BigInteger, nullable=False, comment='投料总量（箱）')
    final_quantity = Column(BigInteger, nullable=False, comment='成品数量（箱）')
    production_unit = Column(String(50), comment='生产单元')
    maker_code = Column(String(100), nullable=False, comment='卷包机代码（多个用逗号分隔）')
    feeder_code = Column(String(100), nullable=False, comment='喂丝机代码（多个用逗号分隔）')
    planned_start = Column(DateTime, nullable=False, comment='计划开始时间')
    planned_end = Column(DateTime, nullable=False, comment='计划结束时间')
    production_date_range = Column(String(100), comment='成品生产日期范围')
    row_number = Column(BigInteger, comment='原始行号')
    validation_status = Column(
        Enum('VALID', 'WARNING', 'ERROR', name='decade_validation_status_enum'),
        default='VALID',
        comment='验证状态'
    )
    validation_message = Column(Text, comment='验证信息')
    created_time = Column(DateTime, default=func.current_timestamp(), comment='创建时间')
    updated_time = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    
    # 索引
    __table_args__ = (
        Index('idx_import_batch', 'import_batch_id'),
        Index('idx_work_order', 'work_order_nr'),
        Index('idx_planned_time', 'planned_start', 'planned_end'),
        Index('idx_validation_status', 'validation_status'),
        {'comment': '原始卷包旬计划表'}
    )