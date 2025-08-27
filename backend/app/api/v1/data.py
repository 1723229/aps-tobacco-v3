"""
APS智慧排产系统 - 数据查询API

提供导入记录、机台信息、物料信息等数据的查询接口
支持分页、过滤、排序等功能
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime

from app.db.connection import get_async_session
from app.schemas.base import (
    ImportPlanListResponse, PaginatedResponse, ImportPlanInfo,
    ImportPlanQuery, SuccessResponse, MachineInfo, MaterialInfo
)
from app.models.base_models import ImportPlan, Machine, Material

router = APIRouter(prefix="/data", tags=["数据查询"])


@router.get("/imports", response_model=ImportPlanListResponse)
async def list_import_plans(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    import_status: Optional[str] = Query(None, description="导入状态过滤"),
    file_name: Optional[str] = Query(None, description="文件名过滤"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    分页查询导入计划列表
    
    支持按状态、文件名、日期范围过滤
    """
    try:
        # 构建查询条件
        conditions = []
        
        if import_status:
            conditions.append(ImportPlan.import_status == import_status)
        
        if file_name:
            conditions.append(ImportPlan.file_name.like(f"%{file_name}%"))
        
        if start_date:
            conditions.append(ImportPlan.created_time >= start_date)
        
        if end_date:
            conditions.append(ImportPlan.created_time <= end_date)
        
        # 查询总数
        count_query = select(func.count(ImportPlan.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # 查询数据
        data_query = select(ImportPlan).order_by(ImportPlan.created_time.desc())
        if conditions:
            data_query = data_query.where(and_(*conditions))
        
        # 分页
        offset = (page - 1) * size
        data_query = data_query.offset(offset).limit(size)
        
        data_result = await db.execute(data_query)
        import_plans = data_result.scalars().all()
        
        # 转换为响应格式
        items = []
        for plan in import_plans:
            item = ImportPlanInfo(
                id=plan.id,
                import_batch_id=plan.import_batch_id,
                file_name=plan.file_name,
                file_size=plan.file_size,
                total_records=plan.total_records,
                valid_records=plan.valid_records,
                error_records=plan.error_records,
                import_status=plan.import_status,
                import_start_time=plan.import_start_time,
                import_end_time=plan.import_end_time,
                created_time=plan.created_time
            )
            items.append(item.model_dump())
        
        # 创建分页响应
        paginated_data = PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
        return ImportPlanListResponse(
            code=200,
            message="查询成功",
            data=paginated_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/imports/{import_batch_id}")
async def get_import_plan_detail(
    import_batch_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询导入计划详情
    """
    try:
        result = await db.execute(
            select(ImportPlan).where(ImportPlan.import_batch_id == import_batch_id)
        )
        import_plan = result.scalar_one_or_none()
        
        if not import_plan:
            raise HTTPException(status_code=404, detail=f"导入批次不存在：{import_batch_id}")
        
        plan_info = ImportPlanInfo(
            id=import_plan.id,
            import_batch_id=import_plan.import_batch_id,
            file_name=import_plan.file_name,
            file_size=import_plan.file_size,
            total_records=import_plan.total_records,
            valid_records=import_plan.valid_records,
            error_records=import_plan.error_records,
            import_status=import_plan.import_status,
            import_start_time=import_plan.import_start_time,
            import_end_time=import_plan.import_end_time,
            created_time=import_plan.created_time
        )
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data=plan_info.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/machines")
async def list_machines(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    machine_type: Optional[str] = Query(None, description="机台类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（机台代码或名称）"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    分页查询机台列表
    
    支持按类型、状态过滤，支持关键词搜索
    """
    try:
        # 构建查询条件
        conditions = []
        
        if machine_type:
            conditions.append(Machine.machine_type == machine_type)
        
        if status:
            conditions.append(Machine.status == status)
        
        if search:
            conditions.append(
                or_(
                    Machine.machine_code.like(f"%{search}%"),
                    Machine.machine_name.like(f"%{search}%")
                )
            )
        
        # 查询总数
        count_query = select(func.count(Machine.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # 查询数据
        data_query = select(Machine).order_by(Machine.machine_code)
        if conditions:
            data_query = data_query.where(and_(*conditions))
        
        # 分页
        offset = (page - 1) * size
        data_query = data_query.offset(offset).limit(size)
        
        data_result = await db.execute(data_query)
        machines = data_result.scalars().all()
        
        # 转换为响应格式
        items = []
        for machine in machines:
            item = MachineInfo(
                id=machine.id,
                machine_code=machine.machine_code,
                machine_name=machine.machine_name,
                machine_type=machine.machine_type,
                equipment_type=machine.equipment_type,
                production_line=machine.production_line,
                status=machine.status
            )
            items.append(item.model_dump())
        
        # 创建分页响应
        paginated_data = PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data=paginated_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/materials")
async def list_materials(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    material_type: Optional[str] = Query(None, description="物料类型过滤"),
    package_type: Optional[str] = Query(None, description="包装类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（物料编号或名称）"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    分页查询物料列表
    
    支持按类型、包装、状态过滤，支持关键词搜索
    """
    try:
        # 构建查询条件
        conditions = []
        
        if material_type:
            conditions.append(Material.material_type == material_type)
        
        if package_type:
            conditions.append(Material.package_type == package_type)
        
        if status:
            conditions.append(Material.status == status)
        
        if search:
            conditions.append(
                or_(
                    Material.article_nr.like(f"%{search}%"),
                    Material.article_name.like(f"%{search}%")
                )
            )
        
        # 查询总数
        count_query = select(func.count(Material.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # 查询数据
        data_query = select(Material).order_by(Material.article_nr)
        if conditions:
            data_query = data_query.where(and_(*conditions))
        
        # 分页
        offset = (page - 1) * size
        data_query = data_query.offset(offset).limit(size)
        
        data_result = await db.execute(data_query)
        materials = data_result.scalars().all()
        
        # 转换为响应格式
        items = []
        for material in materials:
            item = MaterialInfo(
                id=material.id,
                article_nr=material.article_nr,
                article_name=material.article_name,
                material_type=material.material_type,
                package_type=material.package_type,
                specification=material.specification,
                unit=material.unit,
                status=material.status
            )
            items.append(item.model_dump())
        
        # 创建分页响应
        paginated_data = PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data=paginated_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/statistics")
async def get_system_statistics(
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取系统统计信息
    """
    try:
        # 查询导入计划统计
        import_stats_query = select(
            ImportPlan.import_status,
            func.count(ImportPlan.id).label('count')
        ).group_by(ImportPlan.import_status)
        
        import_stats_result = await db.execute(import_stats_query)
        import_stats = {}
        for row in import_stats_result:
            import_stats[row.import_status] = row.count
        
        # 查询机台统计
        machine_stats_query = select(
            Machine.machine_type,
            func.count(Machine.id).label('count')
        ).group_by(Machine.machine_type)
        
        machine_stats_result = await db.execute(machine_stats_query)
        machine_stats = {}
        for row in machine_stats_result:
            machine_stats[row.machine_type] = row.count
        
        # 查询物料统计
        material_stats_query = select(
            Material.material_type,
            func.count(Material.id).label('count')
        ).group_by(Material.material_type)
        
        material_stats_result = await db.execute(material_stats_query)
        material_stats = {}
        for row in material_stats_result:
            material_stats[row.material_type] = row.count
        
        return SuccessResponse(
            code=200,
            message="统计信息查询成功",
            data={
                "import_plans": import_stats,
                "machines": machine_stats,
                "materials": material_stats,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计信息查询失败：{str(e)}")