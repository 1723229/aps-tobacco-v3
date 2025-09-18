"""
月度约束求解算法模块 - T026

该模块实现了烟草生产中的复杂约束求解算法，支持多层次约束优化、
软硬约束处理、线性规划和启发式算法混合求解，为月度排产提供可行的约束满足解决方案。

主要功能：
- 复杂约束建模和求解
- 时间约束、容量约束、机台约束、工作日历约束处理
- 硬约束和软约束的区分处理
- 约束优先级和违反惩罚机制
- 线性规划和启发式算法集成
- 约束冲突分析和建议生成
- 实时约束验证和解决方案优化

算法特点：
- 支持多种约束类型的统一建模
- 提供灵活的求解策略和参数配置
- 集成OR-Tools线性规划求解器
- 支持大规模约束问题的高效求解
- 提供详细的约束违反分析和解决建议

作者: APS开发团队
版本: 1.0.0
依赖: SQLAlchemy, asyncio, OR-Tools, NumPy, scipy
"""

import asyncio
import json
import logging
import time
import argparse
import heapq
import math
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque
import warnings

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

# 尝试导入OR-Tools（生产环境需安装）
try:
    from ortools.linear_solver import pywraplp
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools未安装，将使用启发式约束求解算法")

# 尝试导入scipy（用于高级优化）
try:
    from scipy.optimize import minimize, linprog
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy未安装，部分优化功能将不可用")

# 导入基础模块和数据模型
from .base import (
    BaseAlgorithm, AlgorithmType, Priority, MachineType,
    MonthlyPlanItem, MachineInfo, ScheduleResult,
    MonthlySchedulingError, InvalidInputError, 
    ConstraintViolationError, ResourceConflictError,
    ALGORITHM_CONFIG, SHIFT_CONFIG
)

try:
    from ...models.monthly_plan_models import MonthlyPlan
    from ...models.monthly_work_calendar_models import WorkCalendar  
    from ...models.machine_config_models import MachineConfig, MachineSpeed, MaintenancePlan
    from ...models.base_models import Machine, Material
except ImportError:
    # 开发阶段的占位符
    MonthlyPlan = None
    WorkCalendar = None
    MachineConfig = None
    MachineSpeed = None
    MaintenancePlan = None
    Machine = None
    Material = None

logger = logging.getLogger(__name__)


# =============================================================================
# 约束类型和优先级定义
# =============================================================================

class ConstraintType(Enum):
    """约束类型枚举"""
    # 时间约束
    TIME_WINDOW = "time_window"                    # 时间窗口约束
    DEADLINE = "deadline"                          # 截止时间约束
    PRECEDENCE = "precedence"                      # 优先级约束
    SEQUENCE = "sequence"                          # 顺序约束
    
    # 容量约束
    MACHINE_CAPACITY = "machine_capacity"          # 机台容量约束
    RESOURCE_CAPACITY = "resource_capacity"        # 资源容量约束
    STORAGE_CAPACITY = "storage_capacity"          # 存储容量约束
    
    # 机台约束
    MACHINE_COMPATIBILITY = "machine_compatibility" # 机台兼容性约束
    MACHINE_AVAILABILITY = "machine_availability"  # 机台可用性约束
    SETUP_TIME = "setup_time"                      # 换产时间约束
    MAINTENANCE_WINDOW = "maintenance_window"      # 维护时间窗约束
    
    # 工作日历约束
    WORK_CALENDAR = "work_calendar"                # 工作日历约束
    SHIFT_SCHEDULE = "shift_schedule"              # 班次安排约束
    HOLIDAY_RESTRICTION = "holiday_restriction"   # 节假日限制约束
    
    # 质量约束
    QUALITY_STANDARD = "quality_standard"         # 质量标准约束
    BATCH_SIZE = "batch_size"                     # 批次大小约束
    MATERIAL_CONSTRAINT = "material_constraint"   # 物料约束
    
    # 成本约束
    COST_LIMIT = "cost_limit"                     # 成本限制约束
    BUDGET_CONSTRAINT = "budget_constraint"       # 预算约束
    
    # 自定义约束
    CUSTOM = "custom"                             # 自定义约束


class ConstraintPriority(Enum):
    """约束优先级枚举"""
    CRITICAL = 10    # 关键约束 - 绝对不能违反
    HIGH = 8         # 高优先级 - 强烈避免违反
    MEDIUM = 5       # 中优先级 - 尽量避免违反
    LOW = 3          # 低优先级 - 可以适当违反
    OPTIONAL = 1     # 可选约束 - 违反影响较小


class SolverStrategy(Enum):
    """求解策略枚举"""
    LINEAR_PROGRAMMING = "linear_programming"      # 线性规划
    CONSTRAINT_PROGRAMMING = "constraint_programming"  # 约束规划
    HEURISTIC = "heuristic"                       # 启发式算法
    GENETIC_ALGORITHM = "genetic_algorithm"       # 遗传算法
    SIMULATED_ANNEALING = "simulated_annealing"   # 模拟退火
    HYBRID = "hybrid"                             # 混合策略
    GREEDY = "greedy"                            # 贪心算法


class ViolationType(Enum):
    """违反类型枚举"""
    HARD_VIOLATION = "hard_violation"             # 硬约束违反
    SOFT_VIOLATION = "soft_violation"             # 软约束违反
    PREFERENCE_VIOLATION = "preference_violation" # 偏好违反


# =============================================================================
# 约束数据类定义
# =============================================================================

@dataclass
class TimeWindow:
    """时间窗口数据类"""
    start_time: datetime
    end_time: datetime
    flexible: bool = False                        # 是否允许弹性调整
    flexibility_minutes: int = 30                 # 弹性调整分钟数
    
    def contains(self, timestamp: datetime) -> bool:
        """检查时间点是否在时间窗口内"""
        return self.start_time <= timestamp <= self.end_time
    
    def overlaps(self, other: 'TimeWindow') -> bool:
        """检查与其他时间窗口是否重叠"""
        return (self.start_time < other.end_time and 
                self.end_time > other.start_time)
    
    def duration_hours(self) -> float:
        """计算时间窗口持续时间（小时）"""
        return (self.end_time - self.start_time).total_seconds() / 3600


@dataclass
class CapacityConstraint:
    """容量约束数据类"""
    resource_id: str
    resource_type: str
    max_capacity: Decimal
    min_capacity: Decimal = Decimal('0')
    capacity_unit: str = "pieces"
    time_window: Optional[TimeWindow] = None
    
    def check_violation(self, allocated_capacity: Decimal) -> float:
        """检查容量约束违反程度"""
        if allocated_capacity > self.max_capacity:
            return float((allocated_capacity - self.max_capacity) / self.max_capacity)
        elif allocated_capacity < self.min_capacity:
            return float((self.min_capacity - allocated_capacity) / self.max_capacity)
        return 0.0


@dataclass
class Constraint:
    """通用约束数据类"""
    constraint_id: str
    constraint_type: ConstraintType
    constraint_name: str
    description: str
    is_hard_constraint: bool                      # 是否为硬约束
    priority: ConstraintPriority
    violation_penalty: float                      # 违反惩罚权重
    
    # 约束参数（根据不同约束类型有不同内容）
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 约束适用范围
    applicable_plans: List[str] = field(default_factory=list)
    applicable_machines: List[str] = field(default_factory=list)
    applicable_time_windows: List[TimeWindow] = field(default_factory=list)
    
    # 约束验证函数
    validation_function: Optional[Callable] = None
    
    def evaluate_violation(self, solution_state: Dict[str, Any]) -> Tuple[float, str]:
        """
        评估约束违反程度
        
        Args:
            solution_state: 解决方案状态
            
        Returns:
            Tuple[float, str]: (违反程度[0-1], 违反原因)
        """
        if self.validation_function:
            return self.validation_function(solution_state, self.parameters)
        
        # 默认验证逻辑
        return self._default_validation(solution_state)
    
    def _default_validation(self, solution_state: Dict[str, Any]) -> Tuple[float, str]:
        """默认约束验证逻辑"""
        violation_degree = 0.0
        violation_reason = ""
        
        if self.constraint_type == ConstraintType.TIME_WINDOW:
            violation_degree, violation_reason = self._validate_time_window(solution_state)
        elif self.constraint_type == ConstraintType.MACHINE_CAPACITY:
            violation_degree, violation_reason = self._validate_machine_capacity(solution_state)
        elif self.constraint_type == ConstraintType.WORK_CALENDAR:
            violation_degree, violation_reason = self._validate_work_calendar(solution_state)
        
        return violation_degree, violation_reason
    
    def _validate_time_window(self, solution_state: Dict[str, Any]) -> Tuple[float, str]:
        """验证时间窗口约束"""
        required_window = self.parameters.get('time_window')
        if not required_window:
            return 0.0, ""
        
        assigned_time = solution_state.get('assigned_time')
        if not assigned_time:
            return 1.0, "未分配执行时间"
        
        if not required_window.contains(assigned_time):
            return 1.0, f"执行时间 {assigned_time} 超出约束时间窗口 [{required_window.start_time}, {required_window.end_time}]"
        
        return 0.0, ""
    
    def _validate_machine_capacity(self, solution_state: Dict[str, Any]) -> Tuple[float, str]:
        """验证机台容量约束"""
        max_capacity = self.parameters.get('max_capacity', float('inf'))
        allocated_capacity = solution_state.get('allocated_capacity', 0)
        
        if allocated_capacity > max_capacity:
            violation = (allocated_capacity - max_capacity) / max_capacity
            return min(1.0, violation), f"分配容量 {allocated_capacity} 超出最大容量 {max_capacity}"
        
        return 0.0, ""
    
    def _validate_work_calendar(self, solution_state: Dict[str, Any]) -> Tuple[float, str]:
        """验证工作日历约束"""
        work_days = self.parameters.get('work_days', [])
        assigned_date = solution_state.get('assigned_date')
        
        if assigned_date and assigned_date.weekday() not in work_days:
            return 1.0, f"分配日期 {assigned_date} 不在工作日范围内"
        
        return 0.0, ""


@dataclass
class ConstraintViolation:
    """约束违反记录数据类"""
    constraint_id: str
    constraint_name: str
    violation_type: ViolationType
    violation_degree: float                       # 违反程度 [0-1]
    violation_penalty: float                      # 违反惩罚值
    violation_reason: str                         # 违反原因
    affected_plans: List[str]                     # 受影响的计划
    affected_resources: List[str]                 # 受影响的资源
    suggested_fixes: List[str]                    # 建议修复方案
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Solution:
    """解决方案数据类"""
    solution_id: str
    plan_assignments: Dict[str, Dict[str, Any]]   # 计划分配方案
    resource_allocations: Dict[str, Dict[str, Any]]  # 资源分配方案
    objective_value: float                        # 目标函数值
    is_feasible: bool                            # 是否可行
    constraint_violations: List[ConstraintViolation]  # 约束违反列表
    total_penalty: float                         # 总惩罚值
    solution_quality: float                      # 解决方案质量评分
    solving_time: float                          # 求解时间
    algorithm_used: str                          # 使用的算法
    generation_time: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationConfig:
    """优化配置数据类"""
    max_solving_time: int = 300                  # 最大求解时间（秒）
    gap_tolerance: float = 0.01                  # 间隙容忍度
    solution_limit: int = 10                     # 解决方案数量限制
    hard_constraint_penalty: float = 1000.0     # 硬约束违反惩罚
    soft_constraint_penalty: float = 100.0      # 软约束违反惩罚
    enable_preprocessing: bool = True            # 启用预处理
    enable_heuristics: bool = True               # 启用启发式算法
    parallel_solving: bool = True                # 并行求解
    memory_limit_mb: int = 1024                  # 内存限制（MB）


# =============================================================================
# 约束求解算法基类和具体实现
# =============================================================================

class ConstraintSolver(ABC):
    """约束求解器基类"""
    
    @abstractmethod
    async def solve(
        self,
        constraints: List[Constraint],
        objective_function: Callable,
        variables: Dict[str, Any],
        config: OptimizationConfig
    ) -> Solution:
        """
        求解约束满足问题
        
        Args:
            constraints: 约束条件列表
            objective_function: 目标函数
            variables: 决策变量
            config: 优化配置
            
        Returns:
            Solution: 求解结果
        """
        pass
    
    @abstractmethod
    def validate_solution(self, solution: Solution, constraints: List[Constraint]) -> bool:
        """
        验证解决方案的可行性
        
        Args:
            solution: 解决方案
            constraints: 约束条件列表
            
        Returns:
            bool: 是否可行
        """
        pass


class LinearProgrammingSolver(ConstraintSolver):
    """线性规划求解器"""
    
    def __init__(self):
        self.solver = None
        self.variables = {}
        self.constraints = {}
    
    async def solve(
        self,
        constraints: List[Constraint],
        objective_function: Callable,
        variables: Dict[str, Any],
        config: OptimizationConfig
    ) -> Solution:
        """线性规划求解实现"""
        
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools不可用，回退到启发式求解器")
            heuristic_solver = HeuristicConstraintSolver()
            return await heuristic_solver.solve(constraints, objective_function, variables, config)
        
        start_time = time.time()
        logger.info("开始线性规划约束求解")
        
        # 创建求解器
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise ConstraintViolationError("无法创建OR-Tools线性规划求解器")
        
        try:
            # 创建决策变量
            self._create_variables(variables)
            
            # 添加约束
            self._add_constraints(constraints)
            
            # 设置目标函数
            self._set_objective(objective_function)
            
            # 设置求解器参数
            self.solver.SetTimeLimit(config.max_solving_time * 1000)  # 毫秒
            
            # 执行求解
            status = self.solver.Solve()
            
            solving_time = time.time() - start_time
            
            if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
                logger.info(f"线性规划求解成功，状态: {'最优' if status == pywraplp.Solver.OPTIMAL else '可行'}，耗时: {solving_time:.2f}秒")
                return self._extract_solution(constraints, solving_time)
            else:
                logger.error(f"线性规划求解失败，状态: {status}")
                return self._create_infeasible_solution(constraints, solving_time)
        
        except Exception as e:
            logger.error(f"线性规划求解过程异常: {str(e)}")
            solving_time = time.time() - start_time
            return self._create_error_solution(str(e), constraints, solving_time)
    
    def _create_variables(self, variables: Dict[str, Any]):
        """创建决策变量"""
        self.variables = {}
        
        for var_name, var_config in variables.items():
            var_type = var_config.get('type', 'continuous')
            lower_bound = var_config.get('lower_bound', 0)
            upper_bound = var_config.get('upper_bound', self.solver.infinity())
            
            if var_type == 'binary':
                self.variables[var_name] = self.solver.BoolVar(var_name)
            elif var_type == 'integer':
                self.variables[var_name] = self.solver.IntVar(int(lower_bound), int(upper_bound), var_name)
            else:  # continuous
                self.variables[var_name] = self.solver.NumVar(lower_bound, upper_bound, var_name)
    
    def _add_constraints(self, constraints: List[Constraint]):
        """添加约束条件"""
        self.constraints = {}
        
        for constraint in constraints:
            constraint_obj = self._create_constraint_object(constraint)
            if constraint_obj:
                self.constraints[constraint.constraint_id] = constraint_obj
    
    def _create_constraint_object(self, constraint: Constraint):
        """根据约束类型创建约束对象"""
        
        if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
            return self._create_capacity_constraint(constraint)
        elif constraint.constraint_type == ConstraintType.TIME_WINDOW:
            return self._create_time_window_constraint(constraint)
        elif constraint.constraint_type == ConstraintType.SEQUENCE:
            return self._create_sequence_constraint(constraint)
        else:
            logger.warning(f"约束类型 {constraint.constraint_type} 暂不支持线性规划求解")
            return None
    
    def _create_capacity_constraint(self, constraint: Constraint):
        """创建容量约束"""
        max_capacity = constraint.parameters.get('max_capacity', float('inf'))
        affected_variables = constraint.parameters.get('variables', [])
        
        if affected_variables and max_capacity < float('inf'):
            variables_sum = sum(
                self.variables.get(var_name, 0) 
                for var_name in affected_variables 
                if var_name in self.variables
            )
            return self.solver.Add(variables_sum <= max_capacity)
        return None
    
    def _create_time_window_constraint(self, constraint: Constraint):
        """创建时间窗口约束"""
        time_var = constraint.parameters.get('time_variable')
        time_window = constraint.parameters.get('time_window')
        
        if time_var and time_window and time_var in self.variables:
            start_hours = time_window.start_time.timestamp() / 3600
            end_hours = time_window.end_time.timestamp() / 3600
            
            constraint_obj = self.solver.Add(self.variables[time_var] >= start_hours)
            self.solver.Add(self.variables[time_var] <= end_hours)
            return constraint_obj
        return None
    
    def _create_sequence_constraint(self, constraint: Constraint):
        """创建顺序约束"""
        predecessor = constraint.parameters.get('predecessor_variable')
        successor = constraint.parameters.get('successor_variable')
        min_gap = constraint.parameters.get('min_gap', 0)
        
        if (predecessor and successor and 
            predecessor in self.variables and successor in self.variables):
            return self.solver.Add(
                self.variables[successor] >= self.variables[predecessor] + min_gap
            )
        return None
    
    def _set_objective(self, objective_function: Callable):
        """设置目标函数"""
        # 这里需要根据具体的目标函数实现
        # 简化示例：最大化变量总和
        if self.variables:
            objective_expr = sum(self.variables.values())
            self.solver.Maximize(objective_expr)
    
    def _extract_solution(self, constraints: List[Constraint], solving_time: float) -> Solution:
        """提取求解结果"""
        
        plan_assignments = {}
        resource_allocations = {}
        
        # 提取变量值
        for var_name, var_obj in self.variables.items():
            value = var_obj.solution_value()
            # 根据变量名称分类到计划分配或资源分配
            if var_name.startswith('plan_'):
                plan_assignments[var_name] = {'value': value}
            elif var_name.startswith('resource_'):
                resource_allocations[var_name] = {'value': value}
        
        # 验证约束违反
        constraint_violations = self._check_constraint_violations(
            constraints, plan_assignments, resource_allocations
        )
        
        objective_value = self.solver.Objective().Value()
        is_feasible = len([v for v in constraint_violations if v.violation_type == ViolationType.HARD_VIOLATION]) == 0
        
        return Solution(
            solution_id=f"LP_SOL_{int(time.time())}",
            plan_assignments=plan_assignments,
            resource_allocations=resource_allocations,
            objective_value=objective_value,
            is_feasible=is_feasible,
            constraint_violations=constraint_violations,
            total_penalty=sum(v.violation_penalty for v in constraint_violations),
            solution_quality=self._calculate_solution_quality(objective_value, constraint_violations),
            solving_time=solving_time,
            algorithm_used="linear_programming"
        )
    
    def _create_infeasible_solution(self, constraints: List[Constraint], solving_time: float) -> Solution:
        """创建不可行解决方案"""
        return Solution(
            solution_id=f"LP_INFEAS_{int(time.time())}",
            plan_assignments={},
            resource_allocations={},
            objective_value=float('-inf'),
            is_feasible=False,
            constraint_violations=[],
            total_penalty=float('inf'),
            solution_quality=0.0,
            solving_time=solving_time,
            algorithm_used="linear_programming"
        )
    
    def _create_error_solution(self, error_msg: str, constraints: List[Constraint], solving_time: float) -> Solution:
        """创建错误解决方案"""
        return Solution(
            solution_id=f"LP_ERROR_{int(time.time())}",
            plan_assignments={},
            resource_allocations={},
            objective_value=float('-inf'),
            is_feasible=False,
            constraint_violations=[
                ConstraintViolation(
                    constraint_id="SOLVER_ERROR",
                    constraint_name="求解器错误",
                    violation_type=ViolationType.HARD_VIOLATION,
                    violation_degree=1.0,
                    violation_penalty=1000.0,
                    violation_reason=error_msg,
                    affected_plans=[],
                    affected_resources=[],
                    suggested_fixes=["检查求解器配置", "简化约束模型", "使用启发式算法"]
                )
            ],
            total_penalty=float('inf'),
            solution_quality=0.0,
            solving_time=solving_time,
            algorithm_used="linear_programming"
        )
    
    def _check_constraint_violations(
        self,
        constraints: List[Constraint],
        plan_assignments: Dict[str, Any],
        resource_allocations: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """检查约束违反"""
        violations = []
        
        for constraint in constraints:
            solution_state = {
                'plan_assignments': plan_assignments,
                'resource_allocations': resource_allocations
            }
            
            violation_degree, violation_reason = constraint.evaluate_violation(solution_state)
            
            if violation_degree > 0:
                violation_type = ViolationType.HARD_VIOLATION if constraint.is_hard_constraint else ViolationType.SOFT_VIOLATION
                violation_penalty = violation_degree * constraint.violation_penalty
                
                violation = ConstraintViolation(
                    constraint_id=constraint.constraint_id,
                    constraint_name=constraint.constraint_name,
                    violation_type=violation_type,
                    violation_degree=violation_degree,
                    violation_penalty=violation_penalty,
                    violation_reason=violation_reason,
                    affected_plans=constraint.applicable_plans,
                    affected_resources=constraint.applicable_machines,
                    suggested_fixes=self._generate_fix_suggestions(constraint, violation_degree)
                )
                violations.append(violation)
        
        return violations
    
    def _generate_fix_suggestions(self, constraint: Constraint, violation_degree: float) -> List[str]:
        """生成修复建议"""
        suggestions = []
        
        if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
            suggestions.extend([
                "增加机台产能",
                "重新分配生产任务",
                "调整生产时间窗口",
                "考虑外包部分生产"
            ])
        elif constraint.constraint_type == ConstraintType.TIME_WINDOW:
            suggestions.extend([
                "调整计划执行时间",
                "扩展时间窗口",
                "重新安排任务优先级",
                "考虑加班生产"
            ])
        elif constraint.constraint_type == ConstraintType.WORK_CALENDAR:
            suggestions.extend([
                "调整至工作日执行",
                "安排节假日加班",
                "重新分配到其他时间段",
                "调整生产计划"
            ])
        
        if violation_degree > 0.8:
            suggestions.append("考虑放宽约束条件")
        
        return suggestions
    
    def _calculate_solution_quality(self, objective_value: float, violations: List[ConstraintViolation]) -> float:
        """计算解决方案质量"""
        if not violations:
            return 100.0
        
        # 基于违反程度和惩罚值计算质量分数
        total_penalty = sum(v.violation_penalty for v in violations)
        hard_violations = len([v for v in violations if v.violation_type == ViolationType.HARD_VIOLATION])
        
        if hard_violations > 0:
            return max(0.0, 50.0 - hard_violations * 10)
        
        # 软约束违反的质量计算
        quality_reduction = min(50.0, total_penalty / 100.0)
        return max(0.0, 100.0 - quality_reduction)
    
    def validate_solution(self, solution: Solution, constraints: List[Constraint]) -> bool:
        """验证解决方案可行性"""
        hard_violations = [
            v for v in solution.constraint_violations 
            if v.violation_type == ViolationType.HARD_VIOLATION
        ]
        return len(hard_violations) == 0


class HeuristicConstraintSolver(ConstraintSolver):
    """启发式约束求解器"""
    
    def __init__(self, max_iterations: int = 1000, improvement_threshold: float = 0.001):
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.iteration_count = 0
    
    async def solve(
        self,
        constraints: List[Constraint],
        objective_function: Callable,
        variables: Dict[str, Any],
        config: OptimizationConfig
    ) -> Solution:
        """启发式约束求解实现"""
        
        start_time = time.time()
        logger.info("开始启发式约束求解")
        
        try:
            # 生成初始解
            current_solution = await self._generate_initial_solution(
                constraints, variables, config
            )
            
            # 迭代改进
            best_solution = current_solution
            best_quality = current_solution.solution_quality
            
            for iteration in range(self.max_iterations):
                self.iteration_count = iteration + 1
                
                # 局部搜索改进
                improved_solution = await self._local_search_improvement(
                    current_solution, constraints, objective_function, config
                )
                
                # 评估改进
                improved_quality = improved_solution.solution_quality
                
                if improved_quality > best_quality + self.improvement_threshold:
                    best_solution = improved_solution
                    current_solution = improved_solution
                    best_quality = improved_quality
                    logger.debug(f"迭代 {iteration}: 解决方案质量提升至 {best_quality:.2f}")
                
                # 收敛检查
                if iteration > 10 and (improved_quality - best_quality) < self.improvement_threshold:
                    logger.info(f"启发式算法收敛，迭代次数: {iteration}")
                    break
                
                # 时间限制检查
                if time.time() - start_time > config.max_solving_time:
                    logger.info(f"达到时间限制，停止求解")
                    break
            
            solving_time = time.time() - start_time
            best_solution.solving_time = solving_time
            best_solution.algorithm_used = "heuristic"
            
            logger.info(f"启发式求解完成，质量评分: {best_solution.solution_quality:.2f}，耗时: {solving_time:.2f}秒")
            return best_solution
        
        except Exception as e:
            logger.error(f"启发式求解过程异常: {str(e)}")
            solving_time = time.time() - start_time
            return self._create_error_solution(str(e), solving_time)
    
    async def _generate_initial_solution(
        self,
        constraints: List[Constraint],
        variables: Dict[str, Any],
        config: OptimizationConfig
    ) -> Solution:
        """生成初始解决方案"""
        
        # 使用贪心策略生成初始解
        plan_assignments = {}
        resource_allocations = {}
        
        # 按优先级排序约束
        sorted_constraints = sorted(
            constraints, 
            key=lambda c: c.priority.value, 
            reverse=True
        )
        
        # 逐步分配变量值
        for var_name, var_config in variables.items():
            if var_name.startswith('plan_'):
                plan_assignments[var_name] = self._assign_plan_variable(
                    var_name, var_config, sorted_constraints
                )
            elif var_name.startswith('resource_'):
                resource_allocations[var_name] = self._assign_resource_variable(
                    var_name, var_config, sorted_constraints
                )
        
        # 评估初始解
        constraint_violations = self._evaluate_constraints(
            constraints, plan_assignments, resource_allocations
        )
        
        is_feasible = len([v for v in constraint_violations if v.violation_type == ViolationType.HARD_VIOLATION]) == 0
        total_penalty = sum(v.violation_penalty for v in constraint_violations)
        solution_quality = self._calculate_heuristic_quality(constraint_violations, total_penalty)
        
        return Solution(
            solution_id=f"HEUR_INIT_{int(time.time())}",
            plan_assignments=plan_assignments,
            resource_allocations=resource_allocations,
            objective_value=0.0,  # 将在后续计算
            is_feasible=is_feasible,
            constraint_violations=constraint_violations,
            total_penalty=total_penalty,
            solution_quality=solution_quality,
            solving_time=0.0,
            algorithm_used="heuristic_initial"
        )
    
    def _assign_plan_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """分配计划变量值"""
        
        var_type = var_config.get('type', 'continuous')
        lower_bound = var_config.get('lower_bound', 0)
        upper_bound = var_config.get('upper_bound', 100)
        
        # 检查相关约束
        relevant_constraints = [
            c for c in constraints 
            if var_name in c.parameters.get('variables', [])
        ]
        
        # 基于约束确定合适的值
        if var_type == 'binary':
            # 二进制变量，优先满足硬约束
            hard_constraints = [c for c in relevant_constraints if c.is_hard_constraint]
            if hard_constraints:
                # 简化：如果有硬约束，设为1，否则设为0
                value = 1 if any(c.priority.value >= 8 for c in hard_constraints) else 0
            else:
                value = 1  # 默认启用
        elif var_type == 'integer':
            # 整数变量，取中间值
            value = int((lower_bound + upper_bound) / 2)
        else:
            # 连续变量，根据约束调整
            value = (lower_bound + upper_bound) / 2
            
            # 如果有容量约束，调整到容量范围内
            for constraint in relevant_constraints:
                if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
                    max_capacity = constraint.parameters.get('max_capacity', upper_bound)
                    value = min(value, max_capacity * 0.8)  # 留20%缓冲
        
        return {
            'value': value,
            'assigned_time': datetime.now(),
            'constraints_considered': [c.constraint_id for c in relevant_constraints]
        }
    
    def _assign_resource_variable(
        self,
        var_name: str,
        var_config: Dict[str, Any],
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """分配资源变量值"""
        
        # 类似于计划变量的分配逻辑，但考虑资源特性
        var_type = var_config.get('type', 'continuous')
        lower_bound = var_config.get('lower_bound', 0)
        upper_bound = var_config.get('upper_bound', 100)
        
        if var_type == 'binary':
            value = 1  # 资源默认可用
        else:
            value = upper_bound * 0.7  # 资源分配70%的容量
        
        return {
            'value': value,
            'capacity_utilization': 0.7,
            'availability_status': 'available'
        }
    
    async def _local_search_improvement(
        self,
        current_solution: Solution,
        constraints: List[Constraint],
        objective_function: Callable,
        config: OptimizationConfig
    ) -> Solution:
        """局部搜索改进"""
        
        # 创建解决方案副本
        improved_solution = Solution(
            solution_id=f"HEUR_IMPROVED_{int(time.time())}",
            plan_assignments=current_solution.plan_assignments.copy(),
            resource_allocations=current_solution.resource_allocations.copy(),
            objective_value=current_solution.objective_value,
            is_feasible=current_solution.is_feasible,
            constraint_violations=current_solution.constraint_violations.copy(),
            total_penalty=current_solution.total_penalty,
            solution_quality=current_solution.solution_quality,
            solving_time=current_solution.solving_time,
            algorithm_used="heuristic_improved"
        )
        
        # 执行局部搜索操作
        improvement_operations = [
            self._swap_assignments,
            self._adjust_capacities,
            self._reschedule_times,
            self._rebalance_loads
        ]
        
        # 随机选择改进操作
        operation = np.random.choice(improvement_operations)
        await operation(improved_solution, constraints)
        
        # 重新评估解决方案
        constraint_violations = self._evaluate_constraints(
            constraints, 
            improved_solution.plan_assignments, 
            improved_solution.resource_allocations
        )
        
        improved_solution.constraint_violations = constraint_violations
        improved_solution.total_penalty = sum(v.violation_penalty for v in constraint_violations)
        improved_solution.solution_quality = self._calculate_heuristic_quality(
            constraint_violations, improved_solution.total_penalty
        )
        improved_solution.is_feasible = len([
            v for v in constraint_violations 
            if v.violation_type == ViolationType.HARD_VIOLATION
        ]) == 0
        
        return improved_solution
    
    async def _swap_assignments(self, solution: Solution, constraints: List[Constraint]):
        """交换分配操作"""
        plan_keys = list(solution.plan_assignments.keys())
        if len(plan_keys) >= 2:
            # 随机选择两个计划进行交换
            key1, key2 = np.random.choice(plan_keys, 2, replace=False)
            
            # 交换分配值
            val1 = solution.plan_assignments[key1].get('value', 0)
            val2 = solution.plan_assignments[key2].get('value', 0)
            
            solution.plan_assignments[key1]['value'] = val2
            solution.plan_assignments[key2]['value'] = val1
    
    async def _adjust_capacities(self, solution: Solution, constraints: List[Constraint]):
        """调整容量分配"""
        for key, assignment in solution.resource_allocations.items():
            current_value = assignment.get('value', 0)
            
            # 随机调整 ±10%
            adjustment_factor = 1.0 + (np.random.random() - 0.5) * 0.2
            new_value = current_value * adjustment_factor
            
            assignment['value'] = max(0, new_value)
    
    async def _reschedule_times(self, solution: Solution, constraints: List[Constraint]):
        """重新安排时间"""
        # 查找时间相关的约束
        time_constraints = [
            c for c in constraints 
            if c.constraint_type in [ConstraintType.TIME_WINDOW, ConstraintType.DEADLINE]
        ]
        
        for constraint in time_constraints:
            if constraint.applicable_plans:
                for plan_id in constraint.applicable_plans:
                    plan_key = f"plan_{plan_id}"
                    if plan_key in solution.plan_assignments:
                        # 在时间窗口内随机调整时间
                        time_window = constraint.parameters.get('time_window')
                        if time_window:
                            duration = time_window.duration_hours()
                            random_offset = np.random.random() * duration
                            new_time = time_window.start_time + timedelta(hours=random_offset)
                            solution.plan_assignments[plan_key]['assigned_time'] = new_time
    
    async def _rebalance_loads(self, solution: Solution, constraints: List[Constraint]):
        """重新平衡负载"""
        # 计算当前负载分布
        resource_loads = {}
        for key, allocation in solution.resource_allocations.items():
            utilization = allocation.get('capacity_utilization', 0)
            resource_loads[key] = utilization
        
        if len(resource_loads) >= 2:
            # 找到负载最高和最低的资源
            sorted_resources = sorted(resource_loads.items(), key=lambda x: x[1])
            lowest_load_resource = sorted_resources[0][0]
            highest_load_resource = sorted_resources[-1][0]
            
            # 在高负载和低负载资源间转移部分负载
            if resource_loads[highest_load_resource] > resource_loads[lowest_load_resource] + 0.2:
                transfer_amount = (resource_loads[highest_load_resource] - resource_loads[lowest_load_resource]) * 0.1
                
                solution.resource_allocations[highest_load_resource]['capacity_utilization'] -= transfer_amount
                solution.resource_allocations[lowest_load_resource]['capacity_utilization'] += transfer_amount
    
    def _evaluate_constraints(
        self,
        constraints: List[Constraint],
        plan_assignments: Dict[str, Any],
        resource_allocations: Dict[str, Any]
    ) -> List[ConstraintViolation]:
        """评估约束违反"""
        violations = []
        
        for constraint in constraints:
            solution_state = {
                'plan_assignments': plan_assignments,
                'resource_allocations': resource_allocations
            }
            
            violation_degree, violation_reason = constraint.evaluate_violation(solution_state)
            
            if violation_degree > 0:
                violation_type = ViolationType.HARD_VIOLATION if constraint.is_hard_constraint else ViolationType.SOFT_VIOLATION
                violation_penalty = violation_degree * constraint.violation_penalty
                
                violation = ConstraintViolation(
                    constraint_id=constraint.constraint_id,
                    constraint_name=constraint.constraint_name,
                    violation_type=violation_type,
                    violation_degree=violation_degree,
                    violation_penalty=violation_penalty,
                    violation_reason=violation_reason,
                    affected_plans=constraint.applicable_plans,
                    affected_resources=constraint.applicable_machines,
                    suggested_fixes=self._generate_heuristic_fixes(constraint)
                )
                violations.append(violation)
        
        return violations
    
    def _generate_heuristic_fixes(self, constraint: Constraint) -> List[str]:
        """生成启发式修复建议"""
        fixes = []
        
        if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
            fixes.extend([
                "减少机台分配负载",
                "增加并行机台处理",
                "优化生产效率",
                "调整批次大小"
            ])
        elif constraint.constraint_type == ConstraintType.TIME_WINDOW:
            fixes.extend([
                "调整至允许时间范围",
                "重新排序任务优先级",
                "压缩任务执行时间",
                "启用弹性时间窗口"
            ])
        elif constraint.constraint_type == ConstraintType.WORK_CALENDAR:
            fixes.extend([
                "移至工作日执行",
                "调整工作日历设置",
                "安排特殊工作安排",
                "重新分配到其他时段"
            ])
        
        return fixes
    
    def _calculate_heuristic_quality(
        self,
        violations: List[ConstraintViolation],
        total_penalty: float
    ) -> float:
        """计算启发式解决方案质量"""
        if not violations:
            return 100.0
        
        hard_violations = [v for v in violations if v.violation_type == ViolationType.HARD_VIOLATION]
        soft_violations = [v for v in violations if v.violation_type == ViolationType.SOFT_VIOLATION]
        
        # 硬约束违反严重影响质量
        hard_penalty = len(hard_violations) * 30
        
        # 软约束违反适度影响质量
        soft_penalty = min(40, total_penalty / 50)
        
        quality = max(0.0, 100.0 - hard_penalty - soft_penalty)
        return quality
    
    def _create_error_solution(self, error_msg: str, solving_time: float) -> Solution:
        """创建错误解决方案"""
        return Solution(
            solution_id=f"HEUR_ERROR_{int(time.time())}",
            plan_assignments={},
            resource_allocations={},
            objective_value=float('-inf'),
            is_feasible=False,
            constraint_violations=[
                ConstraintViolation(
                    constraint_id="HEURISTIC_ERROR",
                    constraint_name="启发式求解错误",
                    violation_type=ViolationType.HARD_VIOLATION,
                    violation_degree=1.0,
                    violation_penalty=1000.0,
                    violation_reason=error_msg,
                    affected_plans=[],
                    affected_resources=[],
                    suggested_fixes=["简化约束模型", "调整算法参数", "检查输入数据"]
                )
            ],
            total_penalty=float('inf'),
            solution_quality=0.0,
            solving_time=solving_time,
            algorithm_used="heuristic"
        )
    
    def validate_solution(self, solution: Solution, constraints: List[Constraint]) -> bool:
        """验证解决方案可行性"""
        hard_violations = [
            v for v in solution.constraint_violations 
            if v.violation_type == ViolationType.HARD_VIOLATION
        ]
        return len(hard_violations) == 0


class HybridConstraintSolver(ConstraintSolver):
    """混合约束求解器（线性规划+启发式）"""
    
    def __init__(self, lp_time_ratio: float = 0.6, heuristic_time_ratio: float = 0.4):
        self.lp_time_ratio = lp_time_ratio
        self.heuristic_time_ratio = heuristic_time_ratio
        self.lp_solver = LinearProgrammingSolver()
        self.heuristic_solver = HeuristicConstraintSolver()
    
    async def solve(
        self,
        constraints: List[Constraint],
        objective_function: Callable,
        variables: Dict[str, Any],
        config: OptimizationConfig
    ) -> Solution:
        """混合求解实现"""
        
        start_time = time.time()
        logger.info("开始混合约束求解")
        
        # 阶段1：线性规划求解
        lp_time_limit = int(config.max_solving_time * self.lp_time_ratio)
        lp_config = OptimizationConfig(
            max_solving_time=lp_time_limit,
            gap_tolerance=config.gap_tolerance,
            solution_limit=config.solution_limit,
            hard_constraint_penalty=config.hard_constraint_penalty,
            soft_constraint_penalty=config.soft_constraint_penalty
        )
        
        try:
            logger.info(f"阶段1：线性规划求解（{lp_time_limit}秒）")
            lp_solution = await self.lp_solver.solve(constraints, objective_function, variables, lp_config)
            
            logger.info(f"线性规划阶段完成，质量评分: {lp_solution.solution_quality:.2f}")
            
            # 如果线性规划解质量足够好，直接返回
            if lp_solution.solution_quality >= 90.0 and lp_solution.is_feasible:
                lp_solution.algorithm_used = "hybrid_lp_optimal"
                return lp_solution
            
        except Exception as e:
            logger.warning(f"线性规划阶段失败: {str(e)}，转至启发式求解")
            lp_solution = None
        
        # 阶段2：启发式求解改进
        heuristic_time_limit = int(config.max_solving_time * self.heuristic_time_ratio)
        heuristic_config = OptimizationConfig(
            max_solving_time=heuristic_time_limit,
            gap_tolerance=config.gap_tolerance,
            solution_limit=config.solution_limit,
            hard_constraint_penalty=config.hard_constraint_penalty,
            soft_constraint_penalty=config.soft_constraint_penalty
        )
        
        logger.info(f"阶段2：启发式求解改进（{heuristic_time_limit}秒）")
        heuristic_solution = await self.heuristic_solver.solve(
            constraints, objective_function, variables, heuristic_config
        )
        
        logger.info(f"启发式阶段完成，质量评分: {heuristic_solution.solution_quality:.2f}")
        
        # 选择更好的解决方案
        solving_time = time.time() - start_time
        
        if lp_solution and lp_solution.solution_quality > heuristic_solution.solution_quality:
            logger.info("采用线性规划解决方案")
            lp_solution.solving_time = solving_time
            lp_solution.algorithm_used = "hybrid_lp_better"
            return lp_solution
        else:
            logger.info("采用启发式解决方案")
            heuristic_solution.solving_time = solving_time
            heuristic_solution.algorithm_used = "hybrid_heuristic_better"
            return heuristic_solution
    
    def validate_solution(self, solution: Solution, constraints: List[Constraint]) -> bool:
        """验证解决方案可行性"""
        hard_violations = [
            v for v in solution.constraint_violations 
            if v.violation_type == ViolationType.HARD_VIOLATION
        ]
        return len(hard_violations) == 0


# =============================================================================
# 主约束求解器类
# =============================================================================

class MonthlyConstraintSolver(BaseAlgorithm):
    """
    月度约束求解算法主类
    
    支持复杂约束求解、软硬约束处理、多种求解策略、约束冲突分析和解决方案优化。
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None, config: Optional[Dict] = None):
        """
        初始化约束求解器
        
        Args:
            db_session: 数据库会话
            config: 配置参数
        """
        super().__init__(AlgorithmType.CONSTRAINT_SOLVER, config)
        
        self.db_session = db_session
        self.solving_history = []
        self.performance_metrics = {
            'total_problems_solved': 0,
            'average_solving_time': 0.0,
            'success_rate': 0.0,
            'best_quality_achieved': 0.0,
            'constraint_types_handled': set()
        }
        
        # 初始化求解器
        self.solvers = {
            SolverStrategy.LINEAR_PROGRAMMING: LinearProgrammingSolver(),
            SolverStrategy.HEURISTIC: HeuristicConstraintSolver(),
            SolverStrategy.HYBRID: HybridConstraintSolver()
        }
        
        self.default_config = OptimizationConfig()
    
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """
        执行约束求解（BaseAlgorithm接口实现）
        
        Args:
            input_data: 输入数据，应包含约束、变量和目标函数
            **kwargs: 额外参数
            
        Returns:
            Solution: 求解结果
        """
        
        if isinstance(input_data, dict):
            constraints = input_data.get('constraints', [])
            variables = input_data.get('variables', {})
            objective_function = input_data.get('objective_function')
            strategy = input_data.get('strategy', SolverStrategy.HYBRID)
            config = input_data.get('config', self.default_config)
        else:
            constraints = kwargs.get('constraints', [])
            variables = kwargs.get('variables', {})
            objective_function = kwargs.get('objective_function')
            strategy = kwargs.get('strategy', SolverStrategy.HYBRID)
            config = kwargs.get('config', self.default_config)
        
        return await self.solve_constraints(
            constraints=constraints,
            variables=variables,
            objective_function=objective_function,
            strategy=strategy,
            config=config
        )
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            bool: 是否有效
        """
        if isinstance(input_data, dict):
            constraints = input_data.get('constraints', [])
            variables = input_data.get('variables', {})
        else:
            return False
        
        # 基本验证
        if not constraints:
            logger.warning("约束列表为空")
            return False
        
        if not variables:
            logger.warning("变量字典为空")
            return False
        
        # 验证约束格式
        for constraint in constraints:
            if not isinstance(constraint, Constraint):
                logger.warning(f"约束 {constraint} 格式不正确")
                return False
        
        return True
    
    async def solve_constraints(
        self,
        constraints: List[Constraint],
        variables: Dict[str, Any],
        objective_function: Optional[Callable] = None,
        strategy: SolverStrategy = SolverStrategy.HYBRID,
        config: Optional[OptimizationConfig] = None
    ) -> Solution:
        """
        求解约束满足问题
        
        Args:
            constraints: 约束条件列表
            variables: 决策变量字典
            objective_function: 目标函数
            strategy: 求解策略
            config: 优化配置
            
        Returns:
            Solution: 求解结果
        """
        start_time = time.time()
        problem_id = f"CSP_{int(start_time)}"
        
        try:
            logger.info(f"开始约束求解 {problem_id}，策略: {strategy.value}")
            
            # 参数验证和默认值设置
            if config is None:
                config = self.default_config
            
            if objective_function is None:
                objective_function = self._default_objective_function
            
            # 预处理约束和变量
            if config.enable_preprocessing:
                constraints = await self._preprocess_constraints(constraints)
                variables = await self._preprocess_variables(variables, constraints)
            
            # 约束一致性检查
            consistency_check = await self._check_constraint_consistency(constraints)
            if not consistency_check['is_consistent']:
                logger.warning(f"约束不一致: {consistency_check['conflicts']}")
            
            # 选择并执行求解器
            solver = self.solvers.get(strategy)
            if not solver:
                raise InvalidInputError(f"不支持的求解策略: {strategy}")
            
            # 执行求解
            solution = await solver.solve(constraints, objective_function, variables, config)
            
            # 后处理解决方案
            solution = await self._postprocess_solution(solution, constraints)
            
            # 更新历史记录和性能指标
            self.solving_history.append(solution)
            self._update_performance_metrics(solution, constraints)
            
            solving_time = time.time() - start_time
            logger.info(f"约束求解完成，耗时: {solving_time:.2f}秒，质量评分: {solution.solution_quality:.2f}")
            
            return solution
            
        except Exception as e:
            logger.error(f"约束求解失败: {str(e)}")
            solving_time = time.time() - start_time
            self.performance_metrics['total_problems_solved'] += 1
            raise
    
    async def validate_solution(self, solution: Solution, constraints: List[Constraint]) -> Dict[str, Any]:
        """
        验证解决方案的可行性和质量
        
        Args:
            solution: 解决方案
            constraints: 约束条件列表
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        logger.info(f"开始验证解决方案 {solution.solution_id}")
        
        validation_result = {
            'is_valid': True,
            'is_feasible': solution.is_feasible,
            'quality_score': solution.solution_quality,
            'hard_violations': [],
            'soft_violations': [],
            'constraint_satisfaction_rate': 0.0,
            'recommendations': []
        }
        
        # 重新验证所有约束
        hard_violations = []
        soft_violations = []
        
        for constraint in constraints:
            solution_state = {
                'plan_assignments': solution.plan_assignments,
                'resource_allocations': solution.resource_allocations
            }
            
            violation_degree, violation_reason = constraint.evaluate_violation(solution_state)
            
            if violation_degree > 0:
                violation_info = {
                    'constraint_id': constraint.constraint_id,
                    'constraint_name': constraint.constraint_name,
                    'violation_degree': violation_degree,
                    'violation_reason': violation_reason
                }
                
                if constraint.is_hard_constraint:
                    hard_violations.append(violation_info)
                else:
                    soft_violations.append(violation_info)
        
        validation_result['hard_violations'] = hard_violations
        validation_result['soft_violations'] = soft_violations
        
        # 计算约束满足率
        total_constraints = len(constraints)
        violated_constraints = len(hard_violations) + len(soft_violations)
        validation_result['constraint_satisfaction_rate'] = (total_constraints - violated_constraints) / total_constraints
        
        # 可行性判断
        validation_result['is_feasible'] = len(hard_violations) == 0
        validation_result['is_valid'] = validation_result['is_feasible'] and solution.solution_quality > 50.0
        
        # 生成改进建议
        if not validation_result['is_valid']:
            validation_result['recommendations'] = await self._generate_improvement_recommendations(
                solution, constraints, hard_violations, soft_violations
            )
        
        return validation_result
    
    async def optimize_with_constraints(
        self,
        monthly_plans: List[MonthlyPlanItem],
        machine_configs: List[Dict[str, Any]],
        work_calendar: Dict[str, Any],
        optimization_objectives: Optional[Dict[str, float]] = None,
        constraint_preferences: Optional[Dict[str, float]] = None
    ) -> Solution:
        """
        基于月度计划和约束进行优化
        
        Args:
            monthly_plans: 月度计划列表
            machine_configs: 机台配置列表
            work_calendar: 工作日历
            optimization_objectives: 优化目标权重
            constraint_preferences: 约束偏好设置
            
        Returns:
            Solution: 优化解决方案
        """
        logger.info("开始基于月度计划的约束优化")
        
        # 生成约束条件
        constraints = await self._generate_constraints_from_plans(
            monthly_plans, machine_configs, work_calendar, constraint_preferences
        )
        
        # 生成决策变量
        variables = await self._generate_variables_from_plans(monthly_plans, machine_configs)
        
        # 生成目标函数
        objective_function = self._create_objective_function(optimization_objectives)
        
        # 执行约束求解
        solution = await self.solve_constraints(
            constraints=constraints,
            variables=variables,
            objective_function=objective_function,
            strategy=SolverStrategy.HYBRID
        )
        
        return solution
    
    async def analyze_constraint_conflicts(
        self,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        分析约束冲突
        
        Args:
            constraints: 约束条件列表
            
        Returns:
            Dict[str, Any]: 冲突分析结果
        """
        logger.info("开始分析约束冲突")
        
        conflict_analysis = {
            'has_conflicts': False,
            'conflict_groups': [],
            'irreconcilable_constraints': [],
            'suggested_resolutions': [],
            'conflict_severity': 'low'
        }
        
        # 检查时间窗口冲突
        time_conflicts = await self._detect_time_window_conflicts(constraints)
        if time_conflicts:
            conflict_analysis['conflict_groups'].extend(time_conflicts)
            conflict_analysis['has_conflicts'] = True
        
        # 检查容量冲突
        capacity_conflicts = await self._detect_capacity_conflicts(constraints)
        if capacity_conflicts:
            conflict_analysis['conflict_groups'].extend(capacity_conflicts)
            conflict_analysis['has_conflicts'] = True
        
        # 检查逻辑冲突
        logic_conflicts = await self._detect_logic_conflicts(constraints)
        if logic_conflicts:
            conflict_analysis['irreconcilable_constraints'].extend(logic_conflicts)
            conflict_analysis['has_conflicts'] = True
        
        # 确定冲突严重程度
        if conflict_analysis['irreconcilable_constraints']:
            conflict_analysis['conflict_severity'] = 'critical'
        elif len(conflict_analysis['conflict_groups']) > 5:
            conflict_analysis['conflict_severity'] = 'high'
        elif len(conflict_analysis['conflict_groups']) > 2:
            conflict_analysis['conflict_severity'] = 'medium'
        
        # 生成解决建议
        if conflict_analysis['has_conflicts']:
            conflict_analysis['suggested_resolutions'] = await self._suggest_conflict_resolutions(
                conflict_analysis['conflict_groups'], 
                conflict_analysis['irreconcilable_constraints']
            )
        
        return conflict_analysis
    
    def get_solving_statistics(self) -> Dict[str, Any]:
        """
        获取求解统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            'performance_metrics': self.performance_metrics.copy(),
            'recent_solutions': [
                {
                    'solution_id': sol.solution_id,
                    'quality': sol.solution_quality,
                    'feasible': sol.is_feasible,
                    'solving_time': sol.solving_time,
                    'algorithm': sol.algorithm_used
                }
                for sol in self.solving_history[-10:]  # 最近10个解决方案
            ],
            'constraint_type_distribution': {
                constraint_type.value: sum(
                    1 for sol in self.solving_history 
                    for violation in sol.constraint_violations
                    if violation.constraint_id.startswith(constraint_type.value.upper())
                )
                for constraint_type in ConstraintType
            }
        }
    
    # === 私有方法 ===
    
    def _default_objective_function(self, solution_state: Dict[str, Any]) -> float:
        """默认目标函数"""
        # 简化的目标函数：最大化计划完成度，最小化约束违反
        completion_score = sum(
            assignment.get('value', 0) 
            for assignment in solution_state.get('plan_assignments', {}).values()
        )
        
        violation_penalty = sum(
            violation.violation_penalty 
            for violation in solution_state.get('constraint_violations', [])
        )
        
        return completion_score - violation_penalty
    
    async def _preprocess_constraints(self, constraints: List[Constraint]) -> List[Constraint]:
        """预处理约束条件"""
        logger.debug("执行约束预处理")
        
        # 去除重复约束
        unique_constraints = []
        constraint_ids = set()
        
        for constraint in constraints:
            if constraint.constraint_id not in constraint_ids:
                unique_constraints.append(constraint)
                constraint_ids.add(constraint.constraint_id)
            else:
                logger.debug(f"去除重复约束: {constraint.constraint_id}")
        
        # 约束优先级排序
        unique_constraints.sort(key=lambda c: c.priority.value, reverse=True)
        
        # 约束简化（合并相似约束）
        simplified_constraints = await self._simplify_constraints(unique_constraints)
        
        logger.debug(f"约束预处理完成: {len(constraints)} -> {len(simplified_constraints)}")
        return simplified_constraints
    
    async def _simplify_constraints(self, constraints: List[Constraint]) -> List[Constraint]:
        """简化约束（合并相似约束）"""
        if not constraints:
            return constraints
        
        # 按约束类型分组
        constraint_groups = defaultdict(list)
        for constraint in constraints:
            constraint_groups[constraint.constraint_type].append(constraint)
        
        simplified_constraints = []
        
        for constraint_type, group_constraints in constraint_groups.items():
            if len(group_constraints) <= 1:
                simplified_constraints.extend(group_constraints)
                continue
            
            # 尝试合并相似的约束
            if constraint_type in [ConstraintType.CAPACITY_LIMIT, ConstraintType.RESOURCE_AVAILABILITY]:
                # 合并容量和资源约束
                merged_constraint = await self._merge_capacity_constraints(group_constraints)
                if merged_constraint:
                    simplified_constraints.append(merged_constraint)
                else:
                    simplified_constraints.extend(group_constraints)
            else:
                # 其他类型的约束保持不变
                simplified_constraints.extend(group_constraints)
        
        return simplified_constraints
    
    async def _merge_capacity_constraints(self, constraints: List[Constraint]) -> Optional[Constraint]:
        """合并容量约束"""
        if not constraints:
            return None
        
        # 找到相同机器的约束
        machine_constraints = defaultdict(list)
        for constraint in constraints:
            machine_id = constraint.parameters.get('machine_id')
            if machine_id:
                machine_constraints[machine_id].append(constraint)
        
        merged_constraints = []
        
        for machine_id, machine_group in machine_constraints.items():
            if len(machine_group) == 1:
                merged_constraints.extend(machine_group)
                continue
            
            # 合并相同机器的约束
            total_capacity = sum(
                constraint.parameters.get('capacity', 0) 
                for constraint in machine_group
            )
            
            merged_constraint = Constraint(
                constraint_id=f"MERGED_{machine_id}_CAPACITY",
                constraint_type=ConstraintType.CAPACITY_LIMIT,
                description=f"合并的机器{machine_id}容量约束",
                parameters={
                    'machine_id': machine_id,
                    'capacity': total_capacity,
                    'period': machine_group[0].parameters.get('period', 'daily')
                },
                priority=max(c.priority for c in machine_group),
                is_hard_constraint=all(c.is_hard_constraint for c in machine_group)
            )
            
            merged_constraints.append(merged_constraint)
        
        return merged_constraints[0] if len(merged_constraints) == 1 else None
    
    async def _preprocess_variables(
        self,
        variables: Dict[str, Any],
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """预处理决策变量"""
        logger.debug("执行变量预处理")
        
        # 变量范围调整
        processed_variables = {}
        
        for var_name, var_config in variables.items():
            new_config = var_config.copy()
            
            # 根据约束调整变量范围
            for constraint in constraints:
                if var_name in constraint.parameters.get('variables', []):
                    if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
                        max_capacity = constraint.parameters.get('max_capacity')
                        if max_capacity:
                            current_upper = new_config.get('upper_bound', float('inf'))
                            new_config['upper_bound'] = min(current_upper, max_capacity)
            
            processed_variables[var_name] = new_config
        
        return processed_variables
    
    async def _check_constraint_consistency(
        self,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """检查约束一致性"""
        
        consistency_result = {
            'is_consistent': True,
            'conflicts': [],
            'warnings': []
        }
        
        # 检查互斥约束
        for i, constraint1 in enumerate(constraints):
            for j, constraint2 in enumerate(constraints[i+1:], i+1):
                conflict = self._check_constraint_pair_conflict(constraint1, constraint2)
                if conflict:
                    consistency_result['conflicts'].append(conflict)
                    consistency_result['is_consistent'] = False
        
        return consistency_result
    
    def _check_constraint_pair_conflict(
        self,
        constraint1: Constraint,
        constraint2: Constraint
    ) -> Optional[Dict[str, Any]]:
        """检查两个约束之间的冲突"""
        
        # 检查时间窗口冲突
        if (constraint1.constraint_type == ConstraintType.TIME_WINDOW and
            constraint2.constraint_type == ConstraintType.TIME_WINDOW):
            
            window1 = constraint1.parameters.get('time_window')
            window2 = constraint2.parameters.get('time_window')
            
            if window1 and window2 and not window1.overlaps(window2):
                # 如果两个时间窗口不重叠，但要求同一资源，则冲突
                if (set(constraint1.applicable_machines) & 
                    set(constraint2.applicable_machines)):
                    return {
                        'type': 'time_window_conflict',
                        'constraint1': constraint1.constraint_id,
                        'constraint2': constraint2.constraint_id,
                        'description': '时间窗口不重叠但要求相同资源'
                    }
        
        # 检查容量冲突
        if (constraint1.constraint_type == ConstraintType.MACHINE_CAPACITY and
            constraint2.constraint_type == ConstraintType.MACHINE_CAPACITY):
            
            # 如果同一机台有两个不同的容量限制
            machines1 = set(constraint1.applicable_machines)
            machines2 = set(constraint2.applicable_machines)
            
            if machines1 & machines2:
                capacity1 = constraint1.parameters.get('max_capacity')
                capacity2 = constraint2.parameters.get('max_capacity')
                
                if capacity1 and capacity2 and capacity1 != capacity2:
                    return {
                        'type': 'capacity_conflict',
                        'constraint1': constraint1.constraint_id,
                        'constraint2': constraint2.constraint_id,
                        'description': f'同一机台容量限制冲突: {capacity1} vs {capacity2}'
                    }
        
        return None
    
    async def _postprocess_solution(
        self,
        solution: Solution,
        constraints: List[Constraint]
    ) -> Solution:
        """后处理解决方案"""
        logger.debug(f"执行解决方案后处理: {solution.solution_id}")
        
        # 解决方案修复
        if not solution.is_feasible:
            solution = await self._repair_infeasible_solution(solution, constraints)
        
        # 解决方案改进
        solution = await self._improve_solution(solution, constraints)
        
        return solution
    
    async def _repair_infeasible_solution(
        self,
        solution: Solution,
        constraints: List[Constraint]
    ) -> Solution:
        """修复不可行解决方案"""
        logger.debug("尝试修复不可行解决方案")
        
        # 识别最严重的约束违反
        hard_violations = [
            v for v in solution.constraint_violations
            if v.violation_type == ViolationType.HARD_VIOLATION
        ]
        
        if not hard_violations:
            return solution
        
        # 按违反程度排序
        hard_violations.sort(key=lambda v: v.violation_degree, reverse=True)
        
        # 尝试修复最严重的违反
        repaired_solution = solution
        
        for violation in hard_violations[:3]:  # 只修复前3个最严重的
            repaired_solution = await self._repair_single_violation(
                repaired_solution, violation, constraints
            )
        
        return repaired_solution
    
    async def _repair_single_violation(
        self,
        solution: Solution,
        violation: ConstraintViolation,
        constraints: List[Constraint]
    ) -> Solution:
        """修复单个约束违反"""
        
        # 找到对应的约束
        target_constraint = None
        for constraint in constraints:
            if constraint.constraint_id == violation.constraint_id:
                target_constraint = constraint
                break
        
        if not target_constraint:
            return solution
        
        # 根据约束类型执行修复
        if target_constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
            return await self._repair_capacity_violation(solution, target_constraint, violation)
        elif target_constraint.constraint_type == ConstraintType.TIME_WINDOW:
            return await self._repair_time_violation(solution, target_constraint, violation)
        else:
            # 通用修复：降低相关变量值
            return await self._repair_generic_violation(solution, target_constraint, violation)
    
    async def _repair_capacity_violation(
        self,
        solution: Solution,
        constraint: Constraint,
        violation: ConstraintViolation
    ) -> Solution:
        """修复容量违反"""
        max_capacity = constraint.parameters.get('max_capacity', float('inf'))
        affected_variables = constraint.parameters.get('variables', [])
        
        # 按比例降低相关变量值
        reduction_factor = 1.0 - (violation.violation_degree * 0.5)
        
        for var_name in affected_variables:
            if var_name in solution.plan_assignments:
                current_value = solution.plan_assignments[var_name].get('value', 0)
                solution.plan_assignments[var_name]['value'] = current_value * reduction_factor
            elif var_name in solution.resource_allocations:
                current_value = solution.resource_allocations[var_name].get('value', 0)
                solution.resource_allocations[var_name]['value'] = current_value * reduction_factor
        
        return solution
    
    async def _repair_time_violation(
        self,
        solution: Solution,
        constraint: Constraint,
        violation: ConstraintViolation
    ) -> Solution:
        """修复时间违反"""
        time_window = constraint.parameters.get('time_window')
        time_variable = constraint.parameters.get('time_variable')
        
        if time_window and time_variable:
            # 调整时间到窗口范围内
            if time_variable in solution.plan_assignments:
                solution.plan_assignments[time_variable]['assigned_time'] = time_window.start_time
        
        return solution
    
    async def _repair_generic_violation(
        self,
        solution: Solution,
        constraint: Constraint,
        violation: ConstraintViolation
    ) -> Solution:
        """通用约束违反修复"""
        # 简单策略：降低所有相关变量的值
        reduction_factor = 1.0 - (violation.violation_degree * 0.3)
        
        for plan_id in constraint.applicable_plans:
            plan_key = f"plan_{plan_id}"
            if plan_key in solution.plan_assignments:
                current_value = solution.plan_assignments[plan_key].get('value', 0)
                solution.plan_assignments[plan_key]['value'] = current_value * reduction_factor
        
        return solution
    
    async def _improve_solution(
        self,
        solution: Solution,
        constraints: List[Constraint]
    ) -> Solution:
        """改进解决方案"""
        # 实现局部搜索改进算法，通过调整解决方案来提高质量
        improved_solution = Solution(
            solution_id=f"IMPROVED_{solution.solution_id}",
            variables=solution.variables.copy(),
            objective_value=solution.objective_value,
            constraint_violations=solution.constraint_violations.copy(),
            is_feasible=solution.is_feasible,
            generation_time=solution.generation_time
        )
        
        # 局部搜索改进：尝试微调变量值
        improvement_found = True
        iteration = 0
        max_iterations = 10
        
        while improvement_found and iteration < max_iterations:
            improvement_found = False
            iteration += 1
            
            # 尝试改进每个变量
            for var_name, var_value in list(improved_solution.variables.items()):
                if not isinstance(var_value, (int, float)):
                    continue
                    
                # 尝试微调变量值
                for delta in [-0.1, -0.05, 0.05, 0.1]:
                    new_value = var_value + delta
                    if new_value < 0:
                        continue
                        
                    # 临时更新变量
                    old_value = improved_solution.variables[var_name]
                    improved_solution.variables[var_name] = new_value
                    
                    # 计算新的目标值
                    new_objective = self._calculate_objective_value(improved_solution.variables)
                    
                    # 如果有改进，保持新值
                    if new_objective > improved_solution.objective_value:
                        improved_solution.objective_value = new_objective
                        improvement_found = True
                        break
                    else:
                        # 恢复旧值
                        improved_solution.variables[var_name] = old_value
        
        return improved_solution
    
    def _calculate_objective_value(self, variables: Dict[str, Any]) -> float:
        """计算目标值"""
        # 简化目标函数：最大化所有变量的加权和
        total_value = 0.0
        
        for var_name, var_value in variables.items():
            if isinstance(var_value, (int, float)):
                # 不同变量类型的权重
                if 'utilization' in var_name:
                    total_value += var_value * 2.0  # 利用率权重高
                elif 'efficiency' in var_name:
                    total_value += var_value * 1.5  # 效率权重中等
                else:
                    total_value += var_value  # 默认权重
        
        return total_value
    
    def _update_performance_metrics(
        self,
        solution: Solution,
        constraints: List[Constraint]
    ):
        """更新性能指标"""
        self.performance_metrics['total_problems_solved'] += 1
        
        # 更新平均求解时间
        current_avg = self.performance_metrics['average_solving_time']
        count = self.performance_metrics['total_problems_solved']
        self.performance_metrics['average_solving_time'] = (
            (current_avg * (count - 1) + solution.solving_time) / count
        )
        
        # 更新成功率
        if solution.is_feasible:
            success_count = sum(1 for sol in self.solving_history if sol.is_feasible)
            self.performance_metrics['success_rate'] = success_count / count
        
        # 更新最佳质量
        if solution.solution_quality > self.performance_metrics['best_quality_achieved']:
            self.performance_metrics['best_quality_achieved'] = solution.solution_quality
        
        # 更新约束类型统计
        for constraint in constraints:
            self.performance_metrics['constraint_types_handled'].add(constraint.constraint_type.value)
    
    async def _generate_constraints_from_plans(
        self,
        monthly_plans: List[MonthlyPlanItem],
        machine_configs: List[Dict[str, Any]],
        work_calendar: Dict[str, Any],
        constraint_preferences: Optional[Dict[str, float]]
    ) -> List[Constraint]:
        """从月度计划生成约束条件"""
        constraints = []
        
        # 机台容量约束
        for machine in machine_configs:
            machine_id = machine['machine_id']
            max_capacity = machine.get('monthly_capacity', 10000)
            
            constraint = Constraint(
                constraint_id=f"CAP_{machine_id}",
                constraint_type=ConstraintType.MACHINE_CAPACITY,
                constraint_name=f"{machine_id}容量约束",
                description=f"机台{machine_id}月度容量不得超过{max_capacity}件",
                is_hard_constraint=True,
                priority=ConstraintPriority.HIGH,
                violation_penalty=1000.0,
                parameters={
                    'max_capacity': max_capacity,
                    'variables': [f"plan_{plan.plan_id}" for plan in monthly_plans if machine_id in plan.maker_codes + plan.feeder_codes]
                },
                applicable_machines=[machine_id]
            )
            constraints.append(constraint)
        
        # 时间窗口约束
        for plan in monthly_plans:
            if plan.planned_start and plan.planned_end:
                time_window = TimeWindow(plan.planned_start, plan.planned_end)
                
                constraint = Constraint(
                    constraint_id=f"TIME_{plan.plan_id}",
                    constraint_type=ConstraintType.TIME_WINDOW,
                    constraint_name=f"计划{plan.plan_id}时间窗口约束",
                    description=f"计划{plan.plan_id}必须在{plan.planned_start}到{plan.planned_end}之间执行",
                    is_hard_constraint=True,
                    priority=ConstraintPriority.HIGH,
                    violation_penalty=500.0,
                    parameters={
                        'time_window': time_window,
                        'time_variable': f"plan_{plan.plan_id}_time"
                    },
                    applicable_plans=[str(plan.plan_id)]
                )
                constraints.append(constraint)
        
        # 工作日历约束
        working_days = work_calendar.get('working_days', [0, 1, 2, 3, 4])  # 周一到周五
        
        work_constraint = Constraint(
            constraint_id="WORK_CALENDAR",
            constraint_type=ConstraintType.WORK_CALENDAR,
            constraint_name="工作日历约束",
            description="生产安排必须在工作日进行",
            is_hard_constraint=False,
            priority=ConstraintPriority.MEDIUM,
            violation_penalty=200.0,
            parameters={
                'work_days': working_days
            },
            applicable_plans=[str(plan.plan_id) for plan in monthly_plans]
        )
        constraints.append(work_constraint)
        
        return constraints
    
    async def _generate_variables_from_plans(
        self,
        monthly_plans: List[MonthlyPlanItem],
        machine_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """从月度计划生成决策变量"""
        variables = {}
        
        # 为每个计划创建分配变量
        for plan in monthly_plans:
            var_name = f"plan_{plan.plan_id}"
            variables[var_name] = {
                'type': 'continuous',
                'lower_bound': 0,
                'upper_bound': float(plan.target_quantity),
                'description': f"计划{plan.plan_id}的分配量"
            }
            
            # 时间变量
            time_var_name = f"plan_{plan.plan_id}_time"
            variables[time_var_name] = {
                'type': 'continuous',
                'lower_bound': 0,
                'upper_bound': 24*30,  # 30天，以小时为单位
                'description': f"计划{plan.plan_id}的执行时间"
            }
        
        # 为每个机台创建利用率变量
        for machine in machine_configs:
            var_name = f"resource_{machine['machine_id']}"
            variables[var_name] = {
                'type': 'continuous',
                'lower_bound': 0,
                'upper_bound': machine.get('monthly_capacity', 10000),
                'description': f"机台{machine['machine_id']}的月度利用容量"
            }
        
        return variables
    
    def _create_objective_function(
        self,
        optimization_objectives: Optional[Dict[str, float]]
    ) -> Callable:
        """创建目标函数"""
        
        if optimization_objectives is None:
            optimization_objectives = {
                'maximize_production': 0.6,
                'minimize_cost': 0.3,
                'maximize_efficiency': 0.1
            }
        
        def objective_function(solution_state: Dict[str, Any]) -> float:
            objective_value = 0.0
            
            plan_assignments = solution_state.get('plan_assignments', {})
            resource_allocations = solution_state.get('resource_allocations', {})
            
            # 最大化生产量
            if 'maximize_production' in optimization_objectives:
                production_score = sum(
                    assignment.get('value', 0) 
                    for assignment in plan_assignments.values()
                )
                objective_value += optimization_objectives['maximize_production'] * production_score
            
            # 最小化成本（转换为最大化负成本）
            if 'minimize_cost' in optimization_objectives:
                cost_score = sum(
                    allocation.get('value', 0) * 0.1  # 假设成本因子
                    for allocation in resource_allocations.values()
                )
                objective_value -= optimization_objectives['minimize_cost'] * cost_score
            
            # 最大化效率
            if 'maximize_efficiency' in optimization_objectives:
                efficiency_score = sum(
                    allocation.get('capacity_utilization', 0) 
                    for allocation in resource_allocations.values()
                )
                objective_value += optimization_objectives['maximize_efficiency'] * efficiency_score
            
            return objective_value
        
        return objective_function
    
    async def _generate_improvement_recommendations(
        self,
        solution: Solution,
        constraints: List[Constraint],
        hard_violations: List[Dict[str, Any]],
        soft_violations: List[Dict[str, Any]]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 针对硬约束违反的建议
        if hard_violations:
            recommendations.append("优先解决硬约束违反:")
            for violation in hard_violations[:3]:
                recommendations.append(f"  - {violation['constraint_name']}: {violation['violation_reason']}")
        
        # 针对软约束违反的建议
        if soft_violations and len(soft_violations) > 5:
            recommendations.append("考虑调整软约束设置以提高灵活性")
        
        # 基于解决方案质量的建议
        if solution.solution_quality < 70:
            recommendations.extend([
                "考虑放宽部分约束条件",
                "调整优化目标权重",
                "增加求解时间限制",
                "使用不同的求解策略"
            ])
        
        return recommendations
    
    async def _detect_time_window_conflicts(
        self,
        constraints: List[Constraint]
    ) -> List[Dict[str, Any]]:
        """检测时间窗口冲突"""
        conflicts = []
        
        time_constraints = [
            c for c in constraints 
            if c.constraint_type == ConstraintType.TIME_WINDOW
        ]
        
        for i, constraint1 in enumerate(time_constraints):
            for constraint2 in time_constraints[i+1:]:
                window1 = constraint1.parameters.get('time_window')
                window2 = constraint2.parameters.get('time_window')
                
                if window1 and window2 and not window1.overlaps(window2):
                    # 检查是否有共同的资源需求
                    common_machines = (
                        set(constraint1.applicable_machines) & 
                        set(constraint2.applicable_machines)
                    )
                    
                    if common_machines:
                        conflicts.append({
                            'type': 'time_window_conflict',
                            'constraints': [constraint1.constraint_id, constraint2.constraint_id],
                            'affected_resources': list(common_machines),
                            'description': '不重叠的时间窗口要求相同资源'
                        })
        
        return conflicts
    
    async def _detect_capacity_conflicts(
        self,
        constraints: List[Constraint]
    ) -> List[Dict[str, Any]]:
        """检测容量冲突"""
        conflicts = []
        
        capacity_constraints = [
            c for c in constraints 
            if c.constraint_type == ConstraintType.MACHINE_CAPACITY
        ]
        
        # 按机台分组检查
        machine_constraints = defaultdict(list)
        for constraint in capacity_constraints:
            for machine in constraint.applicable_machines:
                machine_constraints[machine].append(constraint)
        
        for machine, machine_constraint_list in machine_constraints.items():
            if len(machine_constraint_list) > 1:
                # 检查容量设置是否一致
                capacities = [
                    c.parameters.get('max_capacity', float('inf'))
                    for c in machine_constraint_list
                ]
                
                if len(set(capacities)) > 1:
                    conflicts.append({
                        'type': 'capacity_conflict',
                        'machine': machine,
                        'constraints': [c.constraint_id for c in machine_constraint_list],
                        'capacities': capacities,
                        'description': f'机台{machine}有多个不一致的容量限制'
                    })
        
        return conflicts
    
    async def _detect_logic_conflicts(
        self,
        constraints: List[Constraint]
    ) -> List[Dict[str, Any]]:
        """检测逻辑冲突"""
        conflicts = []
        
        # 检查优先级冲突
        precedence_constraints = [
            c for c in constraints 
            if c.constraint_type == ConstraintType.PRECEDENCE
        ]
        
        # 构建优先级图检查循环依赖
        precedence_graph = defaultdict(list)
        for constraint in precedence_constraints:
            predecessor = constraint.parameters.get('predecessor')
            successor = constraint.parameters.get('successor')
            if predecessor and successor:
                precedence_graph[predecessor].append(successor)
        
        # 检查环路
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in precedence_graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in precedence_graph:
            if node not in visited:
                if has_cycle(node):
                    conflicts.append({
                        'type': 'precedence_cycle',
                        'description': '优先级约束中存在循环依赖',
                        'affected_nodes': list(precedence_graph.keys())
                    })
                    break
        
        return conflicts
    
    async def _suggest_conflict_resolutions(
        self,
        conflict_groups: List[Dict[str, Any]],
        irreconcilable_constraints: List[Dict[str, Any]]
    ) -> List[str]:
        """建议冲突解决方案"""
        resolutions = []
        
        for conflict in conflict_groups:
            if conflict['type'] == 'time_window_conflict':
                resolutions.extend([
                    "扩展时间窗口以创建重叠",
                    "重新分配资源到不同机台",
                    "调整任务优先级和执行顺序"
                ])
            elif conflict['type'] == 'capacity_conflict':
                resolutions.extend([
                    "统一容量限制设置",
                    "增加机台产能",
                    "重新分配生产负载"
                ])
        
        for conflict in irreconcilable_constraints:
            if conflict['type'] == 'precedence_cycle':
                resolutions.append("重新设计任务依赖关系以消除循环")
        
        return list(set(resolutions))  # 去重


# =============================================================================
# CLI支持和工具函数
# =============================================================================

async def main():
    """CLI主函数"""
    
    parser = argparse.ArgumentParser(
        description="月度约束求解算法 - 复杂约束求解和优化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础约束求解
  python monthly_constraint_solver.py --constraints constraints.json --variables variables.json
  
  # 指定求解策略
  python monthly_constraint_solver.py --constraints constraints.json --variables variables.json --strategy linear_programming
  
  # 约束冲突分析
  python monthly_constraint_solver.py --analyze-conflicts --constraints constraints.json
  
  # 性能基准测试
  python monthly_constraint_solver.py --benchmark
  
  # 生成示例数据
  python monthly_constraint_solver.py --generate-sample
        """
    )
    
    parser.add_argument('--constraints', type=str, help='约束条件文件路径（JSON格式）')
    parser.add_argument('--variables', type=str, help='决策变量文件路径（JSON格式）')
    parser.add_argument('--strategy', choices=['linear_programming', 'heuristic', 'hybrid'], 
                       default='hybrid', help='求解策略')
    parser.add_argument('--time-limit', type=int, default=300, help='求解时间限制（秒）')
    parser.add_argument('--output', choices=['console', 'json', 'file'], 
                       default='console', help='输出格式')
    parser.add_argument('--output-file', type=str, help='输出文件路径')
    parser.add_argument('--analyze-conflicts', action='store_true', help='分析约束冲突')
    parser.add_argument('--benchmark', action='store_true', help='运行性能基准测试')
    parser.add_argument('--generate-sample', action='store_true', help='生成示例数据')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if args.generate_sample:
        generate_sample_data()
        return
    
    if args.benchmark:
        await run_benchmark()
        return
    
    if args.analyze_conflicts:
        if not args.constraints:
            parser.error("冲突分析需要提供约束文件路径 (--constraints)")
        await analyze_conflicts_cli(args.constraints)
        return
    
    if not args.constraints or not args.variables:
        parser.error("请提供约束条件和变量文件路径 (--constraints 和 --variables)")
    
    # 创建约束求解器
    solver = MonthlyConstraintSolver()
    
    try:
        # 加载约束和变量
        constraints = load_constraints_from_file(args.constraints)
        variables = load_variables_from_file(args.variables)
        
        # 解析策略
        strategy = SolverStrategy(args.strategy)
        
        # 创建配置
        config = OptimizationConfig(
            max_solving_time=args.time_limit,
            gap_tolerance=0.01,
            solution_limit=10
        )
        
        # 执行求解
        solution = await solver.solve_constraints(
            constraints=constraints,
            variables=variables,
            strategy=strategy,
            config=config
        )
        
        # 输出结果
        if args.output == 'console':
            print_solution_result(solution)
        elif args.output == 'json':
            result_json = json.dumps(asdict(solution), ensure_ascii=False, indent=2, default=str)
            if args.output_file:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    f.write(result_json)
                print(f"结果已保存到: {args.output_file}")
            else:
                print(result_json)
        elif args.output == 'file':
            output_file = args.output_file or f"solution_result_{int(time.time())}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(solution), f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到: {output_file}")
    
    except Exception as e:
        logger.error(f"约束求解执行失败: {str(e)}")
        if args.verbose:
            raise


def load_constraints_from_file(file_path: str) -> List[Constraint]:
    """从文件加载约束条件"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        constraints = []
        for constraint_data in data:
            # 解析时间窗口
            time_windows = []
            for tw_data in constraint_data.get('time_windows', []):
                time_window = TimeWindow(
                    start_time=datetime.fromisoformat(tw_data['start_time']),
                    end_time=datetime.fromisoformat(tw_data['end_time']),
                    flexible=tw_data.get('flexible', False),
                    flexibility_minutes=tw_data.get('flexibility_minutes', 30)
                )
                time_windows.append(time_window)
            
            constraint = Constraint(
                constraint_id=constraint_data['constraint_id'],
                constraint_type=ConstraintType(constraint_data['constraint_type']),
                constraint_name=constraint_data['constraint_name'],
                description=constraint_data['description'],
                is_hard_constraint=constraint_data.get('is_hard_constraint', True),
                priority=ConstraintPriority(constraint_data.get('priority', 5)),
                violation_penalty=constraint_data.get('violation_penalty', 100.0),
                parameters=constraint_data.get('parameters', {}),
                applicable_plans=constraint_data.get('applicable_plans', []),
                applicable_machines=constraint_data.get('applicable_machines', []),
                applicable_time_windows=time_windows
            )
            constraints.append(constraint)
        
        logger.info(f"成功加载 {len(constraints)} 个约束条件")
        return constraints
        
    except Exception as e:
        raise InvalidInputError(f"无法加载约束数据: {str(e)}")


def load_variables_from_file(file_path: str) -> Dict[str, Any]:
    """从文件加载决策变量"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            variables = json.load(f)
        
        logger.info(f"成功加载 {len(variables)} 个决策变量")
        return variables
        
    except Exception as e:
        raise InvalidInputError(f"无法加载变量数据: {str(e)}")


async def analyze_conflicts_cli(constraints_file: str):
    """CLI约束冲突分析"""
    
    try:
        constraints = load_constraints_from_file(constraints_file)
        
        solver = MonthlyConstraintSolver()
        conflict_analysis = await solver.analyze_constraint_conflicts(constraints)
        
        print("\n=== 约束冲突分析结果 ===")
        print(f"是否存在冲突: {'是' if conflict_analysis['has_conflicts'] else '否'}")
        print(f"冲突严重程度: {conflict_analysis['conflict_severity']}")
        
        if conflict_analysis['conflict_groups']:
            print(f"\n=== 冲突组合 ({len(conflict_analysis['conflict_groups'])}个) ===")
            for i, conflict in enumerate(conflict_analysis['conflict_groups'], 1):
                print(f"{i}. {conflict['type']}: {conflict['description']}")
        
        if conflict_analysis['irreconcilable_constraints']:
            print(f"\n=== 不可调和约束 ({len(conflict_analysis['irreconcilable_constraints'])}个) ===")
            for i, conflict in enumerate(conflict_analysis['irreconcilable_constraints'], 1):
                print(f"{i}. {conflict['type']}: {conflict['description']}")
        
        if conflict_analysis['suggested_resolutions']:
            print(f"\n=== 解决建议 ===")
            for i, resolution in enumerate(conflict_analysis['suggested_resolutions'], 1):
                print(f"{i}. {resolution}")
    
    except Exception as e:
        logger.error(f"冲突分析失败: {str(e)}")


def print_solution_result(solution: Solution):
    """打印求解结果"""
    
    print(f"\n=== 约束求解结果 ===")
    print(f"解决方案ID: {solution.solution_id}")
    print(f"求解时间: {solution.solving_time:.2f}秒")
    print(f"使用算法: {solution.algorithm_used}")
    print(f"是否可行: {'是' if solution.is_feasible else '否'}")
    print(f"解决方案质量: {solution.solution_quality:.2f}")
    print(f"目标函数值: {solution.objective_value:.2f}")
    print(f"总惩罚值: {solution.total_penalty:.2f}")
    
    if solution.plan_assignments:
        print(f"\n=== 计划分配方案 ===")
        for plan_id, assignment in solution.plan_assignments.items():
            print(f"{plan_id}: {assignment}")
    
    if solution.resource_allocations:
        print(f"\n=== 资源分配方案 ===")
        for resource_id, allocation in solution.resource_allocations.items():
            print(f"{resource_id}: {allocation}")
    
    if solution.constraint_violations:
        print(f"\n=== 约束违反情况 ({len(solution.constraint_violations)}个) ===")
        for violation in solution.constraint_violations:
            violation_type_str = "硬约束" if violation.violation_type == ViolationType.HARD_VIOLATION else "软约束"
            print(f"- {violation.constraint_name} ({violation_type_str})")
            print(f"  违反程度: {violation.violation_degree:.3f}")
            print(f"  违反原因: {violation.violation_reason}")
            print(f"  惩罚值: {violation.violation_penalty:.2f}")
            if violation.suggested_fixes:
                print(f"  建议修复: {', '.join(violation.suggested_fixes[:2])}")
            print()


def generate_sample_data():
    """生成示例数据"""
    
    # 生成示例约束
    sample_constraints = []
    
    # 机台容量约束
    for i in range(1, 4):
        constraint = {
            'constraint_id': f'CAP_JBJ{i:03d}',
            'constraint_type': 'machine_capacity',
            'constraint_name': f'卷包机{i}号容量约束',
            'description': f'卷包机{i}号月度容量不得超过80000件',
            'is_hard_constraint': True,
            'priority': 8,
            'violation_penalty': 1000.0,
            'parameters': {
                'max_capacity': 80000,
                'variables': [f'plan_{j}' for j in range(1, 6) if j % i == 1]
            },
            'applicable_machines': [f'JBJ{i:03d}']
        }
        sample_constraints.append(constraint)
    
    # 时间窗口约束
    base_time = datetime.now()
    for i in range(1, 6):
        start_time = base_time + timedelta(days=i)
        end_time = start_time + timedelta(days=3)
        
        constraint = {
            'constraint_id': f'TIME_PLAN_{i}',
            'constraint_type': 'time_window',
            'constraint_name': f'计划{i}时间窗口约束',
            'description': f'计划{i}必须在指定时间窗口内执行',
            'is_hard_constraint': True,
            'priority': 8,
            'violation_penalty': 500.0,
            'parameters': {
                'time_variable': f'plan_{i}_time'
            },
            'applicable_plans': [str(i)],
            'time_windows': [{
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'flexible': True,
                'flexibility_minutes': 60
            }]
        }
        sample_constraints.append(constraint)
    
    # 工作日历约束
    work_constraint = {
        'constraint_id': 'WORK_CALENDAR_GLOBAL',
        'constraint_type': 'work_calendar',
        'constraint_name': '全局工作日历约束',
        'description': '所有生产活动必须在工作日进行',
        'is_hard_constraint': False,
        'priority': 5,
        'violation_penalty': 200.0,
        'parameters': {
            'work_days': [0, 1, 2, 3, 4]  # 周一到周五
        },
        'applicable_plans': [str(i) for i in range(1, 6)]
    }
    sample_constraints.append(work_constraint)
    
    # 保存约束示例
    with open('sample_constraints.json', 'w', encoding='utf-8') as f:
        json.dump(sample_constraints, f, ensure_ascii=False, indent=2)
    
    # 生成示例变量
    sample_variables = {}
    
    # 计划变量
    for i in range(1, 6):
        sample_variables[f'plan_{i}'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 20000,
            'description': f'计划{i}的分配产量'
        }
        
        sample_variables[f'plan_{i}_time'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 720,  # 30天 * 24小时
            'description': f'计划{i}的执行时间'
        }
    
    # 资源变量
    for i in range(1, 4):
        sample_variables[f'resource_JBJ{i:03d}'] = {
            'type': 'continuous',
            'lower_bound': 0,
            'upper_bound': 80000,
            'description': f'卷包机{i}号的月度利用容量'
        }
    
    # 保存变量示例
    with open('sample_variables.json', 'w', encoding='utf-8') as f:
        json.dump(sample_variables, f, ensure_ascii=False, indent=2)
    
    print("示例数据已生成:")
    print("- sample_constraints.json (约束条件)")
    print("- sample_variables.json (决策变量)")
    print("\n使用方法:")
    print("python monthly_constraint_solver.py --constraints sample_constraints.json --variables sample_variables.json")


async def run_benchmark():
    """运行性能基准测试"""
    
    print("=== 月度约束求解器性能基准测试 ===")
    
    # 生成测试数据
    test_cases = [
        ("小规模", 5, 3),    # 5个约束，3个变量
        ("中规模", 20, 10),  # 20个约束，10个变量
        ("大规模", 50, 25),  # 50个约束，25个变量
    ]
    
    solver = MonthlyConstraintSolver()
    
    for test_name, num_constraints, num_variables in test_cases:
        print(f"\n--- {test_name}测试 ({num_constraints}约束, {num_variables}变量) ---")
        
        # 生成测试约束
        constraints = []
        for i in range(num_constraints):
            constraint = Constraint(
                constraint_id=f'TEST_{i+1}',
                constraint_type=ConstraintType.MACHINE_CAPACITY,
                constraint_name=f'测试约束{i+1}',
                description=f'测试约束{i+1}的描述',
                is_hard_constraint=i % 3 == 0,  # 每3个中有1个硬约束
                priority=ConstraintPriority(5),
                violation_penalty=100.0 + i * 10,
                parameters={
                    'max_capacity': 1000 + i * 100,
                    'variables': [f'var_{j}' for j in range(min(3, num_variables))]
                }
            )
            constraints.append(constraint)
        
        # 生成测试变量
        variables = {}
        for i in range(num_variables):
            variables[f'var_{i}'] = {
                'type': 'continuous',
                'lower_bound': 0,
                'upper_bound': 1000,
                'description': f'测试变量{i}'
            }
        
        # 测试不同策略
        strategies = [SolverStrategy.HEURISTIC, SolverStrategy.HYBRID]
        
        for strategy in strategies:
            start_time = time.time()
            
            try:
                config = OptimizationConfig(max_solving_time=60)  # 1分钟限制
                
                solution = await solver.solve_constraints(
                    constraints=constraints,
                    variables=variables,
                    strategy=strategy,
                    config=config
                )
                
                execution_time = time.time() - start_time
                
                print(f"  {strategy.value}:")
                print(f"    执行时间: {execution_time:.2f}秒")
                print(f"    解决方案质量: {solution.solution_quality:.2f}")
                print(f"    可行性: {'是' if solution.is_feasible else '否'}")
                print(f"    约束违反数: {len(solution.constraint_violations)}")
                
            except Exception as e:
                print(f"  {strategy.value}: 执行失败 - {str(e)}")
    
    # 显示整体性能指标
    stats = solver.get_solving_statistics()
    metrics = stats['performance_metrics']
    
    print(f"\n=== 整体性能指标 ===")
    print(f"总求解次数: {metrics['total_problems_solved']}")
    print(f"平均求解时间: {metrics['average_solving_time']:.2f}秒")
    print(f"成功率: {metrics['success_rate']:.1%}")
    print(f"最佳质量评分: {metrics['best_quality_achieved']:.2f}")
    print(f"处理的约束类型: {len(metrics['constraint_types_handled'])}")


if __name__ == "__main__":
    asyncio.run(main())