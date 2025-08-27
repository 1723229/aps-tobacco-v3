"""
测试旬计划数据查询 - 验证从aps_decade_plan表查询数据
"""
import pytest
from datetime import datetime, date
from app.services.database_query_service import DatabaseQueryService


class TestDecadePlanQuery:
    """旬计划数据查询测试"""
    
    @pytest.mark.asyncio
    async def test_can_query_decade_plans(self):
        """测试能查询旬计划数据"""
        # 查询旬计划数据
        decade_plans = await DatabaseQueryService.get_decade_plans()
        
        # 验证查询成功（可能没有数据，但不应该报错）
        assert isinstance(decade_plans, list)
        
        # 如果有数据，验证数据结构
        if decade_plans:
            plan = decade_plans[0]
            required_fields = [
                'id', 'work_order_nr', 'article_nr', 'quantity_total', 
                'final_quantity', 'maker_code', 'feeder_code',
                'planned_start', 'planned_end'
            ]
            for field in required_fields:
                assert field in plan, f"缺少字段: {field}"
    
    @pytest.mark.asyncio  
    async def test_decade_plan_query_with_batch_id(self):
        """测试按批次ID查询旬计划数据"""
        # 使用测试批次ID查询
        test_batch_id = "test_batch_20241201"
        decade_plans = await DatabaseQueryService.get_decade_plans(
            import_batch_id=test_batch_id
        )
        
        # 验证查询成功
        assert isinstance(decade_plans, list)
        
        # 如果有数据，验证批次ID匹配
        for plan in decade_plans:
            assert plan['import_batch_id'] == test_batch_id
    
    def test_database_query_service_has_decade_plan_method(self):
        """测试数据库查询服务有旬计划查询方法"""
        assert hasattr(DatabaseQueryService, 'get_decade_plans')
        
        # 验证方法是异步的
        import inspect
        assert inspect.iscoroutinefunction(DatabaseQueryService.get_decade_plans)