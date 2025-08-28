"""
APS智慧排产系统 - MES系统集成Mock服务

实现与MES系统的集成接口，包括：
- 工单推送到MES系统
- 生产状态同步
- 维护计划同步
- 设备状态监控
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


@dataclass
class MESResponse:
    """MES系统响应结构"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


@dataclass
class WorkOrderStatus:
    """工单状态结构"""
    work_order_nr: str
    status: str  # PLANNED, RUNNING, PAUSED, COMPLETED, CANCELLED
    progress: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actual_quantity: Optional[int] = None


class MESIntegrationService:
    """MES系统集成服务 - Mock实现"""
    
    def __init__(self):
        self.mock_enabled = True
        self.mock_delay = 0.5  # 模拟网络延迟
        self.work_order_statuses = {}  # 工单状态缓存
        self.production_data = {}  # 生产数据缓存
        
    async def send_work_order_to_mes(
        self, 
        work_orders: List[Dict[str, Any]]
    ) -> MESResponse:
        """
        推送工单到MES系统
        
        Args:
            work_orders: 工单列表
            
        Returns:
            MESResponse: MES系统响应
        """
        try:
            await asyncio.sleep(self.mock_delay)  # 模拟网络延迟
            
            logger.info(f"推送{len(work_orders)}个工单到MES系统")
            
            # Mock实现：模拟MES系统接收工单
            accepted_orders = []
            rejected_orders = []
            
            for order in work_orders:
                work_order_nr = order.get('work_order_nr')
                
                # 模拟业务逻辑：10%概率拒绝
                if hash(work_order_nr) % 10 == 0:
                    rejected_orders.append({
                        'work_order_nr': work_order_nr,
                        'reason': '机台维护中，暂时无法接收工单'
                    })
                else:
                    accepted_orders.append(work_order_nr)
                    # 初始化工单状态
                    self.work_order_statuses[work_order_nr] = WorkOrderStatus(
                        work_order_nr=work_order_nr,
                        status='PLANNED',
                        progress=0.0
                    )
            
            response_data = {
                'accepted_count': len(accepted_orders),
                'rejected_count': len(rejected_orders),
                'accepted_orders': accepted_orders,
                'rejected_orders': rejected_orders,
                'mes_batch_id': f"MES_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            logger.info(f"MES系统响应: 接受{len(accepted_orders)}个, 拒绝{len(rejected_orders)}个")
            
            return MESResponse(
                success=True,
                message=f"工单推送完成: 接受{len(accepted_orders)}个, 拒绝{len(rejected_orders)}个",
                data=response_data
            )
            
        except Exception as e:
            logger.error(f"推送工单到MES系统失败: {str(e)}")
            return MESResponse(
                success=False,
                message=f"MES系统连接失败: {str(e)}",
                error_code="MES_CONNECTION_ERROR"
            )
    
    async def get_work_order_status(
        self, 
        work_order_nrs: List[str]
    ) -> MESResponse:
        """
        查询工单状态
        
        Args:
            work_order_nrs: 工单号列表
            
        Returns:
            MESResponse: 工单状态信息
        """
        try:
            await asyncio.sleep(self.mock_delay * 0.5)
            
            statuses = []
            for work_order_nr in work_order_nrs:
                if work_order_nr in self.work_order_statuses:
                    status = self.work_order_statuses[work_order_nr]
                    # 模拟状态更新
                    status = self._simulate_work_order_progress(status)
                    self.work_order_statuses[work_order_nr] = status
                    
                    statuses.append({
                        'work_order_nr': work_order_nr,
                        'status': status.status,
                        'progress': status.progress,
                        'start_time': status.start_time.isoformat() if status.start_time else None,
                        'end_time': status.end_time.isoformat() if status.end_time else None,
                        'actual_quantity': status.actual_quantity
                    })
                else:
                    statuses.append({
                        'work_order_nr': work_order_nr,
                        'status': 'NOT_FOUND',
                        'progress': 0.0,
                        'message': '工单不存在于MES系统中'
                    })
            
            return MESResponse(
                success=True,
                message=f"查询到{len(statuses)}个工单状态",
                data={'statuses': statuses}
            )
            
        except Exception as e:
            logger.error(f"查询工单状态失败: {str(e)}")
            return MESResponse(
                success=False,
                message=f"查询失败: {str(e)}",
                error_code="STATUS_QUERY_ERROR"
            )
    
    async def get_maintenance_schedule(
        self, 
        machine_codes: List[str] = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> MESResponse:
        """
        获取维护计划
        
        Args:
            machine_codes: 机台代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            MESResponse: 维护计划信息
        """
        try:
            await asyncio.sleep(self.mock_delay * 0.3)
            
            # Mock维护计划数据
            maintenance_plans = []
            
            default_machines = machine_codes or ['HJB001', 'HJB002', 'HWS001', 'HWS002']
            
            for machine_code in default_machines:
                # 模拟每台机器有2-3个维护计划
                for i in range(2):
                    plan_start = (start_date or datetime.now()) + timedelta(days=i*7, hours=2)
                    plan_end = plan_start + timedelta(hours=4)
                    
                    maintenance_plans.append({
                        'maintenance_id': f"MAINT_{machine_code}_{i+1}",
                        'machine_code': machine_code,
                        'maintenance_type': 'ROUTINE' if i % 2 == 0 else 'PREVENTIVE',
                        'priority': 'HIGH' if i == 0 else 'MEDIUM',
                        'planned_start': plan_start.isoformat(),
                        'planned_end': plan_end.isoformat(),
                        'description': f"{machine_code}例行维护" if i % 2 == 0 else f"{machine_code}预防性维护",
                        'estimated_duration_hours': 4,
                        'assigned_technician': f"技术员{(hash(machine_code) % 5) + 1}"
                    })
            
            return MESResponse(
                success=True,
                message=f"查询到{len(maintenance_plans)}个维护计划",
                data={'maintenance_plans': maintenance_plans}
            )
            
        except Exception as e:
            logger.error(f"获取维护计划失败: {str(e)}")
            return MESResponse(
                success=False,
                message=f"维护计划查询失败: {str(e)}",
                error_code="MAINTENANCE_QUERY_ERROR"
            )
    
    async def get_machine_status(
        self, 
        machine_codes: List[str] = None
    ) -> MESResponse:
        """
        获取机台状态
        
        Args:
            machine_codes: 机台代码列表
            
        Returns:
            MESResponse: 机台状态信息
        """
        try:
            await asyncio.sleep(self.mock_delay * 0.2)
            
            default_machines = machine_codes or ['HJB001', 'HJB002', 'HJB003', 'HWS001', 'HWS002', 'HWS003']
            machine_statuses = []
            
            status_options = ['RUNNING', 'IDLE', 'MAINTENANCE', 'ERROR', 'STOPPED']
            
            for machine_code in default_machines:
                # 基于机台代码hash确定状态，保证一致性
                status_index = hash(machine_code) % len(status_options)
                status = status_options[status_index]
                
                machine_statuses.append({
                    'machine_code': machine_code,
                    'status': status,
                    'current_work_order': f"WO_{machine_code}_001" if status == 'RUNNING' else None,
                    'utilization_rate': round(max(0.3, (hash(machine_code) % 100) / 100.0), 2),
                    'last_heartbeat': datetime.now().isoformat(),
                    'error_message': '传感器异常' if status == 'ERROR' else None,
                    'production_count_today': hash(machine_code) % 5000,
                    'efficiency_rating': round(max(0.7, (hash(machine_code + 'eff') % 30 + 70) / 100.0), 2)
                })
            
            return MESResponse(
                success=True,
                message=f"查询到{len(machine_statuses)}台机器状态",
                data={'machine_statuses': machine_statuses}
            )
            
        except Exception as e:
            logger.error(f"获取机台状态失败: {str(e)}")
            return MESResponse(
                success=False,
                message=f"机台状态查询失败: {str(e)}",
                error_code="MACHINE_STATUS_ERROR"
            )
    
    def _simulate_work_order_progress(self, status: WorkOrderStatus) -> WorkOrderStatus:
        """模拟工单进度更新"""
        if status.status == 'PLANNED':
            # 10%概率开始执行
            if hash(status.work_order_nr + str(datetime.now().minute)) % 10 == 0:
                status.status = 'RUNNING'
                status.start_time = datetime.now()
                status.progress = 0.1
        
        elif status.status == 'RUNNING':
            # 模拟进度增长
            progress_increment = (hash(status.work_order_nr) % 10 + 1) / 100.0
            status.progress = min(1.0, status.progress + progress_increment)
            
            # 进度达到100%时完成
            if status.progress >= 1.0:
                status.status = 'COMPLETED'
                status.end_time = datetime.now()
                status.actual_quantity = int(hash(status.work_order_nr) % 1000 + 500)
        
        return status
    
    async def simulate_production_events(self) -> List[Dict[str, Any]]:
        """模拟生产事件"""
        events = []
        
        event_types = ['PRODUCTION_START', 'PRODUCTION_PAUSE', 'QUALITY_CHECK', 'MACHINE_ALARM']
        
        for i in range(3):  # 生成3个随机事件
            event = {
                'event_id': f"EVENT_{datetime.now().strftime('%H%M%S')}_{i}",
                'event_type': event_types[i % len(event_types)],
                'machine_code': f"HJB00{(i % 3) + 1}",
                'timestamp': (datetime.now() - timedelta(minutes=i*10)).isoformat(),
                'severity': 'HIGH' if event_types[i % len(event_types)] == 'MACHINE_ALARM' else 'INFO',
                'message': f"机台{i+1}发生{event_types[i % len(event_types)]}事件"
            }
            events.append(event)
        
        return events


# 全局MES服务实例
mes_service = MESIntegrationService()


async def push_work_orders_to_mes(work_orders: List[Dict[str, Any]]) -> MESResponse:
    """推送工单到MES系统的便利函数"""
    return await mes_service.send_work_order_to_mes(work_orders)


async def query_work_order_statuses(work_order_nrs: List[str]) -> MESResponse:
    """查询工单状态的便利函数"""
    return await mes_service.get_work_order_status(work_order_nrs)


async def get_maintenance_plans() -> MESResponse:
    """获取维护计划的便利函数"""
    return await mes_service.get_maintenance_schedule()


async def get_all_machine_statuses() -> MESResponse:
    """获取所有机台状态的便利函数"""
    return await mes_service.get_machine_status()