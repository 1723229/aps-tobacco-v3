"""
APS智慧排产系统 - 扩展数据模型

实现轮保计划数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Enum, DateTime, Date, Integer
from sqlalchemy.sql import func
from app.db.connection import Base


class MaintenancePlan(Base):
    """轮保计划表 - 对应 aps_maintenance_plan"""
    __tablename__ = "aps_maintenance_plan"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    machine_code = Column(String(20), nullable=False, comment='机台代码')
    maint_start_time = Column(DateTime, nullable=False, comment='轮保开始时间')
    maint_end_time = Column(DateTime, nullable=False, comment='轮保结束时间')