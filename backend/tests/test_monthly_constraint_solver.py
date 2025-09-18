"""
月度约束求解算法测试模块

测试MonthlyConstraintSolver类的各种功能，包括：
- 基础约束求解
- 多种求解策略验证
- 约束冲突分析
- 解决方案验证
- 性能基准测试
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from app.algorithms.monthly_scheduling.monthly_constraint_solver import (
    MonthlyConstraintSolver,
    Constraint,
    ConstraintType,
    ConstraintPriority,
    SolverStrategy,
    OptimizationConfig,
    TimeWindow,
    Solution,
    ViolationType
)
from app.algorithms.monthly_scheduling.base import (
    MonthlyPlanItem,
    Priority
)


class TestMonthlyConstraintSolver:
    """月度约束求解器测试类"""
    
    @pytest.fixture
    async def solver(self):
        """创建约束求解器实例"""
        return MonthlyConstraintSolver()
    
    @pytest.fixture
    def sample_constraints(self):
        """创建示例约束条件"""
        constraints = []
        
        # 机台容量约束
        capacity_constraint = Constraint(
            constraint_id="CAP_JBJ001",
            constraint_type=ConstraintType.MACHINE_CAPACITY,
            constraint_name="卷包机001容量约束",
            description="卷包机001月度容量不得超过80000件",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=1000.0,
            parameters={
                'max_capacity': 80000,
                'variables': ['plan_1', 'plan_2']
            },
            applicable_machines=['JBJ001']
        )
        constraints.append(capacity_constraint)
        
        # 时间窗口约束
        time_window = TimeWindow(
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(days=3)
        )
        
        time_constraint = Constraint(
            constraint_id="TIME_PLAN_1",
            constraint_type=ConstraintType.TIME_WINDOW,
            constraint_name="计划1时间窗口约束",
            description="计划1必须在指定时间窗口内执行",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=500.0,
            parameters={
                'time_window': time_window,
                'time_variable': 'plan_1_time'
            },
            applicable_plans=['1'],
            applicable_time_windows=[time_window]
        )
        constraints.append(time_constraint)
        
        # 工作日历约束
        work_constraint = Constraint(
            constraint_id="WORK_CALENDAR",
            constraint_type=ConstraintType.WORK_CALENDAR,
            constraint_name="工作日历约束",
            description="生产安排必须在工作日进行",
            is_hard_constraint=False,
            priority=ConstraintPriority.MEDIUM,
            violation_penalty=200.0,
            parameters={
                'work_days': [0, 1, 2, 3, 4]  # 周一到周五
            },
            applicable_plans=['1', '2']
        )
        constraints.append(work_constraint)
        
        return constraints
    
    @pytest.fixture
    def sample_variables(self):
        """创建示例决策变量"""
        variables = {}
        
        # 计划变量
        variables['plan_1'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 20000,
            'description': '计划1的分配产量'
        }
        
        variables['plan_2'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 15000,
            'description': '计划2的分配产量'
        }
        
        variables['plan_1_time'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 720,  # 30天 * 24小时
            'description': '计划1的执行时间'
        }
        
        # 资源变量
        variables['resource_JBJ001'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 80000,
            'description': '卷包机001的月度利用容量'
        }
        
        return variables
    
    @pytest.fixture
    def sample_monthly_plans(self):
        """创建示例月度计划"""
        plans = []
        
        base_time = datetime.now()
        
        for i in range(1, 4):
            plan = MonthlyPlanItem(
                plan_id=i,
                batch_id=f'BATCH_{i}',
                work_order_nr=f'WO_{i:03d}',
                article_nr=f'ART_{i:03d}',
                article_name=f'产品_{i}',
                target_quantity=10000.0 + i * 2000,
                planned_boxes=(10000 + i * 2000) * 5,
                feeder_codes=[f'WSJ{i:03d}'],
                maker_codes=[f'JBJ{i:03d}'],
                planned_start=base_time + timedelta(days=i),
                planned_end=base_time + timedelta(days=i+2),
                priority=Priority.MEDIUM
            )
            plans.append(plan)
        
        return plans
    
    @pytest.fixture
    def sample_machine_configs(self):
        """创建示例机台配置"""
        return [
            {
                'machine_id': 'JBJ001',
                'machine_name': '卷包机001',
                'machine_type': 'maker',
                'monthly_capacity': 80000,
                'efficiency_factor': 0.85
            },
            {
                'machine_id': 'JBJ002',
                'machine_name': '卷包机002',
                'machine_type': 'maker',
                'monthly_capacity': 75000,
                'efficiency_factor': 0.88
            },
            {
                'machine_id': 'WSJ001',
                'machine_name': '喂丝机001',
                'machine_type': 'feeder',
                'monthly_capacity': 120000,
                'efficiency_factor': 0.90
            }
        ]
    
    @pytest.fixture
    def sample_work_calendar(self):
        """创建示例工作日历"""
        return {
            'year': 2024,
            'month': 1,
            'working_days': [0, 1, 2, 3, 4],  # 周一到周五
            'working_hours_per_day': 16,
            'total_working_days': 22,
            'holidays': []
        }

    @pytest.mark.asyncio
    async def test_solver_initialization(self, solver):
        """测试求解器初始化"""
        assert solver is not None
        assert solver.algorithm_type.value == "constraint_solver"
        assert len(solver.solvers) == 3  # 三种求解策略
        assert solver.performance_metrics['total_problems_solved'] == 0
    
    @pytest.mark.asyncio
    async def test_constraint_creation(self, sample_constraints):
        """测试约束条件创建"""
        assert len(sample_constraints) == 3
        
        capacity_constraint = sample_constraints[0]
        assert capacity_constraint.constraint_type == ConstraintType.MACHINE_CAPACITY
        assert capacity_constraint.is_hard_constraint == True
        assert capacity_constraint.priority == ConstraintPriority.HIGH
        assert capacity_constraint.parameters['max_capacity'] == 80000
        
        time_constraint = sample_constraints[1]
        assert time_constraint.constraint_type == ConstraintType.TIME_WINDOW
        assert isinstance(time_constraint.parameters['time_window'], TimeWindow)
        
        work_constraint = sample_constraints[2]
        assert work_constraint.constraint_type == ConstraintType.WORK_CALENDAR
        assert work_constraint.is_hard_constraint == False

    @pytest.mark.asyncio
    async def test_input_validation(self, solver, sample_constraints, sample_variables):
        """测试输入验证"""
        # 测试有效输入
        input_data = {
            'constraints': sample_constraints,
            'variables': sample_variables
        }
        assert solver.validate_input(input_data) == True
        
        # 测试无效输入 - 缺少约束
        invalid_input = {
            'constraints': [],
            'variables': sample_variables
        }
        assert solver.validate_input(invalid_input) == False
        
        # 测试无效输入 - 缺少变量
        invalid_input2 = {
            'constraints': sample_constraints,
            'variables': {}
        }
        assert solver.validate_input(invalid_input2) == False

    @pytest.mark.asyncio
    async def test_heuristic_solving(self, solver, sample_constraints, sample_variables):
        """测试启发式求解"""
        config = OptimizationConfig(
            max_solving_time=30,
            solution_limit=5
        )
        
        solution = await solver.solve_constraints(
            constraints=sample_constraints,
            variables=sample_variables,
            strategy=SolverStrategy.HEURISTIC,
            config=config
        )
        
        assert solution is not None
        assert solution.algorithm_used == "heuristic"
        assert solution.solving_time > 0
        assert solution.solution_quality >= 0
        assert len(solution.plan_assignments) > 0 or len(solution.resource_allocations) > 0

    @pytest.mark.asyncio
    async def test_hybrid_solving(self, solver, sample_constraints, sample_variables):
        """测试混合求解策略"""
        config = OptimizationConfig(
            max_solving_time=60,
            solution_limit=10
        )
        
        solution = await solver.solve_constraints(
            constraints=sample_constraints,
            variables=sample_variables,
            strategy=SolverStrategy.HYBRID,
            config=config
        )
        
        assert solution is not None
        assert "hybrid" in solution.algorithm_used.lower()
        assert solution.solving_time > 0

    @pytest.mark.asyncio
    async def test_solution_validation(self, solver, sample_constraints, sample_variables):
        """测试解决方案验证"""
        solution = await solver.solve_constraints(
            constraints=sample_constraints,
            variables=sample_variables,
            strategy=SolverStrategy.HEURISTIC
        )
        
        validation_result = await solver.validate_solution(solution, sample_constraints)
        
        assert 'is_valid' in validation_result
        assert 'is_feasible' in validation_result
        assert 'quality_score' in validation_result
        assert 'constraint_satisfaction_rate' in validation_result
        assert isinstance(validation_result['hard_violations'], list)
        assert isinstance(validation_result['soft_violations'], list)

    @pytest.mark.asyncio
    async def test_constraint_conflict_analysis(self, solver):
        """测试约束冲突分析"""
        # 创建冲突的约束条件
        conflicting_constraints = []
        
        # 时间窗口冲突
        time_window1 = TimeWindow(
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=2)
        )
        
        time_window2 = TimeWindow(
            start_time=datetime.now() + timedelta(hours=3),
            end_time=datetime.now() + timedelta(hours=5)
        )
        
        constraint1 = Constraint(
            constraint_id="TIME_CONFLICT_1",
            constraint_type=ConstraintType.TIME_WINDOW,
            constraint_name="冲突时间窗口1",
            description="时间窗口1",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=500.0,
            parameters={'time_window': time_window1},
            applicable_machines=['JBJ001']
        )
        
        constraint2 = Constraint(
            constraint_id="TIME_CONFLICT_2",
            constraint_type=ConstraintType.TIME_WINDOW,
            constraint_name="冲突时间窗口2",
            description="时间窗口2",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=500.0,
            parameters={'time_window': time_window2},
            applicable_machines=['JBJ001']  # 同一机台
        )
        
        conflicting_constraints.extend([constraint1, constraint2])
        
        conflict_analysis = await solver.analyze_constraint_conflicts(conflicting_constraints)
        
        assert 'has_conflicts' in conflict_analysis
        assert 'conflict_groups' in conflict_analysis
        assert 'conflict_severity' in conflict_analysis
        assert 'suggested_resolutions' in conflict_analysis

    @pytest.mark.asyncio
    async def test_optimize_with_monthly_plans(
        self, 
        solver, 
        sample_monthly_plans, 
        sample_machine_configs, 
        sample_work_calendar
    ):
        """测试基于月度计划的优化"""
        optimization_objectives = {
            'maximize_production': 0.6,
            'minimize_cost': 0.3,
            'maximize_efficiency': 0.1
        }
        
        constraint_preferences = {
            'capacity_constraints': 0.8,
            'time_constraints': 0.9,
            'work_calendar_constraints': 0.6
        }
        
        solution = await solver.optimize_with_constraints(
            monthly_plans=sample_monthly_plans,
            machine_configs=sample_machine_configs,
            work_calendar=sample_work_calendar,
            optimization_objectives=optimization_objectives,
            constraint_preferences=constraint_preferences
        )
        
        assert solution is not None
        assert solution.solution_quality >= 0
        assert len(solution.plan_assignments) > 0

    @pytest.mark.asyncio
    async def test_constraint_violation_handling(self, solver, sample_constraints, sample_variables):
        """测试约束违反处理"""
        # 修改变量范围以产生约束违反
        modified_variables = sample_variables.copy()
        modified_variables['plan_1']['upper_bound'] = 100000  # 超出机台容量
        
        solution = await solver.solve_constraints(
            constraints=sample_constraints,
            variables=modified_variables,
            strategy=SolverStrategy.HEURISTIC
        )
        
        # 验证是否正确处理了约束违反
        assert solution is not None
        
        # 如果有约束违反，应该在solution中反映
        if solution.constraint_violations:
            hard_violations = [
                v for v in solution.constraint_violations
                if v.violation_type == ViolationType.HARD_VIOLATION
            ]
            
            if hard_violations:
                assert not solution.is_feasible

    @pytest.mark.asyncio
    async def test_performance_metrics(self, solver, sample_constraints, sample_variables):
        """测试性能指标收集"""
        initial_count = solver.performance_metrics['total_problems_solved']
        
        await solver.solve_constraints(
            constraints=sample_constraints,
            variables=sample_variables,
            strategy=SolverStrategy.HEURISTIC
        )
        
        # 验证性能指标更新
        assert solver.performance_metrics['total_problems_solved'] == initial_count + 1
        assert solver.performance_metrics['average_solving_time'] > 0
        
        # 获取统计信息
        stats = solver.get_solving_statistics()
        assert 'performance_metrics' in stats
        assert 'recent_solutions' in stats
        assert 'constraint_type_distribution' in stats

    @pytest.mark.asyncio
    async def test_time_window_constraint_evaluation(self):
        """测试时间窗口约束评估"""
        time_window = TimeWindow(
            start_time=datetime(2024, 1, 1, 8, 0),
            end_time=datetime(2024, 1, 1, 17, 0)
        )
        
        constraint = Constraint(
            constraint_id="TIME_TEST",
            constraint_type=ConstraintType.TIME_WINDOW,
            constraint_name="时间测试约束",
            description="测试时间窗口约束",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=500.0,
            parameters={'time_window': time_window}
        )
        
        # 测试合法时间
        valid_solution_state = {
            'assigned_time': datetime(2024, 1, 1, 10, 0)
        }
        violation_degree, reason = constraint.evaluate_violation(valid_solution_state)
        assert violation_degree == 0.0
        assert reason == ""
        
        # 测试非法时间
        invalid_solution_state = {
            'assigned_time': datetime(2024, 1, 1, 20, 0)  # 超出时间窗口
        }
        violation_degree, reason = constraint.evaluate_violation(invalid_solution_state)
        assert violation_degree > 0.0
        assert len(reason) > 0

    @pytest.mark.asyncio
    async def test_capacity_constraint_evaluation(self):
        """测试容量约束评估"""
        constraint = Constraint(
            constraint_id="CAP_TEST",
            constraint_type=ConstraintType.MACHINE_CAPACITY,
            constraint_name="容量测试约束",
            description="测试容量约束",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=1000.0,
            parameters={'max_capacity': 1000}
        )
        
        # 测试合法容量
        valid_solution_state = {
            'allocated_capacity': 800
        }
        violation_degree, reason = constraint.evaluate_violation(valid_solution_state)
        assert violation_degree == 0.0
        
        # 测试超出容量
        invalid_solution_state = {
            'allocated_capacity': 1200
        }
        violation_degree, reason = constraint.evaluate_violation(invalid_solution_state)
        assert violation_degree > 0.0
        assert "超出最大容量" in reason

    def test_time_window_operations(self):
        """测试时间窗口操作"""
        start_time = datetime(2024, 1, 1, 8, 0)
        end_time = datetime(2024, 1, 1, 17, 0)
        
        time_window = TimeWindow(start_time, end_time)
        
        # 测试包含检查
        assert time_window.contains(datetime(2024, 1, 1, 10, 0)) == True
        assert time_window.contains(datetime(2024, 1, 1, 20, 0)) == False
        
        # 测试持续时间计算
        duration = time_window.duration_hours()
        assert duration == 9.0  # 9小时
        
        # 测试重叠检查
        other_window = TimeWindow(
            datetime(2024, 1, 1, 16, 0),
            datetime(2024, 1, 1, 20, 0)
        )
        assert time_window.overlaps(other_window) == True
        
        non_overlapping_window = TimeWindow(
            datetime(2024, 1, 1, 18, 0),
            datetime(2024, 1, 1, 22, 0)
        )
        assert time_window.overlaps(non_overlapping_window) == False

    @pytest.mark.asyncio
    async def test_error_handling(self, solver):
        """测试错误处理"""
        # 测试空约束和变量
        try:
            await solver.solve_constraints(
                constraints=[],
                variables={},
                strategy=SolverStrategy.HEURISTIC
            )
            assert False, "应该抛出异常"
        except Exception as e:
            assert "约束列表为空" in str(e) or "变量字典为空" in str(e)
        
        # 测试无效的求解策略（通过传入无效策略名）
        invalid_input = {
            'constraints': [],
            'variables': {},
            'strategy': 'invalid_strategy'
        }
        assert solver.validate_input(invalid_input) == False


if __name__ == "__main__":
    # 运行基本测试
    import asyncio
    
    async def run_basic_test():
        solver = MonthlyConstraintSolver()
        print(f"约束求解器创建成功，算法类型: {solver.algorithm_type.value}")
        
        # 创建简单测试约束
        constraint = Constraint(
            constraint_id="TEST_CAP",
            constraint_type=ConstraintType.MACHINE_CAPACITY,
            constraint_name="测试容量约束",
            description="测试约束求解器",
            is_hard_constraint=True,
            priority=ConstraintPriority.HIGH,
            violation_penalty=100.0,
            parameters={'max_capacity': 1000}
        )
        
        variables = {
            'test_var': {
                'type': 'continuous',
                'lower_bound': 0,
                'upper_bound': 500
            }
        }
        
        try:
            solution = await solver.solve_constraints(
                constraints=[constraint],
                variables=variables,
                strategy=SolverStrategy.HEURISTIC
            )
            print(f"求解成功！解决方案质量: {solution.solution_quality:.2f}")
            
        except Exception as e:
            print(f"求解失败: {str(e)}")
    
    print("运行月度约束求解器基本测试...")
    asyncio.run(run_basic_test())
    print("测试完成！")