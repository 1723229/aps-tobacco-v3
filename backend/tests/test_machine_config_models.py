"""
测试机台配置相关数据模型
包括机台速度、机台关系、班次配置等
"""
import pytest
from datetime import datetime, time


def test_machine_speed_config_model_exists():
    """测试机台速度配置模型是否存在 - 预期失败"""
    try:
        from app.models.machine_config_models import MachineSpeedConfig
        
        # 尝试创建一个基本的MachineSpeedConfig实例
        speed_config = MachineSpeedConfig(
            machine_code="JJ01",
            machine_type="卷包机",
            standard_speed=800,  # 每分钟800支
            max_speed=1000,
            min_speed=600
        )
        
        # 验证基本属性
        assert speed_config.machine_code == "JJ01"
        assert speed_config.machine_type == "卷包机"
        assert speed_config.standard_speed == 800
        assert speed_config.max_speed == 1000
        assert speed_config.min_speed == 600
        
    except ImportError as e:
        pytest.fail(f"MachineSpeedConfig model not found: {e}")


def test_machine_relation_model_exists():
    """测试机台关系配置模型是否存在 - 预期失败"""
    try:
        from app.models.machine_config_models import MachineRelation
        
        # 尝试创建一个基本的MachineRelation实例
        relation = MachineRelation(
            feeder_code="WS01",
            maker_code="JJ01",
            relation_type="一对一",
            priority=1
        )
        
        # 验证基本属性
        assert relation.feeder_code == "WS01"
        assert relation.maker_code == "JJ01"
        assert relation.relation_type == "一对一"
        assert relation.priority == 1
        
    except ImportError as e:
        pytest.fail(f"MachineRelation model not found: {e}")


def test_shift_config_model_exists():
    """测试班次配置模型是否存在 - 预期失败"""
    try:
        from app.models.machine_config_models import ShiftConfig
        
        # 尝试创建一个基本的ShiftConfig实例
        shift = ShiftConfig(
            shift_name="早班",
            shift_code="A",
            start_time=time(8, 0),  # 08:00
            end_time=time(16, 0),   # 16:00
            is_active=True
        )
        
        # 验证基本属性
        assert shift.shift_name == "早班"
        assert shift.shift_code == "A"
        assert shift.start_time == time(8, 0)
        assert shift.end_time == time(16, 0)
        assert shift.is_active == True
        
    except ImportError as e:
        pytest.fail(f"ShiftConfig model not found: {e}")


def test_machine_config_database_tables():
    """测试机台配置数据库表结构 - 预期失败"""
    try:
        from app.models.machine_config_models import (
            MachineSpeedConfig, 
            MachineRelation, 
            ShiftConfig
        )
        
        # 验证表名
        assert MachineSpeedConfig.__tablename__ == "aps_machine_speed_config"
        assert MachineRelation.__tablename__ == "aps_machine_relation"
        assert ShiftConfig.__tablename__ == "aps_shift_config"
        
        # 验证MachineSpeedConfig必要字段
        speed_fields = ['id', 'machine_code', 'machine_type', 'standard_speed', 'max_speed', 'min_speed']
        for field in speed_fields:
            assert hasattr(MachineSpeedConfig, field), f"Missing field in MachineSpeedConfig: {field}"
        
        # 验证MachineRelation必要字段
        relation_fields = ['id', 'feeder_code', 'maker_code', 'relation_type', 'priority']
        for field in relation_fields:
            assert hasattr(MachineRelation, field), f"Missing field in MachineRelation: {field}"
        
        # 验证ShiftConfig必要字段
        shift_fields = ['id', 'shift_name', 'shift_code', 'start_time', 'end_time', 'is_active']
        for field in shift_fields:
            assert hasattr(ShiftConfig, field), f"Missing field in ShiftConfig: {field}"
            
    except ImportError as e:
        pytest.fail(f"Machine config models not found: {e}")