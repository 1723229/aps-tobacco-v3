"""
APS智慧排产系统 - MES集成API路由

实现MES系统集成的API接口
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.mes_integration import mes_service
from app.schemas.base import SuccessResponse, ErrorResponse

router = APIRouter(prefix="/mes", tags=["MES系统集成"])


class WorkOrderPushRequest(BaseModel):
    """工单推送请求"""
    work_orders: List[Dict[str, Any]]
    mes_config: Optional[Dict[str, Any]] = None


class WorkOrderStatusRequest(BaseModel):
    """工单状态查询请求"""
    work_order_nrs: List[str]


class MaintenanceQueryRequest(BaseModel):
    """维护计划查询请求"""
    machine_codes: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class MachineStatusRequest(BaseModel):
    """机台状态查询请求"""
    machine_codes: Optional[List[str]] = None


@router.post("/work-orders/push")
async def push_work_orders_to_mes(request: WorkOrderPushRequest):
    """
    推送工单到MES系统
    
    Args:
        request: 工单推送请求
        
    Returns:
        推送结果
    """
    try:
        mes_response = await mes_service.send_work_order_to_mes(request.work_orders)
        
        if mes_response.success:
            return SuccessResponse(
                code=200,
                message=mes_response.message,
                data=mes_response.data
            )
        else:
            return ErrorResponse(
                code=500,
                message=mes_response.message,
                error=mes_response.error_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推送工单失败: {str(e)}")


@router.post("/work-orders/status")
async def get_work_order_status(request: WorkOrderStatusRequest):
    """
    查询工单状态
    
    Args:
        request: 工单状态查询请求
        
    Returns:
        工单状态信息
    """
    try:
        mes_response = await mes_service.get_work_order_status(request.work_order_nrs)
        
        if mes_response.success:
            return SuccessResponse(
                code=200,
                message=mes_response.message,
                data=mes_response.data
            )
        else:
            return ErrorResponse(
                code=500,
                message=mes_response.message,
                error=mes_response.error_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询工单状态失败: {str(e)}")


@router.post("/maintenance/schedule")
async def get_maintenance_schedule(request: MaintenanceQueryRequest):
    """
    获取维护计划
    
    Args:
        request: 维护计划查询请求
        
    Returns:
        维护计划信息
    """
    try:
        mes_response = await mes_service.get_maintenance_schedule(
            machine_codes=request.machine_codes,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if mes_response.success:
            return SuccessResponse(
                code=200,
                message=mes_response.message,
                data=mes_response.data
            )
        else:
            return ErrorResponse(
                code=500,
                message=mes_response.message,
                error=mes_response.error_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取维护计划失败: {str(e)}")


@router.post("/machines/status")
async def get_machine_status(request: MachineStatusRequest):
    """
    获取机台状态
    
    Args:
        request: 机台状态查询请求
        
    Returns:
        机台状态信息
    """
    try:
        mes_response = await mes_service.get_machine_status(request.machine_codes)
        
        if mes_response.success:
            return SuccessResponse(
                code=200,
                message=mes_response.message,
                data=mes_response.data
            )
        else:
            return ErrorResponse(
                code=500,
                message=mes_response.message,
                error=mes_response.error_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取机台状态失败: {str(e)}")


@router.get("/events/recent")
async def get_recent_production_events():
    """
    获取最近的生产事件
    
    Returns:
        生产事件列表
    """
    try:
        events = await mes_service.simulate_production_events()
        
        return SuccessResponse(
            code=200,
            message=f"查询到{len(events)}个生产事件",
            data={'events': events}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取生产事件失败: {str(e)}")


@router.get("/health")
async def check_mes_connection():
    """
    检查MES系统连接状态
    
    Returns:
        连接状态信息
    """
    try:
        # 模拟连接检查
        connection_status = {
            'status': 'connected',
            'response_time_ms': 50,
            'last_heartbeat': datetime.now().isoformat(),
            'version': 'MES-Mock-1.0.0',
            'capabilities': [
                'work_order_push',
                'status_query',
                'maintenance_schedule',
                'machine_status',
                'production_events'
            ]
        }
        
        return SuccessResponse(
            code=200,
            message="MES系统连接正常",
            data=connection_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MES系统连接失败: {str(e)}")