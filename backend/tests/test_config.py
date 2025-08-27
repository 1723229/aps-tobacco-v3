"""
APS智慧排产系统 - 核心配置模块测试

验证配置加载、数据库连接字符串、缓存参数等核心功能
使用TDD方法确保配置模块的可靠性
"""
import pytest
import os
from unittest.mock import patch

from app.core.config import Settings, get_settings, validate_configuration, is_development, is_production


class TestSettings:
    """配置设置测试类"""
    
    def test_default_settings(self):
        """测试默认配置值"""
        settings = Settings()
        
        assert settings.app_name == "APS智慧排产系统"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert "mysql+aiomysql" in settings.mysql_url
        assert "redis://" in settings.redis_url
        assert settings.mysql_pool_size == 20
        assert settings.redis_max_connections == 50
    
    def test_mysql_connection_params(self):
        """测试MySQL连接参数"""
        settings = Settings()
        
        assert settings.mysql_pool_size > 0
        assert settings.mysql_pool_max_overflow > 0
        assert settings.mysql_pool_timeout > 0
        assert settings.mysql_pool_recycle > 0
    
    def test_redis_connection_params(self):
        """测试Redis连接参数"""
        settings = Settings()
        
        assert settings.redis_max_connections > 0
        assert settings.redis_decode_responses is True
    
    def test_file_upload_settings(self):
        """测试文件上传配置"""
        settings = Settings()
        
        assert settings.upload_max_size > 0
        assert ".xlsx" in settings.upload_allowed_extensions
        assert ".xls" in settings.upload_allowed_extensions
        assert settings.upload_temp_dir is not None
    
    def test_business_settings(self):
        """测试业务配置"""
        settings = Settings()
        
        assert settings.default_efficiency_rate == 85.0
        assert settings.max_retry_count == 3
        assert settings.scheduling_timeout > 0
    
    @patch.dict(os.environ, {"APS_DEBUG": "true"})
    def test_environment_override(self):
        """测试环境变量覆盖"""
        settings = Settings()
        assert settings.debug is True
    
    def test_upload_dir_validation(self):
        """测试上传目录验证"""
        settings = Settings()
        # 目录应该被创建
        assert os.path.exists(settings.upload_temp_dir)
    
    def test_extensions_validation(self):
        """测试文件扩展名验证"""
        settings = Settings()
        # 所有扩展名都应该以.开头且为小写
        for ext in settings.upload_allowed_extensions:
            assert ext.startswith(".")
            assert ext.islower()


class TestConfigurationValidation:
    """配置验证测试类"""
    
    def test_valid_configuration(self):
        """测试有效配置验证"""
        assert validate_configuration() is True
    
    @patch('app.core.config.settings')
    def test_invalid_mysql_url(self, mock_settings):
        """测试无效MySQL URL"""
        mock_settings.mysql_url = ""
        mock_settings.redis_url = "redis://valid"
        mock_settings.secret_key = "valid-key"
        
        with pytest.raises(ValueError, match="Missing or invalid required configurations"):
            validate_configuration()
    
    @patch('app.core.config.settings')
    def test_invalid_redis_url(self, mock_settings):
        """测试无效Redis URL"""
        mock_settings.mysql_url = "mysql://valid"
        mock_settings.redis_url = ""
        mock_settings.secret_key = "valid-key"
        
        with pytest.raises(ValueError, match="Missing or invalid required configurations"):
            validate_configuration()
    
    @patch('app.core.config.settings')
    def test_invalid_secret_key(self, mock_settings):
        """测试无效密钥"""
        mock_settings.mysql_url = "mysql://valid"
        mock_settings.redis_url = "redis://valid"
        mock_settings.secret_key = "change-me"
        
        with pytest.raises(ValueError, match="Missing or invalid required configurations"):
            validate_configuration()


class TestEnvironmentDetection:
    """环境检测测试类"""
    
    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_development_environment(self):
        """测试开发环境检测"""
        assert is_development() is True
        assert is_production() is False
    
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_environment(self):
        """测试生产环境检测"""
        assert is_development() is False
        assert is_production() is True
    
    @patch('app.core.config.settings')
    def test_debug_mode_development(self, mock_settings):
        """测试调试模式下的开发环境"""
        mock_settings.debug = True
        assert is_development() is True


class TestSettingsSingleton:
    """配置单例测试类"""
    
    def test_get_settings_singleton(self):
        """测试配置获取为单例模式"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # 应该返回同一个实例
        assert settings1 is settings2
    
    def test_settings_caching(self):
        """测试配置缓存机制"""
        # 多次调用应该返回缓存的配置
        for _ in range(5):
            settings = get_settings()
            assert settings.app_name == "APS智慧排产系统"


@pytest.fixture
def clean_environment():
    """清理环境变量的fixture"""
    original_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestIntegration:
    """集成测试类"""
    
    def test_configuration_integration(self):
        """测试配置集成"""
        settings = get_settings()
        
        # 验证配置
        assert validate_configuration() is True
        
        # 检查关键配置
        assert "aps" in settings.mysql_url.lower()
        assert "redis" in settings.redis_url.lower()
        assert settings.app_name
        assert settings.app_version
    
    def test_database_url_format(self):
        """测试数据库URL格式"""
        settings = get_settings()
        
        # MySQL URL应该包含必要的组件
        assert "mysql+aiomysql://" in settings.mysql_url
        assert "@" in settings.mysql_url  # 认证信息
        assert ":" in settings.mysql_url  # 端口
        assert "/" in settings.mysql_url  # 数据库名
    
    def test_redis_url_format(self):
        """测试Redis URL格式"""
        settings = get_settings()
        
        # Redis URL应该包含必要的组件
        assert "redis://" in settings.redis_url
        assert "@" in settings.redis_url  # 认证信息
        assert ":" in settings.redis_url  # 端口
        assert "/" in settings.redis_url  # 数据库编号