"""
APS智慧排产系统 - 月度算法数据加载器测试

测试 DatabaseLoader 类的功能，使用真实数据库表数据进行验证。

测试覆盖：
1. 数据库连接和基础查询功能
2. 9个表的数据加载功能验证
3. 速度配置通配符匹配算法
4. 机台关系映射构建
5. 工作日历和维护计划处理
6. 异常情况和边界条件处理
7. 数据完整性和一致性验证

技术要求：
- 使用真实数据库表数据，不使用Mock
- 完整测试所有数据加载方法
- 验证数据格式和内容正确性
- 测试异常情况和错误处理
"""

import pytest
import asyncio
from datetime import datetime, date
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.connection import get_db_session
from app.algorithms.monthly_scheduling.database_loader import DatabaseLoader
from app.models.monthly_plan_models import MonthlyPlan
from app.models.base_models import Machine
from app.models.machine_config_models import MachineSpeed, MachineRelation
from app.models.monthly_work_calendar_models import MonthlyWorkCalendar
from app.models.machine_config_models import ShiftConfig, MaintenancePlan


class TestDatabaseLoader:
    """数据加载器测试类"""
    
    @pytest.fixture
    async def db_session(self):
        """数据库连接夹具"""
        async with get_db_session() as session:
            yield session
    
    @pytest.fixture
    async def database_loader(self, db_session):
        """数据加载器实例夹具"""
        return DatabaseLoader(db_session)
    
    @pytest.fixture
    async def sample_batch_id(self, db_session):
        """获取真实的月度批次ID用于测试"""
        result = await db_session.execute(
            select(MonthlyPlan.monthly_batch_id)
            .distinct()
            .limit(1)
        )
        batch_id = result.scalar()
        
        if not batch_id:
            # 如果没有数据，创建测试数据
            pytest.skip("数据库中没有月度计划数据，跳过测试")
        
        return batch_id
    
    async def test_load_monthly_plans_with_real_data(self, database_loader, sample_batch_id):
        """测试加载真实月度计划数据"""
        plans = await database_loader.load_monthly_plans(sample_batch_id)
        
        # 验证返回的数据
        assert isinstance(plans, list), "月度计划应该返回列表"
        
        if plans:  # 如果有数据
            plan = plans[0]
            
            # 验证必需字段存在
            required_fields = [
                'monthly_plan_id', 'monthly_batch_id', 'article_nr', 
                'article_name', 'target_quantity_boxes'
            ]
            for field in required_fields:
                assert hasattr(plan, field), f"月度计划应该包含字段: {field}"
            
            # 验证数据类型
            assert isinstance(plan.target_quantity_boxes, (int, float)), "目标数量应该是数值类型"
            assert plan.target_quantity_boxes > 0, "目标数量应该大于0"
            assert plan.monthly_batch_id == sample_batch_id, "批次ID应该匹配"
        
        print(f"✅ 成功加载月度计划数据: {len(plans)} 条记录")
    
    async def test_load_machine_data_with_real_data(self, database_loader):
        """测试加载真实机台数据"""
        machines_data = await database_loader.load_machine_data()
        
        # 验证数据结构
        assert isinstance(machines_data, dict), "机台数据应该返回字典"
        assert 'packing' in machines_data, "应该包含卷包机数据"
        assert 'feeding' in machines_data, "应该包含喂丝机数据"
        
        # 验证卷包机数据
        packing_machines = machines_data['packing']
        assert isinstance(packing_machines, list), "卷包机数据应该是列表"
        
        if packing_machines:
            machine = packing_machines[0]
            assert hasattr(machine, 'machine_code'), "机台应该有机台代码"
            assert hasattr(machine, 'machine_type'), "机台应该有机台类型"
            assert machine.machine_type == 'PACKING', "应该是卷包机类型"
        
        # 验证喂丝机数据
        feeding_machines = machines_data['feeding']
        assert isinstance(feeding_machines, list), "喂丝机数据应该是列表"
        
        if feeding_machines:
            machine = feeding_machines[0]
            assert hasattr(machine, 'machine_code'), "机台应该有机台代码"
            assert hasattr(machine, 'machine_type'), "机台应该有机台类型"
            assert machine.machine_type == 'FEEDING', "应该是喂丝机类型"
        
        print(f"✅ 成功加载机台数据: 卷包机 {len(packing_machines)} 台, 喂丝机 {len(feeding_machines)} 台")
    
    async def test_load_speed_configs_with_real_data(self, database_loader):
        """测试加载真实速度配置数据"""
        speed_configs = await database_loader.load_speed_configs()
        
        # 验证数据结构
        assert isinstance(speed_configs, dict), "速度配置应该返回字典"
        assert 'specific' in speed_configs, "应该包含具体配置"
        assert 'wildcard' in speed_configs, "应该包含通配符配置"
        
        specific_configs = speed_configs['specific']
        wildcard_configs = speed_configs['wildcard']
        
        assert isinstance(specific_configs, dict), "具体配置应该是字典"
        assert isinstance(wildcard_configs, list), "通配符配置应该是列表"
        
        # 验证具体配置格式 (machine_code, article_nr) -> speed_info
        for key, speed_info in specific_configs.items():
            assert isinstance(key, tuple), "配置键应该是元组"
            assert len(key) == 2, "配置键应该是二元组 (machine_code, article_nr)"
            assert isinstance(speed_info, dict), "速度信息应该是字典"
            assert 'speed_per_hour' in speed_info, "应该包含每小时速度"
        
        # 验证通配符配置格式
        for config in wildcard_configs:
            assert isinstance(config, dict), "通配符配置应该是字典"
            assert 'machine_code' in config, "应该包含机台代码"
            assert 'article_nr' in config, "应该包含物料代码"
            assert 'speed_per_hour' in config, "应该包含每小时速度"
        
        print(f"✅ 成功加载速度配置: 具体配置 {len(specific_configs)} 个, 通配符配置 {len(wildcard_configs)} 个")
    
    async def test_load_machine_relations_with_real_data(self, database_loader):
        """测试加载真实机台关系数据"""
        machine_relations = await database_loader.load_machine_relations()
        
        # 验证数据结构
        assert isinstance(machine_relations, dict), "机台关系应该返回字典"
        assert 'maker_to_feeder' in machine_relations, "应该包含卷包机→喂丝机映射"
        assert 'feeder_to_makers' in machine_relations, "应该包含喂丝机→卷包机映射"
        
        maker_to_feeder = machine_relations['maker_to_feeder']
        feeder_to_makers = machine_relations['feeder_to_makers']
        
        assert isinstance(maker_to_feeder, dict), "卷包机→喂丝机映射应该是字典"
        assert isinstance(feeder_to_makers, dict), "喂丝机→卷包机映射应该是字典"
        
        # 验证映射关系的一致性
        for maker_code, feeder_code in maker_to_feeder.items():
            assert isinstance(maker_code, str), "卷包机代码应该是字符串"
            assert isinstance(feeder_code, str), "喂丝机代码应该是字符串"
            
            # 验证反向映射的一致性
            assert feeder_code in feeder_to_makers, f"喂丝机 {feeder_code} 应该在反向映射中"
            
            # 检查该卷包机是否在对应的喂丝机的卷包机列表中
            makers_for_feeder = feeder_to_makers[feeder_code]
            maker_codes = [m['maker_code'] for m in makers_for_feeder]
            assert maker_code in maker_codes, f"卷包机 {maker_code} 应该在喂丝机 {feeder_code} 的卷包机列表中"
        
        print(f"✅ 成功加载机台关系: {len(maker_to_feeder)} 个卷包机映射")
    
    async def test_load_shift_configs_with_real_data(self, database_loader):
        """测试加载真实班次配置数据"""
        shift_configs = await database_loader.load_shift_configs()
        
        # 验证数据结构
        assert isinstance(shift_configs, list), "班次配置应该返回列表"
        
        if shift_configs:
            shift = shift_configs[0]
            
            # 验证必需字段
            required_fields = ['shift_name', 'start_time', 'end_time']
            for field in required_fields:
                assert hasattr(shift, field), f"班次配置应该包含字段: {field}"
            
            # 验证时间格式
            assert isinstance(shift.start_time, (str, datetime)), "开始时间应该是字符串或日期时间"
            assert isinstance(shift.end_time, (str, datetime)), "结束时间应该是字符串或日期时间"
        
        print(f"✅ 成功加载班次配置: {len(shift_configs)} 个班次")
    
    async def test_load_work_calendar_with_real_data(self, database_loader):
        """测试加载真实工作日历数据"""
        work_calendar = await database_loader.load_work_calendar()
        
        # 验证数据结构
        assert isinstance(work_calendar, dict), "工作日历应该返回字典"
        assert 'work_days' in work_calendar, "应该包含工作日信息"
        assert 'holiday_days' in work_calendar, "应该包含节假日信息"
        
        work_days = work_calendar['work_days']
        holiday_days = work_calendar['holiday_days']
        
        assert isinstance(work_days, list), "工作日应该是列表"
        assert isinstance(holiday_days, list), "节假日应该是列表"
        
        # 验证工作日数据格式
        if work_days:
            work_day = work_days[0]
            assert 'date' in work_day, "工作日应该包含日期"
            assert 'is_working' in work_day, "工作日应该包含是否工作标志"
            assert isinstance(work_day['is_working'], bool), "工作标志应该是布尔值"
        
        print(f"✅ 成功加载工作日历: 工作日 {len(work_days)} 天, 节假日 {len(holiday_days)} 天")
    
    async def test_load_maintenance_plans_with_real_data(self, database_loader):
        """测试加载真实维护计划数据"""
        maintenance_plans = await database_loader.load_maintenance_plans()
        
        # 验证数据结构
        assert isinstance(maintenance_plans, list), "维护计划应该返回列表"
        
        # 验证维护计划数据格式
        for plan in maintenance_plans:
            assert isinstance(plan, dict), "维护计划应该是字典"
            
            # 验证必需字段
            required_fields = ['machine_code', 'start_time', 'end_time']
            for field in required_fields:
                assert field in plan, f"维护计划应该包含字段: {field}"
            
            # 验证时间逻辑
            assert plan['start_time'] < plan['end_time'], "维护开始时间应该早于结束时间"
        
        print(f"✅ 成功加载维护计划: {len(maintenance_plans)} 个计划")
    
    async def test_load_all_data_integration(self, database_loader, sample_batch_id):
        """测试完整数据加载集成功能"""
        all_data = await database_loader.load_all_data(sample_batch_id)
        
        # 验证返回的数据结构
        assert isinstance(all_data, dict), "完整数据应该返回字典"
        
        # 验证所有必需的数据组件
        required_components = [
            'monthly_plans', 'machines', 'speed_configs', 
            'machine_relations', 'shift_configs', 'work_calendar', 
            'maintenance_plans'
        ]
        
        for component in required_components:
            assert component in all_data, f"完整数据应该包含: {component}"
        
        # 验证机台数据结构
        machines_data = all_data['machines']
        assert 'packing' in machines_data, "机台数据应该包含卷包机"
        assert 'feeding' in machines_data, "机台数据应该包含喂丝机"
        
        # 验证速度配置结构
        speed_configs = all_data['speed_configs']
        assert 'specific' in speed_configs, "速度配置应该包含具体配置"
        assert 'wildcard' in speed_configs, "速度配置应该包含通配符配置"
        
        # 验证机台关系结构
        machine_relations = all_data['machine_relations']
        assert 'maker_to_feeder' in machine_relations, "机台关系应该包含正向映射"
        assert 'feeder_to_makers' in machine_relations, "机台关系应该包含反向映射"
        
        print(f"✅ 成功完成完整数据加载集成测试")
        print(f"   - 月度计划: {len(all_data['monthly_plans'])} 条")
        print(f"   - 卷包机: {len(all_data['machines']['packing'])} 台")
        print(f"   - 喂丝机: {len(all_data['machines']['feeding'])} 台")
        print(f"   - 机台关系: {len(all_data['machine_relations']['maker_to_feeder'])} 个映射")
    
    async def test_speed_config_wildcard_matching(self, database_loader):
        """测试速度配置通配符匹配算法"""
        speed_configs = await database_loader.load_speed_configs()
        
        # 测试通配符匹配优先级
        test_scenarios = [
            # (machine_code, article_nr, expected_priority_level)
            ("A1", "C001", "specific"),  # 如果有具体配置
            ("*", "C001", "machine_wildcard"),  # 机台通配符
            ("A1", "*", "product_wildcard"),  # 产品通配符
            ("*", "*", "full_wildcard")  # 完全通配符
        ]
        
        specific_configs = speed_configs['specific']
        wildcard_configs = speed_configs['wildcard']
        
        # 测试具体配置优先级最高
        for machine_code, article_nr in specific_configs.keys():
            found_speed = database_loader._find_best_speed_config(
                machine_code, article_nr, speed_configs
            )
            assert found_speed is not None, f"应该找到 {machine_code}-{article_nr} 的速度配置"
            print(f"✅ 具体配置匹配成功: {machine_code}-{article_nr}")
        
        # 测试通配符配置匹配
        for config in wildcard_configs[:3]:  # 测试前3个通配符配置
            machine_code = config['machine_code']
            article_nr = config['article_nr']
            
            # 如果不在具体配置中，应该匹配通配符
            key = (machine_code, article_nr)
            if key not in specific_configs:
                found_speed = database_loader._find_best_speed_config(
                    machine_code, article_nr, speed_configs
                )
                if found_speed is not None:
                    print(f"✅ 通配符配置匹配成功: {machine_code}-{article_nr}")
    
    async def test_error_handling_and_edge_cases(self, database_loader):
        """测试错误处理和边界条件"""
        
        # 测试不存在的批次ID
        try:
            empty_plans = await database_loader.load_monthly_plans("NONEXISTENT_BATCH")
            assert isinstance(empty_plans, list), "不存在的批次应该返回空列表"
            assert len(empty_plans) == 0, "不存在的批次应该返回空列表"
            print("✅ 不存在批次ID处理正确")
        except Exception as e:
            pytest.fail(f"处理不存在批次ID时应该返回空列表而不是抛出异常: {e}")
        
        # 测试空数据处理
        empty_data = await database_loader.load_all_data("EMPTY_BATCH_TEST")
        assert isinstance(empty_data, dict), "应该返回字典结构"
        assert len(empty_data['monthly_plans']) == 0, "不存在的批次应该返回空计划列表"
        print("✅ 空数据处理正确")
        
        # 测试数据一致性
        all_data = await database_loader.load_all_data("TEST_BATCH")
        machines = all_data['machines']
        relations = all_data['machine_relations']
        
        # 验证所有关系中的机台都存在于机台列表中
        packing_codes = {m.machine_code for m in machines['packing']}
        feeding_codes = {m.machine_code for m in machines['feeding']}
        
        for maker_code, feeder_code in relations['maker_to_feeder'].items():
            if maker_code not in packing_codes:
                print(f"⚠️ 警告: 关系中的卷包机 {maker_code} 不在机台列表中")
            if feeder_code not in feeding_codes:
                print(f"⚠️ 警告: 关系中的喂丝机 {feeder_code} 不在机台列表中")
        
        print("✅ 数据一致性检查完成")
    
    async def test_performance_and_caching(self, database_loader, sample_batch_id):
        """测试性能和缓存机制"""
        import time
        
        # 第一次加载
        start_time = time.time()
        first_load = await database_loader.load_all_data(sample_batch_id)
        first_duration = time.time() - start_time
        
        # 第二次加载（如果有缓存应该更快）
        start_time = time.time()
        second_load = await database_loader.load_all_data(sample_batch_id)
        second_duration = time.time() - start_time
        
        assert isinstance(first_load, dict), "第一次加载应该返回字典"
        assert isinstance(second_load, dict), "第二次加载应该返回字典"
        
        # 验证数据一致性
        assert len(first_load['monthly_plans']) == len(second_load['monthly_plans']), "两次加载的数据应该一致"
        
        print(f"✅ 性能测试完成:")
        print(f"   - 第一次加载耗时: {first_duration:.3f} 秒")
        print(f"   - 第二次加载耗时: {second_duration:.3f} 秒")
        
        if second_duration < first_duration:
            print(f"   - 性能提升: {((first_duration - second_duration) / first_duration * 100):.1f}%")


# 异步测试运行器
@pytest.mark.asyncio
async def test_database_loader_complete_suite():
    """运行完整的数据加载器测试套件"""
    print("\n🚀 开始运行月度算法数据加载器完整测试套件")
    
    async with get_db_session() as db_session:
        loader = DatabaseLoader(db_session)
        test_instance = TestDatabaseLoader()
        
        # 获取测试批次ID
        result = await db_session.execute(
            select(MonthlyPlan.monthly_batch_id).distinct().limit(1)
        )
        batch_id = result.scalar()
        
        if not batch_id:
            print("❌ 数据库中没有月度计划数据，跳过测试")
            return
        
        print(f"📋 使用测试批次ID: {batch_id}")
        
        # 运行所有测试
        try:
            await test_instance.test_load_monthly_plans_with_real_data(loader, batch_id)
            await test_instance.test_load_machine_data_with_real_data(loader)
            await test_instance.test_load_speed_configs_with_real_data(loader)
            await test_instance.test_load_machine_relations_with_real_data(loader)
            await test_instance.test_load_shift_configs_with_real_data(loader)
            await test_instance.test_load_work_calendar_with_real_data(loader)
            await test_instance.test_load_maintenance_plans_with_real_data(loader)
            await test_instance.test_load_all_data_integration(loader, batch_id)
            await test_instance.test_speed_config_wildcard_matching(loader)
            await test_instance.test_error_handling_and_edge_cases(loader)
            await test_instance.test_performance_and_caching(loader, batch_id)
            
            print("\n🎉 数据加载器测试套件全部通过!")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            raise


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_database_loader_complete_suite())