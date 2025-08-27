"""
APS智慧排产系统 - FastAPI应用入口

基于技术设计文档实现FastAPI应用和路由配置
包含健康检查、配置验证、数据库连接测试、API路由等功能
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings, validate_configuration
from app.db.connection import check_database_connection, close_db_connections, DatabaseHealthCheck
from app.db.cache import check_redis_connection, close_redis_connections, RedisHealthCheck
from app.api.v1.router import api_v1_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # 验证配置
    try:
        validate_configuration()
        logger.info("✅ Configuration validation passed")
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise
    
    # 检查数据库连接
    if await check_database_connection():
        logger.info("✅ Database connection established")
    else:
        logger.warning("⚠️ Database connection failed")
    
    # 检查Redis连接
    if await check_redis_connection():
        logger.info("✅ Redis connection established")
    else:
        logger.warning("⚠️ Redis connection failed")
    
    yield
    
    # 关闭时
    logger.info("Shutting down application...")
    await close_db_connections()
    await close_redis_connections()
    logger.info("Application shutdown complete")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="APS智慧排产系统 - 卷烟生产排产调度系统",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_v1_router)


@app.get("/")
async def root():
    """根路径 - 系统信息"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    db_health = await DatabaseHealthCheck.ping()
    redis_health = await RedisHealthCheck.ping()
    
    overall_status = "healthy"
    if db_health.get("status") != "healthy" or redis_health.get("status") != "healthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": "2024-08-16T10:00:00Z",  # 实际应用中使用datetime.now()
        "version": settings.app_version,
        "checks": {
            "database": db_health,
            "redis": redis_health,
        }
    }


@app.get("/config")
async def get_config_info():
    """配置信息接口（敏感信息已脱敏）"""
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "environment": "development" if settings.debug else "production",
        "database": {
            "type": "MySQL",
            "pool_size": settings.mysql_pool_size,
            "echo": settings.mysql_echo,
        },
        "redis": {
            "max_connections": settings.redis_max_connections,
            "decode_responses": settings.redis_decode_responses,
        },
        "upload": {
            "max_size_mb": settings.upload_max_size // (1024 * 1024),
            "allowed_extensions": settings.upload_allowed_extensions,
        },
        "business": {
            "default_efficiency_rate": settings.default_efficiency_rate,
            "max_retry_count": settings.max_retry_count,
            "scheduling_timeout": settings.scheduling_timeout,
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )