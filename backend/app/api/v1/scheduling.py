"""
APS智慧排产系统 - 排产算法执行API

实现排产算法执行、状态查询、工单查询等功能
"""
import uuid
from datetime import datetime, date
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


def _parse_datetime(datetime_str_or_obj):
    """解析日期时间字符串或对象"""
    if isinstance(datetime_str_or_obj, datetime):
        return datetime_str_or_obj
    elif isinstance(datetime_str_or_obj, str):
        try:
            # 尝试解析 "2024/10/16 15:40:00" 格式
            return datetime.strptime(datetime_str_or_obj, '%Y/%m/%d %H:%M:%S')
        except ValueError:
            try:
                # 尝试解析 "2024-10-16 15:40:00" 格式
                return datetime.strptime(datetime_str_or_obj, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # 如果都失败了，返回当前时间
                return datetime.now()
    else:
        return datetime.now()


def _parse_date(date_str_or_obj):
    """解析日期字符串或对象"""
    if isinstance(date_str_or_obj, date):
        return date_str_or_obj
    elif isinstance(date_str_or_obj, datetime):
        return date_str_or_obj.date()
    elif isinstance(date_str_or_obj, str):
        try:
            # 尝试解析 "2024/10/16" 格式
            return datetime.strptime(date_str_or_obj, '%Y/%m/%d').date()
        except ValueError:
            try:
                # 尝试解析 "2024-10-16" 格式
                return datetime.strptime(date_str_or_obj, '%Y-%m-%d').date()
            except ValueError:
                # 如果都失败了，返回当前日期
                return date.today()
    else:
        return date.today()


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
    执行排产算法接口 - 改为同步执行方便测试
    
    Args:
        request: 排产请求参数
    
    Returns:
        排产任务信息和执行结果
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
        raise HTTPException(status_code=500, detail=f"排产算法执行失败：{str(e)}")


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
                # 获取生成的工单数据（用于aps_packing_order和aps_feeding_order）
                final_work_orders = pipeline_result.get('final_work_orders', [])
                print(f"🔍 DEBUG: 获取到 {len(final_work_orders)} 个工单数据")
                
                # 获取合并后的计划数据（用于aps_work_order_schedule）
                merged_plans = pipeline_result.get('merged_plans', [])
                print(f"🔍 DEBUG: 获取到 {len(merged_plans)} 个合并后的计划数据")
                
                # 持久化工单到数据库 - 使用直接SQL插入避免ORM模型冲突
                packing_orders_count = 0
                feeding_orders_count = 0
                
                # 确保date在这里导入，避免在条件分支中导入导致的作用域问题
                from datetime import date
                from sqlalchemy import text
                
                print(f"🔍 DEBUG: 开始处理工单，task_id = {task_id}")
                
                for i, work_order in enumerate(final_work_orders):
                    # 兼容不同的字段名：order_type 或 work_order_type
                    order_type = work_order.get('order_type') or work_order.get('work_order_type', '')
                    print(f"🔍 DEBUG: 处理工单 {i+1}/{len(final_work_orders)}, order_type = {order_type}")
                    
                    if order_type == 'PACKING':
                        
                        # 处理机器代码 - 从生成的工单数据中获取
                        machine_code_raw = work_order.get('maker_code') or work_order.get('production_line', 'C1')
                        if ',' in machine_code_raw:
                            machine_code_raw = machine_code_raw.split(',')[0].strip()  # 取第一个机器代码并去掉空格
                        
                        # 映射机器代码到数据库格式 - 数据库中实际是C1, C2, C3而不是C01, C02, C03
                        maker_code = machine_code_raw or 'C1'  # 直接使用原始代码，默认使用C1
                        
                        print(f"🔍 DEBUG: 准备插入卷包机工单，plan_id = {work_order.get('plan_id')}, production_line = {maker_code}")
                        
                        # 卷包机工单 - 直接SQL插入
                        insert_sql = """
                        INSERT INTO aps_packing_order (
                            plan_id, production_line, batch_code, material_code, bom_revision, 
                            quantity, plan_start_time, plan_end_time, sequence, shift,
                            input_plan_id, input_batch_code, input_quantity, batch_sequence,
                            is_whole_batch, is_main_channel, is_deleted, is_last_one,
                            input_material_code, input_bom_revision, tiled,
                            is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date,
                            plan_output_quantity, is_outsourcing, is_backup, task_id, order_status,
                            created_time, updated_time
                        ) VALUES (
                            :plan_id, :production_line, :batch_code, :material_code, :bom_revision,
                            :quantity, :plan_start_time, :plan_end_time, :sequence, :shift,
                            :input_plan_id, :input_batch_code, :input_quantity, :batch_sequence,
                            :is_whole_batch, :is_main_channel, :is_deleted, :is_last_one,
                            :input_material_code, :input_bom_revision, :tiled,
                            :is_vaccum, :is_sh93, :is_hdt, :is_flavor, :unit, :plan_date,
                            :plan_output_quantity, :is_outsourcing, :is_backup, :task_id, :order_status,
                            NOW(), NOW()
                        )
                        """
                        
                        try:
                            await db.execute(text(insert_sql), {
                                'plan_id': work_order.get('plan_id') or work_order.get('work_order_nr', f"HJB{work_order.get('original_work_order_nr', '')}"),
                                'production_line': maker_code,
                                'batch_code': work_order.get('batch_code'),
                                'material_code': work_order.get('material_code') or work_order.get('article_nr', 'UNKNOWN'),
                                'bom_revision': work_order.get('bom_revision'),
                                'quantity': work_order.get('quantity') or work_order.get('final_quantity', 0),
                                'plan_start_time': work_order.get('plan_start_time') or work_order.get('planned_start'),
                                'plan_end_time': work_order.get('plan_end_time') or work_order.get('planned_end'),
                                'sequence': work_order.get('sequence', 1),
                                'shift': work_order.get('shift', '白班'),
                                'input_plan_id': work_order.get('input_plan_id'),
                                'input_batch_code': work_order.get('input_batch_code'),
                                'input_quantity': str(work_order.get('input_quantity', 0)),
                                'batch_sequence': work_order.get('batch_sequence', '1'),
                                'is_whole_batch': work_order.get('is_whole_batch', True),
                                'is_main_channel': work_order.get('is_main_channel', True),
                                'is_deleted': work_order.get('is_deleted', False),
                                'is_last_one': work_order.get('is_last_one', False),
                                'input_material_code': work_order.get('input_material_code'),
                                'input_bom_revision': work_order.get('input_bom_revision'),
                                'tiled': work_order.get('tiled', False),
                                'is_vaccum': work_order.get('is_vaccum', False),
                                'is_sh93': work_order.get('is_sh93', False),
                                'is_hdt': work_order.get('is_hdt', False),
                                'is_flavor': work_order.get('is_flavor', False),
                                'unit': work_order.get('unit', '箱'),
                                'plan_date': _parse_date(work_order.get('plan_date', date.today())),
                                'plan_output_quantity': work_order.get('plan_output_quantity'),
                                'is_outsourcing': work_order.get('is_outsourcing', False),
                                'is_backup': work_order.get('is_backup', False),
                                'task_id': task_id,
                                'order_status': 'PLANNED'
                            })
                            packing_orders_count += 1
                            print(f"🔍 DEBUG: 卷包机工单插入成功")
                        except Exception as e:
                            print(f"🔍 DEBUG: 卷包机工单插入失败: {e}")
                            raise
                        
                    elif order_type == 'FEEDING':
                        # 处理机器代码 - 从生成的工单数据中获取
                        machine_code_raw = work_order.get('feeder_code') or work_order.get('production_line', '15')
                        if ',' in machine_code_raw:
                            machine_code_raw = machine_code_raw.split(',')[0].strip()  # 取第一个机器代码并去掉空格
                        
                        # 映射机器代码到数据库格式 - 数据库中有F01或纯数字如15,16,17...32
                        feeder_code = machine_code_raw or '15'  # 直接使用原始代码，默认使用15
                        
                        print(f"🔍 DEBUG: 准备插入喂丝机工单，plan_id = {work_order.get('plan_id')}, production_line = {feeder_code}")
                        
                        # 喂丝机工单 - 直接SQL插入
                        insert_sql = """
                        INSERT INTO aps_feeding_order (
                            plan_id, production_line, batch_code, material_code, bom_revision, 
                            quantity, plan_start_time, plan_end_time, sequence, shift,
                            is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date,
                            plan_output_quantity, is_outsourcing, is_backup, task_id, order_status,
                            created_time, updated_time
                        ) VALUES (
                            :plan_id, :production_line, :batch_code, :material_code, :bom_revision,
                            :quantity, :plan_start_time, :plan_end_time, :sequence, :shift,
                            :is_vaccum, :is_sh93, :is_hdt, :is_flavor, :unit, :plan_date,
                            :plan_output_quantity, :is_outsourcing, :is_backup, :task_id, :order_status,
                            NOW(), NOW()
                        )
                        """
                        
                        try:
                            await db.execute(text(insert_sql), {
                                'plan_id': work_order.get('plan_id') or work_order.get('work_order_nr', f"HWS{work_order.get('original_work_order_nr', '')}"),
                                'production_line': feeder_code,
                                'batch_code': work_order.get('batch_code'),
                                'material_code': work_order.get('material_code') or work_order.get('article_nr', 'UNKNOWN'),
                                'bom_revision': work_order.get('bom_revision'),
                                'quantity': str(work_order.get('quantity') or work_order.get('final_quantity', 0)),
                                'plan_start_time': work_order.get('plan_start_time') or work_order.get('planned_start'),
                                'plan_end_time': work_order.get('plan_end_time') or work_order.get('planned_end'),
                                'sequence': work_order.get('sequence', 1),
                                'shift': work_order.get('shift', '白班'),
                                'is_vaccum': work_order.get('is_vaccum', False),
                                'is_sh93': work_order.get('is_sh93', False),
                                'is_hdt': work_order.get('is_hdt', False),
                                'is_flavor': work_order.get('is_flavor', False),
                                'unit': work_order.get('unit', '公斤'),
                                'plan_date': _parse_date(work_order.get('plan_date', date.today())),
                                'plan_output_quantity': work_order.get('plan_output_quantity'),
                                'is_outsourcing': work_order.get('is_outsourcing', False),
                                'is_backup': work_order.get('is_backup', False),
                                'task_id': task_id,
                                'order_status': 'PLANNED'
                            })
                            feeding_orders_count += 1
                            print(f"🔍 DEBUG: 喂丝机工单插入成功")
                        except Exception as e:
                            print(f"🔍 DEBUG: 喂丝机工单插入失败: {e}")
                            raise
                    
                    else:
                        print(f"🔍 DEBUG: 未知工单类型: {order_type}")
                
                print(f"🔍 DEBUG: 工单处理完成，准备提交事务，卷包机: {packing_orders_count}, 喂丝机: {feeding_orders_count}")
                
                # 写入工单调度数据到 aps_work_order_schedule 表（使用合并后的计划数据）
                print(f"🔍 DEBUG: 开始写入工单调度数据到 aps_work_order_schedule 表")
                work_order_schedule_count = 0
                
                # 使用合并后的计划数据
                for merged_plan in merged_plans:
                    # 获取合并后计划的基本信息
                    work_order_nr = merged_plan.get('work_order_nr', 'UNKNOWN')
                    article_nr = merged_plan.get('article_nr', 'UNKNOWN')
                    final_quantity = merged_plan.get('final_quantity', 0)
                    quantity_total = merged_plan.get('quantity_total', 0)
                    
                    # 获取时间信息
                    planned_start = _parse_datetime(merged_plan.get('planned_start')) if merged_plan.get('planned_start') else datetime.now()
                    planned_end = _parse_datetime(merged_plan.get('planned_end')) if merged_plan.get('planned_end') else datetime.now()
                    
                    # 获取机台信息，处理可能的逗号分隔格式
                    maker_codes_str = merged_plan.get('maker_code', '')
                    feeder_codes_str = merged_plan.get('feeder_code', '')
                    
                    # 分割逗号分隔的机台代码
                    maker_codes = [code.strip() for code in maker_codes_str.split(',') if code.strip()] if maker_codes_str else ['UNKNOWN']
                    feeder_codes = [code.strip() for code in feeder_codes_str.split(',') if code.strip()] if feeder_codes_str else ['UNKNOWN']
                    
                    try:
                        # 插入工单调度记录 - 分别为每个卷包机×喂丝机组合插入
                        schedule_insert_sql = text("""
                        INSERT INTO aps_work_order_schedule (
                            work_order_nr, article_nr, final_quantity, quantity_total,
                            maker_code, feeder_code, planned_start, planned_end,
                            task_id, schedule_status, is_backup, created_time
                        ) VALUES (
                            :work_order_nr, :article_nr, :final_quantity, :quantity_total,
                            :maker_code, :feeder_code, :planned_start, :planned_end,
                            :task_id, :schedule_status, :is_backup, NOW()
                        )
                        """)
                        
                        # 为每个卷包机×喂丝机组合插入一条记录（笛卡尔积）
                        combo_count = 0
                        for maker_code in maker_codes:
                            for feeder_code in feeder_codes:
                                await db.execute(schedule_insert_sql, {
                                    'work_order_nr': work_order_nr,
                                    'article_nr': article_nr,
                                    'final_quantity': final_quantity,
                                    'quantity_total': quantity_total,
                                    'maker_code': maker_code,
                                    'feeder_code': feeder_code,
                                    'planned_start': planned_start,
                                    'planned_end': planned_end,
                                    'task_id': task_id,
                                    'schedule_status': 'COMPLETED',
                                    'is_backup': False
                                })
                                combo_count += 1
                        work_order_schedule_count += combo_count
                        print(f"🔍 DEBUG: 合并计划调度记录插入成功: {work_order_nr} 共 {combo_count} 条组合记录")
                    except Exception as e:
                        print(f"🔍 DEBUG: 工单调度记录插入失败 {work_order_nr}: {e}")
                        # 不中断流程，继续处理其他工单
                
                print(f"🔍 DEBUG: 工单调度数据写入完成，共 {work_order_schedule_count} 条记录")
                
                await db.commit()
                
                print(f"🔍 DEBUG: 事务提交成功!")
                
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
                    "work_order_schedules_generated": work_order_schedule_count,
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
                conditions.append(PackingOrder.order_status == status)
                    
            if conditions:
                packing_query = packing_query.where(and_(*conditions))
            
            packing_result = await db.execute(packing_query)
            packing_orders = packing_result.scalars().all()
            
            for order in packing_orders:
                work_orders.append({
                    "work_order_no": order.plan_id,
                    "order_type": "PACKING",
                    "machine_type": "卷包机", 
                    "production_line": order.production_line,
                    "material_code": order.material_code,
                    "total_quantity": order.quantity,
                    "order_status": order.order_status,
                    "planned_start_time": order.plan_start_time.isoformat() if order.plan_start_time else None,
                    "planned_finish_time": order.plan_end_time.isoformat() if order.plan_end_time else None,
                    "task_id": order.task_id,
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
                conditions.append(FeedingOrder.order_status == status)
                    
            if conditions:
                feeding_query = feeding_query.where(and_(*conditions))
            
            feeding_result = await db.execute(feeding_query)
            feeding_orders = feeding_result.scalars().all()
            
            for order in feeding_orders:
                work_orders.append({
                    "work_order_no": order.plan_id,
                    "order_type": "FEEDING",
                    "machine_type": "喂丝机",
                    "equipment_code": order.production_line,
                    "material_code": order.material_code,
                    "total_quantity": order.quantity if order.quantity else 0,
                    "order_status": order.order_status,
                    "planned_start_time": order.plan_start_time.isoformat() if order.plan_start_time else None,
                    "planned_finish_time": order.plan_end_time.isoformat() if order.plan_end_time else None,
                    "task_id": order.task_id,
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