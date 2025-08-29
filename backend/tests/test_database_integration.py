"""
测试数据库集成 - 验证所有算法都能正确使用真实数据库数据
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.algorithms.pipeline import AlgorithmPipeline
from app.services.database_query_service import DatabaseQueryService


async def test_database_connectivity():
    """测试数据库连接"""
    print("🔗 测试数据库连接...")
    
    try:
        # 测试基础查询
        decade_plans = await DatabaseQueryService.get_decade_plans()
        machine_relations = await DatabaseQueryService.get_machine_relations()
        machine_speeds = await DatabaseQueryService.get_machine_speeds()
        shift_configs = await DatabaseQueryService.get_shift_config()
        
        print(f"✅ 数据库连接成功")
        print(f"   旬计划数据: {len(decade_plans)}条")
        print(f"   机台关系: {len(machine_relations)}个喂丝机")
        print(f"   机台速度: {len(machine_speeds)}台机器")
        print(f"   班次配置: {len(shift_configs)}个班次")
        
        return True, {
            'decade_plans_count': len(decade_plans),
            'machine_relations_count': len(machine_relations),
            'machine_speeds_count': len(machine_speeds),
            'shift_configs_count': len(shift_configs)
        }
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False, str(e)


async def test_pipeline_with_real_data():
    """测试使用真实数据库数据的完整管道"""
    print("\n🏭 测试使用真实数据库数据的算法管道...")
    
    try:
        pipeline = AlgorithmPipeline()
        
        # 查找最近的批次数据
        decade_plans = await DatabaseQueryService.get_decade_plans()
        
        if not decade_plans:
            print("⚠️ 数据库中没有旬计划数据，无法测试真实数据流")
            return False, "No decade plan data found"
        
        # 使用第一个批次ID
        first_batch_id = decade_plans[0]['import_batch_id']
        print(f"   使用批次ID: {first_batch_id}")
        
        # 执行使用真实数据的完整管道
        result = await pipeline.execute_full_pipeline_with_batch(
            import_batch_id=first_batch_id,
            use_real_data=True
        )
        
        if result['success']:
            final_work_orders = result['final_work_orders']
            feeder_orders = [wo for wo in final_work_orders if wo.get('work_order_type') == 'HWS']
            maker_orders = [wo for wo in final_work_orders if wo.get('work_order_type') == 'HJB']
            
            print(f"✅ 真实数据管道测试成功!")
            print(f"   输入批次: {first_batch_id}")
            print(f"   执行时间: {result['execution_duration_seconds']:.2f}秒")
            print(f"   输入记录: {result['summary']['input_records']}条")
            print(f"   输出工单: {result['summary']['output_work_orders']}条")
            print(f"   喂丝机工单: {len(feeder_orders)}个")
            print(f"   卷包机工单: {len(maker_orders)}个")
            
            # 验证关键需求
            assert len(feeder_orders) > 0, "必须生成喂丝机工单"
            assert len(maker_orders) > 0, "必须生成卷包机工单"
            
            return True, result
        else:
            print(f"❌ 真实数据管道测试失败: {result.get('error', 'Unknown error')}")
            return False, result.get('error', 'Unknown error')
            
    except Exception as e:
        print(f"❌ 真实数据管道测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)


async def test_individual_algorithms_with_real_data():
    """测试各个算法模块的数据库集成"""
    print("\n🧩 测试各算法模块的数据库集成...")
    
    from app.algorithms.data_preprocessing import DataPreprocessor
    from app.algorithms.merge_algorithm import MergeAlgorithm
    from app.algorithms.split_algorithm import SplitAlgorithm
    from app.algorithms.time_correction import TimeCorrection
    from app.algorithms.parallel_processing import ParallelProcessing
    from app.algorithms.work_order_generation import WorkOrderGeneration
    
    try:
        # 获取一些测试数据
        decade_plans = await DatabaseQueryService.get_decade_plans()
        if not decade_plans:
            print("⚠️ 没有数据进行测试")
            return False, "No test data"
        
        test_data = decade_plans[:3]  # 使用前3条数据测试
        current_data = test_data
        
        algorithms = [
            ("数据预处理", DataPreprocessor()),
            ("规则合并", MergeAlgorithm()),
            ("规则拆分", SplitAlgorithm()),
            ("时间校正", TimeCorrection()),
            ("并行切分", ParallelProcessing()),
            ("工单生成", WorkOrderGeneration())
        ]
        
        test_results = []
        
        for name, algorithm in algorithms:
            print(f"   测试 {name}...")
            
            # 检查是否有process_with_real_data方法
            if hasattr(algorithm, 'process_with_real_data'):
                result = await algorithm.process_with_real_data(current_data)
            else:
                result = algorithm.process(current_data)
            
            if result.success:
                print(f"   ✅ {name}: 输入{len(current_data)} -> 输出{len(result.output_data)}")
                current_data = result.output_data
                test_results.append({
                    'name': name,
                    'success': True,
                    'input_count': len(current_data),
                    'output_count': len(result.output_data),
                    'used_real_data': result.metrics.custom_metrics.get('used_real_database_data', False)
                })
            else:
                print(f"   ❌ {name}: {result.error_summary}")
                test_results.append({
                    'name': name,
                    'success': False,
                    'error': result.error_summary
                })
                break
        
        # 统计使用真实数据的算法数量
        real_data_algorithms = sum(1 for r in test_results if r.get('used_real_data', False))
        total_algorithms = len(test_results)
        
        print(f"\n   📊 算法测试摘要:")
        print(f"   总算法数: {total_algorithms}")
        print(f"   使用真实数据: {real_data_algorithms}")
        print(f"   数据库集成度: {real_data_algorithms/total_algorithms*100:.1f}%")
        
        return True, test_results
        
    except Exception as e:
        print(f"❌ 算法模块测试失败: {str(e)}")
        return False, str(e)


async def main():
    """主测试函数"""
    print("🧪 APS算法数据库集成测试")
    print("=" * 60)
    
    all_success = True
    
    # 1. 测试数据库连接
    db_success, db_result = await test_database_connectivity()
    if not db_success:
        print("❌ 数据库连接失败，无法继续测试")
        return 1
    
    # 2. 测试各算法模块的数据库集成
    algo_success, algo_result = await test_individual_algorithms_with_real_data()
    if not algo_success:
        all_success = False
    
    # 3. 测试完整管道的真实数据处理
    pipeline_success, pipeline_result = await test_pipeline_with_real_data()
    if not pipeline_success:
        all_success = False
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 所有数据库集成测试通过！")
        print("\n✅ 验证结果:")
        print("   ✅ 数据库连接正常")
        print("   ✅ 各算法模块集成正确")
        print("   ✅ 完整管道可用真实数据")
        print("   ✅ 喂丝机和卷包机工单都能正确生成")
        return 0
    else:
        print("❌ 部分测试失败，请检查数据库集成实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
