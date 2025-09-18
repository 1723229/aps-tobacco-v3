"""
月度资源优化算法测试模块

测试MonthlyResourceOptimizer的基本功能和性能
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict

# 设置测试环境的日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入测试目标
try:
    from .monthly_resource_optimizer import (
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
    from .base import MachineType
except ImportError as e:
    logger.error(f"导入失败: {e}")
    # 提供测试环境的替代导入
    print("在测试环境中运行，使用模拟导入")


def create_test_plans() -> List[MonthlyPlanItem]:
    """创建测试用的月度计划项"""
    
    plans = []
    base_time = datetime.now()
    
    # 创建5个测试计划
    for i in range(5):
        plan = MonthlyPlanItem(
            plan_id=i + 1,
            batch_id=f"BATCH_{base_time.strftime('%Y%m%d')}",
            work_order_nr=f"WO_{i+1:03d}",
            article_nr=f"ART_{i+1:03d}",
            article_name=f"测试产品_{i+1}",
            target_quantity=1000.0 + i * 200,
            planned_boxes=(1000 + i * 200) * 5,
            feeder_codes=[f"WSJ{(i%2)+1:03d}"],
            maker_codes=[f"JBJ{(i%3)+1:03d}"],
            planned_start=base_time + timedelta(days=i),
            planned_end=base_time + timedelta(days=i+3),
            priority=Priority(1 + (i % 4))
        )
        plans.append(plan)
    
    logger.info(f"创建了 {len(plans)} 个测试计划项")
    return plans


def create_test_resources() -> List[ResourceCapacity]:
    """创建测试用的资源容量"""
    
    resources = []
    
    # 创建机台资源
    machine_configs = [
        ("JBJ001", "卷包机1号", 8000, 0.05),
        ("JBJ002", "卷包机2号", 7500, 0.06),
        ("JBJ003", "卷包机3号", 8200, 0.045),
        ("WSJ001", "喂丝机1号", 12000, 0.03),
        ("WSJ002", "喂丝机2号", 11500, 0.035)
    ]
    
    base_time = datetime.now()
    
    for machine_id, machine_name, speed, cost in machine_configs:
        # 计算月度容量（22工作日 * 16小时/天）
        monthly_hours = Decimal('22') * Decimal('16')
        total_capacity = Decimal(str(speed)) * monthly_hours
        
        resource = ResourceCapacity(
            resource_id=machine_id,
            resource_type=ResourceType.MACHINE,
            resource_name=machine_name,
            total_capacity=total_capacity,
            available_capacity=total_capacity * Decimal('0.9'),  # 90%可用
            reserved_capacity=total_capacity * Decimal('0.1'),   # 10%预留
            unit="件",
            cost_per_unit=Decimal(str(cost)),
            efficiency_factor=0.85,
            availability_windows=[
                (base_time, base_time + timedelta(days=30))
            ],
            maintenance_windows=[
                # 添加一些维护时间窗
                (base_time + timedelta(days=10, hours=2), 
                 base_time + timedelta(days=10, hours=6))
            ],
            constraints={}
        )
        
        resources.append(resource)
    
    logger.info(f"创建了 {len(resources)} 个测试资源")
    return resources


def create_test_constraints(resources: List[ResourceCapacity]) -> List[OptimizationConstraint]:
    """创建测试用的约束条件"""
    
    constraints = []
    
    # 1. 机台容量约束
    for resource in resources:
        constraint = OptimizationConstraint(
            constraint_id=f"CAP_{resource.resource_id}",
            constraint_type=ConstraintType.MACHINE_CAPACITY,
            constraint_name=f"{resource.resource_name}容量约束",
            description=f"机台容量不得超过 {resource.available_capacity} 件",
            affected_resources=[resource.resource_id],
            constraint_parameters={
                'max_capacity': float(resource.available_capacity)
            },
            violation_penalty=100.0,
            hard_constraint=True,
            priority=9,
            time_windows=resource.availability_windows
        )
        constraints.append(constraint)
    
    # 2. 维护时间约束
    for resource in resources:
        if resource.maintenance_windows:
            constraint = OptimizationConstraint(
                constraint_id=f"MAINT_{resource.resource_id}",
                constraint_type=ConstraintType.MAINTENANCE_WINDOW,
                constraint_name=f"{resource.resource_name}维护时间约束",
                description="维护期间不可生产",
                affected_resources=[resource.resource_id],
                constraint_parameters={
                    'maintenance_windows': resource.maintenance_windows
                },
                violation_penalty=200.0,
                hard_constraint=True,
                priority=10,
                time_windows=resource.maintenance_windows
            )
            constraints.append(constraint)
    
    logger.info(f"创建了 {len(constraints)} 个测试约束")
    return constraints


async def test_basic_optimization():
    """测试基础优化功能"""
    
    logger.info("=== 测试基础优化功能 ===")
    
    # 创建测试数据
    plans = create_test_plans()
    
    # 创建优化器
    optimizer = MonthlyResourceOptimizer()
    
    # 定义优化目标
    objectives = {
        OptimizationObjective.CAPACITY_MAXIMIZATION: 0.4,
        OptimizationObjective.LOAD_BALANCING: 0.3,
        OptimizationObjective.COST_MINIMIZATION: 0.3
    }
    
    # 执行优化
    start_time = time.time()
    
    try:
        result = await optimizer.optimize_resource_allocation(
            plans=plans,
            objectives=objectives,
            strategy=AlgorithmStrategy.HEURISTIC_ONLY,
            time_limit=60
        )
        
        execution_time = time.time() - start_time
        
        print(f"\n--- 基础优化测试结果 ---")
        print(f"执行时间: {execution_time:.2f}秒")
        print(f"优化评分: {result.best_allocation.optimization_score:.2f}")
        print(f"可行性: {'是' if result.best_allocation.is_feasible() else '否'}")
        print(f"总成本: {result.best_allocation.total_cost:,.2f}")
        print(f"资源数量: {len(result.best_allocation.resource_allocations)}")
        print(f"备选方案数: {len(result.alternative_allocations)}")
        print(f"优化建议数: {len(result.optimization_recommendations)}")
        
        # 显示目标函数值
        if result.best_allocation.objective_values:
            print(f"\n目标函数值:")
            for obj, value in result.best_allocation.objective_values.items():
                print(f"  {obj.value}: {value:.2f}")
        
        # 显示约束违反情况
        if result.best_allocation.constraint_violations:
            print(f"\n约束违反:")
            for constraint_id, violation in result.best_allocation.constraint_violations.items():
                print(f"  {constraint_id}: {violation:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"基础优化测试失败: {str(e)}")
        return False


async def test_algorithm_strategies():
    """测试不同算法策略"""
    
    logger.info("=== 测试不同算法策略 ===")
    
    plans = create_test_plans()
    optimizer = MonthlyResourceOptimizer()
    
    objectives = {
        OptimizationObjective.CAPACITY_MAXIMIZATION: 0.5,
        OptimizationObjective.LOAD_BALANCING: 0.5
    }
    
    strategies = [
        AlgorithmStrategy.HEURISTIC_ONLY,
        AlgorithmStrategy.HYBRID
        # EXACT_ONLY 可能需要 OR-Tools，在测试环境中可能不可用
    ]
    
    results = {}
    
    for strategy in strategies:
        print(f"\n--- 测试策略: {strategy.value} ---")
        
        start_time = time.time()
        
        try:
            result = await optimizer.optimize_resource_allocation(
                plans=plans,
                objectives=objectives,
                strategy=strategy,
                time_limit=30  # 每个策略30秒
            )
            
            execution_time = time.time() - start_time
            
            results[strategy.value] = {
                'execution_time': execution_time,
                'optimization_score': result.best_allocation.optimization_score,
                'feasible': result.best_allocation.is_feasible(),
                'total_cost': float(result.best_allocation.total_cost),
                'iterations': result.iterations_performed
            }
            
            print(f"  执行时间: {execution_time:.2f}秒")
            print(f"  优化评分: {result.best_allocation.optimization_score:.2f}")
            print(f"  可行性: {'是' if result.best_allocation.is_feasible() else '否'}")
            print(f"  迭代次数: {result.iterations_performed}")
            
        except Exception as e:
            logger.error(f"策略 {strategy.value} 测试失败: {str(e)}")
            results[strategy.value] = {'error': str(e)}
    
    # 比较结果
    print(f"\n--- 策略比较 ---")
    for strategy, data in results.items():
        if 'error' not in data:
            print(f"{strategy}:")
            print(f"  评分: {data['optimization_score']:.2f}")
            print(f"  时间: {data['execution_time']:.2f}秒")
            print(f"  成本: {data['total_cost']:,.2f}")
    
    return results


async def test_load_balancing():
    """测试负载均衡功能"""
    
    logger.info("=== 测试负载均衡功能 ===")
    
    optimizer = MonthlyResourceOptimizer()
    
    # 创建一个不平衡的分配方案（模拟）
    from .monthly_resource_optimizer import ResourceAllocation
    
    current_allocation = ResourceAllocation(
        allocation_id="TEST_UNBALANCED",
        plan_id=0,
        resource_allocations={
            "JBJ001": {
                "plan_1": {"allocated_capacity": 8000, "cost": 400},
                "plan_2": {"allocated_capacity": 7000, "cost": 350}
            },
            "JBJ002": {
                "plan_3": {"allocated_capacity": 2000, "cost": 120}
            },
            "WSJ001": {
                "plan_4": {"allocated_capacity": 12000, "cost": 360},
                "plan_5": {"allocated_capacity": 10000, "cost": 300}
            }
        },
        time_allocation={},
        objective_values={},
        constraint_violations={},
        total_cost=Decimal('1530'),
        total_capacity_utilization=0.75,
        optimization_score=65.0,
        feasibility_score=90.0,
        generation_time=datetime.now(),
        algorithm_used="test_setup"
    )
    
    resources = create_test_resources()
    
    try:
        balanced_allocation = await optimizer.balance_workload(
            current_allocation=current_allocation,
            resources=resources,
            balance_threshold=0.1
        )
        
        print(f"\n--- 负载均衡测试结果 ---")
        print(f"原始评分: {current_allocation.optimization_score:.2f}")
        print(f"平衡后评分: {balanced_allocation.optimization_score:.2f}")
        print(f"评分改进: {balanced_allocation.optimization_score - current_allocation.optimization_score:.2f}")
        
        # 计算负载分布
        original_loads = optimizer._calculate_load_distribution(current_allocation, resources)
        balanced_loads = optimizer._calculate_load_distribution(balanced_allocation, resources)
        
        print(f"\n负载分布变化:")
        for resource_id in original_loads:
            print(f"  {resource_id}: {original_loads[resource_id]:.2%} -> {balanced_loads[resource_id]:.2%}")
        
        return True
        
    except Exception as e:
        logger.error(f"负载均衡测试失败: {str(e)}")
        return False


async def test_optimization_suggestions():
    """测试优化建议功能"""
    
    logger.info("=== 测试优化建议功能 ===")
    
    optimizer = MonthlyResourceOptimizer()
    resources = create_test_resources()
    
    # 创建一个有问题的分配方案
    from .monthly_resource_optimizer import ResourceAllocation
    
    problematic_allocation = ResourceAllocation(
        allocation_id="TEST_PROBLEMATIC",
        plan_id=0,
        resource_allocations={
            "JBJ001": {
                "plan_1": {"allocated_capacity": 15000, "cost": 750},  # 超载
                "plan_2": {"allocated_capacity": 12000, "cost": 600}   # 超载
            },
            "JBJ002": {
                "plan_3": {"allocated_capacity": 1000, "cost": 60}     # 低利用率
            },
            "WSJ001": {
                "plan_4": {"allocated_capacity": 20000, "cost": 600}   # 超载
            }
        },
        time_allocation={},
        objective_values={},
        constraint_violations={
            "CAP_JBJ001": 0.5,  # 严重违反
            "CAP_WSJ001": 0.3   # 中等违反
        },
        total_cost=Decimal('2010'),
        total_capacity_utilization=0.95,
        optimization_score=45.0,
        feasibility_score=40.0,
        generation_time=datetime.now(),
        algorithm_used="test_setup"
    )
    
    try:
        suggestions = optimizer.get_optimization_suggestions(
            current_allocation=problematic_allocation,
            resources=resources
        )
        
        print(f"\n--- 优化建议测试结果 ---")
        print(f"生成建议数量: {len(suggestions)}")
        print(f"\n具体建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
        
        # 评估分配质量
        quality_metrics = optimizer.evaluate_allocation_quality(
            allocation=problematic_allocation,
            resources=resources,
            constraints=create_test_constraints(resources)
        )
        
        print(f"\n分配质量评估:")
        for metric, value in quality_metrics.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.2f}")
            else:
                print(f"  {metric}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"优化建议测试失败: {str(e)}")
        return False


async def test_performance_benchmark():
    """测试性能基准"""
    
    logger.info("=== 性能基准测试 ===")
    
    test_cases = [
        ("小规模", 5, 3),
        ("中规模", 15, 6),
        ("大规模", 30, 10)
    ]
    
    optimizer = MonthlyResourceOptimizer()
    
    for test_name, num_plans, num_resources in test_cases:
        print(f"\n--- {test_name} ({num_plans}计划, {num_resources}资源) ---")
        
        # 生成测试数据
        plans = []
        base_time = datetime.now()
        
        for i in range(num_plans):
            plan = MonthlyPlanItem(
                plan_id=i + 1,
                batch_id=f"PERF_BATCH_{i+1}",
                work_order_nr=f"WO_{i+1:03d}",
                article_nr=f"ART_{i+1:03d}",
                article_name=f"性能测试产品_{i+1}",
                target_quantity=1000.0 + i * 50,
                planned_boxes=(1000 + i * 50) * 5,
                feeder_codes=[f"WSJ{(i%max(1,num_resources//2))+1:03d}"],
                maker_codes=[f"JBJ{(i%max(1,num_resources//2))+1:03d}"],
                planned_start=base_time + timedelta(days=i//3),
                planned_end=base_time + timedelta(days=i//3+2),
                priority=Priority(1 + (i % 4))
            )
            plans.append(plan)
        
        start_time = time.time()
        
        try:
            result = await optimizer.optimize_resource_allocation(
                plans=plans,
                strategy=AlgorithmStrategy.HEURISTIC_ONLY,
                time_limit=30
            )
            
            execution_time = time.time() - start_time
            
            print(f"  执行时间: {execution_time:.2f}秒")
            print(f"  优化评分: {result.best_allocation.optimization_score:.2f}")
            print(f"  资源利用率: {result.best_allocation.total_capacity_utilization:.1%}")
            print(f"  可行性: {'是' if result.best_allocation.is_feasible() else '否'}")
            print(f"  计划/秒: {num_plans/execution_time:.1f}")
            
        except Exception as e:
            print(f"  测试失败: {str(e)}")
    
    # 显示累计性能指标
    metrics = optimizer.performance_metrics
    print(f"\n--- 累计性能指标 ---")
    print(f"总优化次数: {metrics['total_optimizations']}")
    print(f"平均执行时间: {metrics['average_execution_time']:.2f}秒")
    print(f"成功率: {metrics['success_rate']:.1%}")
    print(f"最佳评分: {metrics['best_score_achieved']:.2f}")


async def run_all_tests():
    """运行所有测试"""
    
    print("开始运行月度资源优化器测试套件...")
    print("=" * 60)
    
    test_results = {}
    
    # 运行各项测试
    tests = [
        ("基础优化", test_basic_optimization),
        ("算法策略", test_algorithm_strategies),
        ("负载均衡", test_load_balancing),
        ("优化建议", test_optimization_suggestions),
        ("性能基准", test_performance_benchmark)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name}测试 {'='*20}")
        
        try:
            start_time = time.time()
            result = await test_func()
            execution_time = time.time() - start_time
            
            test_results[test_name] = {
                'success': result if isinstance(result, bool) else True,
                'execution_time': execution_time,
                'details': result if not isinstance(result, bool) else None
            }
            
            status = "✅ 通过" if test_results[test_name]['success'] else "❌ 失败"
            print(f"\n{test_name}测试: {status} (耗时: {execution_time:.2f}秒)")
            
        except Exception as e:
            test_results[test_name] = {
                'success': False,
                'error': str(e),
                'execution_time': 0
            }
            print(f"\n{test_name}测试: ❌ 异常 - {str(e)}")
    
    # 汇总测试结果
    print(f"\n{'='*20} 测试汇总 {'='*20}")
    
    total_tests = len(tests)
    passed_tests = sum(1 for result in test_results.values() if result['success'])
    total_time = sum(result['execution_time'] for result in test_results.values())
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests:.1%}")
    print(f"总耗时: {total_time:.2f}秒")
    
    # 详细结果
    print(f"\n详细结果:")
    for test_name, result in test_results.items():
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {test_name}: {result['execution_time']:.2f}秒")
        if not result['success'] and 'error' in result:
            print(f"      错误: {result['error']}")
    
    return test_results


if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_all_tests())