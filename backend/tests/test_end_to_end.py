"""
完整的端到端测试 - 验证从旬计划数据到工单生成的完整流程
"""
import pytest
from datetime import datetime
from app.algorithms.pipeline import AlgorithmPipeline
from app.services.database_query_service import DatabaseQueryService


class TestEndToEndFlow:
    """端到端流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_data_flow(self):
        """测试完整的数据流：旬计划 → 算法处理 → 工单生成"""
        
        # 1. 验证能查询旬计划数据
        decade_plans = await DatabaseQueryService.get_decade_plans()
        print(f"✓ 查询到 {len(decade_plans)} 条旬计划数据")
        
        # 2. 验证能查询轮保计划
        maintenance_plans = await DatabaseQueryService.get_maintenance_plans()
        print(f"✓ 查询到 {len(maintenance_plans)} 条轮保计划")
        
        # 3. 验证能查询班次配置
        shift_configs = await DatabaseQueryService.get_shift_config()
        print(f"✓ 查询到 {len(shift_configs)} 个班次配置")
        
        # 4. 验证能查询机台关系
        machine_relations = await DatabaseQueryService.get_machine_relations()
        print(f"✓ 查询到 {len(machine_relations)} 个机台关系")
        
        # 5. 创建测试数据（如果没有真实数据）
        if not decade_plans:
            test_data = self._create_test_decade_plan_data()
            print("✓ 使用测试数据进行算法验证")
        else:
            test_data = decade_plans[:5]  # 使用前5条真实数据
            print(f"✓ 使用 {len(test_data)} 条真实数据进行算法验证")
        
        # 6. 测试完整算法管道
        pipeline = AlgorithmPipeline()
        
        # 测试数据预处理
        preprocessing_result = await pipeline.preprocessor.process_with_real_data(test_data)
        assert preprocessing_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 数据预处理: {len(preprocessing_result.output_data)} 条有效数据")
        
        # 测试规则合并
        merge_result = await pipeline.merger.process_with_real_data(preprocessing_result.output_data)
        assert merge_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 规则合并: {len(merge_result.output_data)} 条合并后数据")
        
        # 测试规则拆分
        split_result = await pipeline.splitter.process_with_real_data(merge_result.output_data)
        assert split_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 规则拆分: {len(split_result.output_data)} 条拆分后数据")
        
        # 测试时间校正
        time_correction_result = await pipeline.time_corrector.process_with_real_data(split_result.output_data)
        assert time_correction_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 时间校正: {len(time_correction_result.output_data)} 条校正后数据")
        
        # 测试并行处理
        parallel_result = await pipeline.parallel_processor.process_with_real_data(time_correction_result.output_data)
        assert parallel_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 并行处理: {len(parallel_result.output_data)} 条并行数据")
        
        # 测试工单生成
        work_order_result = await pipeline.work_order_generator.process_with_real_data(parallel_result.output_data)
        assert work_order_result.metrics.custom_metrics.get('used_real_database_data') == True
        print(f"✓ 工单生成: {len(work_order_result.output_data)} 个工单")
        
        # 7. 验证最终工单的完整性
        final_work_orders = work_order_result.output_data
        if final_work_orders:
            sample_order = final_work_orders[0]
            required_fields = [
                'work_order_nr', 'work_order_type', 'machine_type',
                'machine_code', 'product_code', 'plan_quantity',
                'planned_start_time', 'planned_end_time', 'work_order_status'
            ]
            
            for field in required_fields:
                assert field in sample_order, f"工单缺少必要字段: {field}"
            
            print(f"✓ 工单完整性验证通过 - 样例工单号: {sample_order.get('work_order_nr')}")
        
        print("🎉 端到端测试完全通过！")
        
        return {
            'decade_plans_count': len(decade_plans),
            'maintenance_plans_count': len(maintenance_plans), 
            'shift_configs_count': len(shift_configs),
            'machine_relations_count': len(machine_relations),
            'final_work_orders_count': len(final_work_orders),
            'test_passed': True
        }
    
    def _create_test_decade_plan_data(self):
        """创建测试用的旬计划数据"""
        return [
            {
                'id': 1,
                'import_batch_id': 'test_batch_001',
                'work_order_nr': 'WO20241201001',
                'article_nr': '红塔山(硬)',
                'package_type': '硬包',
                'specification': '长嘴',
                'quantity_total': 1000,
                'final_quantity': 950,
                'production_unit': '生产一部',
                'maker_code': 'JJ01',
                'feeder_code': 'WS01',
                'planned_start': datetime(2024, 12, 1, 8, 0),
                'planned_end': datetime(2024, 12, 1, 16, 0),
                'production_date_range': '2024-12-01',
                'validation_status': 'VALID',
                'validation_message': None
            },
            {
                'id': 2,
                'import_batch_id': 'test_batch_001',
                'work_order_nr': 'WO20241201002',
                'article_nr': '云烟(软)',
                'package_type': '软包',
                'specification': '短嘴',
                'quantity_total': 800,
                'final_quantity': 760,
                'production_unit': '生产二部',
                'maker_code': 'JJ02',
                'feeder_code': 'WS02',
                'planned_start': datetime(2024, 12, 1, 9, 0),
                'planned_end': datetime(2024, 12, 1, 17, 0),
                'production_date_range': '2024-12-01',
                'validation_status': 'VALID',
                'validation_message': None
            }
        ]
    
    @pytest.mark.asyncio
    async def test_database_connectivity(self):
        """测试数据库连接性"""
        try:
            # 测试每个数据库查询方法
            decade_plans = await DatabaseQueryService.get_decade_plans()
            maintenance_plans = await DatabaseQueryService.get_maintenance_plans()
            shift_configs = await DatabaseQueryService.get_shift_config()
            machine_relations = await DatabaseQueryService.get_machine_relations()
            
            print(f"数据库连接测试通过:")
            print(f"  - aps_decade_plan: {len(decade_plans)} 条记录")
            print(f"  - aps_maintenance_plan: {len(maintenance_plans)} 条记录")
            print(f"  - aps_shift_config: {len(shift_configs)} 条记录")
            print(f"  - aps_machine_relation: {len(machine_relations)} 条记录")
            
            assert True  # 如果没有异常就通过
            
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            pytest.fail(f"数据库连接测试失败: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_algorithm_with_empty_data(self):
        """测试算法处理空数据的健壮性"""
        pipeline = AlgorithmPipeline()
        
        # 测试空数据处理
        empty_result = await pipeline.execute_full_pipeline([], use_real_data=True)
        
        assert empty_result['success'] == True
        assert empty_result['summary']['input_records'] == 0
        assert empty_result['summary']['output_work_orders'] == 0
        
        print("✓ 空数据处理测试通过")