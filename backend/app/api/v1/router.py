"""
APS智慧排产系统 - API v1 路由汇总

汇总所有v1版本的API路由，提供统一的路由注册
"""
from fastapi import APIRouter

from app.api.v1.plans import router as plans_router
from app.api.v1.data import router as data_router

# 创建v1版本的主路由
api_v1_router = APIRouter(prefix="/api/v1")

# 注册各个子路由
api_v1_router.include_router(plans_router)
api_v1_router.include_router(data_router)

# 导出路由
__all__ = ["api_v1_router"]