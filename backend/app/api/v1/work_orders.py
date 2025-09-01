"""
APS智慧排产系统 - 工单管理API（甘特图数据源重构版）

提供基于WorkOrderSchedule表的工单查询，用于甘特图显示
支持用户示例数据格式：W0001/W0002/W0003 + 机台关系
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime
import logging

from app.db.connection import get_async_session
from app.schemas.base import SuccessResponse
from app.models.work_order_models import WorkOrderSchedule, PackingOrder, FeedingOrder

# 初始化日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/work-orders", tags=["工单管理"])


@router.get("/schedule")
async def get_work_order_schedule(
    task_id: Optional[str] = Query(None, description="排产任务ID过滤"),
    work_order_nr: Optional[str] = Query(None, description="工单号过滤"), 
    machine_code: Optional[str] = Query(None, description="机台代码过滤"),
    article_nr: Optional[str] = Query(None, description="产品代码过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=2000, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询工单排程数据（甘特图数据源）
    
    返回用户示例格式的工单-机台映射数据：
    - work_order_nr: W0001, W0002, W0003
    - article_nr: 产品牌号 (PA, PB etc.)
    - final_quantity: 成品数量（箱）
    - maker_code/feeder_code: 机台代码
    - planned_start/planned_end: 计划时间
    """
    try:
        # 构建查询条件
        query = select(WorkOrderSchedule)
        conditions = []
        
        if task_id:
            conditions.append(WorkOrderSchedule.task_id == task_id)
        if work_order_nr:
            conditions.append(WorkOrderSchedule.work_order_nr.like(f"%{work_order_nr}%"))
        if machine_code:
            # 搜索卷包机或喂丝机代码
            conditions.append(
                WorkOrderSchedule.maker_code.like(f"%{machine_code}%") |
                WorkOrderSchedule.feeder_code.like(f"%{machine_code}%")
            )
        if article_nr:
            conditions.append(WorkOrderSchedule.article_nr.like(f"%{article_nr}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页查询
        total_query = select(func.count()).select_from(WorkOrderSchedule)
        if conditions:
            total_query = total_query.where(and_(*conditions))
        
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        
        # 获取数据
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(WorkOrderSchedule.planned_start, WorkOrderSchedule.work_order_nr)
        
        result = await db.execute(query)
        schedules = result.scalars().all()
        
        # 转换为甘特图所需格式
        schedule_data = []
        for schedule in schedules:
            schedule_data.append({
                "id": schedule.id,
                "work_order_nr": schedule.work_order_nr,
                "article_nr": schedule.article_nr,
                "final_quantity": schedule.final_quantity,
                "quantity_total": schedule.quantity_total,
                "maker_code": schedule.maker_code,
                "feeder_code": schedule.feeder_code,
                "planned_start": schedule.planned_start.isoformat() if schedule.planned_start else None,
                "planned_end": schedule.planned_end.isoformat() if schedule.planned_end else None,
                "task_id": schedule.task_id,
                "schedule_status": schedule.schedule_status,
                "sync_group_id": schedule.sync_group_id,
                "is_backup": schedule.is_backup,
                "backup_reason": schedule.backup_reason,
                "created_time": schedule.created_time.isoformat() if schedule.created_time else None
            })
        
        return SuccessResponse(
            message=f"查询到 {len(schedule_data)} 条工单排程数据",
            data={
                "schedules": schedule_data,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询工单排程失败: {str(e)}")


@router.get("")
async def get_work_orders(
    task_id: Optional[str] = Query(None, description="排产任务ID过滤"),
    import_batch_id: Optional[str] = Query(None, description="导入批次ID过滤"),
    order_type: Optional[str] = Query(None, description="工单类型过滤 (HJB-卷包机, HWS-喂丝机)"),
    orderType: Optional[str] = Query(None, description="工单类型过滤别名"),
    time_range: Optional[str] = Query(None, description="时间范围过滤"),
    timeRange: Optional[str] = Query(None, description="时间范围过滤别名"),
    status: Optional[str] = Query(None, description="工单状态过滤"),
    machine_code: Optional[str] = Query(None, description="机台代码过滤"),
    product_code: Optional[str] = Query(None, description="产品代码过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=2000, description="每页大小"),
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询工单列表接口（甘特图数据源重构）
    
    优先使用WorkOrderSchedule表提供甘特图数据，
    如果没有数据则降级使用MES工单表
    
    Returns:
        工单列表，兼容甘特图所需格式
    """
    try:
        # 处理参数别名
        effective_order_type = order_type or orderType
        effective_time_range = time_range or timeRange
        
        # 优先使用WorkOrderSchedule表数据（甘特图数据源）
        schedule_data = await get_schedule_data(
            db, task_id, machine_code, product_code, page, page_size
        )
        
        if schedule_data and schedule_data["total_count"] > 0:
            # 转换WorkOrderSchedule数据为工单格式
            work_orders = []
            for schedule in schedule_data["schedules"]:
                work_orders.append({
                    "work_order_nr": schedule["work_order_nr"],
                    "work_order_type": "SCHEDULE",  # 标记为排程数据
                    "machine_type": "卷包机+喂丝机",
                    "machine_code": schedule["maker_code"],
                    "feeder_code": schedule["feeder_code"],
                    "product_code": schedule["article_nr"],
                    "plan_quantity": schedule["final_quantity"],
                    "quantity_total": schedule["quantity_total"],
                    "work_order_status": schedule["schedule_status"],
                    "planned_start_time": schedule["planned_start"],
                    "planned_end_time": schedule["planned_end"],
                    "created_time": schedule["created_time"],
                    "task_id": schedule["task_id"],
                    "is_backup": schedule["is_backup"],
                    "backup_reason": schedule["backup_reason"],
                    "sync_group_id": schedule["sync_group_id"]
                })
            
            return SuccessResponse(
                message=f"查询到 {len(work_orders)} 条工单数据（排程数据源）",
                data={
                    "work_orders": work_orders,
                    "total_count": schedule_data["total_count"],
                    "page": page,
                    "page_size": page_size,
                    "data_source": "work_order_schedule"
                }
            )
        
        # 降级使用MES工单数据
        work_orders = await get_mes_work_order_data(
            db, task_id, effective_order_type, status, machine_code, 
            product_code, page, page_size
        )
        return SuccessResponse(
            message=f"查询到 {len(work_orders)} 条工单数据（MES数据源）",
            data={
                "work_orders": work_orders,
                "total_count": len(work_orders),
                "page": page,
                "page_size": page_size,
                "data_source": "mes_work_orders"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询工单失败: {str(e)}")


async def get_schedule_data(
    db: AsyncSession, 
    task_id: Optional[str], 
    machine_code: Optional[str],
    product_code: Optional[str], 
    page: int, 
    page_size: int
) -> Dict[str, Any]:
    """查询WorkOrderSchedule表数据"""
    try:
        query = select(WorkOrderSchedule)
        conditions = []
        
        if task_id:
            conditions.append(WorkOrderSchedule.task_id == task_id)
        if machine_code:
            conditions.append(
                WorkOrderSchedule.maker_code.like(f"%{machine_code}%") |
                WorkOrderSchedule.feeder_code.like(f"%{machine_code}%")
            )
        if product_code:
            conditions.append(WorkOrderSchedule.article_nr.like(f"%{product_code}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 获取总数
        total_query = select(func.count()).select_from(WorkOrderSchedule)
        if conditions:
            total_query = total_query.where(and_(*conditions))
        
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        
        if total_count == 0:
            return {"schedules": [], "total_count": 0}
        
        # 分页查询
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(WorkOrderSchedule.planned_start, WorkOrderSchedule.work_order_nr)
        
        result = await db.execute(query)
        schedules = result.scalars().all()
        
        schedule_data = []
        for schedule in schedules:
            schedule_data.append({
                "work_order_nr": schedule.work_order_nr,
                "article_nr": schedule.article_nr,
                "final_quantity": schedule.final_quantity,
                "quantity_total": schedule.quantity_total,
                "maker_code": schedule.maker_code,
                "feeder_code": schedule.feeder_code,
                "planned_start": schedule.planned_start.isoformat() if schedule.planned_start else None,
                "planned_end": schedule.planned_end.isoformat() if schedule.planned_end else None,
                "task_id": schedule.task_id,
                "schedule_status": schedule.schedule_status,
                "sync_group_id": schedule.sync_group_id,
                "is_backup": schedule.is_backup,
                "backup_reason": schedule.backup_reason,
                "created_time": schedule.created_time.isoformat() if schedule.created_time else None
            })
        
        return {"schedules": schedule_data, "total_count": total_count}
        
    except Exception:
        return {"schedules": [], "total_count": 0}


async def get_mes_work_order_data(
    db: AsyncSession,
    task_id: Optional[str],
    order_type: Optional[str],
    status: Optional[str],
    machine_code: Optional[str],
    product_code: Optional[str],
    page: int,
    page_size: int
) -> List[Dict[str, Any]]:
    """查询MES工单表数据作为降级方案"""
    work_orders = []
    
    try:
        # 如果指定了工单类型，则只查询该类型
        if order_type and order_type.upper() == "HWS":
            # 查询喂丝机工单
            feeding_query = select(FeedingOrder)
            conditions = []
            
            if task_id:
                conditions.append(FeedingOrder.task_id == task_id)
            if status:
                conditions.append(FeedingOrder.work_order_status == status)
            if machine_code:
                conditions.append(FeedingOrder.machine_code.like(f"%{machine_code}%"))
            if product_code:
                conditions.append(FeedingOrder.product_code.like(f"%{product_code}%"))
            
            if conditions:
                feeding_query = feeding_query.where(and_(*conditions))
            
            feeding_result = await db.execute(feeding_query)
            feeding_orders = feeding_result.scalars().all()
            
            for order in feeding_orders:
                work_orders.append({
                    "work_order_nr": order.work_order_nr,
                    "work_order_type": "HWS",
                    "machine_type": "喂丝机",
                    "machine_code": order.machine_code,
                    "feeder_code": order.machine_code,  # 喂丝机代码
                    "product_code": order.product_code,
                    "plan_quantity": order.plan_quantity,
                    "safety_stock": getattr(order, 'safety_stock', 0),
                    "work_order_status": order.work_order_status.value if hasattr(order.work_order_status, 'value') else str(order.work_order_status),
                    "planned_start_time": order.planned_start_time.isoformat() if order.planned_start_time else None,
                    "planned_end_time": order.planned_end_time.isoformat() if order.planned_end_time else None,
                    "actual_start_time": order.actual_start_time.isoformat() if order.actual_start_time else None,
                    "actual_end_time": order.actual_end_time.isoformat() if order.actual_end_time else None,
                    "created_time": order.created_time.isoformat() if order.created_time else None,
                    "updated_time": order.updated_time.isoformat() if order.updated_time else None
                })
        
        elif order_type and order_type.upper() == "HJB":
            # 查询卷包机工单
            packing_query = select(PackingOrder)
            conditions = []
            
            if task_id:
                conditions.append(PackingOrder.task_id == task_id)
            if status:
                conditions.append(PackingOrder.work_order_status == status)
            if machine_code:
                conditions.append(PackingOrder.machine_code.like(f"%{machine_code}%"))
            if product_code:
                conditions.append(PackingOrder.product_code.like(f"%{product_code}%"))
            
            if conditions:
                packing_query = packing_query.where(and_(*conditions))
            
            packing_result = await db.execute(packing_query)
            packing_orders = packing_result.scalars().all()
            
            for order in packing_orders:
                work_orders.append({
                    "work_order_nr": order.work_order_nr,
                    "work_order_type": "HJB",
                    "machine_type": "卷包机",
                    "machine_code": order.machine_code,
                    "feeder_code": None,  # 卷包机没有喂丝机代码
                    "product_code": order.product_code,
                    "plan_quantity": order.plan_quantity,
                    "work_order_status": order.work_order_status.value if hasattr(order.work_order_status, 'value') else str(order.work_order_status),
                    "planned_start_time": order.planned_start_time.isoformat() if order.planned_start_time else None,
                    "planned_end_time": order.planned_end_time.isoformat() if order.planned_end_time else None,
                    "actual_start_time": order.actual_start_time.isoformat() if order.actual_start_time else None,
                    "actual_end_time": order.actual_end_time.isoformat() if order.actual_end_time else None,
                    "created_time": order.created_time.isoformat() if order.created_time else None,
                    "updated_time": order.updated_time.isoformat() if order.updated_time else None
                })
        
        else:
            # 查询所有类型工单
            # 查询喂丝机工单
            feeding_query = select(FeedingOrder)
            feeding_conditions = []
            
            if task_id:
                feeding_conditions.append(FeedingOrder.task_id == task_id)
            if status:
                feeding_conditions.append(FeedingOrder.work_order_status == status)
            if machine_code:
                feeding_conditions.append(FeedingOrder.machine_code.like(f"%{machine_code}%"))
            if product_code:
                feeding_conditions.append(FeedingOrder.product_code.like(f"%{product_code}%"))
            
            if feeding_conditions:
                feeding_query = feeding_query.where(and_(*feeding_conditions))
            
            feeding_result = await db.execute(feeding_query)
            feeding_orders = feeding_result.scalars().all()
            
            for order in feeding_orders:
                work_orders.append({
                    "work_order_nr": order.work_order_nr,
                    "work_order_type": "HWS",
                    "machine_type": "喂丝机",
                    "machine_code": order.machine_code,
                    "feeder_code": order.machine_code,
                    "product_code": order.product_code,
                    "plan_quantity": order.plan_quantity,
                    "safety_stock": getattr(order, 'safety_stock', 0),
                    "work_order_status": order.work_order_status.value if hasattr(order.work_order_status, 'value') else str(order.work_order_status),
                    "planned_start_time": order.planned_start_time.isoformat() if order.planned_start_time else None,
                    "planned_end_time": order.planned_end_time.isoformat() if order.planned_end_time else None,
                    "actual_start_time": order.actual_start_time.isoformat() if order.actual_start_time else None,
                    "actual_end_time": order.actual_end_time.isoformat() if order.actual_end_time else None,
                    "created_time": order.created_time.isoformat() if order.created_time else None,
                    "updated_time": order.updated_time.isoformat() if order.updated_time else None
                })
            
            # 查询卷包机工单
            packing_query = select(PackingOrder)
            packing_conditions = []
            
            if task_id:
                packing_conditions.append(PackingOrder.task_id == task_id)
            if status:
                packing_conditions.append(PackingOrder.work_order_status == status)
            if machine_code:
                packing_conditions.append(PackingOrder.machine_code.like(f"%{machine_code}%"))
            if product_code:
                packing_conditions.append(PackingOrder.product_code.like(f"%{product_code}%"))
            
            if packing_conditions:
                packing_query = packing_query.where(and_(*packing_conditions))
            
            packing_result = await db.execute(packing_query)
            packing_orders = packing_result.scalars().all()
            
            for order in packing_orders:
                work_orders.append({
                    "work_order_nr": order.work_order_nr,
                    "work_order_type": "HJB",
                    "machine_type": "卷包机",
                    "machine_code": order.machine_code,
                    "feeder_code": None,
                    "product_code": order.product_code,
                    "plan_quantity": order.plan_quantity,
                    "work_order_status": order.work_order_status.value if hasattr(order.work_order_status, 'value') else str(order.work_order_status),
                    "planned_start_time": order.planned_start_time.isoformat() if order.planned_start_time else None,
                    "planned_end_time": order.planned_end_time.isoformat() if order.planned_end_time else None,
                    "actual_start_time": order.actual_start_time.isoformat() if order.actual_start_time else None,
                    "actual_end_time": order.actual_end_time.isoformat() if order.actual_end_time else None,
                    "created_time": order.created_time.isoformat() if order.created_time else None,
                    "updated_time": order.updated_time.isoformat() if order.updated_time else None
                })
        
        # 排序（按计划开始时间）
        work_orders.sort(key=lambda x: x.get("planned_start_time") or "")
        
        return work_orders
        
    except Exception as e:
        logger.error(f"查询MES工单数据失败: {str(e)}")
        return []


@router.get("/{work_order_nr}")
async def get_work_order_detail(
    work_order_nr: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询单个工单详情
    
    Args:
        work_order_nr: 工单号
        
    Returns:
        工单详情
    """
    try:
        # 先尝试在卷包机工单中查找
        packing_result = await db.execute(
            select(PackingOrder).where(PackingOrder.work_order_nr == work_order_nr)
        )
        packing_order = packing_result.scalar_one_or_none()
        
        if packing_order:
            return SuccessResponse(
                code=200,
                message="查询成功",
                data={
                    "work_order_nr": packing_order.work_order_nr,
                    "work_order_type": "HJB",
                    "machine_type": "卷包机",
                    "machine_code": packing_order.machine_code,
                    "product_code": packing_order.product_code,
                    "plan_quantity": packing_order.plan_quantity,
                    "work_order_status": packing_order.work_order_status.value if hasattr(packing_order.work_order_status, 'value') else str(packing_order.work_order_status),
                    "planned_start_time": packing_order.planned_start_time.isoformat() if packing_order.planned_start_time else None,
                    "planned_end_time": packing_order.planned_end_time.isoformat() if packing_order.planned_end_time else None,
                    "actual_start_time": packing_order.actual_start_time.isoformat() if packing_order.actual_start_time else None,
                    "actual_end_time": packing_order.actual_end_time.isoformat() if packing_order.actual_end_time else None,
                    "created_time": packing_order.created_time.isoformat() if packing_order.created_time else None,
                    "updated_time": packing_order.updated_time.isoformat() if packing_order.updated_time else None
                }
            )
        
        # 再尝试在喂丝机工单中查找
        feeding_result = await db.execute(
            select(FeedingOrder).where(FeedingOrder.work_order_nr == work_order_nr)
        )
        feeding_order = feeding_result.scalar_one_or_none()
        
        if feeding_order:
            return SuccessResponse(
                code=200,
                message="查询成功",
                data={
                    "work_order_nr": feeding_order.work_order_nr,
                    "work_order_type": "HWS",
                    "machine_type": "喂丝机",
                    "machine_code": feeding_order.machine_code,
                    "product_code": feeding_order.product_code,
                    "plan_quantity": feeding_order.plan_quantity,
                    "safety_stock": getattr(feeding_order, 'safety_stock', 0),
                    "work_order_status": feeding_order.work_order_status.value if hasattr(feeding_order.work_order_status, 'value') else str(feeding_order.work_order_status),
                    "planned_start_time": feeding_order.planned_start_time.isoformat() if feeding_order.planned_start_time else None,
                    "planned_end_time": feeding_order.planned_end_time.isoformat() if feeding_order.planned_end_time else None,
                    "actual_start_time": feeding_order.actual_start_time.isoformat() if feeding_order.actual_start_time else None,
                    "actual_end_time": feeding_order.actual_end_time.isoformat() if feeding_order.actual_end_time else None,
                    "created_time": feeding_order.created_time.isoformat() if feeding_order.created_time else None,
                    "updated_time": feeding_order.updated_time.isoformat() if feeding_order.updated_time else None
                }
            )
        
        # 如果都没找到
        raise HTTPException(status_code=404, detail=f"工单不存在：{work_order_nr}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工单查询失败：{str(e)}")


@router.get("/statistics/summary")
async def get_work_order_statistics(
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取工单统计信息
    
    Returns:
        工单统计数据
    """
    try:
        # 查询卷包机工单统计
        packing_count_result = await db.execute(select(func.count(PackingOrder.id)))
        packing_count = packing_count_result.scalar() or 0
        
        # 查询喂丝机工单统计
        feeding_count_result = await db.execute(select(func.count(FeedingOrder.id)))
        feeding_count = feeding_count_result.scalar() or 0
        
        # 查询状态分组统计（卷包机）
        packing_status_result = await db.execute(
            select(
                PackingOrder.work_order_status,
                func.count(PackingOrder.id).label('count')
            ).group_by(PackingOrder.work_order_status)
        )
        packing_status_stats = {}
        for row in packing_status_result:
            status = row.work_order_status.value if hasattr(row.work_order_status, 'value') else str(row.work_order_status)
            packing_status_stats[status] = row.count
        
        # 查询状态分组统计（喂丝机）
        feeding_status_result = await db.execute(
            select(
                FeedingOrder.work_order_status,
                func.count(FeedingOrder.id).label('count')
            ).group_by(FeedingOrder.work_order_status)
        )
        feeding_status_stats = {}
        for row in feeding_status_result:
            status = row.work_order_status.value if hasattr(row.work_order_status, 'value') else str(row.work_order_status)
            feeding_status_stats[status] = row.count
        
        return SuccessResponse(
            code=200,
            message="统计信息查询成功",
            data={
                "total_work_orders": packing_count + feeding_count,
                "packing_orders": {
                    "total": packing_count,
                    "status_breakdown": packing_status_stats
                },
                "feeding_orders": {
                    "total": feeding_count,
                    "status_breakdown": feeding_status_stats
                },
                "by_type": {
                    "HJB": packing_count,
                    "HWS": feeding_count
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计信息查询失败：{str(e)}")
