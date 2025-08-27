"""
测试数据库模型集成 - 验证能从真实数据库查询轮保计划和班次配置
"""
import pytest
from datetime import datetime, date
from app.models.extended_models import MaintenancePlan
from app.db.connection import get_db_session


class TestDatabaseIntegration:
    """数据库集成测试"""
    
    def test_can_import_maintenance_plan_model(self):
        """测试能导入轮保计划模型"""
        assert MaintenancePlan.__tablename__ == "aps_maintenance_plan"
    
    @pytest.mark.asyncio
    async def test_can_query_maintenance_plans_from_database(self):
        """测试能从数据库查询轮保计划"""
        from app.services.database_query_service import DatabaseQueryService
        
        # 查询轮保计划
        maintenance_plans = await DatabaseQueryService.get_maintenance_plans()
        
        # 验证查询成功（可能没有数据，但不应该报错）
        assert isinstance(maintenance_plans, list)
        
        # 如果有数据，验证数据结构
        if maintenance_plans:
            plan = maintenance_plans[0]
            assert 'machine_code' in plan
            assert 'maint_start_time' in plan
            assert 'maint_end_time' in plan
    
    @pytest.mark.asyncio
    async def test_can_query_shift_configs_from_database(self):
        """测试能从数据库查询班次配置"""
        from app.services.database_query_service import DatabaseQueryService
        
        # 查询班次配置
        shift_configs = await DatabaseQueryService.get_shift_config()
        
        # 验证查询成功
        assert isinstance(shift_configs, list)
        
        # 如果有数据，验证数据结构
        if shift_configs:
            config = shift_configs[0]
            assert 'name' in config
            assert 'start_time' in config
            assert 'end_time' in config
    
    @pytest.mark.asyncio  
    async def test_can_query_machine_relations_from_database(self):
        """测试能从数据库查询机台关系"""
        from app.services.database_query_service import DatabaseQueryService
        
        # 查询机台关系
        relations = await DatabaseQueryService.get_machine_relations()
        
        # 验证查询成功
        assert isinstance(relations, dict)
        
        # 如果有数据，验证数据结构
        if relations:
            # 每个喂丝机对应一个卷包机列表
            feeder_code = list(relations.keys())[0]
            maker_codes = relations[feeder_code]
            assert isinstance(maker_codes, list)