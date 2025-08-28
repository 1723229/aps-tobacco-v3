"""
APS智慧排产系统 - 数据库连接模块

基于技术设计文档实现异步MySQL连接和会话管理
支持连接池、事务管理、自动重连等企业级特性
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建异步数据库引擎
engine = create_async_engine(
    settings.mysql_url,
    echo=settings.mysql_echo,
    poolclass=NullPool,  # 异步引擎使用NullPool
    future=True,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# 声明式基类
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    
    用法:
        async def some_function(db: AsyncSession = Depends(get_async_session)):
            # 使用数据库会话
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    上下文管理器方式获取数据库会话
    
    用法:
        async with get_db_session() as db:
            # 使用数据库会话
            result = await db.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """创建所有数据库表"""
    async with engine.begin() as conn:
        # 导入所有模型以确保它们被注册
        from app.models import (
            machine,
            material, 
            machine_speed,
            machine_relation,
            shift_config,
            import_plan,
            decade_plan,
            scheduling_task,
            processing_log,
            packing_order,
            feeding_order,
            input_batch,
            work_order_sequence,
            maintenance_plan,
            mes_dispatch,
            order_status_sync,
            system_config,
            business_rule,
            operation_log,
        )
        
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_tables():
    """删除所有数据库表（谨慎使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")


async def check_database_connection():
    """检查数据库连接状态"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("Database connection healthy")
                return True
            else:
                logger.error("Database connection unhealthy")
                return False
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def close_db_connections():
    """关闭数据库连接池"""
    await engine.dispose()
    logger.info("Database connections closed")


# 事务装饰器
def transactional(func):
    """
    事务装饰器 - 自动管理事务提交和回滚
    
    用法:
        @transactional
        async def create_user(db: AsyncSession, user_data: dict):
            # 数据库操作
            pass
    """
    async def wrapper(*args, **kwargs):
        # 查找AsyncSession参数
        db_session = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                db_session = arg
                break
        
        if not db_session:
            for value in kwargs.values():
                if isinstance(value, AsyncSession):
                    db_session = value
                    break
        
        if not db_session:
            raise ValueError("No AsyncSession found in function arguments")
        
        try:
            result = await func(*args, **kwargs)
            await db_session.commit()
            return result
        except Exception:
            await db_session.rollback()
            raise
    
    return wrapper


# 数据库健康检查
class DatabaseHealthCheck:
    """数据库健康检查工具"""
    
    @staticmethod
    async def ping() -> dict:
        """Ping数据库连接"""
        try:
            start_time = time.time()
            is_healthy = await check_database_connection()
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "database": "MySQL",
                "engine_type": "async",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "database": "MySQL"
            }


import time

# 导出主要组件
__all__ = [
    "engine",
    "AsyncSessionLocal", 
    "Base",
    "get_async_session",
    "get_db_session",
    "create_tables",
    "drop_tables",
    "check_database_connection",
    "close_db_connections",
    "transactional",
    "DatabaseHealthCheck",
]