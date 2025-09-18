#!/usr/bin/env python3
"""
月度约束求解算法演示脚本

展示MonthlyConstraintSolver的主要功能：
- 约束建模和求解
- 多种求解策略对比
- 约束冲突分析
- 解决方案验证和优化建议
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.algorithms.monthly_scheduling.monthly_constraint_solver import (
    MonthlyConstraintSolver,
    Constraint,
    ConstraintType,
    ConstraintPriority,
    SolverStrategy,
    OptimizationConfig,
    TimeWindow,
    ViolationType
)
from app.algorithms.monthly_scheduling.base import (
    MonthlyPlanItem,
    Priority
)


async def demonstrate_constraint_solver():
    """演示约束求解器的主要功能"""
    
    print("=" * 80)
    print("🏭 APS烟草生产月度约束求解算法演示")
    print("=" * 80)
    print()
    
    # 1. 创建求解器实例
    print("1️⃣ 创建月度约束求解器")
    solver = MonthlyConstraintSolver()
    print(f"   ✅ 求解器类型: {solver.algorithm_type.value}")
    print(f"   ✅ 支持的求解策略: {len(solver.solvers)}种")
    print()
    
    # 2. 创建示例月度计划
    print("2️⃣ 创建示例月度生产计划")
    monthly_plans = []
    base_time = datetime.now()
    
    for i in range(1, 4):
        plan = MonthlyPlanItem(
            plan_id=i,
            batch_id=f'MONTHLY_2024_{i:02d}',
            work_order_nr=f'WO_2024_{i:03d}',
            article_nr=f'ZS_{i:03d}',
            article_name=f'中华香烟_{i}号',
            target_quantity=15000.0 + i * 5000,
            planned_boxes=(15000 + i * 5000) * 5,
            feeder_codes=[f'WSJ{(i-1)%2+1:03d}'],
            maker_codes=[f'JBJ{(i-1)%3+1:03d}'],
            planned_start=base_time + timedelta(days=i*2),
            planned_end=base_time + timedelta(days=i*2+5),
            priority=Priority.HIGH if i == 1 else Priority.MEDIUM
        )
        monthly_plans.append(plan)
        print(f"   📋 计划{i}: {plan.article_name}, 目标产量: {plan.target_quantity:,.0f}万支")
    
    print()
    
    # 3. 创建约束条件
    print("3️⃣ 构建约束条件模型")
    constraints = []
    
    # 3.1 机台容量约束
    machine_constraints = [
        ('JBJ001', '卷包机001', 80000),
        ('JBJ002', '卷包机002', 75000),
        ('JBJ003', '卷包机003', 70000),
        ('WSJ001', '喂丝机001', 120000),
        ('WSJ002', '喂丝机002', 110000)
    ]
    
    for machine_id, machine_name, capacity in machine_constraints:
        applicable_plans = []
        for plan in monthly_plans:
            if machine_id in plan.maker_codes + plan.feeder_codes:
                applicable_plans.append(str(plan.plan_id))
        
        if applicable_plans:
            constraint = Constraint(
                constraint_id=f'CAP_{machine_id}',
                constraint_type=ConstraintType.MACHINE_CAPACITY,
                constraint_name=f'{machine_name}容量约束',
                description=f'{machine_name}月度容量不得超过{capacity:,}件',
                is_hard_constraint=True,
                priority=ConstraintPriority.CRITICAL,
                violation_penalty=2000.0,
                parameters={
                    'max_capacity': capacity,
                    'variables': [f'plan_{pid}' for pid in applicable_plans]
                },
                applicable_machines=[machine_id],
                applicable_plans=applicable_plans
            )
            constraints.append(constraint)
            print(f"   🏭 {machine_name}: 最大容量 {capacity:,}件, 适用计划: {applicable_plans}")
    
    # 3.2 时间窗口约束
    for plan in monthly_plans:
        if plan.planned_start and plan.planned_end:
            time_window = TimeWindow(plan.planned_start, plan.planned_end)
            constraint = Constraint(
                constraint_id=f'TIME_{plan.plan_id}',
                constraint_type=ConstraintType.TIME_WINDOW,
                constraint_name=f'计划{plan.plan_id}时间窗口',
                description=f'计划{plan.plan_id}必须在{plan.planned_start.strftime("%m-%d")}到{plan.planned_end.strftime("%m-%d")}期间执行',
                is_hard_constraint=True,
                priority=ConstraintPriority.HIGH,
                violation_penalty=1500.0,
                parameters={
                    'time_window': time_window,
                    'time_variable': f'plan_{plan.plan_id}_time'
                },
                applicable_plans=[str(plan.plan_id)],
                applicable_time_windows=[time_window]
            )
            constraints.append(constraint)
            print(f"   ⏰ 计划{plan.plan_id}时间窗口: {time_window.duration_hours():.1f}小时")
    
    # 3.3 工作日历约束
    work_constraint = Constraint(
        constraint_id='WORK_CALENDAR_2024',
        constraint_type=ConstraintType.WORK_CALENDAR,
        constraint_name='2024年工作日历约束',
        description='生产安排必须遵循工作日历，避开节假日',
        is_hard_constraint=False,
        priority=ConstraintPriority.MEDIUM,
        violation_penalty=500.0,
        parameters={
            'work_days': [0, 1, 2, 3, 4],  # 周一到周五
            'holidays': ['2024-01-01', '2024-02-10', '2024-02-11']  # 示例节假日
        },
        applicable_plans=[str(plan.plan_id) for plan in monthly_plans]
    )
    constraints.append(work_constraint)
    print(f"   📅 工作日历约束: 工作日 周一-周五, {len(work_constraint.parameters['holidays'])}个节假日")
    
    # 3.4 质量标准约束
    quality_constraint = Constraint(
        constraint_id='QUALITY_STANDARD_2024',
        constraint_type=ConstraintType.QUALITY_STANDARD,
        constraint_name='产品质量标准约束',
        description='所有产品必须满足质量标准要求',
        is_hard_constraint=False,
        priority=ConstraintPriority.HIGH,
        violation_penalty=800.0,
        parameters={
            'min_quality_score': 95.0,
            'quality_check_frequency': 'daily'
        },
        applicable_plans=[str(plan.plan_id) for plan in monthly_plans]
    )
    constraints.append(quality_constraint)
    print(f"   🎯 质量标准约束: 最低质量分数 {quality_constraint.parameters['min_quality_score']}分")
    
    print(f"\n   📊 约束条件总计: {len(constraints)}个")
    print()
    
    # 4. 创建决策变量
    print("4️⃣ 定义决策变量")
    variables = {}
    
    # 为每个计划创建分配变量
    for plan in monthly_plans:
        # 产量分配变量
        var_name = f'plan_{plan.plan_id}'
        variables[var_name] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': float(plan.target_quantity),
            'description': f'计划{plan.plan_id}的实际分配产量'
        }
        
        # 时间分配变量
        time_var_name = f'plan_{plan.plan_id}_time'
        variables[time_var_name] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 24*31,  # 31天，以小时为单位
            'description': f'计划{plan.plan_id}的执行时间（小时）'
        }
        
        print(f"   📊 {var_name}: 0 ~ {plan.target_quantity:,.0f}万支")
    
    # 机台利用率变量
    for machine_id, machine_name, capacity in machine_constraints:
        var_name = f'resource_{machine_id}'
        variables[var_name] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': capacity,
            'description': f'{machine_name}的月度利用容量'
        }
        print(f"   🏭 {var_name}: 0 ~ {capacity:,}件")
    
    print(f"\n   📊 决策变量总计: {len(variables)}个")
    print()
    
    # 5. 约束冲突分析
    print("5️⃣ 执行约束冲突分析")
    conflict_analysis = await solver.analyze_constraint_conflicts(constraints)
    
    print(f"   🔍 冲突检查结果:")
    print(f"   - 是否存在冲突: {'⚠️  是' if conflict_analysis['has_conflicts'] else '✅ 否'}")
    print(f"   - 冲突严重程度: {conflict_analysis['conflict_severity']}")
    print(f"   - 冲突组合数量: {len(conflict_analysis['conflict_groups'])}个")
    print(f"   - 不可调和约束: {len(conflict_analysis['irreconcilable_constraints'])}个")
    
    if conflict_analysis['conflict_groups']:
        print(f"   🚨 发现的冲突:")
        for i, conflict in enumerate(conflict_analysis['conflict_groups'][:3], 1):
            print(f"      {i}. {conflict['type']}: {conflict['description']}")
    
    if conflict_analysis['suggested_resolutions']:
        print(f"   💡 解决建议:")
        for i, resolution in enumerate(conflict_analysis['suggested_resolutions'][:3], 1):
            print(f"      {i}. {resolution}")
    
    print()
    
    # 6. 多策略求解对比
    print("6️⃣ 多策略求解对比")
    
    strategies_to_test = [
        (SolverStrategy.HEURISTIC, "启发式算法", 30),
        (SolverStrategy.HYBRID, "混合策略", 60)
    ]
    
    solutions = {}
    
    for strategy, strategy_name, time_limit in strategies_to_test:
        print(f"\n   🧮 {strategy_name} 求解中...")
        
        config = OptimizationConfig(
            max_solving_time=time_limit,
            solution_limit=5,
            hard_constraint_penalty=2000.0,
            soft_constraint_penalty=500.0
        )
        
        try:
            solution = await solver.solve_constraints(
                constraints=constraints,
                variables=variables,
                strategy=strategy,
                config=config
            )
            
            solutions[strategy] = solution
            
            print(f"   ✅ {strategy_name}求解完成:")
            print(f"      - 解决方案ID: {solution.solution_id}")
            print(f"      - 求解时间: {solution.solving_time:.3f}秒")
            print(f"      - 解决方案质量: {solution.solution_quality:.2f}分")
            print(f"      - 可行性: {'✅ 可行' if solution.is_feasible else '❌ 不可行'}")
            print(f"      - 目标函数值: {solution.objective_value:.2f}")
            print(f"      - 约束违反数: {len(solution.constraint_violations)}个")
            print(f"      - 总惩罚值: {solution.total_penalty:.2f}")
            
            if solution.constraint_violations:
                hard_violations = [v for v in solution.constraint_violations if v.violation_type == ViolationType.HARD_VIOLATION]
                soft_violations = [v for v in solution.constraint_violations if v.violation_type == ViolationType.SOFT_VIOLATION]
                print(f"      - 硬约束违反: {len(hard_violations)}个")
                print(f"      - 软约束违反: {len(soft_violations)}个")
            
        except Exception as e:
            print(f"   ❌ {strategy_name}求解失败: {str(e)}")
    
    # 7. 最佳解决方案分析
    if solutions:
        print(f"\n7️⃣ 最佳解决方案分析")
        
        best_solution = max(solutions.values(), key=lambda s: s.solution_quality)
        print(f"   🏆 最佳解决方案: {best_solution.algorithm_used}")
        print(f"   📊 质量评分: {best_solution.solution_quality:.2f}")
        
        # 解决方案验证
        validation = await solver.validate_solution(best_solution, constraints)
        print(f"\n   🔍 解决方案验证:")
        print(f"   - 有效性: {'✅ 有效' if validation['is_valid'] else '❌ 无效'}")
        print(f"   - 可行性: {'✅ 可行' if validation['is_feasible'] else '❌ 不可行'}")
        print(f"   - 约束满足率: {validation['constraint_satisfaction_rate']:.1%}")
        
        if best_solution.plan_assignments:
            print(f"\n   📋 计划分配结果:")
            for plan_var, assignment in best_solution.plan_assignments.items():
                plan_id = plan_var.split('_')[1]
                allocated_value = assignment.get('value', 0)
                print(f"   - 计划{plan_id}: {allocated_value:,.0f}万支")
        
        if best_solution.resource_allocations:
            print(f"\n   🏭 资源分配结果:")
            for resource_var, allocation in best_solution.resource_allocations.items():
                resource_id = resource_var.split('_')[1]
                utilization = allocation.get('capacity_utilization', 0)
                print(f"   - {resource_id}: 利用率 {utilization:.1%}")
        
        if validation['recommendations']:
            print(f"\n   💡 优化建议:")
            for i, recommendation in enumerate(validation['recommendations'][:5], 1):
                print(f"   {i}. {recommendation}")
    
    # 8. 性能统计
    print(f"\n8️⃣ 性能统计信息")
    stats = solver.get_solving_statistics()
    metrics = stats['performance_metrics']
    
    print(f"   📈 求解器性能:")
    print(f"   - 总求解次数: {metrics['total_problems_solved']}")
    print(f"   - 平均求解时间: {metrics['average_solving_time']:.3f}秒")
    print(f"   - 成功率: {metrics['success_rate']:.1%}")
    print(f"   - 最佳质量评分: {metrics['best_quality_achieved']:.2f}")
    print(f"   - 处理的约束类型: {len(metrics['constraint_types_handled'])}种")
    
    if stats['recent_solutions']:
        print(f"\n   🕐 最近的解决方案:")
        for i, sol_info in enumerate(stats['recent_solutions'][-3:], 1):
            print(f"   {i}. {sol_info['solution_id'][:20]}... - 质量: {sol_info['quality']:.1f}, 算法: {sol_info['algorithm']}")
    
    print()
    print("=" * 80)
    print("🎉 月度约束求解算法演示完成！")
    print("=" * 80)


async def demonstrate_advanced_features():
    """演示高级功能"""
    
    print("\n" + "=" * 80)
    print("🚀 高级功能演示")
    print("=" * 80)
    
    solver = MonthlyConstraintSolver()
    
    # 演示基于月度计划的直接优化
    print("\n1️⃣ 基于月度计划的直接优化")
    
    # 创建月度计划
    monthly_plans = [
        MonthlyPlanItem(
            plan_id=1,
            batch_id='MONTHLY_2024_01',
            work_order_nr='WO_2024_001',
            article_nr='ZS_001',
            article_name='中华香烟（软包）',
            target_quantity=25000.0,
            planned_boxes=125000,
            feeder_codes=['WSJ001'],
            maker_codes=['JBJ001', 'JBJ002'],
            planned_start=datetime.now() + timedelta(days=1),
            planned_end=datetime.now() + timedelta(days=10),
            priority=Priority.HIGH
        ),
        MonthlyPlanItem(
            plan_id=2,
            batch_id='MONTHLY_2024_02',
            work_order_nr='WO_2024_002',
            article_nr='ZS_002',
            article_name='中华香烟（硬包）',
            target_quantity=20000.0,
            planned_boxes=100000,
            feeder_codes=['WSJ002'],
            maker_codes=['JBJ002', 'JBJ003'],
            planned_start=datetime.now() + timedelta(days=5),
            planned_end=datetime.now() + timedelta(days=15),
            priority=Priority.MEDIUM
        )
    ]
    
    # 机台配置
    machine_configs = [
        {
            'machine_id': 'JBJ001',
            'machine_name': '卷包机001',
            'machine_type': 'maker',
            'monthly_capacity': 80000,
            'efficiency_factor': 0.85,
            'cost_per_unit': 0.05
        },
        {
            'machine_id': 'JBJ002',
            'machine_name': '卷包机002',
            'machine_type': 'maker',
            'monthly_capacity': 75000,
            'efficiency_factor': 0.88,
            'cost_per_unit': 0.04
        },
        {
            'machine_id': 'WSJ001',
            'machine_name': '喂丝机001',
            'machine_type': 'feeder',
            'monthly_capacity': 120000,
            'efficiency_factor': 0.90,
            'cost_per_unit': 0.03
        }
    ]
    
    # 工作日历
    work_calendar = {
        'year': 2024,
        'month': 1,
        'working_days': [0, 1, 2, 3, 4],  # 周一到周五
        'working_hours_per_day': 16,
        'total_working_days': 22,
        'holidays': ['2024-01-01', '2024-02-10']
    }
    
    # 优化目标
    optimization_objectives = {
        'maximize_production': 0.5,
        'minimize_cost': 0.3,
        'maximize_efficiency': 0.2
    }
    
    # 约束偏好
    constraint_preferences = {
        'capacity_constraints': 0.9,
        'time_constraints': 0.8,
        'work_calendar_constraints': 0.6,
        'quality_constraints': 0.7
    }
    
    print(f"   📋 月度计划: {len(monthly_plans)}个")
    print(f"   🏭 机台配置: {len(machine_configs)}个")
    print(f"   📅 工作日历: {work_calendar['year']}年{work_calendar['month']}月")
    
    try:
        solution = await solver.optimize_with_constraints(
            monthly_plans=monthly_plans,
            machine_configs=machine_configs,
            work_calendar=work_calendar,
            optimization_objectives=optimization_objectives,
            constraint_preferences=constraint_preferences
        )
        
        print(f"\n   ✅ 优化完成:")
        print(f"   - 解决方案质量: {solution.solution_quality:.2f}")
        print(f"   - 可行性: {'✅ 可行' if solution.is_feasible else '❌ 不可行'}")
        print(f"   - 求解时间: {solution.solving_time:.3f}秒")
        print(f"   - 计划分配: {len(solution.plan_assignments)}个")
        print(f"   - 资源分配: {len(solution.resource_allocations)}个")
        
    except Exception as e:
        print(f"   ❌ 优化失败: {str(e)}")
    
    print(f"\n🎯 高级功能演示完成！")


if __name__ == "__main__":
    print("启动月度约束求解算法演示...")
    print()
    
    # 运行主要演示
    asyncio.run(demonstrate_constraint_solver())
    
    # 运行高级功能演示
    asyncio.run(demonstrate_advanced_features())
    
    print("\n" + "🏁 演示结束，感谢使用APS月度约束求解算法！" + "\n")