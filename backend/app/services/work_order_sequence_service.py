"""
APS智慧排产系统 - 工单号生成服务

实现MES规范的工单号生成，支持序列管理和自动递增
格式：H + 工单类型（2位）+ 9位流水号
"""
from typing import Dict, Any
from datetime import datetime, date
from app.services.database_query_service import DatabaseQueryService
import logging

logger = logging.getLogger(__name__)


class WorkOrderSequenceService:
    """工单号序列生成服务"""
    
    @staticmethod
    async def generate_plan_id(order_type: str, sequence_date: date = None) -> str:
        """
        生成MES规范的计划ID
        
        格式：H + 工单类型（2位）+ 9位流水号
        例：HWS000000001（喂丝机）、HJB000000001（卷包机）
        
        Args:
            order_type: 工单类型 'HWS' 或 'HJB'
            sequence_date: 序列日期，None表示今天
            
        Returns:
            str: MES规范的计划ID
        """
        if sequence_date is None:
            sequence_date = datetime.now().date()
        
        # 验证工单类型
        if order_type not in ['HWS', 'HJB']:
            raise ValueError(f"无效的工单类型: {order_type}，只支持 'HWS' 和 'HJB'")
        
        try:
            # 获取并更新序列号
            sequence_info = await DatabaseQueryService.get_work_order_sequence(
                order_type=order_type,
                sequence_date=sequence_date
            )
            
            # 生成MES规范的计划ID：H + 工单类型 + 9位流水号
            sequence_number = sequence_info['sequence_number']
            plan_id = f"H{order_type}{sequence_number:09d}"
            
            logger.info(f"生成MES计划ID: {plan_id} (类型: {order_type}, 序列: {sequence_number})")
            
            return plan_id
            
        except Exception as e:
            logger.error(f"工单号生成失败: {str(e)}")
            # 生成临时ID作为降级方案
            import random
            fallback_sequence = random.randint(1, 999999999)
            fallback_id = f"H{order_type}{fallback_sequence:09d}"
            logger.warning(f"使用降级方案生成临时ID: {fallback_id}")
            return fallback_id
    
    @staticmethod
    async def generate_feeding_plan_id() -> str:
        """
        生成喂丝机工单计划ID
        
        Returns:
            str: HWS格式的计划ID
        """
        return await WorkOrderSequenceService.generate_plan_id('HWS')
    
    @staticmethod
    async def generate_packing_plan_id() -> str:
        """
        生成卷包机工单计划ID
        
        Returns:
            str: HJB格式的计划ID
        """
        return await WorkOrderSequenceService.generate_plan_id('HJB')
    
    @staticmethod
    async def batch_generate_plan_ids(order_types: list, sequence_date: date = None) -> Dict[str, str]:
        """
        批量生成计划ID
        
        Args:
            order_types: 工单类型列表，如 ['HWS', 'HJB', 'HWS']
            sequence_date: 序列日期
            
        Returns:
            Dict[str, str]: {工单类型: 计划ID}
        """
        if sequence_date is None:
            sequence_date = datetime.now().date()
        
        plan_ids = {}
        for order_type in order_types:
            try:
                plan_id = await WorkOrderSequenceService.generate_plan_id(order_type, sequence_date)
                plan_ids[f"{order_type}_{len([t for t in order_types[:order_types.index(order_type)+1] if t == order_type])}"] = plan_id
            except Exception as e:
                logger.error(f"批量生成工单号失败 - 类型 {order_type}: {str(e)}")
                # 继续处理其他类型
                continue
        
        logger.info(f"批量生成 {len(plan_ids)} 个计划ID")
        return plan_ids
    
    @staticmethod
    async def get_sequence_status(order_type: str = None) -> Dict[str, Any]:
        """
        获取序列生成状态统计
        
        Args:
            order_type: 工单类型，None表示查询所有
            
        Returns:
            Dict[str, Any]: 序列状态统计
        """
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        # 查询序列状态
        if order_type:
            query = """
            SELECT order_type, sequence_date, current_sequence, last_plan_id, updated_time
            FROM aps_work_order_sequence 
            WHERE order_type = :order_type
            ORDER BY sequence_date DESC
            LIMIT 10
            """
            params = {'order_type': order_type}
        else:
            query = """
            SELECT order_type, sequence_date, current_sequence, last_plan_id, updated_time
            FROM aps_work_order_sequence 
            ORDER BY sequence_date DESC, order_type
            LIMIT 20
            """
            params = {}
        
        try:
            async with get_db_session() as db:
                result = await db.execute(text(query), params)
                rows = result.fetchall()
                
                sequences = []
                total_sequences = {}
                
                for row in rows:
                    sequences.append({
                        'order_type': row.order_type,
                        'sequence_date': row.sequence_date.strftime('%Y-%m-%d'),
                        'current_sequence': row.current_sequence,
                        'last_plan_id': row.last_plan_id,
                        'updated_time': row.updated_time.strftime('%Y-%m-%d %H:%M:%S') if row.updated_time else None
                    })
                    
                    # 统计总数
                    if row.order_type not in total_sequences:
                        total_sequences[row.order_type] = 0
                    total_sequences[row.order_type] += row.current_sequence
                
                return {
                    'sequences': sequences,
                    'total_sequences': total_sequences,
                    'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            logger.error(f"查询序列状态失败: {str(e)}")
            return {
                'sequences': [],
                'total_sequences': {},
                'error': str(e)
            }
    
    @staticmethod
    async def reset_sequence(order_type: str, sequence_date: date = None) -> bool:
        """
        重置指定日期的序列号（谨慎使用）
        
        Args:
            order_type: 工单类型
            sequence_date: 序列日期，None表示今天
            
        Returns:
            bool: 是否重置成功
        """
        if sequence_date is None:
            sequence_date = datetime.now().date()
        
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        try:
            async with get_db_session() as db:
                # 重置序列为0
                reset_query = """
                UPDATE aps_work_order_sequence 
                SET current_sequence = 0, 
                    last_plan_id = NULL,
                    updated_time = NOW()
                WHERE order_type = :order_type 
                AND DATE(sequence_date) = :sequence_date
                """
                
                result = await db.execute(text(reset_query), {
                    'order_type': order_type,
                    'sequence_date': sequence_date
                })
                
                await db.commit()
                
                affected_rows = result.rowcount
                if affected_rows > 0:
                    logger.info(f"重置序列成功: {order_type} - {sequence_date}")
                    return True
                else:
                    logger.warning(f"重置序列失败，未找到记录: {order_type} - {sequence_date}")
                    return False
                
        except Exception as e:
            logger.error(f"重置序列失败: {str(e)}")
            return False


# 便捷函数
async def generate_feeding_plan_id() -> str:
    """快速生成喂丝机工单ID"""
    return await WorkOrderSequenceService.generate_feeding_plan_id()


async def generate_packing_plan_id() -> str:
    """快速生成卷包机工单ID"""
    return await WorkOrderSequenceService.generate_packing_plan_id()


async def get_sequence_stats() -> Dict[str, Any]:
    """快速获取序列统计"""
    return await WorkOrderSequenceService.get_sequence_status()