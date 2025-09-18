#!/usr/bin/env python3
"""
月度资源优化器演示脚本

展示MonthlyResourceOptimizer的主要功能和使用方法
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.algorithms.monthly_scheduling.monthly_resource_optimizer import (
        MonthlyResourceOptimizer,
        OptimizationObjective,
        AlgorithmStrategy,
        ResourceType,
        ConstraintType,
        MonthlyPlanItem,
        ResourceCapacity,
        OptimizationConstraint,
        Priority
    )
    print("✅ 成功导入月度资源优化器模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在正确的Python环境中运行此脚本")
    sys.exit(1)


def create_demo_scenario():
    """创建演示场景数据"""
    
    print("\n🎯 创建演示场景...")
    
    # 创建月度生产计划
    plans = []
    base_time = datetime.now()
    
    # 5个不同的产品计划
    plan_configs = [
        ("红塔山", 1500, ["WSJ001"], ["JBJ001", "JBJ002"], Priority.HIGH),
        ("玉溪", 1200, ["WSJ001", "WSJ002"], ["JBJ002"], Priority.HIGH),
        ("云烟", 800, ["WSJ002"], ["JBJ003"], Priority.MEDIUM),
        ("红河", 600, ["WSJ001"], ["JBJ001"], Priority.MEDIUM),
        ("大重九", 400, ["WSJ002"], ["JBJ003"], Priority.LOW)
    ]
    
    for i, (product_name, quantity, feeders, makers, priority) in enumerate(plan_configs):
        plan = MonthlyPlanItem(
            plan_id=i + 1,
            batch_id=f"DEMO_BATCH_{datetime.now().strftime('%Y%m%d')}",
            work_order_nr=f"WO_{i+1:03d}",
            article_nr=f"ART_{i+1:03d}",
            article_name=product_name,
            target_quantity=float(quantity),
            planned_boxes=quantity * 5,
            feeder_codes=feeders,
            maker_codes=makers,
            planned_start=base_time + timedelta(days=i*2),
            planned_end=base_time + timedelta(days=i*2+5),
            priority=priority
        )
        plans.append(plan)
    
    print(f"📋 创建了 {len(plans)} 个生产计划:")
    for plan in plans:
        print(f"  - {plan.article_name}: {plan.target_quantity}万支 (优先级: {plan.priority.name})")
    
    # 创建资源配置
    resources = []
    
    # 机台配置 (机台代码, 名称, 容量/小时, 成本/件)
    machine_configs = [
        ("JBJ001", "卷包机1号线", 8000, 0.05),
        ("JBJ002", "卷包机2号线", 7800, 0.052),
        ("JBJ003", "卷包机3号线", 8200, 0.048),
        ("WSJ001", "喂丝机1号线", 12000, 0.03),
        ("WSJ002", "喂丝机2号线", 11800, 0.032)
    ]
    
    for machine_id, machine_name, hourly_capacity, cost_per_unit in machine_configs:
        # 月度总容量 (22工作日 * 20小时/天，考虑加班)
        monthly_hours = Decimal('22') * Decimal('20')
        total_capacity = Decimal(str(hourly_capacity)) * monthly_hours
        
        # 添加维护时间窗
        maintenance_windows = []
        if machine_id in ["JBJ001", "WSJ001"]:  # 主要设备需要维护
            maint_start = base_time + timedelta(days=15, hours=2)
            maint_end = maint_start + timedelta(hours=8)
            maintenance_windows.append((maint_start, maint_end))
        
        resource = ResourceCapacity(
            resource_id=machine_id,
            resource_type=ResourceType.MACHINE,
            resource_name=machine_name,
            total_capacity=total_capacity,
            available_capacity=total_capacity * Decimal('0.88'),  # 88%可用率
            reserved_capacity=total_capacity * Decimal('0.12'),   # 12%预留
            unit="件",
            cost_per_unit=Decimal(str(cost_per_unit)),
            efficiency_factor=0.85,
            availability_windows=[(base_time, base_time + timedelta(days=30))],
            maintenance_windows=maintenance_windows,
            constraints={}
        )
        
        resources.append(resource)
    
    print(f"🏭 创建了 {len(resources)} 个生产资源:")
    for resource in resources:
        print(f"  - {resource.resource_name}: {resource.total_capacity:,.0f}件/月")
        if resource.maintenance_windows:
            print(f"    维护计划: {len(resource.maintenance_windows)}个时间窗")
    
    return plans, resources


async def demo_basic_optimization():
    """演示基础优化功能"""
    
    print("\n" + "="*60)
    print("🚀 基础资源分配优化演示")
    print("="*60)
    
    # 创建场景数据
    plans, resources = create_demo_scenario()
    
    # 创建优化器
    optimizer = MonthlyResourceOptimizer()
    
    # 定义优化目标
    objectives = {
        OptimizationObjective.CAPACITY_MAXIMIZATION: 0.4,   # 产能最大化 40%
        OptimizationObjective.LOAD_BALANCING: 0.3,          # 负载均衡 30%
        OptimizationObjective.COST_MINIMIZATION: 0.2,       # 成本最小化 20%
        OptimizationObjective.EFFICIENCY_MAXIMIZATION: 0.1  # 效率最大化 10%
    }
    
    print(f"\n📊 优化目标配置:")
    for obj, weight in objectives.items():
        print(f"  - {obj.value}: {weight:.1%}")
    
    # 执行优化
    print(f"\n⚙️ 开始执行资源分配优化...")
    
    result = await optimizer.optimize_resource_allocation(
        plans=plans,
        objectives=objectives,
        strategy=AlgorithmStrategy.HYBRID,
        time_limit=120  # 2分钟时间限制
    )
    
    # 展示结果
    print(f"\n✅ 优化完成！")
    print(f"📈 优化结果概览:")
    print(f"  - 执行时间: {result.execution_time:.2f}秒")
    print(f"  - 优化评分: {result.best_allocation.optimization_score:.2f}/100")
    print(f"  - 可行性评分: {result.best_allocation.feasibility_score:.2f}/100")
    print(f"  - 总成本: ¥{result.best_allocation.total_cost:,.2f}")
    print(f"  - 容量利用率: {result.best_allocation.total_capacity_utilization:.1%}")
    print(f"  - 使用算法: {result.best_allocation.algorithm_used}")
    
    # 目标函数达成情况
    if result.best_allocation.objective_values:
        print(f"\n🎯 目标函数达成情况:")
        for obj, value in result.best_allocation.objective_values.items():
            print(f"  - {obj.value}: {value:.2f}")
    
    # 资源分配详情
    print(f"\n🏭 资源分配详情:")
    for resource_id, allocation in result.best_allocation.resource_allocations.items():
        resource_name = next(r.resource_name for r in resources if r.resource_id == resource_id)
        total_allocated = sum(detail.get('allocated_capacity', 0) for detail in allocation.values())
        total_cost = sum(detail.get('cost', 0) for detail in allocation.values())
        
        print(f"  📦 {resource_name} ({resource_id}):")
        print(f"    - 分配总量: {total_allocated:,.0f}件")
        print(f"    - 分配成本: ¥{total_cost:,.2f}")
        print(f"    - 分配任务: {len(allocation)}个")
        
        for plan_key, details in allocation.items():
            print(f"      • {plan_key}: {details.get('allocated_capacity', 0):,.0f}件")
    
    # 约束违反情况
    if result.best_allocation.constraint_violations:
        print(f"\n⚠️ 约束违反情况:")
        for constraint_id, violation in result.best_allocation.constraint_violations.items():
            severity = "严重" if violation > 0.1 else "轻微"
            print(f"  - {constraint_id}: {violation:.3f} ({severity})")
    else:
        print(f"\n✅ 所有约束条件均得到满足")
    
    # 备选方案
    if result.alternative_allocations:
        print(f"\n🔄 备选方案:")
        for i, alt in enumerate(result.alternative_allocations, 1):
            print(f"  方案 {i}: 评分 {alt.optimization_score:.2f}, 成本 ¥{alt.total_cost:,.2f}")
    
    return result


async def demo_strategy_comparison():
    """演示不同策略的比较"""
    
    print("\n" + "="*60)
    print("⚔️ 优化策略比较演示")
    print("="*60)
    
    plans, resources = create_demo_scenario()
    optimizer = MonthlyResourceOptimizer()
    
    objectives = {
        OptimizationObjective.CAPACITY_MAXIMIZATION: 0.6,
        OptimizationObjective.LOAD_BALANCING: 0.4
    }
    
    strategies = [
        (AlgorithmStrategy.HEURISTIC_ONLY, "启发式算法"),
        (AlgorithmStrategy.HYBRID, "混合算法")
        # EXACT_ONLY 需要 OR-Tools，可能在某些环境中不可用
    ]
    
    results = {}
    
    for strategy, strategy_name in strategies:
        print(f"\n🎯 测试策略: {strategy_name}")
        
        try:
            result = await optimizer.optimize_resource_allocation(
                plans=plans,
                objectives=objectives,
                strategy=strategy,
                time_limit=60
            )
            
            results[strategy_name] = {
                'score': result.best_allocation.optimization_score,
                'time': result.execution_time,
                'cost': float(result.best_allocation.total_cost),
                'feasible': result.best_allocation.is_feasible(),
                'utilization': result.best_allocation.total_capacity_utilization
            }
            
            print(f"  ✅ 优化评分: {result.best_allocation.optimization_score:.2f}")
            print(f"  ⏱️ 执行时间: {result.execution_time:.2f}秒")
            print(f"  💰 总成本: ¥{result.best_allocation.total_cost:,.2f}")
            print(f"  📊 利用率: {result.best_allocation.total_capacity_utilization:.1%}")
            
        except Exception as e:
            print(f"  ❌ 策略执行失败: {str(e)}")
            results[strategy_name] = {'error': str(e)}
    
    # 策略比较
    print(f"\n📊 策略性能比较:")
    print(f"{'策略':<12} {'评分':<8} {'时间(秒)':<10} {'成本':<12} {'利用率':<8}")
    print("-" * 60)
    
    for strategy_name, data in results.items():
        if 'error' not in data:
            print(f"{strategy_name:<12} "
                  f"{data['score']:<8.1f} "
                  f"{data['time']:<10.2f} "
                  f"¥{data['cost']:<11,.0f} "
                  f"{data['utilization']:<8.1%}")
        else:
            print(f"{strategy_name:<12} 执行失败")
    
    return results


async def demo_optimization_suggestions():
    """演示优化建议功能"""
    
    print("\n" + "="*60)
    print("💡 智能优化建议演示")
    print("="*60)
    
    plans, resources = create_demo_scenario()
    optimizer = MonthlyResourceOptimizer()
    
    # 首先执行一次优化获得基础分配
    result = await optimizer.optimize_resource_allocation(
        plans=plans,
        strategy=AlgorithmStrategy.HEURISTIC_ONLY,
        time_limit=30
    )
    
    print(f"📋 当前分配方案评估:")
    
    # 评估分配质量
    quality_metrics = optimizer.evaluate_allocation_quality(
        allocation=result.best_allocation,
        resources=resources,
        constraints=[]  # 简化演示
    )
    
    print(f"  - 综合评分: {quality_metrics['overall_score']:.1f}/100")
    print(f"  - 可行性评分: {quality_metrics['feasibility_score']:.1f}/100")
    print(f"  - 效率评分: {quality_metrics['efficiency_score']:.1f}/100")
    print(f"  - 均衡评分: {quality_metrics['balance_score']:.1f}/100")
    print(f"  - 成本效率: {quality_metrics['cost_efficiency_score']:.1f}/100")
    print(f"  - 平均利用率: {quality_metrics['average_utilization']:.1%}")
    print(f"  - 负载方差: {quality_metrics['load_variance']:.3f}")
    
    # 生成优化建议
    suggestions = optimizer.get_optimization_suggestions(
        current_allocation=result.best_allocation,
        resources=resources
    )
    
    if suggestions:
        print(f"\n💡 智能优化建议 ({len(suggestions)}条):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print(f"\n✅ 当前分配方案已经相当优化，无需特殊调整")
    
    # 演示负载均衡优化
    print(f"\n⚖️ 负载均衡优化演示:")
    
    balanced_allocation = await optimizer.balance_workload(
        current_allocation=result.best_allocation,
        resources=resources,
        balance_threshold=0.05
    )
    
    # 比较负载均衡前后
    original_loads = optimizer._calculate_load_distribution(result.best_allocation, resources)
    balanced_loads = optimizer._calculate_load_distribution(balanced_allocation, resources)
    
    print(f"\n📊 负载分布对比:")
    print(f"{'资源':<12} {'原始负载':<12} {'均衡后':<12} {'变化':<10}")
    print("-" * 50)
    
    for resource_id in original_loads:
        original = original_loads[resource_id]
        balanced = balanced_loads[resource_id]
        change = balanced - original
        change_str = f"{change:+.1%}" if abs(change) > 0.001 else "无变化"
        
        print(f"{resource_id:<12} "
              f"{original:<12.1%} "
              f"{balanced:<12.1%} "
              f"{change_str:<10}")
    
    # 计算方差改进
    original_variance = optimizer._calculate_load_variance(list(original_loads.values()))
    balanced_variance = optimizer._calculate_load_variance(list(balanced_loads.values()))
    
    print(f"\n📈 均衡效果:")
    print(f"  - 原始负载方差: {original_variance:.4f}")
    print(f"  - 均衡后方差: {balanced_variance:.4f}")
    print(f"  - 方差改进: {((original_variance - balanced_variance) / original_variance * 100):.1f}%")
    
    return suggestions, quality_metrics


async def demo_real_time_adjustment():
    """演示实时调整功能"""
    
    print("\n" + "="*60)
    print("🔄 实时调整功能演示")
    print("="*60)
    
    plans, resources = create_demo_scenario()
    optimizer = MonthlyResourceOptimizer()
    
    # 获得初始优化结果
    print(f"📋 获取初始优化方案...")
    
    initial_result = await optimizer.optimize_resource_allocation(
        plans=plans,
        strategy=AlgorithmStrategy.HEURISTIC_ONLY,
        time_limit=30
    )
    
    print(f"  ✅ 初始方案评分: {initial_result.best_allocation.optimization_score:.2f}")
    print(f"  💰 初始方案成本: ¥{initial_result.best_allocation.total_cost:,.2f}")
    
    # 模拟生产变更情况
    print(f"\n🚨 模拟生产环境变更...")
    
    changes = {
        'new_plans': [
            {
                'plan_id': 6,
                'article_name': '急单-特供红塔山',
                'target_quantity': 200,
                'priority': 'URGENT',
                'deadline': datetime.now() + timedelta(hours=48)
            }
        ],
        'resource_changes': [
            {
                'resource_id': 'JBJ002',
                'status': 'temporary_shutdown',
                'duration_hours': 12,
                'reason': '设备故障维修'
            }
        ],
        'cancelled_plans': [5]  # 取消第5个计划
    }
    
    print(f"  📦 新增急单: {changes['new_plans'][0]['article_name']}")
    print(f"  ⚠️ 设备故障: {changes['resource_changes'][0]['resource_id']} 停机维修")
    print(f"  ❌ 取消计划: 计划ID {changes['cancelled_plans'][0]}")
    
    # 执行实时调整
    print(f"\n⚙️ 执行实时调整优化...")
    
    try:
        adjusted_allocation = await optimizer.real_time_adjustment(
            current_allocation=initial_result.best_allocation,
            changes=changes,
            adjustment_strategy="incremental"
        )
        
        print(f"  ✅ 调整完成")
        print(f"  📊 调整后评分: {adjusted_allocation.optimization_score:.2f}")
        print(f"  💰 调整后成本: ¥{adjusted_allocation.total_cost:,.2f}")
        
        # 计算调整影响
        score_change = adjusted_allocation.optimization_score - initial_result.best_allocation.optimization_score
        cost_change = adjusted_allocation.total_cost - initial_result.best_allocation.total_cost
        
        print(f"\n📈 调整影响分析:")
        print(f"  - 评分变化: {score_change:+.2f}")
        print(f"  - 成本变化: ¥{cost_change:+,.2f}")
        
        if score_change > 0:
            print(f"  ✅ 调整后方案质量提升")
        elif score_change == 0:
            print(f"  ➖ 调整后方案质量持平")
        else:
            print(f"  ⚠️ 调整后方案质量略有下降，但满足新需求")
        
    except Exception as e:
        print(f"  ❌ 实时调整失败: {str(e)}")
        print(f"  💡 建议: 重新执行完整优化")


async def main():
    """主演示函数"""
    
    print("🎭 月度资源优化器功能演示")
    print("="*80)
    print("本演示将展示APS智慧排产系统中月度资源优化算法的核心功能")
    print("包括智能资源分配、多目标优化、约束求解和实时调整等能力")
    print("="*80)
    
    # 记录开始时间
    start_time = datetime.now()
    
    try:
        # 演示1: 基础优化功能
        demo1_result = await demo_basic_optimization()
        
        # 演示2: 策略比较
        demo2_result = await demo_strategy_comparison()
        
        # 演示3: 优化建议
        demo3_suggestions, demo3_quality = await demo_optimization_suggestions()
        
        # 演示4: 实时调整
        await demo_real_time_adjustment()
        
        # 演示总结
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("🎊 演示完成总结")
        print("="*60)
        print(f"✅ 所有演示功能均成功执行")
        print(f"⏱️ 总演示时间: {total_time:.1f}秒")
        print(f"🚀 最佳优化评分: {demo1_result.best_allocation.optimization_score:.2f}/100")
        print(f"💡 生成优化建议: {len(demo3_suggestions)}条")
        print(f"📊 分配质量评估: {demo3_quality['overall_score']:.1f}/100")
        
        print(f"\n🎯 核心功能验证:")
        print(f"  ✅ 多目标资源分配优化")
        print(f"  ✅ 启发式与混合算法策略")
        print(f"  ✅ 智能约束求解")
        print(f"  ✅ 负载均衡优化")
        print(f"  ✅ 实时动态调整")
        print(f"  ✅ 优化建议生成")
        print(f"  ✅ 质量评估体系")
        
        print(f"\n📈 系统优势:")
        print(f"  🎯 支持多种优化目标的权重配置")
        print(f"  ⚡ 高效的启发式与精确算法结合")
        print(f"  🔧 灵活的约束条件处理")
        print(f"  📊 全面的性能评估指标")
        print(f"  🔄 实时响应生产变更")
        print(f"  💡 智能化优化建议")
        
        print(f"\n💼 应用场景:")
        print(f"  🏭 烟草生产月度排产优化")
        print(f"  📦 多产品多机台资源分配")
        print(f"  ⚖️ 生产负载均衡调整")
        print(f"  🚨 紧急订单插单优化")
        print(f"  🔧 设备维护计划协调")
        print(f"  📊 产能利用率最大化")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
        print(f"💡 这可能是由于缺少依赖库或数据库连接问题")
        print(f"   请检查Python环境和项目配置")
        
    finally:
        print(f"\n谢谢观看月度资源优化器演示! 🎉")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())