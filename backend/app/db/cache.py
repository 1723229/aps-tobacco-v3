"""
APS智慧排产系统 - Redis缓存连接模块

基于技术设计文档实现Redis连接池和缓存管理
支持分布式缓存、会话存储、任务队列等功能
"""
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from typing import Optional, Any, Union, Dict
import json
import pickle
import logging
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建Redis连接池
redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=settings.redis_decode_responses,
    socket_connect_timeout=10,
    socket_keepalive=True,
    socket_keepalive_options={},
    health_check_interval=30,
)

# 创建Redis客户端
redis_client = redis.Redis(connection_pool=redis_pool)


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, client: redis.Redis = None):
        self.client = client or redis_client
    
    async def get(self, key: str, decode_json: bool = True) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            if decode_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        encode_json: bool = True
    ) -> bool:
        """设置缓存值"""
        try:
            if encode_json:
                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(value, ensure_ascii=False, default=str)
                elif not isinstance(value, (str, bytes, int, float)):
                    value = json.dumps(value, ensure_ascii=False, default=str)
            
            if ttl:
                return await self.client.setex(key, ttl, value)
            else:
                return await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """删除缓存"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache delete error for keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置键过期时间"""
        try:
            return await self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取键剩余生存时间"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Cache ttl error for key {key}: {e}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            return await self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        """获取哈希字段值"""
        try:
            value = await self.client.hget(key, field)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache hash_get error for key {key}, field {field}: {e}")
            return None
    
    async def hash_set(self, key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置哈希字段值"""
        try:
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            
            result = await self.client.hset(key, field, value)
            
            if ttl:
                await self.client.expire(key, ttl)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Cache hash_set error for key {key}, field {field}: {e}")
            return False
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """获取哈希所有字段"""
        try:
            data = await self.client.hgetall(key)
            result = {}
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value
            return result
        except Exception as e:
            logger.error(f"Cache hash_get_all error for key {key}: {e}")
            return {}
    
    async def list_push(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """向列表推送值"""
        try:
            json_values = []
            for value in values:
                if isinstance(value, (dict, list, tuple)):
                    json_values.append(json.dumps(value, ensure_ascii=False, default=str))
                else:
                    json_values.append(str(value))
            
            result = await self.client.lpush(key, *json_values)
            
            if ttl:
                await self.client.expire(key, ttl)
            
            return result
        except Exception as e:
            logger.error(f"Cache list_push error for key {key}: {e}")
            return 0
    
    async def list_pop(self, key: str) -> Optional[Any]:
        """从列表弹出值"""
        try:
            value = await self.client.rpop(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache list_pop error for key {key}: {e}")
            return None
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> list:
        """获取列表范围值"""
        try:
            values = await self.client.lrange(key, start, end)
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)
            return result
        except Exception as e:
            logger.error(f"Cache list_range error for key {key}: {e}")
            return []


@asynccontextmanager
async def get_cache_manager():
    """获取缓存管理器上下文"""
    cache = CacheManager()
    try:
        yield cache
    finally:
        # 这里可以添加清理逻辑
        pass


async def get_redis_client() -> redis.Redis:
    """获取Redis客户端"""
    return redis_client


async def check_redis_connection() -> bool:
    """检查Redis连接状态"""
    try:
        await redis_client.ping()
        logger.info("Redis connection healthy")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


async def close_redis_connections():
    """关闭Redis连接"""
    await redis_client.close()
    logger.info("Redis connections closed")


class RedisHealthCheck:
    """Redis健康检查工具"""
    
    @staticmethod
    async def ping() -> dict:
        """Ping Redis连接"""
        try:
            start_time = time.time()
            await redis_client.ping()
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            info = await redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


import time

# 导出主要组件
__all__ = [
    "redis_client",
    "redis_pool",
    "CacheManager",
    "get_cache_manager",
    "get_redis_client",
    "check_redis_connection",
    "close_redis_connections",
    "RedisHealthCheck",
]