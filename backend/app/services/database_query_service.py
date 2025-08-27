"""
APS智慧排产系统 - 数据库查询服务

提供轮保计划、班次配置、机台关系等数据的查询服务
这些数据将被算法模块使用，替代硬编码的假数据
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connection import get_db_session
import logging

logger = logging.getLogger(__name__)


class DatabaseQueryService:
    """数据库查询服务类"""
    
    @staticmethod
    async def get_decade_plans(
        import_batch_id: str = None,
        work_order_nrs: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        validation_status: str = 'VALID'
    ) -> List[Dict[str, Any]]:
        """
        查询旬计划数据 - 这是算法处理的核心源数据
        
        Args:
            import_batch_id: 导入批次ID
            work_order_nrs: 工单号列表
            start_date: 计划开始日期范围
            end_date: 计划结束日期范围
            validation_status: 验证状态，默认只查询有效数据
            
        Returns:
            List[Dict]: 旬计划数据列表
        """
        if start_date is None:
            # 默认查询范围扩大到过去1年到未来1年，确保覆盖所有数据
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=365)).date()
        if end_date is None:
            from datetime import timedelta
            end_date = (datetime.now() + timedelta(days=365)).date()
            
        query = """
        SELECT id, import_batch_id, work_order_nr, article_nr, 
               package_type, specification, quantity_total, final_quantity,
               production_unit, maker_code, feeder_code,
               planned_start, planned_end, production_date_range,
               validation_status, validation_message
        FROM aps_decade_plan
        WHERE DATE(planned_start) >= :start_date
        AND DATE(planned_start) <= :end_date
        AND validation_status = :validation_status
        """
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'validation_status': validation_status
        }
        
        # 添加可选过滤条件
        if import_batch_id:
            query += " AND import_batch_id = :import_batch_id"
            params['import_batch_id'] = import_batch_id
            
        if work_order_nrs:
            query += " AND work_order_nr IN :work_order_nrs"
            params['work_order_nrs'] = tuple(work_order_nrs)
        
        query += " ORDER BY planned_start, work_order_nr"
        
        async with get_db_session() as db:
            result = await db.execute(text(query), params)
            rows = result.fetchall()
            
            decade_plans = []
            for row in rows:
                decade_plans.append({
                    'id': row.id,
                    'import_batch_id': row.import_batch_id,
                    'work_order_nr': row.work_order_nr,
                    'article_nr': row.article_nr,
                    'package_type': row.package_type,
                    'specification': row.specification,
                    'quantity_total': row.quantity_total,
                    'final_quantity': row.final_quantity,
                    'production_unit': row.production_unit,
                    'maker_code': row.maker_code,
                    'feeder_code': row.feeder_code,
                    'planned_start': row.planned_start,
                    'planned_end': row.planned_end,
                    'production_date_range': row.production_date_range,
                    'validation_status': row.validation_status,
                    'validation_message': row.validation_message
                })
            
            logger.info(f"查询到 {len(decade_plans)} 条旬计划数据")
            return decade_plans
    
    @staticmethod
    async def get_maintenance_plans(
        machine_codes: List[str] = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        查询轮保计划
        
        Args:
            machine_codes: 机台代码列表，None表示查询所有
            start_date: 开始日期，None表示今天
            end_date: 结束日期，None表示开始日期+7天
            
        Returns:
            List[Dict]: 轮保计划列表
        """
        if start_date is None:
            start_date = datetime.now().date()
        if end_date is None:
            from datetime import timedelta
            end_date = start_date + timedelta(days=7)
        
        query = """
        SELECT machine_code, maint_start_time, maint_end_time, 
               maint_type, maint_level, plan_status
        FROM aps_maintenance_plan 
        WHERE DATE(maint_start_time) >= :start_date 
        AND DATE(maint_start_time) <= :end_date
        AND plan_status IN ('PLANNED', 'CONFIRMED')
        """
        
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        if machine_codes:
            query += " AND machine_code IN :machine_codes"
            params['machine_codes'] = tuple(machine_codes)
        
        async with get_db_session() as db:
            result = await db.execute(text(query), params)
            rows = result.fetchall()
            
            maintenance_plans = []
            for row in rows:
                maintenance_plans.append({
                    'machine_code': row.machine_code,
                    'maint_start_time': row.maint_start_time,
                    'maint_end_time': row.maint_end_time,
                    'maint_type': row.maint_type,
                    'maint_level': row.maint_level,
                    'plan_status': row.plan_status
                })
            
            logger.info(f"查询到 {len(maintenance_plans)} 条轮保计划")
            return maintenance_plans
    
    @staticmethod
    async def get_shift_config(
        machine_name: str = '*',
        effective_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        查询班次配置
        
        Args:
            machine_name: 机台名称，默认'*'表示所有机台
            effective_date: 生效日期，None表示今天
            
        Returns:
            List[Dict]: 班次配置列表
        """
        if effective_date is None:
            effective_date = datetime.now().date()
        
        query = """
        SELECT shift_name, machine_name, start_time, end_time,
               is_ot_needed, max_ot_duration
        FROM aps_shift_config 
        WHERE machine_name = :machine_name
        AND effective_from <= :effective_date
        AND (effective_to IS NULL OR effective_to >= :effective_date)
        AND status = 'ACTIVE'
        ORDER BY shift_name
        """
        
        params = {
            'machine_name': machine_name,
            'effective_date': effective_date
        }
        
        async with get_db_session() as db:
            result = await db.execute(text(query), params)
            rows = result.fetchall()
            
            shift_configs = []
            for row in rows:
                # 处理时间对象转换为字符串
                # 数据库可能返回time或timedelta对象
                if hasattr(row.start_time, 'strftime'):
                    # time对象
                    start_time = row.start_time.strftime('%H:%M')
                elif hasattr(row.start_time, 'total_seconds'):
                    # timedelta对象，转换为时间
                    total_seconds = int(row.start_time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    start_time = f'{hours:02d}:{minutes:02d}'
                else:
                    start_time = '08:00'
                
                if hasattr(row.end_time, 'strftime'):
                    # time对象
                    end_time = row.end_time.strftime('%H:%M')
                elif hasattr(row.end_time, 'total_seconds'):
                    # timedelta对象，转换为时间
                    total_seconds = int(row.end_time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    end_time = f'{hours:02d}:{minutes:02d}'
                else:
                    end_time = '16:00'
                
                # 处理max_ot_duration
                max_ot_duration = None
                if row.max_ot_duration:
                    if hasattr(row.max_ot_duration, 'strftime'):
                        # time对象
                        max_ot_duration = row.max_ot_duration.strftime('%H:%M')
                    elif hasattr(row.max_ot_duration, 'total_seconds'):
                        # timedelta对象，转换为时间
                        total_seconds = int(row.max_ot_duration.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        max_ot_duration = f'{hours:02d}:{minutes:02d}'
                
                shift_configs.append({
                    'name': row.shift_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_ot_needed': bool(row.is_ot_needed) if row.is_ot_needed is not None else False,
                    'max_ot_duration': max_ot_duration
                })
            
            logger.info(f"查询到 {len(shift_configs)} 个班次配置")
            return shift_configs
    
    @staticmethod
    async def get_machine_relations() -> Dict[str, List[str]]:
        """
        查询机台关系映射
        
        Returns:
            Dict[str, List[str]]: {喂丝机代码: [卷包机代码列表]}
        """
        query = """
        SELECT feeder_code, maker_code, priority
        FROM aps_machine_relation 
        WHERE status = 'ACTIVE'
        AND (effective_to IS NULL OR effective_to >= CURDATE())
        ORDER BY feeder_code, priority
        """
        
        async with get_db_session() as db:
            result = await db.execute(text(query))
            rows = result.fetchall()
            
            relations = {}
            for row in rows:
                feeder_code = row.feeder_code
                maker_code = row.maker_code
                
                if feeder_code not in relations:
                    relations[feeder_code] = []
                
                relations[feeder_code].append(maker_code)
            
            logger.info(f"查询到 {len(relations)} 个喂丝机的机台关系")
            return relations