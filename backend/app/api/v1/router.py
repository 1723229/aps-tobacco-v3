"""
APS智慧排产系统 - API v1 路由汇总

汇总所有v1版本的API路由，提供统一的路由注册
"""
from fastapi import APIRouter

from app.api.v1.plans import router as plans_router
from app.api.v1.data import router as data_router
from app.api.v1.scheduling import router as scheduling_router
from app.api.v1.mes import router as mes_router
from app.api.v1.work_orders import router as work_orders_router
from app.api.v1.machines import router as machines_router

# 创建v1版本的主路由
api_v1_router = APIRouter(prefix="/api/v1")

# 注册各个子路由
api_v1_router.include_router(plans_router)
api_v1_router.include_router(data_router)
api_v1_router.include_router(scheduling_router)
api_v1_router.include_router(mes_router)
api_v1_router.include_router(work_orders_router)
api_v1_router.include_router(machines_router)

# 导出路由
__all__ = ["api_v1_router"]