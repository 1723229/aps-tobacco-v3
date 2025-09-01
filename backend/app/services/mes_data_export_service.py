"""
APS智慧排产系统 - MES接口数据导出服务

实现符合MES接口规范的数据导出功能，支持XML和JSON格式
提供工单数据的结构化导出和状态同步
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging

from app.services.database_query_service import DatabaseQueryService
from app.models.work_order_models import FeedingOrder, PackingOrder, WorkOrderSchedule

logger = logging.getLogger(__name__)


@dataclass
class MESExportConfig:
    """MES导出配置"""
    export_format: str = "XML"  # XML, JSON
    include_feeding_orders: bool = True
    include_packing_orders: bool = True
    include_input_batch: bool = True
    validate_data: bool = True
    pretty_format: bool = True


class MESDataExportService:
    """MES数据导出服务"""
    
    def __init__(self):
        self.config = MESExportConfig()
        
    async def export_work_orders_by_task(
        self, 
        task_id: str, 
        export_format: str = "XML"
    ) -> Dict[str, Any]:
        """
        按排产任务ID导出工单数据
        
        Args:
            task_id: 排产任务ID
            export_format: 导出格式 XML/JSON
            
        Returns:
            Dict: 导出结果
        """
        try:
            # 查询喂丝机工单
            feeding_orders = await self._get_feeding_orders_by_task(task_id)
            
            # 查询卷包机工单
            packing_orders = await self._get_packing_orders_by_task(task_id)
            
            # 构建导出数据
            export_data = {
                'task_id': task_id,
                'export_time': datetime.now().isoformat(),
                'feeding_orders_count': len(feeding_orders),
                'packing_orders_count': len(packing_orders),
                'feeding_orders': feeding_orders,
                'packing_orders': packing_orders
            }
            
            # 根据格式导出
            if export_format.upper() == "XML":
                content = self._generate_mes_xml(export_data)
                content_type = "application/xml"
            else:
                content = self._generate_mes_json(export_data)
                content_type = "application/json"
            
            logger.info(f"MES数据导出完成 - 任务{task_id}: {len(feeding_orders)}个喂丝机工单, {len(packing_orders)}个卷包机工单")
            
            return {
                'success': True,
                'task_id': task_id,
                'export_format': export_format,
                'content_type': content_type,
                'content': content,
                'statistics': {
                    'feeding_orders': len(feeding_orders),
                    'packing_orders': len(packing_orders),
                    'total_orders': len(feeding_orders) + len(packing_orders)
                }
            }
            
        except Exception as e:
            logger.error(f"MES数据导出失败 - 任务{task_id}: {str(e)}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def export_work_orders_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        export_format: str = "XML"
    ) -> Dict[str, Any]:
        """
        按日期范围导出工单数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            export_format: 导出格式
            
        Returns:
            Dict: 导出结果
        """
        try:
            # 查询指定日期范围的工单
            feeding_orders = await self._get_feeding_orders_by_date_range(start_date, end_date)
            packing_orders = await self._get_packing_orders_by_date_range(start_date, end_date)
            
            export_data = {
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'export_time': datetime.now().isoformat(),
                'feeding_orders_count': len(feeding_orders),
                'packing_orders_count': len(packing_orders),
                'feeding_orders': feeding_orders,
                'packing_orders': packing_orders
            }
            
            if export_format.upper() == "XML":
                content = self._generate_mes_xml(export_data)
                content_type = "application/xml"
            else:
                content = self._generate_mes_json(export_data)
                content_type = "application/json"
            
            return {
                'success': True,
                'content_type': content_type,
                'content': content,
                'statistics': {
                    'feeding_orders': len(feeding_orders),
                    'packing_orders': len(packing_orders),
                    'date_range': f"{start_date.date()} ~ {end_date.date()}"
                }
            }
            
        except Exception as e:
            logger.error(f"按日期范围导出MES数据失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _get_feeding_orders_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """查询指定任务的喂丝机工单"""
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        query = """
        SELECT plan_id, production_line, batch_code, material_code, bom_revision, quantity,
               plan_start_time, plan_end_time, sequence, shift,
               is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date, plan_output_quantity,
               is_outsourcing, is_backup, order_status
        FROM aps_feeding_order 
        WHERE task_id = :task_id 
        ORDER BY plan_start_time, sequence
        """
        
        async with get_db_session() as db:
            result = await db.execute(text(query), {'task_id': task_id})
            rows = result.fetchall()
            
            orders = []
            for row in rows:
                orders.append({
                    'plan_id': row.plan_id,
                    'production_line': row.production_line,
                    'batch_code': row.batch_code,
                    'material_code': row.material_code,
                    'bom_revision': row.bom_revision,
                    'quantity': row.quantity,
                    'plan_start_time': row.plan_start_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_start_time else None,
                    'plan_end_time': row.plan_end_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_end_time else None,
                    'sequence': row.sequence,
                    'shift': row.shift,
                    'is_vaccum': bool(row.is_vaccum),
                    'is_sh93': bool(row.is_sh93),
                    'is_hdt': bool(row.is_hdt),
                    'is_flavor': bool(row.is_flavor),
                    'unit': row.unit,
                    'plan_date': row.plan_date.strftime('%Y/%m/%d') if row.plan_date else None,
                    'plan_output_quantity': row.plan_output_quantity,
                    'is_outsourcing': bool(row.is_outsourcing),
                    'is_backup': bool(row.is_backup),
                    'order_status': row.order_status
                })
            
            return orders
    
    async def _get_packing_orders_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """查询指定任务的卷包机工单"""
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        query = """
        SELECT plan_id, production_line, batch_code, material_code, bom_revision, quantity,
               plan_start_time, plan_end_time, sequence, shift,
               input_plan_id, input_batch_code, input_quantity, batch_sequence,
               is_whole_batch, is_main_channel, is_deleted, is_last_one,
               input_material_code, input_bom_revision, tiled,
               is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date, plan_output_quantity,
               is_outsourcing, is_backup, order_status
        FROM aps_packing_order 
        WHERE task_id = :task_id 
        ORDER BY plan_start_time, sequence
        """
        
        async with get_db_session() as db:
            result = await db.execute(text(query), {'task_id': task_id})
            rows = result.fetchall()
            
            orders = []
            for row in rows:
                # 构建InputBatch结构
                input_batch = None
                if row.input_plan_id:
                    input_batch = {
                        'input_plan_id': row.input_plan_id,
                        'input_batch_code': row.input_batch_code,
                        'quantity': row.input_quantity,
                        'batch_sequence': row.batch_sequence,
                        'is_whole_batch': bool(row.is_whole_batch) if row.is_whole_batch is not None else None,
                        'is_main_channel': bool(row.is_main_channel),
                        'is_deleted': bool(row.is_deleted),
                        'is_last_one': bool(row.is_last_one) if row.is_last_one is not None else None,
                        'material_code': row.input_material_code,
                        'bom_revision': row.input_bom_revision,
                        'tiled': bool(row.tiled) if row.tiled is not None else None,
                        'remark1': None,
                        'remark2': None
                    }
                
                orders.append({
                    'plan_id': row.plan_id,
                    'production_line': row.production_line,
                    'batch_code': row.batch_code,
                    'material_code': row.material_code,
                    'bom_revision': row.bom_revision,
                    'quantity': row.quantity,
                    'plan_start_time': row.plan_start_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_start_time else None,
                    'plan_end_time': row.plan_end_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_end_time else None,
                    'sequence': row.sequence,
                    'shift': row.shift,
                    'input_batch': input_batch,
                    'is_vaccum': bool(row.is_vaccum),
                    'is_sh93': bool(row.is_sh93),
                    'is_hdt': bool(row.is_hdt),
                    'is_flavor': bool(row.is_flavor),
                    'unit': row.unit,
                    'plan_date': row.plan_date.strftime('%Y/%m/%d') if row.plan_date else None,
                    'plan_output_quantity': row.plan_output_quantity,
                    'is_outsourcing': bool(row.is_outsourcing),
                    'is_backup': bool(row.is_backup),
                    'order_status': row.order_status
                })
            
            return orders
    
    async def _get_feeding_orders_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """按日期范围查询喂丝机工单"""
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        query = """
        SELECT plan_id, production_line, batch_code, material_code, bom_revision, quantity,
               plan_start_time, plan_end_time, sequence, shift,
               is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date, plan_output_quantity,
               is_outsourcing, is_backup, order_status, task_id
        FROM aps_feeding_order 
        WHERE plan_start_time >= :start_date AND plan_start_time <= :end_date
        ORDER BY plan_start_time, sequence
        """
        
        async with get_db_session() as db:
            result = await db.execute(text(query), {
                'start_date': start_date,
                'end_date': end_date
            })
            rows = result.fetchall()
            
            return [self._row_to_feeding_dict(row) for row in rows]
    
    async def _get_packing_orders_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """按日期范围查询卷包机工单"""
        from app.db.connection import get_db_session
        from sqlalchemy import text
        
        query = """
        SELECT plan_id, production_line, batch_code, material_code, bom_revision, quantity,
               plan_start_time, plan_end_time, sequence, shift,
               input_plan_id, input_batch_code, input_quantity, batch_sequence,
               is_whole_batch, is_main_channel, is_deleted, is_last_one,
               input_material_code, input_bom_revision, tiled,
               is_vaccum, is_sh93, is_hdt, is_flavor, unit, plan_date, plan_output_quantity,
               is_outsourcing, is_backup, order_status, task_id
        FROM aps_packing_order 
        WHERE plan_start_time >= :start_date AND plan_start_time <= :end_date
        ORDER BY plan_start_time, sequence
        """
        
        async with get_db_session() as db:
            result = await db.execute(text(query), {
                'start_date': start_date,
                'end_date': end_date
            })
            rows = result.fetchall()
            
            return [self._row_to_packing_dict(row) for row in rows]
    
    def _row_to_feeding_dict(self, row) -> Dict[str, Any]:
        """数据库行转换为喂丝机工单字典"""
        return {
            'plan_id': row.plan_id,
            'production_line': row.production_line,
            'batch_code': row.batch_code,
            'material_code': row.material_code,
            'bom_revision': row.bom_revision,
            'quantity': row.quantity,
            'plan_start_time': row.plan_start_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_start_time else None,
            'plan_end_time': row.plan_end_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_end_time else None,
            'sequence': row.sequence,
            'shift': row.shift,
            'is_vaccum': bool(row.is_vaccum),
            'is_sh93': bool(row.is_sh93),
            'is_hdt': bool(row.is_hdt),
            'is_flavor': bool(row.is_flavor),
            'unit': row.unit,
            'plan_date': row.plan_date.strftime('%Y/%m/%d') if row.plan_date else None,
            'plan_output_quantity': row.plan_output_quantity,
            'is_outsourcing': bool(row.is_outsourcing),
            'is_backup': bool(row.is_backup),
            'order_status': row.order_status,
            'task_id': row.task_id
        }
    
    def _row_to_packing_dict(self, row) -> Dict[str, Any]:
        """数据库行转换为卷包机工单字典"""
        input_batch = None
        if row.input_plan_id:
            input_batch = {
                'input_plan_id': row.input_plan_id,
                'input_batch_code': row.input_batch_code,
                'quantity': row.input_quantity,
                'batch_sequence': row.batch_sequence,
                'is_whole_batch': bool(row.is_whole_batch) if row.is_whole_batch is not None else None,
                'is_main_channel': bool(row.is_main_channel),
                'is_deleted': bool(row.is_deleted),
                'is_last_one': bool(row.is_last_one) if row.is_last_one is not None else None,
                'material_code': row.input_material_code,
                'bom_revision': row.input_bom_revision,
                'tiled': bool(row.tiled) if row.tiled is not None else None,
                'remark1': None,
                'remark2': None
            }
        
        return {
            'plan_id': row.plan_id,
            'production_line': row.production_line,
            'batch_code': row.batch_code,
            'material_code': row.material_code,
            'bom_revision': row.bom_revision,
            'quantity': row.quantity,
            'plan_start_time': row.plan_start_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_start_time else None,
            'plan_end_time': row.plan_end_time.strftime('%Y/%m/%d %H:%M:%S') if row.plan_end_time else None,
            'sequence': row.sequence,
            'shift': row.shift,
            'input_batch': input_batch,
            'is_vaccum': bool(row.is_vaccum),
            'is_sh93': bool(row.is_sh93),
            'is_hdt': bool(row.is_hdt),
            'is_flavor': bool(row.is_flavor),
            'unit': row.unit,
            'plan_date': row.plan_date.strftime('%Y/%m/%d') if row.plan_date else None,
            'plan_output_quantity': row.plan_output_quantity,
            'is_outsourcing': bool(row.is_outsourcing),
            'is_backup': bool(row.is_backup),
            'order_status': row.order_status,
            'task_id': row.task_id
        }
    
    def _generate_mes_xml(self, export_data: Dict[str, Any]) -> str:
        """生成MES规范的XML格式数据"""
        root = ET.Element("MESWorkOrders")
        
        # 添加元信息
        meta = ET.SubElement(root, "Metadata")
        ET.SubElement(meta, "ExportTime").text = export_data['export_time']
        ET.SubElement(meta, "TaskId").text = export_data.get('task_id', '')
        
        stats = ET.SubElement(meta, "Statistics")
        ET.SubElement(stats, "FeedingOrdersCount").text = str(export_data['feeding_orders_count'])
        ET.SubElement(stats, "PackingOrdersCount").text = str(export_data['packing_orders_count'])
        
        # 添加喂丝机工单
        feeding_orders = ET.SubElement(root, "FeedingOrders")
        for order in export_data['feeding_orders']:
            order_elem = ET.SubElement(feeding_orders, "FeedingOrder")
            self._add_feeding_order_elements(order_elem, order)
        
        # 添加卷包机工单
        packing_orders = ET.SubElement(root, "PackingOrders")
        for order in export_data['packing_orders']:
            order_elem = ET.SubElement(packing_orders, "PackingOrder")
            self._add_packing_order_elements(order_elem, order)
        
        # 格式化XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
    
    def _add_feeding_order_elements(self, parent: ET.Element, order: Dict[str, Any]):
        """添加喂丝机工单XML元素"""
        ET.SubElement(parent, "PlanId").text = order.get('plan_id', '')
        ET.SubElement(parent, "ProductionLine").text = order.get('production_line', '')
        ET.SubElement(parent, "BatchCode").text = order.get('batch_code') or ''
        ET.SubElement(parent, "MaterialCode").text = order.get('material_code', '')
        ET.SubElement(parent, "BomRevision").text = order.get('bom_revision') or ''
        ET.SubElement(parent, "Quantity").text = order.get('quantity') or ''
        ET.SubElement(parent, "PlanStartTime").text = order.get('plan_start_time', '')
        ET.SubElement(parent, "PlanEndTime").text = order.get('plan_end_time', '')
        ET.SubElement(parent, "Sequence").text = str(order.get('sequence', 1))
        ET.SubElement(parent, "Shift").text = order.get('shift') or ''
        ET.SubElement(parent, "IsVaccum").text = str(order.get('is_vaccum', False)).lower()
        ET.SubElement(parent, "IsSh93").text = str(order.get('is_sh93', False)).lower()
        ET.SubElement(parent, "IsHdt").text = str(order.get('is_hdt', False)).lower()
        ET.SubElement(parent, "IsFlavor").text = str(order.get('is_flavor', False)).lower()
        ET.SubElement(parent, "Unit").text = order.get('unit', '公斤')
        ET.SubElement(parent, "PlanDate").text = order.get('plan_date', '')
        ET.SubElement(parent, "IsOutsourcing").text = str(order.get('is_outsourcing', False)).lower()
        ET.SubElement(parent, "IsBackup").text = str(order.get('is_backup', False)).lower()
    
    def _add_packing_order_elements(self, parent: ET.Element, order: Dict[str, Any]):
        """添加卷包机工单XML元素"""
        ET.SubElement(parent, "PlanId").text = order.get('plan_id', '')
        ET.SubElement(parent, "ProductionLine").text = order.get('production_line', '')
        ET.SubElement(parent, "BatchCode").text = order.get('batch_code') or ''
        ET.SubElement(parent, "MaterialCode").text = order.get('material_code', '')
        ET.SubElement(parent, "BomRevision").text = order.get('bom_revision') or ''
        ET.SubElement(parent, "Quantity").text = str(order.get('quantity', 0))
        ET.SubElement(parent, "PlanStartTime").text = order.get('plan_start_time', '')
        ET.SubElement(parent, "PlanEndTime").text = order.get('plan_end_time', '')
        ET.SubElement(parent, "Sequence").text = str(order.get('sequence', 1))
        ET.SubElement(parent, "Shift").text = order.get('shift') or ''
        
        # InputBatch信息
        input_batch = order.get('input_batch')
        if input_batch:
            input_elem = ET.SubElement(parent, "InputBatch")
            ET.SubElement(input_elem, "InputPlanId").text = input_batch.get('input_plan_id', '')
            ET.SubElement(input_elem, "InputBatchCode").text = input_batch.get('input_batch_code') or ''
            ET.SubElement(input_elem, "Quantity").text = input_batch.get('quantity') or ''
            ET.SubElement(input_elem, "BatchSequence").text = str(input_batch.get('batch_sequence') or '')
            ET.SubElement(input_elem, "IsWholeBatch").text = str(input_batch.get('is_whole_batch') or '').lower()
            ET.SubElement(input_elem, "IsMainChannel").text = str(input_batch.get('is_main_channel', True)).lower()
            ET.SubElement(input_elem, "IsDeleted").text = str(input_batch.get('is_deleted', False)).lower()
            ET.SubElement(input_elem, "IsLastOne").text = str(input_batch.get('is_last_one') or '').lower()
            ET.SubElement(input_elem, "MaterialCode").text = input_batch.get('material_code', '')
            ET.SubElement(input_elem, "BomRevision").text = input_batch.get('bom_revision') or ''
            ET.SubElement(input_elem, "Tiled").text = str(input_batch.get('tiled') or '').lower()
        
        # 工艺控制字段
        ET.SubElement(parent, "IsVaccum").text = str(order.get('is_vaccum', False)).lower()
        ET.SubElement(parent, "IsSh93").text = str(order.get('is_sh93', False)).lower()
        ET.SubElement(parent, "IsHdt").text = str(order.get('is_hdt', False)).lower()
        ET.SubElement(parent, "IsFlavor").text = str(order.get('is_flavor', False)).lower()
        ET.SubElement(parent, "Unit").text = order.get('unit', '箱')
        ET.SubElement(parent, "PlanDate").text = order.get('plan_date', '')
        ET.SubElement(parent, "IsOutsourcing").text = str(order.get('is_outsourcing', False)).lower()
        ET.SubElement(parent, "IsBackup").text = str(order.get('is_backup', False)).lower()
    
    def _generate_mes_json(self, export_data: Dict[str, Any]) -> str:
        """生成MES规范的JSON格式数据"""
        return json.dumps(export_data, ensure_ascii=False, indent=2 if self.config.pretty_format else None)


# 便捷函数
async def export_mes_data_by_task(task_id: str, export_format: str = "XML") -> Dict[str, Any]:
    """按任务ID导出MES数据的便捷函数"""
    service = MESDataExportService()
    return await service.export_work_orders_by_task(task_id, export_format)


async def export_mes_data_by_date(start_date: datetime, end_date: datetime, export_format: str = "XML") -> Dict[str, Any]:
    """按日期范围导出MES数据的便捷函数"""
    service = MESDataExportService()
    return await service.export_work_orders_by_date_range(start_date, end_date, export_format)