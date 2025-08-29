"""
APS智慧排产系统 - 工单管理API

提供工单查询、状态更新等功能
支持卷包机工单和喂丝机工单的统一管理
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.connection import get_async_session
from app.schemas.base import SuccessResponse
from app.models.work_order_models import PackingOrder, FeedingOrder

router = APIRouter(prefix="/work-orders", tags=["工单管理"])


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
    查询工单列表接口
    
    Args:
        task_id: 排产任务ID过滤
        import_batch_id: 导入批次ID过滤
        order_type: 工单类型过滤 (HJB-卷包机, HWS-喂丝机)
        orderType: 工单类型过滤别名
        time_range: 时间范围过滤
        timeRange: 时间范围过滤别名
        status: 工单状态过滤
        machine_code: 机台代码过滤
        product_code: 产品代码过滤
        page: 页码
        page_size: 每页大小
        
    Returns:
        工单列表
    """
    try:
        # 处理参数别名
        effective_order_type = order_type or orderType
        effective_time_range = time_range or timeRange
        
        # 查询真实工单数据
        work_orders = []
        total_count = 0
        
        # 查询卷包机工单
        if not effective_order_type or effective_order_type == 'HJB':
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
        
        # 查询喂丝机工单
        if not effective_order_type or effective_order_type == 'HWS':
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
        
        total_count = len(work_orders)
        
        # 简单分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_orders = work_orders[start_idx:end_idx]
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "work_orders": paginated_orders,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工单查询失败：{str(e)}")


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
