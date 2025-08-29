"""
APS智慧排产系统 - 机台配置管理API

提供机台、机台关系、机台速度、维护计划、班次配置等基础数据的CRUD功能
"""
from typing import Optional, List
from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_, or_
from pydantic import BaseModel, Field

from app.db.connection import get_async_session
from app.schemas.base import SuccessResponse
from app.models.base_models import Machine
from app.models.machine_config_models import MachineRelation, MachineSpeed, MaintenancePlan, ShiftConfig

router = APIRouter(prefix="/machines", tags=["机台配置管理"])


# === Pydantic 模型定义 ===

class MachineRequest(BaseModel):
    machine_code: str = Field(..., max_length=20, description="机台代码")
    machine_name: str = Field(..., max_length=100, description="机台名称")
    machine_type: str = Field(..., description="机台类型：PACKING/FEEDING")
    equipment_type: Optional[str] = Field(None, max_length=50, description="设备型号")
    production_line: Optional[str] = Field(None, max_length=50, description="生产线")
    status: str = Field(default="ACTIVE", description="机台状态：ACTIVE/INACTIVE/MAINTENANCE")


class MachineRelationRequest(BaseModel):
    feeder_code: str = Field(..., max_length=20, description="喂丝机代码")
    maker_code: str = Field(..., max_length=20, description="卷包机代码")
    relation_type: str = Field(..., max_length=20, description="关系类型")
    priority: int = Field(..., description="优先级")


class MachineSpeedRequest(BaseModel):
    machine_code: str = Field(..., max_length=20, description="机台代码")
    article_nr: str = Field(..., max_length=100, description="物料编号")
    speed: float = Field(..., description="生产速度（箱/小时）")
    efficiency_rate: float = Field(..., description="效率率（百分比）")
    effective_from: Optional[datetime] = Field(None, description="生效开始日期")
    effective_to: Optional[datetime] = Field(None, description="生效结束日期")
    status: Optional[str] = Field("ACTIVE", description="状态")




class MaintenancePlanRequest(BaseModel):
    plan_code: str = Field(..., max_length=50, description="维护计划编号")
    machine_code: str = Field(..., max_length=20, description="机台代码")
    maintenance_type: str = Field(..., max_length=20, description="维护类型")
    planned_start_time: datetime = Field(..., description="计划开始时间")
    planned_end_time: datetime = Field(..., description="计划结束时间")
    actual_start_time: Optional[datetime] = Field(None, description="实际开始时间")
    actual_end_time: Optional[datetime] = Field(None, description="实际结束时间")
    status: str = Field(default="PLANNED", description="状态")
    description: Optional[str] = Field(None, max_length=500, description="维护描述")


class ShiftConfigRequest(BaseModel):
    shift_name: str = Field(..., max_length=20, description="班次名称")
    shift_code: str = Field(..., max_length=10, description="班次代码")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    is_active: bool = Field(default=True, description="是否激活")


# === 机台基础信息 CRUD ===

@router.get("/machines")
async def get_machines(
    machine_code: Optional[str] = Query(None, description="机台代码过滤"),
    machine_type: Optional[str] = Query(None, description="机台类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """查询机台列表"""
    try:
        # 构建查询条件
        query = select(Machine)
        conditions = []
        
        if machine_code:
            conditions.append(Machine.machine_code.like(f"%{machine_code}%"))
        if machine_type:
            conditions.append(Machine.machine_type == machine_type)
        if status:
            conditions.append(Machine.status == status)
            
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        total_query = select(func.count(Machine.id)).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Machine.id.desc())
        result = await db.execute(query)
        machines = result.scalars().all()
        
        return SuccessResponse(
            message="查询机台列表成功",
            data={
                "items": [
                    {
                        "id": m.id,
                        "machine_code": m.machine_code,
                        "machine_name": m.machine_name,
                        "machine_type": m.machine_type,
                        "equipment_type": m.equipment_type,
                        "production_line": m.production_line,
                        "status": m.status,
                        "created_time": m.created_time,
                        "updated_time": m.updated_time
                    } for m in machines
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询机台失败: {str(e)}")


@router.post("/machines")
async def create_machine(
    request: MachineRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """创建机台"""
    try:
        # 检查机台代码是否重复
        existing = await db.execute(
            select(Machine).where(Machine.machine_code == request.machine_code)
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="机台代码已存在")
        
        machine = Machine(
            machine_code=request.machine_code,
            machine_name=request.machine_name,
            machine_type=request.machine_type,
            equipment_type=request.equipment_type,
            production_line=request.production_line,
            status=request.status
        )
        
        db.add(machine)
        await db.commit()
        await db.refresh(machine)
        
        return SuccessResponse(message="机台创建成功", data={"id": machine.id})
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建机台失败: {str(e)}")


@router.put("/machines/{machine_id}")
async def update_machine(
    machine_id: int,
    request: MachineRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """更新机台"""
    try:
        result = await db.execute(select(Machine).where(Machine.id == machine_id))
        machine = result.scalar()
        if not machine:
            raise HTTPException(status_code=404, detail="机台不存在")
        
        # 检查机台代码是否重复（排除自己）
        existing = await db.execute(
            select(Machine).where(
                and_(Machine.machine_code == request.machine_code, Machine.id != machine_id)
            )
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="机台代码已存在")
        
        machine.machine_code = request.machine_code
        machine.machine_name = request.machine_name
        machine.machine_type = request.machine_type
        machine.equipment_type = request.equipment_type
        machine.production_line = request.production_line
        machine.status = request.status
        
        await db.commit()
        
        return SuccessResponse(message="机台更新成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新机台失败: {str(e)}")


@router.delete("/machines/{machine_id}")
async def delete_machine(
    machine_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除机台"""
    try:
        result = await db.execute(select(Machine).where(Machine.id == machine_id))
        machine = result.scalar()
        if not machine:
            raise HTTPException(status_code=404, detail="机台不存在")
        
        await db.execute(delete(Machine).where(Machine.id == machine_id))
        await db.commit()
        
        return SuccessResponse(message="机台删除成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除机台失败: {str(e)}")


# === 机台关系 CRUD ===

@router.get("/machine-relations")
async def get_machine_relations(
    feeder_code: Optional[str] = Query(None, description="喂丝机代码过滤"),
    maker_code: Optional[str] = Query(None, description="卷包机代码过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """查询机台关系列表"""
    try:
        query = select(MachineRelation)
        conditions = []
        
        if feeder_code:
            conditions.append(MachineRelation.feeder_code.like(f"%{feeder_code}%"))
        if maker_code:
            conditions.append(MachineRelation.maker_code.like(f"%{maker_code}%"))
            
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        total_query = select(func.count(MachineRelation.id)).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(MachineRelation.priority)
        result = await db.execute(query)
        relations = result.scalars().all()
        
        return SuccessResponse(
            message="查询机台关系列表成功",
            data={
                "items": [
                    {
                        "id": r.id,
                        "feeder_code": r.feeder_code,
                        "maker_code": r.maker_code,
                        "relation_type": r.relation_type,
                        "priority": r.priority,
                        "created_time": r.created_time,
                        "updated_time": r.updated_time
                    } for r in relations
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询机台关系失败: {str(e)}")


@router.post("/machine-relations")
async def create_machine_relation(
    request: MachineRelationRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """创建机台关系"""
    try:
        relation = MachineRelation(
            feeder_code=request.feeder_code,
            maker_code=request.maker_code,
            relation_type=request.relation_type,
            priority=request.priority
        )
        
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        
        return SuccessResponse(message="机台关系创建成功", data={"id": relation.id})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建机台关系失败: {str(e)}")


@router.put("/machine-relations/{relation_id}")
async def update_machine_relation(
    relation_id: int,
    request: MachineRelationRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """更新机台关系"""
    try:
        result = await db.execute(select(MachineRelation).where(MachineRelation.id == relation_id))
        relation = result.scalar()
        if not relation:
            raise HTTPException(status_code=404, detail="机台关系不存在")
        
        relation.feeder_code = request.feeder_code
        relation.maker_code = request.maker_code
        relation.relation_type = request.relation_type
        relation.priority = request.priority
        
        await db.commit()
        
        return SuccessResponse(message="机台关系更新成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新机台关系失败: {str(e)}")


@router.delete("/machine-relations/{relation_id}")
async def delete_machine_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除机台关系"""
    try:
        result = await db.execute(select(MachineRelation).where(MachineRelation.id == relation_id))
        relation = result.scalar()
        if not relation:
            raise HTTPException(status_code=404, detail="机台关系不存在")
        
        await db.execute(delete(MachineRelation).where(MachineRelation.id == relation_id))
        await db.commit()
        
        return SuccessResponse(message="机台关系删除成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除机台关系失败: {str(e)}")


# === 机台速度 CRUD ===

@router.get("/machine-speeds")
async def get_machine_speeds(
    machine_code: Optional[str] = Query(None, description="机台代码过滤"),
    article_nr: Optional[str] = Query(None, description="物料编号过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """查询机台速度列表"""
    try:
        query = select(MachineSpeed)
        conditions = []
        
        if machine_code:
            conditions.append(MachineSpeed.machine_code.like(f"%{machine_code}%"))
        if article_nr:
            conditions.append(MachineSpeed.article_nr.like(f"%{article_nr}%"))
            
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        count_query = select(func.count(MachineSpeed.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(MachineSpeed.id.desc())
        result = await db.execute(query)
        speeds = result.scalars().all()
        
        return SuccessResponse(
            message="查询机台速度列表成功",
            data={
                "items": [
                    {
                        "id": s.id,
                        "machine_code": s.machine_code,
                        "article_nr": s.article_nr,
                        "speed": float(s.speed),
                        "efficiency_rate": float(s.efficiency_rate),
                        "effective_from": s.effective_from,
                        "effective_to": s.effective_to,
                        "status": s.status,
                        "created_time": s.created_time,
                        "updated_time": s.updated_time
                    } for s in speeds
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询机台速度失败: {str(e)}")


@router.post("/machine-speeds")
async def create_machine_speed(
    request: MachineSpeedRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """创建机台速度"""
    try:
        speed = MachineSpeed(
            machine_code=request.machine_code,
            article_nr=request.article_nr,
            speed=request.speed,
            efficiency_rate=request.efficiency_rate,
            effective_from=request.effective_from or datetime.now(),
            effective_to=request.effective_to,
            status=request.status or "ACTIVE"
        )
        
        db.add(speed)
        await db.commit()
        await db.refresh(speed)
        
        return SuccessResponse(message="机台速度创建成功", data={"id": speed.id})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建机台速度失败: {str(e)}")


@router.put("/machine-speeds/{speed_id}")
async def update_machine_speed(
    speed_id: int,
    request: MachineSpeedRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """更新机台速度"""
    try:
        result = await db.execute(select(MachineSpeed).where(MachineSpeed.id == speed_id))
        speed = result.scalar()
        if not speed:
            raise HTTPException(status_code=404, detail="机台速度不存在")
        
        speed.machine_code = request.machine_code
        speed.article_nr = request.article_nr
        speed.speed = request.speed
        speed.efficiency_rate = request.efficiency_rate
        if request.effective_from:
            speed.effective_from = request.effective_from
        if request.effective_to:
            speed.effective_to = request.effective_to
        if request.status:
            speed.status = request.status
        
        await db.commit()
        
        return SuccessResponse(message="机台速度更新成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新机台速度失败: {str(e)}")


@router.delete("/machine-speeds/{speed_id}")
async def delete_machine_speed(
    speed_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除机台速度"""
    try:
        result = await db.execute(select(MachineSpeed).where(MachineSpeed.id == speed_id))
        speed = result.scalar()
        if not speed:
            raise HTTPException(status_code=404, detail="机台速度不存在")
        
        await db.execute(delete(MachineSpeed).where(MachineSpeed.id == speed_id))
        await db.commit()
        
        return SuccessResponse(message="机台速度删除成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除机台速度失败: {str(e)}")


# === 维护计划 CRUD ===

@router.get("/maintenance-plans")
async def get_maintenance_plans(
    machine_code: Optional[str] = Query(None, description="机台代码过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    maintenance_type: Optional[str] = Query(None, description="维护类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """查询维护计划列表"""
    try:
        query = select(MaintenancePlan)
        conditions = []
        
        if machine_code:
            conditions.append(MaintenancePlan.machine_code.like(f"%{machine_code}%"))
        if status:
            conditions.append(MaintenancePlan.plan_status == status)
        if maintenance_type:
            conditions.append(MaintenancePlan.maint_type == maintenance_type)
            
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        count_query = select(func.count(MaintenancePlan.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(MaintenancePlan.maint_start_time.desc())
        result = await db.execute(query)
        plans = result.scalars().all()
        
        return SuccessResponse(
            message="查询维护计划列表成功",
            data={
                "items": [
                    {
                        "id": p.id,
                        "plan_code": p.maint_plan_no,
                        "machine_code": p.machine_code,
                        "maintenance_type": p.maint_type,
                        "planned_start_time": p.maint_start_time,
                        "planned_end_time": p.maint_end_time,
                        "actual_start_time": p.actual_start_time,
                        "actual_end_time": p.actual_end_time,
                        "status": p.plan_status,
                        "description": p.maint_description,
                        "created_time": p.created_time,
                        "updated_time": p.updated_time
                    } for p in plans
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询维护计划失败: {str(e)}")


@router.post("/maintenance-plans")
async def create_maintenance_plan(
    request: MaintenancePlanRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """创建维护计划"""
    try:
        # 检查计划编号是否重复
        existing = await db.execute(
            select(MaintenancePlan).where(MaintenancePlan.maint_plan_no == request.plan_code)
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="维护计划编号已存在")
        
        plan = MaintenancePlan(
            maint_plan_no=request.plan_code,
            schedule_date=request.planned_start_time,
            equipment_position="生产线",  # 默认设备位置
            machine_code=request.machine_code,
            maint_start_time=request.planned_start_time,
            maint_end_time=request.planned_end_time,
            actual_start_time=request.actual_start_time,
            actual_end_time=request.actual_end_time,
            maint_type=request.maintenance_type,
            maint_description=request.description,
            plan_status=request.status
        )
        
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        
        return SuccessResponse(message="维护计划创建成功", data={"id": plan.id})
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建维护计划失败: {str(e)}")


@router.put("/maintenance-plans/{plan_id}")
async def update_maintenance_plan(
    plan_id: int,
    request: MaintenancePlanRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """更新维护计划"""
    try:
        result = await db.execute(select(MaintenancePlan).where(MaintenancePlan.id == plan_id))
        plan = result.scalar()
        if not plan:
            raise HTTPException(status_code=404, detail="维护计划不存在")
        
        # 检查计划编号是否重复（排除自己）
        existing = await db.execute(
            select(MaintenancePlan).where(
                and_(MaintenancePlan.maint_plan_no == request.plan_code, MaintenancePlan.id != plan_id)
            )
        )
        if existing.scalar():
            raise HTTPException(status_code=400, detail="维护计划编号已存在")
        
        plan.maint_plan_no = request.plan_code
        plan.schedule_date = request.planned_start_time
        plan.machine_code = request.machine_code
        plan.maint_type = request.maintenance_type
        plan.maint_start_time = request.planned_start_time
        plan.maint_end_time = request.planned_end_time
        plan.actual_start_time = request.actual_start_time
        plan.actual_end_time = request.actual_end_time
        plan.plan_status = request.status
        plan.maint_description = request.description
        
        await db.commit()
        
        return SuccessResponse(message="维护计划更新成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新维护计划失败: {str(e)}")


@router.delete("/maintenance-plans/{plan_id}")
async def delete_maintenance_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除维护计划"""
    try:
        result = await db.execute(select(MaintenancePlan).where(MaintenancePlan.id == plan_id))
        plan = result.scalar()
        if not plan:
            raise HTTPException(status_code=404, detail="维护计划不存在")
        
        await db.execute(delete(MaintenancePlan).where(MaintenancePlan.id == plan_id))
        await db.commit()
        
        return SuccessResponse(message="维护计划删除成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除维护计划失败: {str(e)}")


# === 班次配置 CRUD ===

@router.get("/shift-configs")
async def get_shift_configs(
    shift_name: Optional[str] = Query(None, description="班次名称过滤"),
    is_active: Optional[bool] = Query(None, description="激活状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """查询班次配置列表"""
    try:
        query = select(ShiftConfig)
        conditions = []
        
        if shift_name:
            conditions.append(ShiftConfig.shift_name.like(f"%{shift_name}%"))
        if is_active is not None:
            conditions.append(ShiftConfig.status == ('ACTIVE' if is_active else 'INACTIVE'))
            
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        count_query = select(func.count(ShiftConfig.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(ShiftConfig.start_time)
        result = await db.execute(query)
        configs = result.scalars().all()
        
        return SuccessResponse(
            message="查询班次配置列表成功",
            data={
                "items": [
                    {
                        "id": c.id,
                        "shift_name": c.shift_name,
                        "shift_code": c.machine_name,
                        "start_time": c.start_time.strftime("%H:%M:%S"),
                        "end_time": c.end_time.strftime("%H:%M:%S"),
                        "is_active": c.status == 'ACTIVE',
                        "created_time": c.created_time,
                        "updated_time": c.updated_time
                    } for c in configs
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询班次配置失败: {str(e)}")


@router.post("/shift-configs")
async def create_shift_config(
    request: ShiftConfigRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """创建班次配置"""
    try:
        from datetime import datetime
        
        config = ShiftConfig(
            shift_name=request.shift_name,
            machine_name=request.shift_code,  # 使用 machine_name 字段存储班次代码
            start_time=request.start_time,
            end_time=request.end_time,
            effective_from=datetime.now(),  # 设置必需的生效开始时间
            status='ACTIVE' if request.is_active else 'INACTIVE'
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        return SuccessResponse(message="班次配置创建成功", data={"id": config.id})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建班次配置失败: {str(e)}")


@router.put("/shift-configs/{config_id}")
async def update_shift_config(
    config_id: int,
    request: ShiftConfigRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """更新班次配置"""
    try:
        result = await db.execute(select(ShiftConfig).where(ShiftConfig.id == config_id))
        config = result.scalar()
        if not config:
            raise HTTPException(status_code=404, detail="班次配置不存在")
        
        config.shift_name = request.shift_name
        config.machine_name = request.shift_code  # 使用 machine_name 字段存储班次代码
        config.start_time = request.start_time
        config.end_time = request.end_time
        config.status = 'ACTIVE' if request.is_active else 'INACTIVE'
        
        await db.commit()
        
        return SuccessResponse(message="班次配置更新成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新班次配置失败: {str(e)}")


@router.delete("/shift-configs/{config_id}")
async def delete_shift_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """删除班次配置"""
    try:
        result = await db.execute(select(ShiftConfig).where(ShiftConfig.id == config_id))
        config = result.scalar()
        if not config:
            raise HTTPException(status_code=404, detail="班次配置不存在")
        
        await db.execute(delete(ShiftConfig).where(ShiftConfig.id == config_id))
        await db.commit()
        
        return SuccessResponse(message="班次配置删除成功")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除班次配置失败: {str(e)}")
