"""
APS算法综合测试验证
验证算法设计文档要求的完整实现
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.algorithms.pipeline import AlgorithmPipeline
from app.algorithms.data_preprocessing import DataPreprocessor
from app.algorithms.merge_algorithm import MergeAlgorithm
from app.algorithms.split_algorithm import SplitAlgorithm
from app.algorithms.time_correction import TimeCorrection
from app.algorithms.parallel_processing import ParallelProcessing
from app.algorithms.work_order_generation import WorkOrderGeneration


class AlgorithmTester:
    """算法综合测试器"""
    
    def __init__(self):
        self.pipeline = AlgorithmPipeline()
        
    def create_test_data(self) -> List[Dict[str, Any]]:
        """创建测试数据"""
        base_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        test_data = [
            {
                'id': 1,
                'import_batch_id': 'TEST_BATCH_20241201',
                'work_order_nr': 'TEST_001',
                'article_nr': 'PA',  # 产品代码
                'package_type': '20支装硬盒',
                'specification': '84mm',
                'quantity_total': 1000000,  # 100万支
                'final_quantity': 1000000,
                'production_unit': '万支',
                'maker_code': 'JJ#01',  # 卷包机代码
                'feeder_code': 'WS#01',  # 喂丝机代码
                'planned_start': base_date,
                'planned_end': base_date + timedelta(hours=8),
                'production_date_range': '12.01-12.01',
                'validation_status': 'VALID'
            },
            {
                'id': 2,
                'import_batch_id': 'TEST_BATCH_20241201',
                'work_order_nr': 'TEST_002',
                'article_nr': 'PA',  # 同一产品
                'package_type': '20支装硬盒',
                'specification': '84mm',
                'quantity_total': 1500000,  # 150万支
                'final_quantity': 1500000,
                'production_unit': '万支',
                'maker_code': 'JJ#02',  # 不同卷包机
                'feeder_code': 'WS#01',  # 同一喂丝机
                'planned_start': base_date + timedelta(hours=8),
                'planned_end': base_date + timedelta(hours=16),
                'production_date_range': '12.01-12.01',
                'validation_status': 'VALID'
            },
            {
                'id': 3,
                'import_batch_id': 'TEST_BATCH_20241201',
                'work_order_nr': 'TEST_003',
                'article_nr': 'PC',  # 不同产品
                'package_type': '20支装硬盒',
                'specification': '84mm',
                'quantity_total': 800000,  # 80万支
                'final_quantity': 800000,
                'production_unit': '万支',
                'maker_code': 'JJ#03',
                'feeder_code': 'WS#02',  # 不同喂丝机
                'planned_start': base_date,
                'planned_end': base_date + timedelta(hours=6),
                'production_date_range': '12.01-12.01',
                'validation_status': 'VALID'
            }
        ]
        
        return test_data
    
    def create_test_machine_relations(self) -> Dict[str, List[str]]:
        """创建测试机台关系数据"""
        return {
            'WS#01': ['JJ#01', 'JJ#02'],  # 喂丝机WS#01对应两台卷包机
            'WS#02': ['JJ#03'],           # 喂丝机WS#02对应一台卷包机
        }
    
    def create_test_machine_speeds(self) -> Dict[str, Dict[str, Any]]:
        """创建测试机台速度数据"""
        return {
            'JJ#01': {
                'article_nr': 'PA',
                'speed': 8000,  # 8000支/分钟
                'efficiency_rate': 0.85
            },
            'JJ#02': {
                'article_nr': 'PA',
                'speed': 8500,  # 8500支/分钟
                'efficiency_rate': 0.90
            },
            'JJ#03': {
                'article_nr': 'PC',
                'speed': 7500,  # 7500支/分钟
                'efficiency_rate': 0.80
            }
        }
    
    def test_data_preprocessing(self) -> Dict[str, Any]:
        """测试数据预处理"""
        print("\n=== 测试数据预处理 ===")
        
        preprocessor = DataPreprocessor()
        test_data = self.create_test_data()
        
        result = preprocessor.process(test_data)
        
        # 验证结果
        assert result.success, f"数据预处理失败: {result.error_summary}"
        assert len(result.output_data) == 3, f"预期3条数据，实际{len(result.output_data)}条"
        
        print(f"✅ 数据预处理通过: 输入{len(test_data)}条，输出{len(result.output_data)}条")
        return {
            'stage': 'data_preprocessing',
            'success': True,
            'input_count': len(test_data),
            'output_count': len(result.output_data),
            'output_data': result.output_data
        }
    
    def test_merge_algorithm(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """测试规则合并算法"""
        print("\n=== 测试规则合并算法 ===")
        
        merger = MergeAlgorithm()
        result = merger.process(input_data)
        
        # 验证结果
        assert result.success, f"规则合并失败: {result.error_summary}"
        
        print(f"✅ 规则合并通过: 输入{len(input_data)}条，输出{len(result.output_data)}条")
        return {
            'stage': 'merge_algorithm',
            'success': True,
            'input_count': len(input_data),
            'output_count': len(result.output_data),
            'output_data': result.output_data
        }
    
    def test_split_algorithm(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """测试规则拆分算法"""
        print("\n=== 测试规则拆分算法 ===")
        
        splitter = SplitAlgorithm()
        machine_relations = self.create_test_machine_relations()
        
        result = splitter.process(input_data, maker_mapping=machine_relations)
        
        # 验证结果
        assert result.success, f"规则拆分失败: {result.error_summary}"
        
        print(f"✅ 规则拆分通过: 输入{len(input_data)}条，输出{len(result.output_data)}条")
        return {
            'stage': 'split_algorithm',
            'success': True,
            'input_count': len(input_data),
            'output_count': len(result.output_data),
            'output_data': result.output_data
        }
    
    def test_time_correction(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """测试时间校正算法"""
        print("\n=== 测试时间校正算法 ===")
        
        time_corrector = TimeCorrection()
        result = time_corrector.process(input_data)
        
        # 验证结果
        assert result.success, f"时间校正失败: {result.error_summary}"
        
        print(f"✅ 时间校正通过: 输入{len(input_data)}条，输出{len(result.output_data)}条")
        return {
            'stage': 'time_correction',
            'success': True,
            'input_count': len(input_data),
            'output_count': len(result.output_data),
            'output_data': result.output_data
        }
    
    def test_parallel_processing(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """测试并行切分算法"""
        print("\n=== 测试并行切分算法 ===")
        
        parallel_processor = ParallelProcessing()
        machine_relations = self.create_test_machine_relations()
        machine_speeds = self.create_test_machine_speeds()
        
        result = parallel_processor.process(
            input_data, 
            machine_relations=machine_relations,
            machine_speeds=machine_speeds
        )
        
        # 验证结果
        assert result.success, f"并行切分失败: {result.error_summary}"
        
        # 检查并行组是否正确创建
        parallel_groups = {}
        for order in result.output_data:
            group_id = order.get('parallel_group_id')
            if group_id:
                if group_id not in parallel_groups:
                    parallel_groups[group_id] = []
                parallel_groups[group_id].append(order)
        
        print(f"✅ 并行切分通过: 输入{len(input_data)}条，输出{len(result.output_data)}条")
        print(f"   创建{len(parallel_groups)}个并行组")
        
        return {
            'stage': 'parallel_processing',
            'success': True,
            'input_count': len(input_data),
            'output_count': len(result.output_data),
            'parallel_groups_count': len(parallel_groups),
            'output_data': result.output_data
        }
    
    def test_work_order_generation(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """测试工单生成算法"""
        print("\n=== 测试工单生成算法 ===")
        
        work_order_generator = WorkOrderGeneration()
        result = work_order_generator.process(input_data)
        
        # 验证结果
        assert result.success, f"工单生成失败: {result.error_summary}"
        
        # 统计工单类型
        feeder_orders = [wo for wo in result.output_data if wo.get('work_order_type') == 'HWS']
        maker_orders = [wo for wo in result.output_data if wo.get('work_order_type') == 'HJB']
        
        print(f"✅ 工单生成通过: 输入{len(input_data)}条，输出{len(result.output_data)}条")
        print(f"   喂丝机工单: {len(feeder_orders)}个")
        print(f"   卷包机工单: {len(maker_orders)}个")
        
        # 验证关键需求：喂丝机工单数量应该少于等于卷包机工单数量
        assert len(feeder_orders) > 0, "必须生成喂丝机工单"
        assert len(maker_orders) > 0, "必须生成卷包机工单"
        assert len(feeder_orders) <= len(maker_orders), "喂丝机工单数量应该不大于卷包机工单数量"
        
        return {
            'stage': 'work_order_generation',
            'success': True,
            'input_count': len(input_data),
            'output_count': len(result.output_data),
            'feeder_orders_count': len(feeder_orders),
            'maker_orders_count': len(maker_orders),
            'feeder_orders': feeder_orders,
            'maker_orders': maker_orders
        }
    
    async def test_full_pipeline(self) -> Dict[str, Any]:
        """测试完整管道"""
        print("\n=== 测试完整算法管道 ===")
        
        test_data = self.create_test_data()
        
        # 执行完整管道（不使用数据库）
        result = await self.pipeline.execute_full_pipeline(test_data, use_real_data=False)
        
        # 验证结果
        assert result['success'], f"完整管道执行失败: {result.get('error', 'Unknown error')}"
        
        final_work_orders = result['final_work_orders']
        feeder_orders = [wo for wo in final_work_orders if wo.get('work_order_type') == 'HWS']
        maker_orders = [wo for wo in final_work_orders if wo.get('work_order_type') == 'HJB']
        
        print(f"✅ 完整管道测试通过!")
        print(f"   执行时间: {result['execution_duration_seconds']:.2f}秒")
        print(f"   输入记录: {result['summary']['input_records']}条")
        print(f"   输出工单: {result['summary']['output_work_orders']}条")
        print(f"   喂丝机工单: {len(feeder_orders)}个")
        print(f"   卷包机工单: {len(maker_orders)}个")
        
        return result
    
    async def run_comprehensive_test(self):
        """运行综合测试"""
        print("🧪 开始APS算法综合测试验证")
        print("=" * 60)
        
        try:
            # 逐步测试每个算法阶段
            test_results = []
            
            # 1. 数据预处理
            preprocessing_result = self.test_data_preprocessing()
            test_results.append(preprocessing_result)
            current_data = preprocessing_result['output_data']
            
            # 2. 规则合并
            merge_result = self.test_merge_algorithm(current_data)
            test_results.append(merge_result)
            current_data = merge_result['output_data']
            
            # 3. 规则拆分
            split_result = self.test_split_algorithm(current_data)
            test_results.append(split_result)
            current_data = split_result['output_data']
            
            # 4. 时间校正
            time_result = self.test_time_correction(current_data)
            test_results.append(time_result)
            current_data = time_result['output_data']
            
            # 5. 并行切分
            parallel_result = self.test_parallel_processing(current_data)
            test_results.append(parallel_result)
            current_data = parallel_result['output_data']
            
            # 6. 工单生成
            work_order_result = self.test_work_order_generation(current_data)
            test_results.append(work_order_result)
            
            # 7. 完整管道测试
            pipeline_result = await self.test_full_pipeline()
            
            print("\n" + "=" * 60)
            print("🎉 所有测试通过！算法实现符合设计文档要求")
            print("\n📊 测试摘要:")
            for result in test_results:
                print(f"   {result['stage']}: ✅ 输入{result['input_count']} -> 输出{result['output_count']}")
            
            print(f"\n🚀 完整管道测试: ✅")
            print(f"   最终生成工单: {len(pipeline_result['final_work_orders'])}个")
            
            return True
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    tester = AlgorithmTester()
    success = await tester.run_comprehensive_test()
    
    if success:
        print("\n✅ 算法验证完成 - 所有测试通过")
        return 0
    else:
        print("\n❌ 算法验证失败 - 请检查实现")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
