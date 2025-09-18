"""
月度时间线生成算法测试脚本

测试 MonthlyTimelineGenerator 类的基本功能
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal

# 模拟导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.algorithms.monthly_scheduling.monthly_timeline_generator import (
    MonthlyTimelineGenerator,
    TimelineOptimizationMode,
    TimelineOutputFormat,
    TaskPriority
)


async def test_basic_timeline_generation():
    """测试基础时间线生成功能"""
    print("=== 测试基础时间线生成功能 ===")
    
    # 创建时间线生成器
    generator = MonthlyTimelineGenerator()
    
    # 准备测试数据
    test_plan_data = [
        {
            'monthly_work_order_nr': 'WO2024001',
            'monthly_article_nr': 'CIG001',
            'monthly_target_quantity': 500,
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ001',
            'monthly_planned_start': datetime(2024, 1, 1),
            'monthly_planned_end': datetime(2024, 1, 31)
        },
        {
            'monthly_work_order_nr': 'WO2024002',
            'monthly_article_nr': 'CIG002',
            'monthly_target_quantity': 800,
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ002',
            'monthly_planned_start': datetime(2024, 1, 1),
            'monthly_planned_end': datetime(2024, 1, 31)
        },
        {
            'monthly_work_order_nr': 'WO2024003',
            'monthly_article_nr': 'CIG001',
            'monthly_target_quantity': 300,
            'monthly_feeder_codes': 'WSJ002',
            'monthly_maker_codes': 'JBJ001',
            'monthly_planned_start': datetime(2024, 1, 1),
            'monthly_planned_end': datetime(2024, 1, 31)
        }
    ]
    
    try:
        # 生成时间线
        result = await generator.generate_timeline(
            test_plan_data,
            year=2024,
            month=1,
            optimization_mode=TimelineOptimizationMode.BALANCED,
            output_formats=[TimelineOutputFormat.GANTT_CHART, TimelineOutputFormat.STATISTICS]
        )
        
        print(f"✅ 时间线生成成功!")
        print(f"   时间线ID: {result.timeline_id}")
        print(f"   已调度任务数: {len(result.scheduled_tasks)}")
        print(f"   时间窗口数: {len(result.time_windows)}")
        print(f"   检测冲突数: {len(result.conflicts)}")
        print(f"   执行时间: {result.execution_time:.2f}秒")
        
        # 验证调度结果
        if result.scheduled_tasks:
            print(f"\n   前3个调度任务:")
            for i, task in enumerate(result.scheduled_tasks[:3]):
                print(f"   {i+1}. {task.work_order_nr} - {task.article_nr}")
                print(f"      机台: {task.machine_id}")
                print(f"      时间: {task.start_time.strftime('%Y-%m-%d %H:%M')} - {task.end_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"      数量: {task.allocated_quantity}")
                print(f"      优先级: {task.priority.name}")
        
        # 验证优化指标
        if result.optimization_metrics:
            metrics = result.optimization_metrics
            print(f"\n   优化指标:")
            print(f"   总完工时间: {metrics.total_makespan}")
            print(f"   切换时间占比: {metrics.setup_time_ratio:.1%}")
            print(f"   排产效率: {metrics.schedule_efficiency:.1f}")
            print(f"   优化评分: {metrics.optimization_score:.1f}")
        
        # 验证甘特图数据
        if result.gantt_data:
            print(f"\n   甘特图数据:")
            print(f"   任务数: {len(result.gantt_data.tasks)}")
            print(f"   机台数: {len(result.gantt_data.machines)}")
            print(f"   里程碑数: {len(result.gantt_data.milestones)}")
        
        return result
        
    except Exception as e:
        print(f"❌ 时间线生成失败: {str(e)}")
        return None


async def test_optimization_modes():
    """测试不同优化模式"""
    print("\n=== 测试不同优化模式 ===")
    
    generator = MonthlyTimelineGenerator()
    
    # 准备测试数据
    test_data = [
        {
            'monthly_work_order_nr': f'WO{i+1:03d}',
            'monthly_article_nr': f'CIG{(i % 3) + 1:03d}',
            'monthly_target_quantity': 200 + (i * 50),
            'monthly_feeder_codes': f'WSJ{(i % 2) + 1:03d}',
            'monthly_maker_codes': f'JBJ{(i % 3) + 1:03d}'
        }
        for i in range(5)
    ]
    
    modes = [
        TimelineOptimizationMode.FAST,
        TimelineOptimizationMode.STANDARD,
        TimelineOptimizationMode.BALANCED,
        TimelineOptimizationMode.COMPREHENSIVE
    ]
    
    results = {}
    
    for mode in modes:
        try:
            print(f"\n   测试 {mode.value} 模式...")
            start_time = datetime.now()
            
            result = await generator.generate_timeline(
                test_data, 2024, 1, mode
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            results[mode.value] = {
                'success': True,
                'execution_time': execution_time,
                'scheduled_tasks': len(result.scheduled_tasks),
                'conflicts': len(result.conflicts),
                'optimization_score': result.optimization_metrics.optimization_score if result.optimization_metrics else 0
            }
            
            print(f"   ✅ {mode.value}: {execution_time:.2f}秒, {len(result.scheduled_tasks)}任务, 评分{results[mode.value]['optimization_score']:.1f}")
            
        except Exception as e:
            print(f"   ❌ {mode.value} 失败: {str(e)}")
            results[mode.value] = {'success': False, 'error': str(e)}
    
    return results


async def test_conflict_resolution():
    """测试冲突解决功能"""
    print("\n=== 测试冲突解决功能 ===")
    
    generator = MonthlyTimelineGenerator()
    
    # 创建容易产生冲突的测试数据（同机台同时间）
    conflict_data = [
        {
            'monthly_work_order_nr': 'WO_CONFLICT_1',
            'monthly_article_nr': 'CIG001',
            'monthly_target_quantity': 1000,  # 大数量
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ001',  # 同机台
        },
        {
            'monthly_work_order_nr': 'WO_CONFLICT_2',
            'monthly_article_nr': 'CIG002',
            'monthly_target_quantity': 1200,  # 大数量
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ001',  # 同机台
        }
    ]
    
    try:
        result = await generator.generate_timeline(
            conflict_data, 2024, 1, TimelineOptimizationMode.BALANCED
        )
        
        print(f"   检测到冲突数: {len(result.conflicts)}")
        
        if result.conflicts:
            print(f"   冲突详情:")
            for i, conflict in enumerate(result.conflicts[:3]):  # 只显示前3个
                print(f"   {i+1}. {conflict.conflict_type.value}")
                print(f"      严重程度: {conflict.severity:.1%}")
                print(f"      描述: {conflict.description}")
                print(f"      可自动解决: {'是' if conflict.auto_resolvable else '否'}")
        
        # 测试冲突解决
        print(f"\n   测试冲突解决...")
        resolved_conflicts = await generator.resolve_conflicts(result.conflicts, result.scheduled_tasks)
        print(f"   解决后剩余冲突数: {len(resolved_conflicts)}")
        
        return len(result.conflicts), len(resolved_conflicts)
        
    except Exception as e:
        print(f"   ❌ 冲突解决测试失败: {str(e)}")
        return None, None


async def test_emergency_insertion():
    """测试紧急任务插入功能"""
    print("\n=== 测试紧急任务插入功能 ===")
    
    generator = MonthlyTimelineGenerator()
    
    # 基础调度数据
    base_data = [
        {
            'monthly_work_order_nr': 'WO_BASE_1',
            'monthly_article_nr': 'CIG001',
            'monthly_target_quantity': 300,
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ001'
        },
        {
            'monthly_work_order_nr': 'WO_BASE_2',
            'monthly_article_nr': 'CIG002',
            'monthly_target_quantity': 400,
            'monthly_feeder_codes': 'WSJ001',
            'monthly_maker_codes': 'JBJ001'
        }
    ]
    
    try:
        # 生成基础时间线
        base_result = await generator.generate_timeline(
            base_data, 2024, 1, TimelineOptimizationMode.FAST
        )
        
        print(f"   基础调度任务数: {len(base_result.scheduled_tasks)}")
        
        if base_result.scheduled_tasks:
            # 准备紧急任务
            emergency_task = {
                'task_id': 'EMERGENCY_001',
                'work_order_nr': 'WO_EMERGENCY',
                'article_nr': 'CIG_URGENT',
                'machine_id': 'JBJ001',
                'required_start_time': datetime(2024, 1, 15, 10, 0),
                'required_end_time': datetime(2024, 1, 15, 18, 0),
                'quantity': 200
            }
            
            # 插入紧急任务
            updated_schedule, new_conflicts = await generator.insert_emergency_task(
                emergency_task, base_result.scheduled_tasks, base_result.time_windows
            )
            
            print(f"   插入紧急任务后:")
            print(f"   总任务数: {len(updated_schedule)}")
            print(f"   新增冲突数: {len(new_conflicts)}")
            
            # 查找紧急任务
            emergency_scheduled = [t for t in updated_schedule if t.task_id == 'EMERGENCY_001']
            if emergency_scheduled:
                task = emergency_scheduled[0]
                print(f"   紧急任务已调度:")
                print(f"   时间: {task.start_time} - {task.end_time}")
                print(f"   机台: {task.machine_id}")
                print(f"   优先级: {task.priority.name}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 紧急任务插入测试失败: {str(e)}")
        return False


async def test_statistics_generation():
    """测试统计信息生成"""
    print("\n=== 测试统计信息生成 ===")
    
    generator = MonthlyTimelineGenerator()
    
    # 准备多样化的测试数据
    test_data = [
        {
            'monthly_work_order_nr': f'WO_STAT_{i+1}',
            'monthly_article_nr': f'CIG{(i % 4) + 1:03d}',
            'monthly_target_quantity': 100 + (i * 100),
            'monthly_feeder_codes': f'WSJ{(i % 2) + 1:03d}',
            'monthly_maker_codes': f'JBJ{(i % 3) + 1:03d}'
        }
        for i in range(8)
    ]
    
    try:
        result = await generator.generate_timeline(
            test_data,
            2024, 1,
            TimelineOptimizationMode.BALANCED,
            [TimelineOutputFormat.STATISTICS]
        )
        
        # 获取统计信息
        stats = generator.get_timeline_statistics(result)
        
        print(f"   ✅ 统计信息生成成功!")
        print(f"   基础统计:")
        if 'basic_stats' in stats:
            basic = stats['basic_stats']
            print(f"   总任务数: {basic.get('total_tasks', 0)}")
            print(f"   总机台数: {basic.get('total_machines', 0)}")
            print(f"   时间跨度: {basic.get('timeline_span_hours', 0):.1f}小时")
        
        print(f"   机台利用率:")
        if 'machine_utilization' in stats:
            for machine_id, util in stats['machine_utilization'].items():
                print(f"   {machine_id}: {util:.1f}%")
        
        print(f"   产品统计:")
        if 'product_statistics' in stats:
            for product, product_stats in list(stats['product_statistics'].items())[:3]:
                print(f"   {product}: {product_stats.get('task_count', 0)}任务, {product_stats.get('total_quantity', 0):.0f}数量")
        
        return stats
        
    except Exception as e:
        print(f"   ❌ 统计信息生成失败: {str(e)}")
        return None


async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始月度时间线生成器测试")
    print("=" * 50)
    
    test_results = {}
    
    # 1. 基础功能测试
    basic_result = await test_basic_timeline_generation()
    test_results['basic'] = basic_result is not None
    
    # 2. 优化模式测试
    optimization_results = await test_optimization_modes()
    test_results['optimization_modes'] = len([r for r in optimization_results.values() if r.get('success', False)])
    
    # 3. 冲突解决测试
    initial_conflicts, resolved_conflicts = await test_conflict_resolution()
    test_results['conflict_resolution'] = initial_conflicts is not None
    
    # 4. 紧急任务插入测试
    emergency_success = await test_emergency_insertion()
    test_results['emergency_insertion'] = emergency_success
    
    # 5. 统计信息生成测试
    stats_result = await test_statistics_generation()
    test_results['statistics'] = stats_result is not None
    
    # 总结测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"   基础功能: {'✅ 通过' if test_results['basic'] else '❌ 失败'}")
    print(f"   优化模式: {test_results['optimization_modes']}/4 模式成功")
    print(f"   冲突解决: {'✅ 通过' if test_results['conflict_resolution'] else '❌ 失败'}")
    print(f"   紧急插入: {'✅ 通过' if test_results['emergency_insertion'] else '❌ 失败'}")
    print(f"   统计生成: {'✅ 通过' if test_results['statistics'] else '❌ 失败'}")
    
    total_passed = sum([
        1 if test_results['basic'] else 0,
        1 if test_results['optimization_modes'] >= 3 else 0,  # 至少3个模式成功
        1 if test_results['conflict_resolution'] else 0,
        1 if test_results['emergency_insertion'] else 0,
        1 if test_results['statistics'] else 0
    ])
    
    print(f"\n🎯 总体结果: {total_passed}/5 测试通过")
    
    if total_passed >= 4:
        print("🎉 月度时间线生成器测试基本通过!")
    elif total_passed >= 2:
        print("⚠️  月度时间线生成器部分功能需要改进")
    else:
        print("🔧 月度时间线生成器需要进一步调试")
    
    return test_results


if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_all_tests())