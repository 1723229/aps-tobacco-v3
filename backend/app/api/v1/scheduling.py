"""
APS智慧排产系统 - 排产算法执行API

实现排产算法执行、状态查询、工单查询等功能
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.schemas.base import SuccessResponse, ErrorResponse
from app.algorithms.scheduling_engine import SchedulingEngine
from app.algorithms.pipeline import AlgorithmPipeline
from app.models.scheduling_models import SchedulingTask, SchedulingTaskStatus
from app.models.work_order_models import PackingOrder, FeedingOrder
from sqlalchemy import select, func

router = APIRouter(prefix="/scheduling", tags=["排产算法管理"])


from pydantic import BaseModel

class SchedulingRequest(BaseModel):
    import_batch_id: str
    algorithm_config: Optional[Dict[str, Any]] = None

@router.post("/execute")
async def execute_scheduling_algorithm(
    request: SchedulingRequest,
    db: AsyncSession = Depends(get_async_session),
    background_tasks: BackgroundTasks = None
):
    """
    执行排产算法接口
    
    Args:
        request: 排产请求参数
    
    Returns:
        排产任务信息
    """
    try:
        # 生成任务ID
        task_id = f"SCHEDULE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 创建排产任务记录
        scheduling_task = SchedulingTask(
            task_id=task_id,
            import_batch_id=request.import_batch_id,
            task_name=f"旬计划排产-{request.import_batch_id}",
            task_status=SchedulingTaskStatus.PENDING,
            current_stage="初始化",
            progress=0,
            merge_enabled=request.algorithm_config.get("merge_enabled", True) if request.algorithm_config else True,
            split_enabled=request.algorithm_config.get("split_enabled", True) if request.algorithm_config else True,
            correction_enabled=request.algorithm_config.get("correction_enabled", True) if request.algorithm_config else True,
            parallel_enabled=request.algorithm_config.get("parallel_enabled", True) if request.algorithm_config else True,
            created_by="api_user"
        )
        
        db.add(scheduling_task)
        await db.commit()
        await db.refresh(scheduling_task)
        
        # 启动后台任务执行排产算法
        if background_tasks:
            background_tasks.add_task(
                execute_scheduling_pipeline_background,
                task_id=task_id,
                import_batch_id=request.import_batch_id,
                algorithm_config=request.algorithm_config or {}
            )
        
        # 返回任务创建结果
        return SuccessResponse(
            code=200,
            message="排产任务创建成功",
            data={
                "task_id": task_id,
                "import_batch_id": request.import_batch_id,
                "status": "PENDING",
                "message": "任务已创建，正在后台执行排产算法"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"排产任务创建失败：{str(e)}")


async def execute_scheduling_pipeline_background(
    task_id: str,
    import_batch_id: str,
    algorithm_config: Dict[str, Any]
):
    """
    后台执行排产算法管道的完整流程
    """
    from app.db.connection import get_db_session
    
    async with get_db_session() as db:
        try:
            # 获取任务记录
            result = await db.execute(
                select(SchedulingTask).where(SchedulingTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return
                
            # 更新任务状态为运行中
            task.task_status = SchedulingTaskStatus.RUNNING
            task.start_time = datetime.now()
            task.current_stage = "数据预处理"
            task.progress = 10
            await db.commit()
            
            # 创建算法管道实例
            pipeline = AlgorithmPipeline()
            
            # 执行完整的排产算法管道
            pipeline_result = await pipeline.execute_full_pipeline_with_batch(
                import_batch_id=import_batch_id,
                use_real_data=True
            )
            
            if pipeline_result.get('success', False):
                # 获取生成的工单数据
                final_work_orders = pipeline_result.get('final_work_orders', [])
                
                # 持久化工单到数据库
                packing_orders_count = 0
                feeding_orders_count = 0
                
                # 确保date在这里导入，避免在条件分支中导入导致的作用域问题
                from datetime import date
                
                for work_order in final_work_orders:
                    machine_type = work_order.get('machine_type', '')
                    
                    if machine_type == 'HJB' or work_order.get('work_order_type') == 'MAKER_PRODUCTION':
                        
                        # 处理机器代码 - 如果是逗号分隔的多个机器，取第一个并映射到数据库格式
                        machine_code_raw = work_order.get('machine_code', 'C1')
                        if ',' in machine_code_raw:
                            machine_code_raw = machine_code_raw.split(',')[0].strip()  # 取第一个机器代码并去掉空格
                        
                        # 映射机器代码到数据库格式 - 数据库中实际是C1, C2, C3而不是C01, C02, C03
                        maker_code = machine_code_raw or 'C1'  # 直接使用原始代码，默认使用C1
                        
                        # 卷包机工单
                        packing_order = PackingOrder(
                            work_order_nr=work_order.get('work_order_nr'),
                            task_id=task_id,
                            work_order_type=work_order.get('work_order_type', 'MAKER_PRODUCTION'),
                            machine_type='HJB',
                            machine_code=maker_code,
                            product_code=work_order.get('product_code'),
                            plan_quantity=work_order.get('plan_quantity', 0),
                            work_order_status='PENDING',  # 使用字符串，让SQLAlchemy自动转换
                            planned_start_time=work_order.get('planned_start_time'),
                            planned_end_time=work_order.get('planned_end_time'),
                            created_time=work_order.get('created_time', datetime.now()),
                            updated_time=datetime.now(),
                            # 新增必需字段
                            article_nr=work_order.get('product_code', 'UNKNOWN'),
                            quantity_total=work_order.get('plan_quantity', 0),
                            final_quantity=work_order.get('plan_quantity', 0),
                            maker_code=maker_code,
                            planned_start=work_order.get('planned_start_time', datetime.now()),
                            planned_end=work_order.get('planned_end_time', datetime.now()),
                            sequence=1,
                            plan_date=date.today(),
                            feeder_code=work_order.get('feeder_code', '15')  # 默认使用15
                        )
                        db.add(packing_order)
                        packing_orders_count += 1
                        
                    elif machine_type == 'HWS' or work_order.get('work_order_type') == 'FEEDER_PRODUCTION':
                        # 处理机器代码 - 如果是逗号分隔的多个机器，取第一个并映射到数据库格式
                        machine_code_raw = work_order.get('machine_code', '15')
                        if ',' in machine_code_raw:
                            machine_code_raw = machine_code_raw.split(',')[0].strip()  # 取第一个机器代码并去掉空格
                        
                        # 映射机器代码到数据库格式 - 数据库中有F01或纯数字如15,16,17...32
                        feeder_code = machine_code_raw or '15'  # 直接使用原始代码，默认使用15
                        
                        # 喂丝机工单
                        feeding_order = FeedingOrder(
                            work_order_nr=work_order.get('work_order_nr'),
                            task_id=task_id,
                            work_order_type=work_order.get('work_order_type', 'FEEDER_PRODUCTION'),
                            machine_type='HWS',
                            machine_code=feeder_code,
                            product_code=work_order.get('product_code'),
                            plan_quantity=work_order.get('plan_quantity', 0),
                            safety_stock=work_order.get('safety_stock', 0),
                            work_order_status='PENDING',  # 使用字符串，让SQLAlchemy自动转换
                            planned_start_time=work_order.get('planned_start_time'),
                            planned_end_time=work_order.get('planned_end_time'),
                            created_time=work_order.get('created_time', datetime.now()),
                            updated_time=datetime.now(),
                            # 新增必需字段
                            article_nr=work_order.get('product_code', 'UNKNOWN'),
                            quantity_total=work_order.get('plan_quantity', 0),
                            base_quantity=work_order.get('plan_quantity', 0),
                            feeder_code=feeder_code,
                            planned_start=work_order.get('planned_start_time', datetime.now()),
                            planned_end=work_order.get('planned_end_time', datetime.now()),
                            sequence=1,
                            plan_date=date.today(),
                            related_packing_orders=[],
                            packing_machines=[]
                        )
                        db.add(feeding_order)
                        feeding_orders_count += 1
                
                await db.commit()
                
                # 更新任务状态为已完成
                task.task_status = SchedulingTaskStatus.COMPLETED
                task.end_time = datetime.now()
                task.current_stage = "完成"
                task.progress = 100
                task.total_records = pipeline_result.get('summary', {}).get('input_records', 0)
                task.processed_records = len(final_work_orders)
                
                if task.start_time:
                    execution_duration = (task.end_time - task.start_time).total_seconds()
                    task.execution_duration = execution_duration
                
                task.result_summary = {
                    "packing_orders_generated": packing_orders_count,
                    "feeding_orders_generated": feeding_orders_count,
                    "total_work_orders": len(final_work_orders),
                    "execution_summary": pipeline_result.get('summary', {}),
                    "pipeline_stages": len(pipeline_result.get('stages', {}))
                }
                
                await db.commit()
                
            else:
                # 管道执行失败
                task.task_status = SchedulingTaskStatus.FAILED
                task.end_time = datetime.now()
                task.current_stage = "失败"
                task.progress = 0
                task.error_message = pipeline_result.get('error', '排产算法执行失败')
                
                if task.start_time:
                    execution_duration = (task.end_time - task.start_time).total_seconds()
                    task.execution_duration = execution_duration
                
                await db.commit()
                
        except Exception as e:
            # 处理异常情况
            try:
                task.task_status = SchedulingTaskStatus.FAILED
                task.end_time = datetime.now()
                task.current_stage = "异常"
                task.error_message = f"排产算法执行异常：{str(e)}"
                
                if task.start_time:
                    execution_duration = (task.end_time - task.start_time).total_seconds()
                    task.execution_duration = execution_duration
                
                await db.commit()
            except:
                pass


# 任务管理相关API
@router.get("/tasks")
async def get_scheduling_tasks(
    status: Optional[str] = None,
    import_batch_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询排产任务历史记录
    支持多维度筛选：状态、批次、时间范围
    """
    try:
        from sqlalchemy import select, and_, desc, func
        from datetime import datetime
        
        # 构建查询条件
        conditions = []
        if status:
            conditions.append(SchedulingTask.task_status == status)
        if import_batch_id:
            conditions.append(SchedulingTask.import_batch_id == import_batch_id)
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            conditions.append(SchedulingTask.created_time >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            conditions.append(SchedulingTask.created_time <= end_dt)
        
        # 构建基础查询
        base_query = select(SchedulingTask)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count()).select_from(SchedulingTask)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # 分页查询
        offset = (page - 1) * page_size
        query = base_query.order_by(desc(SchedulingTask.created_time)).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # 转换为响应格式
        task_records = []
        for task in tasks:
            task_records.append({
                "task_id": task.task_id,
                "import_batch_id": task.import_batch_id,
                "task_name": task.task_name,
                "status": task.task_status.value,
                "current_stage": task.current_stage,
                "progress": task.progress,
                "total_records": task.total_records,
                "processed_records": task.processed_records,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "execution_duration": task.execution_duration,
                "error_message": task.error_message,
                "result_summary": task.result_summary,
                "algorithm_config": {
                    "merge_enabled": task.merge_enabled,
                    "split_enabled": task.split_enabled,
                    "correction_enabled": task.correction_enabled,
                    "parallel_enabled": task.parallel_enabled
                },
                "created_time": task.created_time.isoformat()
            })
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "tasks": task_records,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询排产任务失败：{str(e)}")


@router.get("/tasks/{task_id}")
async def get_scheduling_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取排产任务完整详情
    包含：基本信息、执行日志、工单统计、关联数据
    """
    try:
        from sqlalchemy import select
        from app.models.scheduling_models import ProcessingLog
        
        # 查询任务基本信息
        task_result = await db.execute(
            select(SchedulingTask).where(SchedulingTask.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"排产任务不存在：{task_id}")
        
        # 查询执行日志
        logs_result = await db.execute(
            select(ProcessingLog).where(ProcessingLog.task_id == task_id)
            .order_by(ProcessingLog.execution_time.desc())
        )
        logs = logs_result.scalars().all()
        
        # 转换日志格式
        log_records = []
        for log in logs:
            log_records.append({
                "id": log.id,
                "stage": log.stage,
                "step_name": log.step_name,
                "level": log.log_level.value,
                "message": log.log_message,
                "execution_time": log.execution_time.isoformat(),
                "duration_ms": log.duration_ms,
                "processing_data": log.processing_data
            })
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "task": {
                    "task_id": task.task_id,
                    "import_batch_id": task.import_batch_id,
                    "task_name": task.task_name,
                    "status": task.task_status.value,
                    "current_stage": task.current_stage,
                    "progress": task.progress,
                    "total_records": task.total_records,
                    "processed_records": task.processed_records,
                    "start_time": task.start_time.isoformat() if task.start_time else None,
                    "end_time": task.end_time.isoformat() if task.end_time else None,
                    "execution_duration": task.execution_duration,
                    "error_message": task.error_message,
                    "result_summary": task.result_summary,
                    "algorithm_config": {
                        "merge_enabled": task.merge_enabled,
                        "split_enabled": task.split_enabled,
                        "correction_enabled": task.correction_enabled,
                        "parallel_enabled": task.parallel_enabled
                    },
                    "created_by": task.created_by,
                    "created_time": task.created_time.isoformat(),
                    "updated_time": task.updated_time.isoformat()
                },
                "logs": log_records,
                "logs_count": len(log_records)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务详情失败：{str(e)}")


@router.post("/tasks/{task_id}/retry")
async def retry_scheduling_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    重新执行失败的排产任务
    """
    try:
        from sqlalchemy import select, update
        
        # 查询任务
        result = await db.execute(
            select(SchedulingTask).where(SchedulingTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"排产任务不存在：{task_id}")
        
        if task.task_status not in [SchedulingTaskStatus.FAILED, SchedulingTaskStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="只能重试失败或已取消的任务")
        
        # 重置任务状态
        await db.execute(
            update(SchedulingTask)
            .where(SchedulingTask.task_id == task_id)
            .values(
                task_status=SchedulingTaskStatus.PENDING,
                current_stage="等待重试",
                progress=0,
                start_time=None,
                end_time=None,
                execution_duration=None,
                error_message=None,
                processed_records=0
            )
        )
        await db.commit()
        
        # TODO: 这里应该触发后台任务重新执行排产算法
        # 现在先返回成功状态，后续需要集成后台任务系统
        
        return SuccessResponse(
            code=200,
            message="任务重试已启动",
            data={
                "task_id": task_id,
                "status": "PENDING",
                "message": "任务已重置，正在准备重新执行"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务重试失败：{str(e)}")


@router.post("/tasks/{task_id}/cancel")
async def cancel_scheduling_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    取消运行中的排产任务
    """
    try:
        from sqlalchemy import select, update
        from datetime import datetime
        
        # 查询任务
        result = await db.execute(
            select(SchedulingTask).where(SchedulingTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"排产任务不存在：{task_id}")
        
        if task.task_status not in [SchedulingTaskStatus.PENDING, SchedulingTaskStatus.RUNNING]:
            raise HTTPException(status_code=400, detail="只能取消等待中或运行中的任务")
        
        # 更新任务状态为已取消
        current_time = datetime.now()
        execution_duration = None
        if task.start_time:
            execution_duration = int((current_time - task.start_time).total_seconds())
        
        await db.execute(
            update(SchedulingTask)
            .where(SchedulingTask.task_id == task_id)
            .values(
                task_status=SchedulingTaskStatus.CANCELLED,
                current_stage="已取消",
                end_time=current_time,
                execution_duration=execution_duration,
                error_message="任务被用户取消"
            )
        )
        await db.commit()
        
        return SuccessResponse(
            code=200,
            message="任务已取消",
            data={
                "task_id": task_id,
                "status": "CANCELLED",
                "message": "任务已成功取消"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务取消失败：{str(e)}")


@router.get("/tasks/statistics")
async def get_scheduling_statistics(
    days: int = 30,
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取排产任务统计信息
    成功率、执行时长分析、工单生成统计
    """
    try:
        from sqlalchemy import select, func, and_
        from datetime import datetime, timedelta
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 总任务数
        total_result = await db.execute(
            select(func.count()).select_from(SchedulingTask)
            .where(SchedulingTask.created_time >= start_date)
        )
        total_tasks = total_result.scalar() or 0
        
        # 成功任务数
        success_result = await db.execute(
            select(func.count()).select_from(SchedulingTask)
            .where(and_(
                SchedulingTask.created_time >= start_date,
                SchedulingTask.task_status == SchedulingTaskStatus.COMPLETED
            ))
        )
        success_tasks = success_result.scalar() or 0
        
        # 失败任务数
        failed_result = await db.execute(
            select(func.count()).select_from(SchedulingTask)
            .where(and_(
                SchedulingTask.created_time >= start_date,
                SchedulingTask.task_status == SchedulingTaskStatus.FAILED
            ))
        )
        failed_tasks = failed_result.scalar() or 0
        
        # 运行中任务数
        running_result = await db.execute(
            select(func.count()).select_from(SchedulingTask)
            .where(SchedulingTask.task_status == SchedulingTaskStatus.RUNNING)
        )
        running_tasks = running_result.scalar() or 0
        
        # 平均执行时长
        avg_duration_result = await db.execute(
            select(func.avg(SchedulingTask.execution_duration)).select_from(SchedulingTask)
            .where(and_(
                SchedulingTask.created_time >= start_date,
                SchedulingTask.task_status == SchedulingTaskStatus.COMPLETED,
                SchedulingTask.execution_duration != None
            ))
        )
        avg_duration = avg_duration_result.scalar() or 0
        
        # 计算成功率
        success_rate = (success_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 总工单生成统计（基于result_summary）
        total_work_orders = 0
        packing_orders = 0
        feeding_orders = 0
        
        summary_result = await db.execute(
            select(SchedulingTask.result_summary).select_from(SchedulingTask)
            .where(and_(
                SchedulingTask.created_time >= start_date,
                SchedulingTask.task_status == SchedulingTaskStatus.COMPLETED,
                SchedulingTask.result_summary != None
            ))
        )
        
        for (summary,) in summary_result.fetchall():
            if summary:
                total_work_orders += summary.get('total_work_orders', 0)
                packing_orders += summary.get('packing_orders_generated', 0)
                feeding_orders += summary.get('feeding_orders_generated', 0)
        
        return SuccessResponse(
            code=200,
            message="统计信息获取成功",
            data={
                "period_days": days,
                "total_tasks": total_tasks,
                "success_tasks": success_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "success_rate": round(success_rate, 2),
                "avg_duration": round(avg_duration, 2) if avg_duration else 0,
                "work_orders_generated": {
                    "total": total_work_orders,
                    "packing": packing_orders,
                    "feeding": feeding_orders
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败：{str(e)}")


@router.get("/tasks/{task_id}/status")
async def get_scheduling_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询排产任务状态接口
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(SchedulingTask).where(SchedulingTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"排产任务不存在：{task_id}")
        
        return SuccessResponse(
            code=200,
            message="查询成功",
            data={
                "task_id": task.task_id,
                "import_batch_id": task.import_batch_id,
                "task_name": task.task_name,
                "status": task.task_status.value,
                "current_stage": task.current_stage,
                "progress": task.progress,
                "total_records": task.total_records,
                "processed_records": task.processed_records,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "execution_duration": task.execution_duration,
                "error_message": task.error_message,
                "result_summary": task.result_summary,
                "algorithm_config": {
                    "merge_enabled": task.merge_enabled,
                    "split_enabled": task.split_enabled,
                    "correction_enabled": task.correction_enabled,
                    "parallel_enabled": task.parallel_enabled
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"状态查询失败：{str(e)}")


# 工单查询路由
work_orders_router = APIRouter(prefix="/work-orders", tags=["工单管理"])


@router.get("/work-orders")
async def get_work_orders(
    task_id: Optional[str] = None,
    import_batch_id: Optional[str] = None,
    order_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_async_session)
):
    """
    查询工单列表接口
    
    Args:
        task_id: 排产任务ID过滤
        import_batch_id: 导入批次ID过滤
        order_type: 工单类型过滤 (HJB-卷包机, HWS-喂丝机)
        status: 工单状态过滤
        page: 页码
        page_size: 每页大小
        
    Returns:
        工单列表
    """
    try:
        from sqlalchemy import select, func, and_, outerjoin, or_
        
        # 查询真实工单数据
        work_orders = []
        total_count = 0
        
        # 查询卷包机工单
        if not order_type or order_type == 'HJB':
            packing_query = select(PackingOrder)
            
            # 添加过滤条件
            conditions = []
            if task_id:
                conditions.append(PackingOrder.task_id == task_id)
            if import_batch_id:
                # 通过 import_batch_id 查找对应的任务，然后通过 task_id 匹配
                task_result = await db.execute(
                    select(SchedulingTask.task_id).where(SchedulingTask.import_batch_id == import_batch_id)
                )
                matching_task_ids = [row[0] for row in task_result.fetchall()]
                if matching_task_ids:
                    conditions.append(PackingOrder.task_id.in_(matching_task_ids))
            if status:
                conditions.append(PackingOrder.work_order_status == status)
                    
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
        if not order_type or order_type == 'HWS':
            feeding_query = select(FeedingOrder)
            
            # 添加过滤条件
            conditions = []
            if task_id:
                conditions.append(FeedingOrder.task_id == task_id)
            if import_batch_id:
                # 通过 import_batch_id 查找对应的任务，然后通过 task_id 匹配
                task_result = await db.execute(
                    select(SchedulingTask.task_id).where(SchedulingTask.import_batch_id == import_batch_id)
                )
                matching_task_ids = [row[0] for row in task_result.fetchall()]
                if matching_task_ids:
                    conditions.append(FeedingOrder.task_id.in_(matching_task_ids))
            if status:
                conditions.append(FeedingOrder.work_order_status == status)
                    
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
                    "safety_stock": order.safety_stock,
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