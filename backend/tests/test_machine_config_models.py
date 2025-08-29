"""
测试机台配置相关数据模型
包括机台速度、机台关系、班次配置等
"""
import pytest
from datetime import datetime, time


def test_machine_speed_model_exists():
    """测试机台速度模型是否存在"""
    try:
        from app.models.machine_config_models import MachineSpeed
        from decimal import Decimal
        
        # 尝试创建一个基本的MachineSpeed实例
        machine_speed = MachineSpeed(
            machine_code="JJ01",
            article_nr="A001",
            speed=Decimal("120.50"),  # 生产速度（箱/小时）
            efficiency_rate=Decimal("85.00"),
            effective_from=datetime.now(),
            status="ACTIVE"
        )
        
        # 验证基本属性
        assert machine_speed.machine_code == "JJ01"
        assert machine_speed.article_nr == "A001"
        assert machine_speed.speed == Decimal("120.50")
        assert machine_speed.efficiency_rate == Decimal("85.00")
        assert machine_speed.status == "ACTIVE"
        
    except ImportError as e:
        pytest.fail(f"MachineSpeed model not found: {e}")


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
            machine_name="ALL",
            start_time=time(8, 0),  # 08:00
            end_time=time(16, 0),   # 16:00
            effective_from=datetime.now(),
            status="ACTIVE"
        )
        
        # 验证基本属性
        assert shift.shift_name == "早班"
        assert shift.machine_name == "ALL"
        assert shift.start_time == time(8, 0)
        assert shift.end_time == time(16, 0)
        assert shift.status == "ACTIVE"
        
    except ImportError as e:
        pytest.fail(f"ShiftConfig model not found: {e}")


def test_machine_config_database_tables():
    """测试机台配置数据库表结构"""
    try:
        from app.models.machine_config_models import (
            MachineSpeed, 
            MachineRelation, 
            ShiftConfig
        )
        
        # 验证表名
        assert MachineSpeed.__tablename__ == "aps_machine_speed"
        assert MachineRelation.__tablename__ == "aps_machine_relation"
        assert ShiftConfig.__tablename__ == "aps_shift_config"
        
        # 验证MachineSpeed必要字段
        speed_fields = ['id', 'machine_code', 'article_nr', 'speed', 'efficiency_rate', 'effective_from', 'status']
        for field in speed_fields:
            assert hasattr(MachineSpeed, field), f"Missing field in MachineSpeed: {field}"
        
        # 验证MachineRelation必要字段
        relation_fields = ['id', 'feeder_code', 'maker_code', 'relation_type', 'priority']
        for field in relation_fields:
            assert hasattr(MachineRelation, field), f"Missing field in MachineRelation: {field}"
        
        # 验证ShiftConfig必要字段
        shift_fields = ['id', 'shift_name', 'machine_name', 'start_time', 'end_time', 'effective_from', 'status']
        for field in shift_fields:
            assert hasattr(ShiftConfig, field), f"Missing field in ShiftConfig: {field}"
            
    except ImportError as e:
        pytest.fail(f"Machine config models not found: {e}")