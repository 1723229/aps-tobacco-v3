"""
测试工单结果数据模型
按照TDD原则，先编写失败测试
"""
import pytest
from datetime import datetime


def test_packing_order_model_exists():
    """测试卷包机工单模型是否存在 - 预期失败"""
    # 这个测试应该失败，因为PackingOrder还没有实现
    try:
        from app.models.work_order_models import PackingOrder
        
        # 尝试创建一个基本的PackingOrder实例
        order = PackingOrder(
            work_order_nr="HJB20250827001",
            work_order_type="HJB",
            machine_type="卷包机",
            machine_code="JJ01",
            product_code="红塔山(硬)",
            plan_quantity=1000
        )
        
        # 验证基本属性
        assert order.work_order_nr == "HJB20250827001"
        assert order.work_order_type == "HJB"
        assert order.machine_type == "卷包机"
        assert order.machine_code == "JJ01"
        assert order.product_code == "红塔山(硬)"
        assert order.plan_quantity == 1000
        
    except ImportError as e:
        pytest.fail(f"PackingOrder model not found: {e}")


def test_packing_order_database_table():
    """测试卷包机工单对应的数据库表结构 - 预期失败"""
    try:
        from app.models.work_order_models import PackingOrder
        
        # 验证表名
        assert hasattr(PackingOrder, '__tablename__')
        assert PackingOrder.__tablename__ == "aps_packing_order"
        
        # 验证必要字段存在
        required_fields = [
            'id', 'work_order_nr', 'work_order_type', 'machine_type',
            'machine_code', 'product_code', 'plan_quantity', 'work_order_status'
        ]
        
        for field in required_fields:
            assert hasattr(PackingOrder, field), f"Missing required field: {field}"
            
    except ImportError as e:
        pytest.fail(f"PackingOrder model not found: {e}")


def test_feeding_order_model_exists():
    """测试喂丝机工单模型是否存在 - 预期失败"""
    # 这个测试应该失败，因为FeedingOrder还没有实现
    try:
        from app.models.work_order_models import FeedingOrder
        
        # 尝试创建一个基本的FeedingOrder实例
        order = FeedingOrder(
            work_order_nr="HWS20250827001",
            work_order_type="HWS",
            machine_type="喂丝机",
            machine_code="WS01",
            product_code="红塔山(硬)",
            plan_quantity=1100  # 包含安全库存
        )
        
        # 验证基本属性
        assert order.work_order_nr == "HWS20250827001"
        assert order.work_order_type == "HWS"
        assert order.machine_type == "喂丝机"
        assert order.machine_code == "WS01"
        assert order.product_code == "红塔山(硬)"
        assert order.plan_quantity == 1100
        
    except ImportError as e:
        pytest.fail(f"FeedingOrder model not found: {e}")


def test_feeding_order_database_table():
    """测试喂丝机工单对应的数据库表结构 - 预期失败"""
    try:
        from app.models.work_order_models import FeedingOrder
        
        # 验证表名
        assert hasattr(FeedingOrder, '__tablename__')
        assert FeedingOrder.__tablename__ == "aps_feeding_order"
        
        # 验证必要字段存在
        required_fields = [
            'id', 'work_order_nr', 'work_order_type', 'machine_type',
            'machine_code', 'product_code', 'plan_quantity', 'work_order_status',
            'safety_stock'  # 喂丝机特有的安全库存字段
        ]
        
        for field in required_fields:
            assert hasattr(FeedingOrder, field), f"Missing required field: {field}"
            
    except ImportError as e:
        pytest.fail(f"FeedingOrder model not found: {e}")