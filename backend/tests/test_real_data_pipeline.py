"""
测试使用真实旬计划数据的完整算法流程
"""
import pytest
from app.algorithms.pipeline import AlgorithmPipeline
from app.services.database_query_service import DatabaseQueryService


class TestRealDataPipeline:
    """真实数据管道测试"""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_real_decade_plan_data(self):
        """测试使用真实旬计划数据执行完整管道"""
        
        # 1. 查询真实旬计划数据
        decade_plans = await DatabaseQueryService.get_decade_plans()
        print(f"✓ 查询到 {len(decade_plans)} 条旬计划数据")
        
        # 验证确实有数据
        assert len(decade_plans) > 0, "应该有旬计划数据"
        
        # 2. 取前5条数据进行测试
        test_data = decade_plans[:5]
        print(f"✓ 使用前 {len(test_data)} 条真实数据进行测试")
        
        # 输出样例数据
        if test_data:
            sample = test_data[0]
            print(f"  样例数据: 工单号={sample['work_order_nr']}, 产品={sample['article_nr']}, 数量={sample['quantity_total']}")
        
        # 3. 执行完整算法管道
        pipeline = AlgorithmPipeline()
        result = await pipeline.execute_full_pipeline(test_data, use_real_data=True)
        
        # 4. 验证执行结果
        assert result['success'] == True, f"管道执行失败: {result.get('error', '未知错误')}"
        assert result['summary']['input_records'] == len(test_data)
        
        print(f"✓ 管道执行成功:")
        print(f"  - 输入记录: {result['summary']['input_records']}")
        print(f"  - 输出工单: {result['summary']['output_work_orders']}")
        print(f"  - 执行时间: {result['execution_duration_seconds']:.2f}秒")
        
        # 5. 验证每个阶段都使用了真实数据
        for stage_name, stage_result in result['stages'].items():
            custom_metrics = stage_result.get('custom_metrics', {})
            if 'used_real_database_data' in custom_metrics:
                assert custom_metrics['used_real_database_data'] == True, f"阶段 {stage_name} 没有使用真实数据"
                print(f"  ✓ {stage_name} 阶段使用真实数据")
        
        return result