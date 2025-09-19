"""
APS智慧排产系统 - 核心配置模块

基于技术设计文档1.2技术栈配置系统参数和数据库连接
支持环境变量配置和默认值，提供类型安全的配置管理
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置类 - 基于Pydantic Settings提供类型安全的配置管理"""
    
    # 应用基础配置
    app_name: str = "APS智慧排产系统"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 数据库配置 - MySQL 8.0+ (真实数据库)
    mysql_url: str = "mysql+aiomysql://aps:Aps%40123456@10.0.0.99:3306/aps"
    mysql_echo: bool = False
    mysql_pool_size: int = 20
    mysql_pool_max_overflow: int = 30
    mysql_pool_timeout: int = 30
    mysql_pool_recycle: int = 1800
    
    # Redis配置 - 7.0+
    redis_url: str = "redis://10.0.0.99:6379/13"
    redis_max_connections: int = 50
    redis_decode_responses: bool = True
    
    # LLM配置 - 阿里云DashScope
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: Optional[str] = None
    llm_model: str = "qwen-max"
    
    # FastAPI配置
    host: str = "0.0.0.0"
    port: int = 8810
    reload: bool = False
    workers: int = 1
    
    # 文件上传配置
    upload_max_size: int = 50 * 1024 * 1024  # 50MB
    upload_allowed_extensions: List[str] = [".xlsx", ".xls"]
    upload_temp_dir: str = "/tmp/aps_uploads"
    data_dir: str = "data"  # 数据存储根目录
    
    # 任务队列配置（Celery）
    celery_broker_url: str = "redis://:Redis_Apex_2025.@10.0.0.66:6379/14"
    celery_result_backend: str = "redis://:Redis_Apex_2025.@10.0.0.66:6379/15"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "Asia/Shanghai"
    
    # 安全配置
    secret_key: str = "aps-secret-key-change-in-production"
    encryption_key: Optional[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 业务配置
    default_efficiency_rate: float = 85.0  # 默认效率系数 85%
    max_retry_count: int = 3
    scheduling_timeout: int = 3600  # 排产算法超时时间（秒）
    
    @field_validator('upload_temp_dir')
    @classmethod
    def validate_upload_dir(cls, v):
        """验证并创建上传临时目录"""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator('data_dir')
    @classmethod
    def validate_data_dir(cls, v):
        """验证并创建数据存储目录"""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator('upload_allowed_extensions')
    @classmethod
    def validate_extensions(cls, v):
        """验证文件扩展名格式"""
        return [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in v]
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="APS_",
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例 - 使用LRU缓存提升性能"""
    return Settings()


# 导出配置实例
settings = get_settings()


# 数据库URL别名（兼容性）
DATABASE_URL = settings.mysql_url
REDIS_URL = settings.redis_url

# 环境检查函数
def is_development() -> bool:
    """检查是否为开发环境"""
    return settings.debug or os.getenv("ENVIRONMENT", "development").lower() in ["dev", "development"]


def is_production() -> bool:
    """检查是否为生产环境"""
    return os.getenv("ENVIRONMENT", "development").lower() in ["prod", "production"]


def is_testing() -> bool:
    """检查是否为测试环境"""
    return os.getenv("ENVIRONMENT", "development").lower() in ["test", "testing"]


# 配置验证函数
def validate_configuration():
    """验证关键配置项"""
    required_configs = [
        ("mysql_url", settings.mysql_url),
        ("redis_url", settings.redis_url),
        ("secret_key", settings.secret_key),
    ]
    
    missing_configs = []
    for name, value in required_configs:
        if not value or value in ["", "change-me", "your-secret-key"]:
            missing_configs.append(name)
    
    if missing_configs:
        raise ValueError(f"Missing or invalid required configurations: {', '.join(missing_configs)}")
    
    return True


if __name__ == "__main__":
    # 配置验证和调试输出
    try:
        validate_configuration()
        print("✅ Configuration validation passed")
        print(f"📊 App: {settings.app_name} v{settings.app_version}")
        print(f"🗄️  Database: {settings.mysql_url.split('@')[1] if '@' in settings.mysql_url else 'Not configured'}")
        print(f"🔄 Redis: {settings.redis_url.split('@')[1] if '@' in settings.redis_url else 'Not configured'}")
        print(f"🚀 Server: {settings.host}:{settings.port}")
        print(f"🔧 Environment: {'Development' if is_development() else 'Production' if is_production() else 'Testing' if is_testing() else 'Unknown'}")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")