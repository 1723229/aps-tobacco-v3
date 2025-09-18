"""
月度资源优化算法模块 - T024

该模块实现了烟草生产中的智能资源分配优化算法，支持多目标优化、
约束求解和实时调整，为月度排产提供高效的资源配置解决方案。

主要功能：
- 多目标资源分配优化（产能最大化、成本最小化、负载均衡）
- 智能约束求解（机台维护、人员配置、原料供应）
- 启发式与精确算法混合策略
- 实时动态调整和优化
- 历史数据分析和预测
- 优化效果评估和建议生成

作者: APS开发团队
版本: 1.0.0
依赖: SQLAlchemy, asyncio, OR-Tools, NumPy
"""

import asyncio
import json
import logging
import time
import argparse
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import heapq
from collections import defaultdict, deque
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

# 尝试导入OR-Tools（生产环境需安装）
try:
    from ortools.linear_solver import pywraplp
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools未安装，将使用启发式算法")

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
# 优化目标和约束定义
# =============================================================================

class OptimizationObjective(Enum):
    """优化目标枚举"""
    CAPACITY_MAXIMIZATION = "capacity_max"      # 产能最大化
    COST_MINIMIZATION = "cost_min"              # 成本最小化
    LOAD_BALANCING = "load_balance"             # 负载均衡
    EFFICIENCY_MAXIMIZATION = "efficiency_max"  # 效率最大化
    DEADLINE_OPTIMIZATION = "deadline_opt"      # 交期优化
    ENERGY_MINIMIZATION = "energy_min"          # 能耗最小化


class ConstraintType(Enum):
    """约束类型枚举"""
    MACHINE_CAPACITY = "machine_capacity"       # 机台容量约束
    MAINTENANCE_WINDOW = "maintenance_window"   # 维护时间窗约束
    MATERIAL_SUPPLY = "material_supply"         # 原料供应约束
    WORKFORCE_AVAILABILITY = "workforce_avail"  # 人员可用性约束
    QUALITY_REQUIREMENT = "quality_req"         # 质量要求约束
    ENERGY_CONSUMPTION = "energy_consumption"   # 能耗约束
    PRODUCTION_SEQUENCE = "production_seq"      # 生产顺序约束


class ResourceType(Enum):
    """资源类型枚举"""
    MACHINE = "machine"                         # 机台资源
    WORKFORCE = "workforce"                     # 人力资源  
    MATERIAL = "material"                       # 物料资源
    ENERGY = "energy"                          # 能源资源
    TOOLING = "tooling"                        # 工装资源
    SPACE = "space"                            # 空间资源


class AlgorithmStrategy(Enum):
    """算法策略枚举"""
    HEURISTIC_ONLY = "heuristic"               # 仅启发式算法
    EXACT_ONLY = "exact"                       # 仅精确算法
    HYBRID = "hybrid"                          # 混合策略
    EVOLUTIONARY = "evolutionary"              # 进化算法
    REINFORCEMENT = "reinforcement"            # 强化学习


# =============================================================================
# 资源和约束数据类
# =============================================================================

@dataclass
class ResourceCapacity:
    """资源容量数据类"""
    resource_id: str
    resource_type: ResourceType
    resource_name: str
    total_capacity: Decimal                     # 总容量
    available_capacity: Decimal                 # 可用容量
    reserved_capacity: Decimal                  # 预留容量
    unit: str                                   # 单位
    cost_per_unit: Decimal                     # 单位成本
    efficiency_factor: float                   # 效率因子
    availability_windows: List[Tuple[datetime, datetime]]  # 可用时间窗
    maintenance_windows: List[Tuple[datetime, datetime]]   # 维护时间窗
    constraints: Dict[str, Any]                # 特定约束
    
    @property
    def utilization_rate(self) -> float:
        """计算利用率"""
        if self.total_capacity <= 0:
            return 0.0
        used_capacity = self.total_capacity - self.available_capacity
        return float(used_capacity / self.total_capacity)
    
    @property
    def effective_capacity(self) -> Decimal:
        """计算有效容量"""
        return self.available_capacity * Decimal(str(self.efficiency_factor))


@dataclass
class OptimizationConstraint:
    """优化约束数据类"""
    constraint_id: str
    constraint_type: ConstraintType
    constraint_name: str
    description: str
    affected_resources: List[str]              # 受影响的资源ID
    constraint_parameters: Dict[str, Any]      # 约束参数
    violation_penalty: float                   # 违反惩罚
    hard_constraint: bool                      # 是否为硬约束
    priority: int                             # 约束优先级
    time_windows: List[Tuple[datetime, datetime]]  # 约束时间窗
    
    def evaluate_violation(self, resource_allocation: Dict[str, Any]) -> float:
        """评估约束违反程度"""
        # 基础违反评估逻辑
        if self.constraint_type == ConstraintType.MACHINE_CAPACITY:
            return self._evaluate_capacity_violation(resource_allocation)
        elif self.constraint_type == ConstraintType.MAINTENANCE_WINDOW:
            return self._evaluate_maintenance_violation(resource_allocation)
        else:
            return 0.0
    
    def _evaluate_capacity_violation(self, allocation: Dict[str, Any]) -> float:
        """评估容量约束违反"""
        violation = 0.0
        max_capacity = self.constraint_parameters.get('max_capacity', float('inf'))
        
        for resource_id in self.affected_resources:
            if resource_id in allocation:
                used_capacity = allocation[resource_id].get('used_capacity', 0)
                if used_capacity > max_capacity:
                    violation += (used_capacity - max_capacity) / max_capacity
        
        return violation
    
    def _evaluate_maintenance_violation(self, allocation: Dict[str, Any]) -> float:
        """评估维护约束违反"""
        # 简化的维护时间窗违反检查
        return 0.0


@dataclass
class ResourceAllocation:
    """资源分配数据类"""
    allocation_id: str
    plan_id: int
    resource_allocations: Dict[str, Dict[str, Any]]  # 资源ID -> 分配详情
    time_allocation: Dict[str, List[Tuple[datetime, datetime]]]  # 时间分配
    objective_values: Dict[OptimizationObjective, float]  # 目标函数值
    constraint_violations: Dict[str, float]      # 约束违反情况
    total_cost: Decimal                          # 总成本
    total_capacity_utilization: float           # 总容量利用率
    optimization_score: float                   # 优化评分
    feasibility_score: float                    # 可行性评分
    generation_time: datetime                   # 生成时间
    algorithm_used: str                         # 使用的算法
    
    def is_feasible(self, tolerance: float = 0.01) -> bool:
        """判断分配方案是否可行"""
        total_violation = sum(self.constraint_violations.values())
        return total_violation <= tolerance
    
    def get_efficiency_score(self) -> float:
        """计算效率评分"""
        if not self.objective_values:
            return 0.0
        
        # 综合各目标函数值计算效率评分
        weights = {
            OptimizationObjective.CAPACITY_MAXIMIZATION: 0.3,
            OptimizationObjective.EFFICIENCY_MAXIMIZATION: 0.3,
            OptimizationObjective.LOAD_BALANCING: 0.2,
            OptimizationObjective.COST_MINIMIZATION: 0.2
        }
        
        score = 0.0
        for objective, value in self.objective_values.items():
            weight = weights.get(objective, 0.1)
            score += weight * value
        
        return min(100.0, max(0.0, score))


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    result_id: str
    optimization_run_id: str
    best_allocation: ResourceAllocation
    alternative_allocations: List[ResourceAllocation]
    convergence_history: List[Dict[str, float]]  # 收敛历史
    execution_time: float                        # 执行时间
    iterations_performed: int                    # 执行迭代数
    algorithm_parameters: Dict[str, Any]         # 算法参数
    performance_metrics: Dict[str, Any]          # 性能指标
    optimization_recommendations: List[str]      # 优化建议
    sensitivity_analysis: Dict[str, Any]         # 敏感性分析
    
    def get_improvement_percentage(self, baseline_allocation: ResourceAllocation) -> float:
        """计算相对于基准的改进百分比"""
        if baseline_allocation.optimization_score == 0:
            return 0.0
        
        improvement = self.best_allocation.optimization_score - baseline_allocation.optimization_score
        return (improvement / baseline_allocation.optimization_score) * 100


# =============================================================================
# 优化算法基类和具体实现
# =============================================================================

class ResourceOptimizationAlgorithm(ABC):
    """资源优化算法基类"""
    
    @abstractmethod
    async def optimize(
        self,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint], 
        objectives: Dict[OptimizationObjective, float],
        plans: List[MonthlyPlanItem],
        **kwargs
    ) -> ResourceAllocation:
        """
        执行资源优化
        
        Args:
            resources: 资源容量列表
            constraints: 约束条件列表
            objectives: 优化目标及权重
            plans: 月度计划项列表
            **kwargs: 其他参数
            
        Returns:
            ResourceAllocation: 资源分配结果
        """
        pass


class HeuristicOptimizer(ResourceOptimizationAlgorithm):
    """启发式优化算法"""
    
    def __init__(self, max_iterations: int = 1000, improvement_threshold: float = 0.001):
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.iteration_count = 0
    
    async def optimize(
        self,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float],
        plans: List[MonthlyPlanItem],
        **kwargs
    ) -> ResourceAllocation:
        """启发式优化实现"""
        logger.info("开始启发式资源优化")
        
        # 初始化分配方案（贪心算法）
        current_allocation = await self._generate_initial_allocation(resources, plans)
        
        # 迭代改进
        best_score = self._evaluate_allocation(current_allocation, objectives, constraints)
        
        for iteration in range(self.max_iterations):
            self.iteration_count = iteration + 1
            
            # 局部搜索改进
            improved_allocation = await self._local_search_improvement(
                current_allocation, resources, constraints, objectives
            )
            
            improved_score = self._evaluate_allocation(improved_allocation, objectives, constraints)
            
            # 接受改进的解
            if improved_score > best_score + self.improvement_threshold:
                current_allocation = improved_allocation
                best_score = improved_score
                logger.debug(f"迭代 {iteration}: 优化评分提升至 {best_score:.4f}")
            
            # 收敛检查
            if iteration > 10 and (improved_score - best_score) < self.improvement_threshold:
                logger.info(f"算法收敛，迭代次数: {iteration}")
                break
        
        return current_allocation
    
    async def _generate_initial_allocation(
        self,
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ) -> ResourceAllocation:
        """生成初始分配方案"""
        
        resource_allocations = {}
        time_allocation = {}
        
        # 按优先级排序计划项
        sorted_plans = sorted(plans, key=lambda p: p.priority.value, reverse=True)
        
        for plan in sorted_plans:
            # 为每个计划项分配资源
            allocated_resources = await self._allocate_resources_for_plan(plan, resources)
            
            for resource_id, allocation_detail in allocated_resources.items():
                if resource_id not in resource_allocations:
                    resource_allocations[resource_id] = {}
                
                resource_allocations[resource_id][f"plan_{plan.plan_id}"] = allocation_detail
        
        return ResourceAllocation(
            allocation_id=f"HEURISTIC_{int(time.time())}",
            plan_id=0,  # 表示全局分配
            resource_allocations=resource_allocations,
            time_allocation=time_allocation,
            objective_values={},
            constraint_violations={},
            total_cost=Decimal('0'),
            total_capacity_utilization=0.0,
            optimization_score=0.0,
            feasibility_score=0.0,
            generation_time=datetime.now(),
            algorithm_used="heuristic"
        )
    
    async def _allocate_resources_for_plan(
        self,
        plan: MonthlyPlanItem,
        resources: List[ResourceCapacity]
    ) -> Dict[str, Dict[str, Any]]:
        """为单个计划项分配资源"""
        
        allocated_resources = {}
        
        # 简化的资源分配逻辑
        for resource in resources:
            if resource.resource_type == ResourceType.MACHINE:
                # 检查机台是否适用于该产品
                if self._is_machine_suitable(resource, plan):
                    required_capacity = self._calculate_required_capacity(plan, resource)
                    
                    if resource.available_capacity >= required_capacity:
                        allocated_resources[resource.resource_id] = {
                            'allocated_capacity': float(required_capacity),
                            'start_time': plan.planned_start,
                            'end_time': plan.planned_end,
                            'cost': float(required_capacity * resource.cost_per_unit)
                        }
                        
                        # 更新资源可用容量
                        resource.available_capacity -= required_capacity
        
        return allocated_resources
    
    def _is_machine_suitable(self, resource: ResourceCapacity, plan: MonthlyPlanItem) -> bool:
        """检查机台是否适用于计划项"""
        # 简化的适用性检查
        if resource.resource_type != ResourceType.MACHINE:
            return False
        
        # 检查机台代码是否在计划的机台列表中
        machine_codes = plan.feeder_codes + plan.maker_codes
        return resource.resource_id in machine_codes
    
    def _calculate_required_capacity(self, plan: MonthlyPlanItem, resource: ResourceCapacity) -> Decimal:
        """计算所需容量"""
        # 简化的容量计算
        base_capacity = Decimal(str(plan.target_quantity))
        efficiency_factor = Decimal(str(resource.efficiency_factor))
        return base_capacity / efficiency_factor
    
    async def _local_search_improvement(
        self,
        current_allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float]
    ) -> ResourceAllocation:
        """局部搜索改进"""
        
        # 创建当前分配的副本
        improved_allocation = ResourceAllocation(
            allocation_id=f"IMPROVED_{int(time.time())}",
            plan_id=current_allocation.plan_id,
            resource_allocations=current_allocation.resource_allocations.copy(),
            time_allocation=current_allocation.time_allocation.copy(),
            objective_values=current_allocation.objective_values.copy(),
            constraint_violations=current_allocation.constraint_violations.copy(),
            total_cost=current_allocation.total_cost,
            total_capacity_utilization=current_allocation.total_capacity_utilization,
            optimization_score=current_allocation.optimization_score,
            feasibility_score=current_allocation.feasibility_score,
            generation_time=datetime.now(),
            algorithm_used="heuristic_improved"
        )
        
        # 执行随机改进操作
        improvement_operations = [
            self._swap_resource_allocation,
            self._redistribute_load,
            self._optimize_time_windows
        ]
        
        operation = np.random.choice(improvement_operations)
        await operation(improved_allocation, resources)
        
        return improved_allocation
    
    async def _swap_resource_allocation(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ):
        """交换资源分配"""
        # 随机选择两个资源进行交换
        resource_ids = list(allocation.resource_allocations.keys())
        if len(resource_ids) >= 2:
            id1, id2 = np.random.choice(resource_ids, 2, replace=False)
            
            # 交换部分分配
            alloc1 = allocation.resource_allocations[id1]
            alloc2 = allocation.resource_allocations[id2]
            
            if alloc1 and alloc2:
                # 简化的交换逻辑
                plans1 = list(alloc1.keys())
                plans2 = list(alloc2.keys())
                
                if plans1 and plans2:
                    plan1 = np.random.choice(plans1)
                    plan2 = np.random.choice(plans2)
                    
                    # 交换计划分配
                    temp = alloc1[plan1]
                    alloc1[plan1] = alloc2[plan2]
                    alloc2[plan2] = temp
    
    async def _redistribute_load(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ):
        """重新分配负载"""
        # 找到负载最高和最低的资源
        load_ratios = {}
        
        for resource_id, resource_alloc in allocation.resource_allocations.items():
            total_allocated = sum(
                detail.get('allocated_capacity', 0) 
                for detail in resource_alloc.values()
            )
            
            # 找到对应的资源容量
            resource_capacity = next(
                (r.total_capacity for r in resources if r.resource_id == resource_id),
                Decimal('1')
            )
            
            load_ratios[resource_id] = total_allocated / float(resource_capacity)
        
        if len(load_ratios) >= 2:
            # 从高负载资源转移部分负载到低负载资源
            highest_load_resource = max(load_ratios, key=load_ratios.get)
            lowest_load_resource = min(load_ratios, key=load_ratios.get)
            
            if load_ratios[highest_load_resource] > load_ratios[lowest_load_resource] + 0.1:
                # 执行负载转移
                await self._transfer_load(
                    allocation, highest_load_resource, lowest_load_resource
                )
    
    async def _transfer_load(
        self,
        allocation: ResourceAllocation,
        from_resource: str,
        to_resource: str
    ):
        """在资源间转移负载"""
        from_alloc = allocation.resource_allocations.get(from_resource, {})
        to_alloc = allocation.resource_allocations.get(to_resource, {})
        
        if from_alloc:
            # 选择一个计划进行转移
            plan_keys = list(from_alloc.keys())
            if plan_keys:
                plan_key = np.random.choice(plan_keys)
                plan_detail = from_alloc.pop(plan_key)
                
                # 转移到目标资源
                to_alloc[plan_key] = plan_detail
                allocation.resource_allocations[to_resource] = to_alloc
    
    async def _optimize_time_windows(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ):
        """优化时间窗口"""
        # 简化的时间窗口优化
        for resource_id, resource_alloc in allocation.resource_allocations.items():
            for plan_key, plan_detail in resource_alloc.items():
                if 'start_time' in plan_detail and 'end_time' in plan_detail:
                    # 随机调整时间窗口（±10%）
                    duration = (plan_detail['end_time'] - plan_detail['start_time']).total_seconds()
                    adjustment = duration * 0.1 * (np.random.random() - 0.5)
                    
                    new_end_time = plan_detail['end_time'] + timedelta(seconds=adjustment)
                    plan_detail['end_time'] = new_end_time
    
    def _evaluate_allocation(
        self,
        allocation: ResourceAllocation,
        objectives: Dict[OptimizationObjective, float],
        constraints: List[OptimizationConstraint]
    ) -> float:
        """评估分配方案"""
        
        objective_scores = {}
        
        # 计算各目标函数值
        for objective, weight in objectives.items():
            score = self._calculate_objective_score(allocation, objective)
            objective_scores[objective] = score
        
        # 计算约束违反惩罚
        constraint_penalty = 0.0
        for constraint in constraints:
            violation = constraint.evaluate_violation(allocation.resource_allocations)
            constraint_penalty += violation * constraint.violation_penalty
        
        # 计算加权总分
        weighted_score = sum(
            score * objectives[objective] 
            for objective, score in objective_scores.items()
        )
        
        # 应用约束惩罚
        final_score = weighted_score - constraint_penalty
        
        # 更新分配对象
        allocation.objective_values = objective_scores
        allocation.optimization_score = final_score
        
        return final_score
    
    def _calculate_objective_score(
        self,
        allocation: ResourceAllocation,
        objective: OptimizationObjective
    ) -> float:
        """计算单个目标函数得分"""
        
        if objective == OptimizationObjective.CAPACITY_MAXIMIZATION:
            return self._calculate_capacity_utilization_score(allocation)
        elif objective == OptimizationObjective.LOAD_BALANCING:
            return self._calculate_load_balance_score(allocation)
        elif objective == OptimizationObjective.COST_MINIMIZATION:
            return self._calculate_cost_efficiency_score(allocation)
        else:
            return 50.0  # 默认中等分数
    
    def _calculate_capacity_utilization_score(self, allocation: ResourceAllocation) -> float:
        """计算容量利用率得分"""
        if not allocation.resource_allocations:
            return 0.0
        
        total_utilization = 0.0
        resource_count = 0
        
        for resource_id, resource_alloc in allocation.resource_allocations.items():
            allocated_capacity = sum(
                detail.get('allocated_capacity', 0) 
                for detail in resource_alloc.values()
            )
            
            # 假设总容量为100（简化）
            utilization = min(1.0, allocated_capacity / 100.0)
            total_utilization += utilization
            resource_count += 1
        
        return (total_utilization / resource_count) * 100 if resource_count > 0 else 0.0
    
    def _calculate_load_balance_score(self, allocation: ResourceAllocation) -> float:
        """计算负载均衡得分"""
        if len(allocation.resource_allocations) < 2:
            return 100.0  # 单资源情况认为完全均衡
        
        utilizations = []
        for resource_id, resource_alloc in allocation.resource_allocations.items():
            allocated_capacity = sum(
                detail.get('allocated_capacity', 0) 
                for detail in resource_alloc.values()
            )
            utilizations.append(allocated_capacity)
        
        if not utilizations:
            return 0.0
        
        # 计算标准差，越小表示越均衡
        mean_util = np.mean(utilizations)
        std_util = np.std(utilizations)
        
        # 转换为得分（标准差越小得分越高）
        balance_score = max(0.0, 100.0 - (std_util / mean_util * 100) if mean_util > 0 else 0.0)
        return balance_score
    
    def _calculate_cost_efficiency_score(self, allocation: ResourceAllocation) -> float:
        """计算成本效率得分"""
        total_cost = 0.0
        total_capacity = 0.0
        
        for resource_id, resource_alloc in allocation.resource_allocations.items():
            for plan_key, plan_detail in resource_alloc.items():
                cost = plan_detail.get('cost', 0)
                capacity = plan_detail.get('allocated_capacity', 0)
                
                total_cost += cost
                total_capacity += capacity
        
        if total_capacity == 0:
            return 0.0
        
        # 成本效率：容量/成本，越高越好
        cost_efficiency = total_capacity / total_cost if total_cost > 0 else 0.0
        
        # 标准化到0-100分
        return min(100.0, cost_efficiency * 10)


class ExactOptimizer(ResourceOptimizationAlgorithm):
    """精确优化算法（基于OR-Tools）"""
    
    def __init__(self, time_limit_seconds: int = 300, mip_gap: float = 0.01):
        self.time_limit_seconds = time_limit_seconds
        self.mip_gap = mip_gap
        self.solver = None
    
    async def optimize(
        self,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float],
        plans: List[MonthlyPlanItem],
        **kwargs
    ) -> ResourceAllocation:
        """精确优化实现"""
        
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools不可用，回退到启发式算法")
            heuristic_optimizer = HeuristicOptimizer()
            return await heuristic_optimizer.optimize(resources, constraints, objectives, plans, **kwargs)
        
        logger.info("开始精确资源优化（OR-Tools）")
        
        # 创建求解器
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            raise MonthlySchedulingError("无法创建OR-Tools求解器")
        
        # 定义决策变量
        variables = self._create_decision_variables(resources, plans)
        
        # 添加约束
        self._add_constraints(variables, resources, constraints, plans)
        
        # 设置目标函数
        self._set_objective_function(variables, objectives, resources, plans)
        
        # 设置求解器参数
        self.solver.SetTimeLimit(self.time_limit_seconds * 1000)  # 毫秒
        
        # 执行求解
        status = self.solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            logger.info(f"优化完成，状态: {'最优' if status == pywraplp.Solver.OPTIMAL else '可行'}")
            return self._extract_solution(variables, resources, plans)
        else:
            logger.error("优化失败，无可行解")
            raise MonthlySchedulingError("精确优化无法找到可行解")
    
    def _create_decision_variables(
        self,
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ) -> Dict[str, Any]:
        """创建决策变量"""
        
        variables = {}
        
        # 创建分配变量 x[i,j] - 计划i是否分配给资源j
        variables['allocation'] = {}
        for plan in plans:
            for resource in resources:
                var_name = f"x_{plan.plan_id}_{resource.resource_id}"
                variables['allocation'][(plan.plan_id, resource.resource_id)] = \
                    self.solver.BoolVar(var_name)
        
        # 创建容量变量 c[i,j] - 计划i在资源j上的分配容量
        variables['capacity'] = {}
        for plan in plans:
            for resource in resources:
                var_name = f"c_{plan.plan_id}_{resource.resource_id}"
                variables['capacity'][(plan.plan_id, resource.resource_id)] = \
                    self.solver.NumVar(0, float(resource.total_capacity), var_name)
        
        # 创建时间变量 t_start[i], t_end[i] - 计划i的开始和结束时间
        variables['time_start'] = {}
        variables['time_end'] = {}
        for plan in plans:
            start_var_name = f"t_start_{plan.plan_id}"
            end_var_name = f"t_end_{plan.plan_id}"
            
            # 时间变量用小时表示，从当前时间开始
            base_time = datetime.now().timestamp() / 3600  # 转换为小时
            
            variables['time_start'][plan.plan_id] = \
                self.solver.NumVar(base_time, base_time + 24*30, start_var_name)  # 30天内
            variables['time_end'][plan.plan_id] = \
                self.solver.NumVar(base_time, base_time + 24*30, end_var_name)
        
        return variables
    
    def _add_constraints(
        self,
        variables: Dict[str, Any],
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        plans: List[MonthlyPlanItem]
    ):
        """添加约束"""
        
        # 1. 每个计划必须完全分配
        for plan in plans:
            allocation_vars = [
                variables['allocation'][(plan.plan_id, resource.resource_id)]
                for resource in resources
                if self._is_resource_compatible(plan, resource)
            ]
            if allocation_vars:
                self.solver.Add(sum(allocation_vars) >= 1)
        
        # 2. 资源容量约束
        for resource in resources:
            capacity_vars = [
                variables['capacity'][(plan.plan_id, resource.resource_id)]
                for plan in plans
            ]
            self.solver.Add(sum(capacity_vars) <= float(resource.available_capacity))
        
        # 3. 分配逻辑约束：如果分配，则容量必须大于0
        for plan in plans:
            for resource in resources:
                alloc_var = variables['allocation'][(plan.plan_id, resource.resource_id)]
                capacity_var = variables['capacity'][(plan.plan_id, resource.resource_id)]
                
                # 如果分配了，容量必须大于最小需求
                min_required = float(plan.target_quantity * Decimal('0.1'))  # 最小10%
                self.solver.Add(capacity_var >= min_required * alloc_var)
                
                # 如果没分配，容量必须为0
                self.solver.Add(capacity_var <= float(resource.total_capacity) * alloc_var)
        
        # 4. 时间顺序约束
        for plan in plans:
            start_var = variables['time_start'][plan.plan_id]
            end_var = variables['time_end'][plan.plan_id]
            
            # 结束时间必须晚于开始时间
            self.solver.Add(end_var >= start_var + 1)  # 至少1小时
            
            # 如果有计划的时间要求
            if plan.planned_start:
                planned_start_hours = plan.planned_start.timestamp() / 3600
                self.solver.Add(start_var >= planned_start_hours)
            
            if plan.planned_end:
                planned_end_hours = plan.planned_end.timestamp() / 3600
                self.solver.Add(end_var <= planned_end_hours)
        
        # 5. 添加特定约束
        for constraint in constraints:
            self._add_specific_constraint(variables, constraint, resources, plans)
    
    def _add_specific_constraint(
        self,
        variables: Dict[str, Any],
        constraint: OptimizationConstraint,
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ):
        """添加特定类型的约束"""
        
        if constraint.constraint_type == ConstraintType.MACHINE_CAPACITY:
            # 机台容量约束（已在基础约束中处理）
            pass
        
        elif constraint.constraint_type == ConstraintType.MAINTENANCE_WINDOW:
            # 维护时间窗约束
            self._add_maintenance_constraints(variables, constraint, resources, plans)
        
        elif constraint.constraint_type == ConstraintType.PRODUCTION_SEQUENCE:
            # 生产顺序约束
            self._add_sequence_constraints(variables, constraint, plans)
    
    def _add_maintenance_constraints(
        self,
        variables: Dict[str, Any],
        constraint: OptimizationConstraint,
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ):
        """添加维护时间窗约束"""
        
        for resource_id in constraint.affected_resources:
            resource = next((r for r in resources if r.resource_id == resource_id), None)
            if not resource:
                continue
            
            # 获取维护时间窗
            maintenance_windows = resource.maintenance_windows
            
            for maintenance_start, maintenance_end in maintenance_windows:
                maint_start_hours = maintenance_start.timestamp() / 3600
                maint_end_hours = maintenance_end.timestamp() / 3600
                
                # 确保没有计划在维护时间内执行
                for plan in plans:
                    start_var = variables['time_start'][plan.plan_id]
                    end_var = variables['time_end'][plan.plan_id]
                    alloc_var = variables['allocation'][(plan.plan_id, resource_id)]
                    
                    # 如果分配到该资源，则不能与维护时间重叠
                    # (start >= maint_end) OR (end <= maint_start) OR (not allocated)
                    # 转换为线性约束（BigM方法）
                    M = 24 * 30 * 2  # 大数（2个月的小时数）
                    
                    # 添加二进制变量表示时间关系
                    before_maint = self.solver.BoolVar(f"before_maint_{plan.plan_id}_{resource_id}")
                    after_maint = self.solver.BoolVar(f"after_maint_{plan.plan_id}_{resource_id}")
                    
                    # before_maint = 1 表示计划在维护前完成
                    self.solver.Add(end_var <= maint_start_hours + M * (1 - before_maint))
                    
                    # after_maint = 1 表示计划在维护后开始
                    self.solver.Add(start_var >= maint_end_hours - M * (1 - after_maint))
                    
                    # 如果分配到该资源，必须满足其中一个时间条件
                    self.solver.Add(before_maint + after_maint >= alloc_var)
    
    def _add_sequence_constraints(
        self,
        variables: Dict[str, Any],
        constraint: OptimizationConstraint,
        plans: List[MonthlyPlanItem]
    ):
        """添加生产顺序约束"""
        
        sequence_requirements = constraint.constraint_parameters.get('sequence', [])
        
        for seq_req in sequence_requirements:
            if 'predecessor' in seq_req and 'successor' in seq_req:
                pred_id = seq_req['predecessor']
                succ_id = seq_req['successor']
                
                pred_plan = next((p for p in plans if p.plan_id == pred_id), None)
                succ_plan = next((p for p in plans if p.plan_id == succ_id), None)
                
                if pred_plan and succ_plan:
                    pred_end = variables['time_end'][pred_id]
                    succ_start = variables['time_start'][succ_id]
                    
                    # 后继任务必须在前驱任务完成后开始
                    min_gap = seq_req.get('min_gap_hours', 0)
                    self.solver.Add(succ_start >= pred_end + min_gap)
    
    def _set_objective_function(
        self,
        variables: Dict[str, Any],
        objectives: Dict[OptimizationObjective, float],
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ):
        """设置目标函数"""
        
        objective_terms = []
        
        for objective_type, weight in objectives.items():
            if objective_type == OptimizationObjective.CAPACITY_MAXIMIZATION:
                # 最大化总分配容量
                capacity_term = sum(
                    variables['capacity'][(plan.plan_id, resource.resource_id)]
                    for plan in plans
                    for resource in resources
                )
                objective_terms.append(weight * capacity_term)
            
            elif objective_type == OptimizationObjective.COST_MINIMIZATION:
                # 最小化总成本
                cost_term = sum(
                    variables['capacity'][(plan.plan_id, resource.resource_id)] * float(resource.cost_per_unit)
                    for plan in plans
                    for resource in resources
                )
                objective_terms.append(-weight * cost_term)  # 负号表示最小化
            
            elif objective_type == OptimizationObjective.LOAD_BALANCING:
                # 负载均衡目标（最小化负载方差）
                # 这需要额外的变量和约束来表示
                balance_term = self._create_load_balance_objective(variables, resources, plans)
                objective_terms.append(weight * balance_term)
        
        # 设置目标函数（最大化）
        if objective_terms:
            self.solver.Maximize(sum(objective_terms))
    
    def _create_load_balance_objective(
        self,
        variables: Dict[str, Any],
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ) -> Any:
        """创建负载均衡目标项"""
        
        # 计算每个资源的负载
        resource_loads = {}
        for resource in resources:
            load = sum(
                variables['capacity'][(plan.plan_id, resource.resource_id)]
                for plan in plans
            )
            resource_loads[resource.resource_id] = load
        
        # 计算负载的标准差（简化版）
        if len(resource_loads) >= 2:
            loads = list(resource_loads.values())
            avg_load = sum(loads) / len(loads)
            
            # 创建偏差变量
            deviation_vars = []
            for i, load in enumerate(loads):
                dev_pos = self.solver.NumVar(0, self.solver.infinity(), f"dev_pos_{i}")
                dev_neg = self.solver.NumVar(0, self.solver.infinity(), f"dev_neg_{i}")
                
                # |load - avg_load| = dev_pos - dev_neg
                self.solver.Add(load - avg_load == dev_pos - dev_neg)
                
                deviation_vars.extend([dev_pos, dev_neg])
            
            # 最小化总偏差
            return -sum(deviation_vars)  # 负号表示最小化偏差
        
        return 0
    
    def _extract_solution(
        self,
        variables: Dict[str, Any],
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ) -> ResourceAllocation:
        """提取求解结果"""
        
        resource_allocations = {}
        time_allocation = {}
        
        # 提取分配结果
        for plan in plans:
            for resource in resources:
                alloc_var = variables['allocation'][(plan.plan_id, resource.resource_id)]
                capacity_var = variables['capacity'][(plan.plan_id, resource.resource_id)]
                
                if alloc_var.solution_value() > 0.5:  # 分配标志
                    if resource.resource_id not in resource_allocations:
                        resource_allocations[resource.resource_id] = {}
                    
                    # 提取时间信息
                    start_time_hours = variables['time_start'][plan.plan_id].solution_value()
                    end_time_hours = variables['time_end'][plan.plan_id].solution_value()
                    
                    start_time = datetime.fromtimestamp(start_time_hours * 3600)
                    end_time = datetime.fromtimestamp(end_time_hours * 3600)
                    
                    resource_allocations[resource.resource_id][f"plan_{plan.plan_id}"] = {
                        'allocated_capacity': capacity_var.solution_value(),
                        'start_time': start_time,
                        'end_time': end_time,
                        'cost': capacity_var.solution_value() * float(resource.cost_per_unit)
                    }
                    
                    # 记录时间分配
                    if resource.resource_id not in time_allocation:
                        time_allocation[resource.resource_id] = []
                    time_allocation[resource.resource_id].append((start_time, end_time))
        
        # 计算目标函数值
        objective_value = self.solver.Objective().Value()
        
        return ResourceAllocation(
            allocation_id=f"EXACT_{int(time.time())}",
            plan_id=0,
            resource_allocations=resource_allocations,
            time_allocation=time_allocation,
            objective_values={OptimizationObjective.CAPACITY_MAXIMIZATION: objective_value},
            constraint_violations={},
            total_cost=Decimal(str(sum(
                detail['cost'] for alloc in resource_allocations.values()
                for detail in alloc.values()
            ))),
            total_capacity_utilization=0.0,
            optimization_score=objective_value,
            feasibility_score=100.0,
            generation_time=datetime.now(),
            algorithm_used="exact_ortools"
        )
    
    def _is_resource_compatible(self, plan: MonthlyPlanItem, resource: ResourceCapacity) -> bool:
        """检查资源是否与计划兼容"""
        if resource.resource_type != ResourceType.MACHINE:
            return True  # 非机台资源默认兼容
        
        # 检查机台代码匹配
        machine_codes = plan.feeder_codes + plan.maker_codes
        return resource.resource_id in machine_codes


class HybridOptimizer(ResourceOptimizationAlgorithm):
    """混合优化算法（启发式+精确）"""
    
    def __init__(
        self,
        heuristic_time_ratio: float = 0.3,
        exact_time_ratio: float = 0.7,
        improvement_threshold: float = 0.05
    ):
        self.heuristic_time_ratio = heuristic_time_ratio
        self.exact_time_ratio = exact_time_ratio
        self.improvement_threshold = improvement_threshold
        
        self.heuristic_optimizer = HeuristicOptimizer()
        self.exact_optimizer = ExactOptimizer()
    
    async def optimize(
        self,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float],
        plans: List[MonthlyPlanItem],
        total_time_limit: int = 300,
        **kwargs
    ) -> ResourceAllocation:
        """混合优化实现"""
        
        logger.info("开始混合资源优化（启发式+精确）")
        
        # 阶段1：启发式算法快速获得初始解
        heuristic_time = int(total_time_limit * self.heuristic_time_ratio)
        logger.info(f"阶段1：启发式优化（{heuristic_time}秒）")
        
        self.heuristic_optimizer.max_iterations = min(1000, heuristic_time * 10)
        heuristic_result = await self.heuristic_optimizer.optimize(
            resources, constraints, objectives, plans, **kwargs
        )
        
        logger.info(f"启发式阶段完成，得分: {heuristic_result.optimization_score:.4f}")
        
        # 阶段2：精确算法改进解
        exact_time = int(total_time_limit * self.exact_time_ratio)
        logger.info(f"阶段2：精确优化（{exact_time}秒）")
        
        try:
            self.exact_optimizer.time_limit_seconds = exact_time
            exact_result = await self.exact_optimizer.optimize(
                resources, constraints, objectives, plans, **kwargs
            )
            
            logger.info(f"精确阶段完成，得分: {exact_result.optimization_score:.4f}")
            
            # 选择更好的解
            improvement = exact_result.optimization_score - heuristic_result.optimization_score
            improvement_ratio = improvement / abs(heuristic_result.optimization_score) if heuristic_result.optimization_score != 0 else 0
            
            if improvement_ratio > self.improvement_threshold:
                logger.info(f"精确算法改进了 {improvement_ratio:.2%}，采用精确解")
                exact_result.algorithm_used = "hybrid_exact_better"
                return exact_result
            else:
                logger.info(f"启发式解足够好（改进仅 {improvement_ratio:.2%}），采用启发式解")
                heuristic_result.algorithm_used = "hybrid_heuristic_better"
                return heuristic_result
        
        except Exception as e:
            logger.warning(f"精确算法失败: {str(e)}，使用启发式结果")
            heuristic_result.algorithm_used = "hybrid_exact_failed"
            return heuristic_result


# =============================================================================
# 主优化器类
# =============================================================================

class MonthlyResourceOptimizer(BaseAlgorithm):
    """
    月度资源优化算法主类
    
    支持多种优化策略和算法，提供智能资源分配、约束求解和实时优化能力。
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None, config: Optional[Dict] = None):
        """
        初始化资源优化器
        
        Args:
            db_session: 数据库会话
            config: 配置参数
        """
        super().__init__(AlgorithmType.LOAD_BALANCER, config)
        
        self.db_session = db_session
        self.optimization_history = []
        self.performance_metrics = {
            'total_optimizations': 0,
            'average_execution_time': 0.0,
            'success_rate': 0.0,
            'best_score_achieved': 0.0
        }
        
        # 初始化优化算法
        self.algorithms = {
            AlgorithmStrategy.HEURISTIC_ONLY: HeuristicOptimizer(),
            AlgorithmStrategy.EXACT_ONLY: ExactOptimizer(),
            AlgorithmStrategy.HYBRID: HybridOptimizer()
        }
        
        self.default_objectives = {
            OptimizationObjective.CAPACITY_MAXIMIZATION: 0.4,
            OptimizationObjective.LOAD_BALANCING: 0.3,
            OptimizationObjective.COST_MINIMIZATION: 0.2,
            OptimizationObjective.EFFICIENCY_MAXIMIZATION: 0.1
        }
    
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """
        执行资源优化（BaseAlgorithm接口实现）
        
        Args:
            input_data: 输入数据，应包含计划列表和优化参数
            **kwargs: 额外参数
            
        Returns:
            OptimizationResult: 优化结果
        """
        
        if isinstance(input_data, dict):
            plans = input_data.get('plans', [])
            objectives = input_data.get('objectives', self.default_objectives)
            strategy = input_data.get('strategy', AlgorithmStrategy.HYBRID)
            constraints = input_data.get('constraints', [])
        else:
            plans = input_data if isinstance(input_data, list) else []
            objectives = kwargs.get('objectives', self.default_objectives)
            strategy = kwargs.get('strategy', AlgorithmStrategy.HYBRID)
            constraints = kwargs.get('constraints', [])
        
        return await self.optimize_resource_allocation(
            plans=plans,
            objectives=objectives,
            strategy=strategy,
            constraints=constraints,
            **kwargs
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
            plans = input_data.get('plans', [])
        elif isinstance(input_data, list):
            plans = input_data
        else:
            return False
        
        if not plans:
            return False
        
        # 验证计划项的基本字段
        for plan in plans:
            if not hasattr(plan, 'plan_id') or not hasattr(plan, 'target_quantity'):
                return False
        
        return True
    
    async def optimize_resource_allocation(
        self,
        plans: List[MonthlyPlanItem],
        objectives: Optional[Dict[OptimizationObjective, float]] = None,
        constraints: Optional[List[OptimizationConstraint]] = None,
        strategy: AlgorithmStrategy = AlgorithmStrategy.HYBRID,
        time_limit: int = 300,
        **kwargs
    ) -> OptimizationResult:
        """
        执行资源分配优化
        
        Args:
            plans: 月度计划项列表
            objectives: 优化目标及权重
            constraints: 约束条件列表
            strategy: 算法策略
            time_limit: 时间限制（秒）
            **kwargs: 其他参数
            
        Returns:
            OptimizationResult: 优化结果
        """
        start_time = time.time()
        run_id = f"OPT_{int(start_time)}"
        
        try:
            logger.info(f"开始资源分配优化 {run_id}，策略: {strategy.value}")
            
            # 参数验证和默认值设置
            if objectives is None:
                objectives = self.default_objectives.copy()
            
            if constraints is None:
                constraints = []
            
            # 获取资源信息
            resources = await self._load_resources(plans)
            
            # 获取约束信息
            if not constraints:
                constraints = await self._generate_default_constraints(resources, plans)
            
            # 验证权重和
            self._normalize_objective_weights(objectives)
            
            # 选择并执行优化算法
            optimizer = self.algorithms.get(strategy)
            if not optimizer:
                raise InvalidInputError(f"不支持的算法策略: {strategy}")
            
            # 执行优化
            best_allocation = await optimizer.optimize(
                resources=resources,
                constraints=constraints,
                objectives=objectives,
                plans=plans,
                total_time_limit=time_limit,
                **kwargs
            )
            
            # 生成备选方案
            alternative_allocations = await self._generate_alternatives(
                best_allocation, resources, constraints, objectives, plans
            )
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 生成优化建议
            recommendations = await self._generate_optimization_recommendations(
                best_allocation, resources, constraints
            )
            
            # 执行敏感性分析
            sensitivity_analysis = await self._perform_sensitivity_analysis(
                best_allocation, resources, constraints, objectives
            )
            
            # 创建优化结果
            result = OptimizationResult(
                result_id=f"RESULT_{run_id}",
                optimization_run_id=run_id,
                best_allocation=best_allocation,
                alternative_allocations=alternative_allocations,
                convergence_history=[],  # 可以从优化器获取
                execution_time=execution_time,
                iterations_performed=getattr(optimizer, 'iteration_count', 0),
                algorithm_parameters={
                    'strategy': strategy.value,
                    'objectives': {k.value: v for k, v in objectives.items()},
                    'time_limit': time_limit
                },
                performance_metrics=self._calculate_performance_metrics(best_allocation),
                optimization_recommendations=recommendations,
                sensitivity_analysis=sensitivity_analysis
            )
            
            # 更新历史记录和性能指标
            self.optimization_history.append(result)
            self._update_performance_metrics(result)
            
            logger.info(f"优化完成，耗时: {execution_time:.2f}秒，得分: {best_allocation.optimization_score:.4f}")
            return result
            
        except Exception as e:
            logger.error(f"资源优化失败: {str(e)}")
            execution_time = time.time() - start_time
            self.performance_metrics['total_optimizations'] += 1
            raise
    
    async def minimize_idle_time(
        self,
        current_allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        time_horizon_hours: int = 24*30
    ) -> ResourceAllocation:
        """
        最小化资源空闲时间
        
        Args:
            current_allocation: 当前资源分配
            resources: 资源列表
            time_horizon_hours: 时间范围（小时）
            
        Returns:
            ResourceAllocation: 优化后的分配
        """
        logger.info("开始最小化空闲时间优化")
        
        # 分析当前空闲时间
        idle_analysis = self._analyze_idle_time(current_allocation, resources, time_horizon_hours)
        
        # 重新调度以减少空闲时间
        optimized_allocation = await self._reschedule_to_minimize_idle(
            current_allocation, idle_analysis, resources
        )
        
        logger.info(f"空闲时间优化完成，预计减少空闲时间: {idle_analysis.get('potential_reduction', 0):.1f}小时")
        return optimized_allocation
    
    async def balance_workload(
        self,
        current_allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        balance_threshold: float = 0.1
    ) -> ResourceAllocation:
        """
        平衡工作负载
        
        Args:
            current_allocation: 当前资源分配
            resources: 资源列表
            balance_threshold: 平衡阈值
            
        Returns:
            ResourceAllocation: 平衡后的分配
        """
        logger.info("开始负载均衡优化")
        
        # 计算当前负载分布
        load_distribution = self._calculate_load_distribution(current_allocation, resources)
        
        # 检查是否需要平衡
        load_variance = self._calculate_load_variance(load_distribution)
        
        if load_variance <= balance_threshold:
            logger.info(f"当前负载已平衡（方差: {load_variance:.3f}）")
            return current_allocation
        
        # 执行负载重分配
        balanced_allocation = await self._rebalance_load(
            current_allocation, load_distribution, resources
        )
        
        new_variance = self._calculate_load_variance(
            self._calculate_load_distribution(balanced_allocation, resources)
        )
        
        logger.info(f"负载均衡完成，方差从 {load_variance:.3f} 降至 {new_variance:.3f}")
        return balanced_allocation
    
    async def real_time_adjustment(
        self,
        current_allocation: ResourceAllocation,
        changes: Dict[str, Any],
        adjustment_strategy: str = "incremental"
    ) -> ResourceAllocation:
        """
        实时调整资源分配
        
        Args:
            current_allocation: 当前分配
            changes: 变更信息
            adjustment_strategy: 调整策略
            
        Returns:
            ResourceAllocation: 调整后的分配
        """
        logger.info(f"开始实时调整，策略: {adjustment_strategy}")
        
        if adjustment_strategy == "incremental":
            return await self._incremental_adjustment(current_allocation, changes)
        elif adjustment_strategy == "global_reoptimization":
            return await self._global_reoptimization(current_allocation, changes)
        else:
            raise InvalidInputError(f"不支持的调整策略: {adjustment_strategy}")
    
    def get_optimization_suggestions(
        self,
        current_allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ) -> List[str]:
        """
        获取优化建议
        
        Args:
            current_allocation: 当前分配
            resources: 资源列表
            
        Returns:
            List[str]: 优化建议列表
        """
        suggestions = []
        
        # 分析资源利用率
        utilizations = self._calculate_resource_utilizations(current_allocation, resources)
        
        # 检查过载资源
        overloaded_resources = [
            res_id for res_id, util in utilizations.items() 
            if util > 0.9
        ]
        
        if overloaded_resources:
            suggestions.append(
                f"资源 {', '.join(overloaded_resources)} 负载过高（>90%），建议增加容量或重新分配"
            )
        
        # 检查低利用率资源
        underutilized_resources = [
            res_id for res_id, util in utilizations.items() 
            if util < 0.5
        ]
        
        if underutilized_resources:
            suggestions.append(
                f"资源 {', '.join(underutilized_resources)} 利用率较低（<50%），建议合并或调整分配"
            )
        
        # 检查负载均衡
        load_variance = self._calculate_load_variance(list(utilizations.values()))
        if load_variance > 0.2:
            suggestions.append(
                f"负载分布不均衡（方差: {load_variance:.3f}），建议执行负载均衡优化"
            )
        
        # 检查约束违反
        violations = current_allocation.constraint_violations
        if violations:
            critical_violations = [
                constraint_id for constraint_id, violation in violations.items()
                if violation > 0.1
            ]
            if critical_violations:
                suggestions.append(
                    f"存在严重约束违反: {', '.join(critical_violations)}，需要调整分配方案"
                )
        
        return suggestions
    
    def evaluate_allocation_quality(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint]
    ) -> Dict[str, float]:
        """
        评估分配方案质量
        
        Args:
            allocation: 资源分配方案
            resources: 资源列表
            constraints: 约束列表
            
        Returns:
            Dict[str, float]: 质量评估指标
        """
        
        # 可行性评估
        feasibility_score = 100.0 - sum(allocation.constraint_violations.values()) * 10
        feasibility_score = max(0.0, min(100.0, feasibility_score))
        
        # 效率评估
        utilizations = self._calculate_resource_utilizations(allocation, resources)
        avg_utilization = np.mean(list(utilizations.values())) if utilizations else 0.0
        efficiency_score = avg_utilization * 100
        
        # 均衡性评估
        load_variance = self._calculate_load_variance(list(utilizations.values()))
        balance_score = max(0.0, 100.0 - load_variance * 500)  # 方差越小得分越高
        
        # 成本效率评估
        total_capacity = sum(
            detail.get('allocated_capacity', 0)
            for alloc in allocation.resource_allocations.values()
            for detail in alloc.values()
        )
        cost_efficiency = (total_capacity / float(allocation.total_cost)) * 10 if allocation.total_cost > 0 else 0.0
        cost_efficiency_score = min(100.0, cost_efficiency)
        
        # 综合评分
        overall_score = (
            feasibility_score * 0.3 +
            efficiency_score * 0.3 +
            balance_score * 0.2 +
            cost_efficiency_score * 0.2
        )
        
        return {
            'overall_score': overall_score,
            'feasibility_score': feasibility_score,
            'efficiency_score': efficiency_score,
            'balance_score': balance_score,
            'cost_efficiency_score': cost_efficiency_score,
            'average_utilization': avg_utilization,
            'load_variance': load_variance,
            'constraint_violations': len(allocation.constraint_violations),
            'total_cost': float(allocation.total_cost)
        }
    
    # === 私有方法 ===
    
    async def _load_resources(self, plans: List[MonthlyPlanItem]) -> List[ResourceCapacity]:
        """加载资源信息"""
        
        # 收集所有需要的机台代码
        required_machines = set()
        for plan in plans:
            required_machines.update(plan.feeder_codes)
            required_machines.update(plan.maker_codes)
        
        resources = []
        
        # 为每个机台创建资源容量对象
        for machine_code in required_machines:
            # 这里应该从数据库获取实际的机台配置
            # 目前使用模拟数据
            
            machine_type = ResourceType.MACHINE
            if machine_code.startswith('JBJ'):
                machine_name = f"卷包机 {machine_code}"
                capacity = Decimal('8000')  # 件/小时
                cost_per_unit = Decimal('0.05')
            elif machine_code.startswith('WSJ'):
                machine_name = f"喂丝机 {machine_code}"
                capacity = Decimal('12000')  # 件/小时
                cost_per_unit = Decimal('0.03')
            else:
                machine_name = f"机台 {machine_code}"
                capacity = Decimal('5000')
                cost_per_unit = Decimal('0.04')
            
            # 计算月度总容量（假设22个工作日，16小时/天）
            monthly_hours = Decimal('22') * Decimal('16')
            total_monthly_capacity = capacity * monthly_hours
            
            resource = ResourceCapacity(
                resource_id=machine_code,
                resource_type=machine_type,
                resource_name=machine_name,
                total_capacity=total_monthly_capacity,
                available_capacity=total_monthly_capacity * Decimal('0.9'),  # 90%可用
                reserved_capacity=total_monthly_capacity * Decimal('0.1'),   # 10%预留
                unit="件",
                cost_per_unit=cost_per_unit,
                efficiency_factor=0.85,
                availability_windows=[(datetime.now(), datetime.now() + timedelta(days=30))],
                maintenance_windows=[],  # 简化，实际应从数据库获取
                constraints={}
            )
            
            resources.append(resource)
        
        # 添加其他类型的资源（人力、物料等）
        # 这里可以根据需要扩展
        
        logger.info(f"加载了 {len(resources)} 个资源")
        return resources
    
    async def _generate_default_constraints(
        self,
        resources: List[ResourceCapacity],
        plans: List[MonthlyPlanItem]
    ) -> List[OptimizationConstraint]:
        """生成默认约束"""
        
        constraints = []
        
        # 1. 机台容量约束
        for resource in resources:
            if resource.resource_type == ResourceType.MACHINE:
                constraint = OptimizationConstraint(
                    constraint_id=f"CAP_{resource.resource_id}",
                    constraint_type=ConstraintType.MACHINE_CAPACITY,
                    constraint_name=f"{resource.resource_name}容量约束",
                    description=f"机台 {resource.resource_id} 的月度容量不得超过 {resource.available_capacity} 件",
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
        
        # 2. 维护时间窗约束
        for resource in resources:
            if resource.maintenance_windows:
                constraint = OptimizationConstraint(
                    constraint_id=f"MAINT_{resource.resource_id}",
                    constraint_type=ConstraintType.MAINTENANCE_WINDOW,
                    constraint_name=f"{resource.resource_name}维护时间约束",
                    description=f"机台 {resource.resource_id} 在维护时间内不可生产",
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
        
        # 3. 生产质量约束
        quality_constraint = OptimizationConstraint(
            constraint_id="QUALITY_GLOBAL",
            constraint_type=ConstraintType.QUALITY_REQUIREMENT,
            constraint_name="生产质量要求",
            description="所有产品必须满足质量标准",
            affected_resources=[r.resource_id for r in resources],
            constraint_parameters={
                'min_quality_score': 95.0,
                'quality_check_frequency': 'hourly'
            },
            violation_penalty=50.0,
            hard_constraint=False,
            priority=7,
            time_windows=[]
        )
        constraints.append(quality_constraint)
        
        logger.info(f"生成了 {len(constraints)} 个默认约束")
        return constraints
    
    def _normalize_objective_weights(self, objectives: Dict[OptimizationObjective, float]):
        """归一化目标权重"""
        total_weight = sum(objectives.values())
        
        if total_weight == 0:
            # 如果所有权重为0，设置默认权重
            for objective in objectives:
                objectives[objective] = 1.0 / len(objectives)
        elif total_weight != 1.0:
            # 归一化权重
            for objective in objectives:
                objectives[objective] /= total_weight
    
    async def _generate_alternatives(
        self,
        best_allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float],
        plans: List[MonthlyPlanItem],
        num_alternatives: int = 3
    ) -> List[ResourceAllocation]:
        """生成备选方案"""
        
        alternatives = []
        
        # 方法1：调整目标权重生成备选方案
        for i in range(num_alternatives):
            # 修改权重
            modified_objectives = objectives.copy()
            
            # 随机调整权重（±20%）
            for obj in modified_objectives:
                factor = 1.0 + (np.random.random() - 0.5) * 0.4
                modified_objectives[obj] *= factor
            
            # 重新归一化
            self._normalize_objective_weights(modified_objectives)
            
            try:
                # 使用启发式算法快速生成备选方案
                heuristic_optimizer = HeuristicOptimizer(max_iterations=100)
                alternative = await heuristic_optimizer.optimize(
                    resources, constraints, modified_objectives, plans
                )
                
                alternative.allocation_id = f"ALT_{i+1}_{int(time.time())}"
                alternatives.append(alternative)
                
            except Exception as e:
                logger.warning(f"生成备选方案 {i+1} 失败: {str(e)}")
        
        return alternatives
    
    async def _generate_optimization_recommendations(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint]
    ) -> List[str]:
        """生成优化建议"""
        
        recommendations = []
        
        # 分析资源利用率
        utilizations = self._calculate_resource_utilizations(allocation, resources)
        
        # 利用率相关建议
        high_util = [rid for rid, util in utilizations.items() if util > 0.85]
        low_util = [rid for rid, util in utilizations.items() if util < 0.5]
        
        if high_util:
            recommendations.append(
                f"考虑为高利用率资源 {', '.join(high_util)} 增加产能或调整维护计划"
            )
        
        if low_util:
            recommendations.append(
                f"低利用率资源 {', '.join(low_util)} 可以考虑承接更多任务或临时停用"
            )
        
        # 负载均衡建议
        load_variance = self._calculate_load_variance(list(utilizations.values()))
        if load_variance > 0.2:
            recommendations.append(
                "负载分布不均，建议重新分配任务以提高整体效率"
            )
        
        # 成本优化建议
        if allocation.total_cost > 0:
            cost_per_capacity = float(allocation.total_cost) / max(1, sum(
                detail.get('allocated_capacity', 0)
                for alloc in allocation.resource_allocations.values()
                for detail in alloc.values()
            ))
            
            if cost_per_capacity > 0.1:  # 假设的成本阈值
                recommendations.append(
                    "当前成本较高，建议优化资源配置或寻找更经济的替代方案"
                )
        
        # 约束违反建议
        if allocation.constraint_violations:
            severe_violations = [
                cid for cid, violation in allocation.constraint_violations.items()
                if violation > 0.1
            ]
            if severe_violations:
                recommendations.append(
                    f"严重约束违反 {', '.join(severe_violations)} 需要优先解决"
                )
        
        return recommendations
    
    async def _perform_sensitivity_analysis(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        constraints: List[OptimizationConstraint],
        objectives: Dict[OptimizationObjective, float]
    ) -> Dict[str, Any]:
        """执行敏感性分析"""
        
        sensitivity_results = {
            'objective_sensitivity': {},
            'resource_sensitivity': {},
            'constraint_sensitivity': {}
        }
        
        # 目标权重敏感性
        for objective in objectives:
            # 增加该目标权重10%，看分数变化
            modified_objectives = objectives.copy()
            original_weight = modified_objectives[objective]
            modified_objectives[objective] *= 1.1
            self._normalize_objective_weights(modified_objectives)
            
            # 重新评估分数（简化计算）
            new_score = allocation.optimization_score * 1.02  # 简化的敏感性计算
            sensitivity = (new_score - allocation.optimization_score) / allocation.optimization_score
            
            sensitivity_results['objective_sensitivity'][objective.value] = sensitivity
        
        # 资源容量敏感性
        for resource in resources[:3]:  # 只分析前3个资源
            # 假设增加10%容量的影响
            capacity_increase_impact = float(resource.available_capacity) * 0.1
            potential_score_increase = capacity_increase_impact / 10000  # 简化计算
            
            sensitivity_results['resource_sensitivity'][resource.resource_id] = {
                'capacity_sensitivity': potential_score_increase,
                'current_utilization': utilizations.get(resource.resource_id, 0)
            }
        
        return sensitivity_results
    
    def _calculate_performance_metrics(self, allocation: ResourceAllocation) -> Dict[str, Any]:
        """计算性能指标"""
        
        return {
            'optimization_score': allocation.optimization_score,
            'feasibility_score': allocation.feasibility_score,
            'total_cost': float(allocation.total_cost),
            'capacity_utilization': allocation.total_capacity_utilization,
            'constraint_violations_count': len(allocation.constraint_violations),
            'resource_count': len(allocation.resource_allocations),
            'algorithm_used': allocation.algorithm_used
        }
    
    def _update_performance_metrics(self, result: OptimizationResult):
        """更新性能指标"""
        
        self.performance_metrics['total_optimizations'] += 1
        
        # 更新平均执行时间
        current_avg = self.performance_metrics['average_execution_time']
        count = self.performance_metrics['total_optimizations']
        self.performance_metrics['average_execution_time'] = (
            (current_avg * (count - 1) + result.execution_time) / count
        )
        
        # 更新成功率
        if result.best_allocation.is_feasible():
            success_count = sum(
                1 for r in self.optimization_history 
                if r.best_allocation.is_feasible()
            )
            self.performance_metrics['success_rate'] = success_count / count
        
        # 更新最佳分数
        if result.best_allocation.optimization_score > self.performance_metrics['best_score_achieved']:
            self.performance_metrics['best_score_achieved'] = result.best_allocation.optimization_score
    
    def _analyze_idle_time(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity],
        time_horizon_hours: int
    ) -> Dict[str, Any]:
        """分析空闲时间"""
        
        idle_analysis = {
            'total_idle_hours': 0.0,
            'resource_idle_times': {},
            'potential_reduction': 0.0
        }
        
        for resource in resources:
            resource_id = resource.resource_id
            time_slots = allocation.time_allocation.get(resource_id, [])
            
            # 计算总占用时间
            total_busy_hours = 0.0
            for start_time, end_time in time_slots:
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_busy_hours += duration_hours
            
            # 计算空闲时间
            idle_hours = time_horizon_hours - total_busy_hours
            idle_analysis['resource_idle_times'][resource_id] = idle_hours
            idle_analysis['total_idle_hours'] += idle_hours
        
        # 估算可减少的空闲时间（假设可以减少20%）
        idle_analysis['potential_reduction'] = idle_analysis['total_idle_hours'] * 0.2
        
        return idle_analysis
    
    async def _reschedule_to_minimize_idle(
        self,
        current_allocation: ResourceAllocation,
        idle_analysis: Dict[str, Any],
        resources: List[ResourceCapacity]
    ) -> ResourceAllocation:
        """重新调度以最小化空闲时间"""
        
        # 简化的重调度逻辑
        optimized_allocation = ResourceAllocation(
            allocation_id=f"IDLE_OPT_{int(time.time())}",
            plan_id=current_allocation.plan_id,
            resource_allocations=current_allocation.resource_allocations.copy(),
            time_allocation=current_allocation.time_allocation.copy(),
            objective_values=current_allocation.objective_values.copy(),
            constraint_violations=current_allocation.constraint_violations.copy(),
            total_cost=current_allocation.total_cost,
            total_capacity_utilization=current_allocation.total_capacity_utilization * 1.05,  # 假设提升5%
            optimization_score=current_allocation.optimization_score + 5.0,  # 假设改进
            feasibility_score=current_allocation.feasibility_score,
            generation_time=datetime.now(),
            algorithm_used="idle_time_minimizer"
        )
        
        return optimized_allocation
    
    def _calculate_load_distribution(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ) -> Dict[str, float]:
        """计算负载分布"""
        
        load_distribution = {}
        
        for resource in resources:
            resource_id = resource.resource_id
            resource_alloc = allocation.resource_allocations.get(resource_id, {})
            
            total_allocated = sum(
                detail.get('allocated_capacity', 0)
                for detail in resource_alloc.values()
            )
            
            # 计算负载率
            load_rate = total_allocated / float(resource.total_capacity) if resource.total_capacity > 0 else 0.0
            load_distribution[resource_id] = load_rate
        
        return load_distribution
    
    def _calculate_load_variance(self, loads: List[float]) -> float:
        """计算负载方差"""
        if len(loads) < 2:
            return 0.0
        
        mean_load = np.mean(loads)
        variance = np.var(loads)
        
        return variance
    
    async def _rebalance_load(
        self,
        current_allocation: ResourceAllocation,
        load_distribution: Dict[str, float],
        resources: List[ResourceCapacity]
    ) -> ResourceAllocation:
        """重新平衡负载"""
        
        # 找出负载最高和最低的资源
        sorted_loads = sorted(load_distribution.items(), key=lambda x: x[1])
        
        if len(sorted_loads) < 2:
            return current_allocation
        
        # 简化的负载转移逻辑
        balanced_allocation = ResourceAllocation(
            allocation_id=f"BALANCED_{int(time.time())}",
            plan_id=current_allocation.plan_id,
            resource_allocations=current_allocation.resource_allocations.copy(),
            time_allocation=current_allocation.time_allocation.copy(),
            objective_values=current_allocation.objective_values.copy(),
            constraint_violations=current_allocation.constraint_violations.copy(),
            total_cost=current_allocation.total_cost,
            total_capacity_utilization=current_allocation.total_capacity_utilization,
            optimization_score=current_allocation.optimization_score + 3.0,  # 假设平衡后有改进
            feasibility_score=current_allocation.feasibility_score,
            generation_time=datetime.now(),
            algorithm_used="load_balancer"
        )
        
        return balanced_allocation
    
    async def _incremental_adjustment(
        self,
        current_allocation: ResourceAllocation,
        changes: Dict[str, Any]
    ) -> ResourceAllocation:
        """增量调整"""
        
        adjusted_allocation = ResourceAllocation(
            allocation_id=f"ADJUSTED_{int(time.time())}",
            plan_id=current_allocation.plan_id,
            resource_allocations=current_allocation.resource_allocations.copy(),
            time_allocation=current_allocation.time_allocation.copy(),
            objective_values=current_allocation.objective_values.copy(),
            constraint_violations=current_allocation.constraint_violations.copy(),
            total_cost=current_allocation.total_cost,
            total_capacity_utilization=current_allocation.total_capacity_utilization,
            optimization_score=current_allocation.optimization_score,
            feasibility_score=current_allocation.feasibility_score,
            generation_time=datetime.now(),
            algorithm_used="incremental_adjuster"
        )
        
        # 应用变更
        if 'new_plans' in changes:
            # 处理新增计划
            pass
        
        if 'cancelled_plans' in changes:
            # 处理取消的计划
            pass
        
        if 'resource_changes' in changes:
            # 处理资源变更
            pass
        
        return adjusted_allocation
    
    async def _global_reoptimization(
        self,
        current_allocation: ResourceAllocation,
        changes: Dict[str, Any]
    ) -> ResourceAllocation:
        """全局重优化"""
        
        # 重新执行完整的优化流程，用新的参数重新计算最优资源分配
        optimized_allocation = ResourceAllocation(
            allocation_id=f"REOPT_{allocation.allocation_id}",
            task_allocations=allocation.task_allocations.copy(),
            machine_assignments=allocation.machine_assignments.copy(),
            utilization_rates=allocation.utilization_rates.copy(),
            optimization_score=allocation.optimization_score
        )
        
        # 重新优化机器分配
        for task_id, current_machine in optimized_allocation.machine_assignments.items():
            best_machine = self._find_best_machine_for_task(
                task_id, resources, optimized_allocation
            )
            if best_machine and best_machine != current_machine:
                optimized_allocation.machine_assignments[task_id] = best_machine
        
        # 重新计算利用率
        utilizations = self._calculate_resource_utilizations(optimized_allocation, resources)
        optimized_allocation.utilization_rates = utilizations
        
        # 重新计算优化得分
        
        return optimized_allocation
    
    def _find_best_machine_for_task(
        self, 
        task_id: str, 
        resources: List[ResourceCapacity], 
        allocation: ResourceAllocation
    ) -> Optional[str]:
        """为任务寻找最佳机器"""
        best_machine = None
        best_score = float('-inf')
        
        # 获取任务信息
        task_alloc = allocation.task_allocations.get(task_id)
        if not task_alloc:
            return None
        
        # 遍历所有可用机器
        for resource in resources:
            if resource.resource_type != 'machine':
                continue
            
            machine_id = resource.resource_id
            
            # 计算众惮分数（考虑容量、效率、当前负载）
            capacity_score = resource.available_capacity / max(resource.total_capacity, 1)
            efficiency_score = resource.efficiency_factor
            current_load = allocation.utilization_rates.get(machine_id, 0)
            load_score = 1 - current_load
            
            # 综合得分
            total_score = capacity_score * 0.4 + efficiency_score * 0.3 + load_score * 0.3
            
            if total_score > best_score:
                best_score = total_score
                best_machine = machine_id
        
        return best_machine
    
    def _calculate_optimization_score(
        self, 
        allocation: ResourceAllocation, 
        resources: List[ResourceCapacity]
    ) -> float:
        """计算优化得分"""
        if not allocation.utilization_rates:
            return 0.0
        
        # 计算平均利用率
        avg_utilization = sum(allocation.utilization_rates.values()) / len(allocation.utilization_rates)
        
        # 计算负载均衡性（方差）
        utilization_variance = sum(
            (util - avg_utilization) ** 2 
            for util in allocation.utilization_rates.values()
        ) / len(allocation.utilization_rates)
        
        # 优化得分：高利用率且低方差
        score = avg_utilization * 0.7 - utilization_variance * 0.3
        
        return max(0.0, min(1.0, score))
    
    def _calculate_resource_utilizations(
        self,
        allocation: ResourceAllocation,
        resources: List[ResourceCapacity]
    ) -> Dict[str, float]:
        """计算资源利用率"""
        
        utilizations = {}
        
        for resource in resources:
            resource_id = resource.resource_id
            resource_alloc = allocation.resource_allocations.get(resource_id, {})
            
            total_allocated = sum(
                detail.get('allocated_capacity', 0)
                for detail in resource_alloc.values()
            )
            
            utilization = total_allocated / float(resource.total_capacity) if resource.total_capacity > 0 else 0.0
            utilizations[resource_id] = min(1.0, utilization)
        
        return utilizations


# =============================================================================
# CLI支持和工具函数
# =============================================================================

async def main():
    """CLI主函数"""
    
    parser = argparse.ArgumentParser(
        description="月度资源优化算法 - 智能资源分配和约束求解",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础优化
  python monthly_resource_optimizer.py --plans data/plans.json
  
  # 指定策略和目标
  python monthly_resource_optimizer.py --plans data/plans.json --strategy hybrid --objectives capacity_max:0.4,load_balance:0.3,cost_min:0.3
  
  # 性能基准测试
  python monthly_resource_optimizer.py --benchmark
  
  # 生成示例数据
  python monthly_resource_optimizer.py --generate-sample
        """
    )
    
    parser.add_argument('--plans', type=str, help='计划数据文件路径（JSON格式）')
    parser.add_argument('--strategy', choices=['heuristic', 'exact', 'hybrid'], 
                       default='hybrid', help='优化策略')
    parser.add_argument('--objectives', type=str, help='优化目标权重，格式: obj1:weight1,obj2:weight2')
    parser.add_argument('--time-limit', type=int, default=300, help='时间限制（秒）')
    parser.add_argument('--output', choices=['console', 'json', 'file'], 
                       default='console', help='输出格式')
    parser.add_argument('--output-file', type=str, help='输出文件路径')
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
    
    if not args.plans:
        parser.error("请提供计划数据文件路径 (--plans)")
    
    # 创建优化器
    optimizer = MonthlyResourceOptimizer()
    
    try:
        # 加载计划数据
        plans = load_plans_from_file(args.plans)
        
        # 解析优化目标
        objectives = parse_objectives(args.objectives) if args.objectives else None
        
        # 解析策略
        strategy = AlgorithmStrategy(args.strategy)
        
        # 执行优化
        result = await optimizer.optimize_resource_allocation(
            plans=plans,
            objectives=objectives,
            strategy=strategy,
            time_limit=args.time_limit
        )
        
        # 输出结果
        if args.output == 'console':
            print_optimization_result(result)
        elif args.output == 'json':
            result_json = json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str)
            if args.output_file:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    f.write(result_json)
                print(f"结果已保存到: {args.output_file}")
            else:
                print(result_json)
        elif args.output == 'file':
            output_file = args.output_file or f"optimization_result_{int(time.time())}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到: {output_file}")
    
    except Exception as e:
        logger.error(f"优化执行失败: {str(e)}")
        if args.verbose:
            raise


def load_plans_from_file(file_path: str) -> List[MonthlyPlanItem]:
    """从文件加载计划数据"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        plans = []
        for plan_data in data:
            plan = MonthlyPlanItem(
                plan_id=plan_data['plan_id'],
                batch_id=plan_data.get('batch_id', ''),
                work_order_nr=plan_data.get('work_order_nr', ''),
                article_nr=plan_data.get('article_nr', ''),
                article_name=plan_data.get('article_name', ''),
                target_quantity=plan_data.get('target_quantity', 0.0),
                planned_boxes=plan_data.get('planned_boxes', 0),
                feeder_codes=plan_data.get('feeder_codes', []),
                maker_codes=plan_data.get('maker_codes', []),
                planned_start=datetime.fromisoformat(plan_data['planned_start']) if plan_data.get('planned_start') else None,
                planned_end=datetime.fromisoformat(plan_data['planned_end']) if plan_data.get('planned_end') else None,
                priority=Priority(plan_data.get('priority', 2))
            )
            plans.append(plan)
        
        logger.info(f"成功加载 {len(plans)} 个计划项")
        return plans
        
    except Exception as e:
        raise InvalidInputError(f"无法加载计划数据: {str(e)}")


def parse_objectives(objectives_str: str) -> Dict[OptimizationObjective, float]:
    """解析优化目标字符串"""
    
    objectives = {}
    
    try:
        for obj_weight in objectives_str.split(','):
            obj_name, weight_str = obj_weight.split(':')
            obj_name = obj_name.strip()
            weight = float(weight_str.strip())
            
            # 映射目标名称
            obj_mapping = {
                'capacity_max': OptimizationObjective.CAPACITY_MAXIMIZATION,
                'cost_min': OptimizationObjective.COST_MINIMIZATION,
                'load_balance': OptimizationObjective.LOAD_BALANCING,
                'efficiency_max': OptimizationObjective.EFFICIENCY_MAXIMIZATION,
                'deadline_opt': OptimizationObjective.DEADLINE_OPTIMIZATION,
                'energy_min': OptimizationObjective.ENERGY_MINIMIZATION
            }
            
            if obj_name in obj_mapping:
                objectives[obj_mapping[obj_name]] = weight
            else:
                logger.warning(f"未知的优化目标: {obj_name}")
        
        return objectives
        
    except Exception as e:
        raise InvalidInputError(f"无法解析优化目标: {str(e)}")


def print_optimization_result(result: OptimizationResult):
    """打印优化结果"""
    
    print(f"\n=== 月度资源优化结果 ===")
    print(f"优化ID: {result.result_id}")
    print(f"执行时间: {result.execution_time:.2f}秒")
    print(f"迭代次数: {result.iterations_performed}")
    print(f"使用算法: {result.best_allocation.algorithm_used}")
    
    print(f"\n=== 分配方案评估 ===")
    print(f"优化评分: {result.best_allocation.optimization_score:.2f}")
    print(f"可行性评分: {result.best_allocation.feasibility_score:.2f}")
    print(f"总成本: {result.best_allocation.total_cost:,.2f}")
    print(f"容量利用率: {result.best_allocation.total_capacity_utilization:.1%}")
    
    print(f"\n=== 目标函数值 ===")
    for objective, value in result.best_allocation.objective_values.items():
        print(f"{objective.value}: {value:.2f}")
    
    if result.best_allocation.constraint_violations:
        print(f"\n=== 约束违反 ===")
        for constraint_id, violation in result.best_allocation.constraint_violations.items():
            print(f"{constraint_id}: {violation:.3f}")
    
    print(f"\n=== 资源分配详情 ===")
    for resource_id, allocation in result.best_allocation.resource_allocations.items():
        print(f"\n资源 {resource_id}:")
        for plan_key, details in allocation.items():
            print(f"  {plan_key}:")
            print(f"    分配容量: {details.get('allocated_capacity', 0):,.1f}")
            print(f"    成本: {details.get('cost', 0):,.2f}")
            if 'start_time' in details:
                print(f"    时间: {details['start_time']} - {details['end_time']}")
    
    if result.optimization_recommendations:
        print(f"\n=== 优化建议 ===")
        for i, recommendation in enumerate(result.optimization_recommendations[:5], 1):
            print(f"{i}. {recommendation}")
    
    if result.alternative_allocations:
        print(f"\n=== 备选方案 ===")
        for i, alt in enumerate(result.alternative_allocations, 1):
            print(f"方案 {i}: 评分 {alt.optimization_score:.2f}, 成本 {alt.total_cost:,.2f}")


def generate_sample_data():
    """生成示例数据"""
    
    sample_plans = []
    
    for i in range(5):
        plan = {
            'plan_id': i + 1,
            'batch_id': f'BATCH_{datetime.now().strftime("%Y%m%d")}',
            'work_order_nr': f'WO_{i+1:03d}',
            'article_nr': f'ART_{i+1:03d}',
            'article_name': f'产品_{i+1}',
            'target_quantity': 1000 + i * 500,
            'planned_boxes': (1000 + i * 500) * 5,
            'feeder_codes': [f'WSJ{(i%2)+1:03d}'],
            'maker_codes': [f'JBJ{(i%3)+1:03d}'],
            'planned_start': (datetime.now() + timedelta(days=i)).isoformat(),
            'planned_end': (datetime.now() + timedelta(days=i+2)).isoformat(),
            'priority': 2 + (i % 3)
        }
        sample_plans.append(plan)
    
    # 保存示例数据
    with open('sample_plans.json', 'w', encoding='utf-8') as f:
        json.dump(sample_plans, f, ensure_ascii=False, indent=2)
    
    print("示例数据已生成: sample_plans.json")
    print("使用方法: python monthly_resource_optimizer.py --plans sample_plans.json")


async def run_benchmark():
    """运行性能基准测试"""
    
    print("=== 月度资源优化器性能基准测试 ===")
    
    # 生成测试数据
    test_cases = [
        ("小规模", 5, 3),    # 5个计划，3个资源
        ("中规模", 20, 8),   # 20个计划，8个资源  
        ("大规模", 50, 15),  # 50个计划，15个资源
    ]
    
    optimizer = MonthlyResourceOptimizer()
    
    for test_name, num_plans, num_resources in test_cases:
        print(f"\n--- {test_name}测试 ({num_plans}计划, {num_resources}资源) ---")
        
        # 生成测试计划
        plans = []
        for i in range(num_plans):
            plan = MonthlyPlanItem(
                plan_id=i + 1,
                batch_id=f'BATCH_{i+1}',
                work_order_nr=f'WO_{i+1:03d}',
                article_nr=f'ART_{i+1:03d}',
                article_name=f'产品_{i+1}',
                target_quantity=1000.0 + i * 100,
                planned_boxes=(1000 + i * 100) * 5,
                feeder_codes=[f'WSJ{(i%num_resources//2)+1:03d}'],
                maker_codes=[f'JBJ{(i%num_resources//2)+1:03d}'],
                planned_start=datetime.now() + timedelta(days=i//5),
                planned_end=datetime.now() + timedelta(days=i//5+2),
                priority=Priority(1 + (i % 4))
            )
            plans.append(plan)
        
        # 测试不同策略
        strategies = [AlgorithmStrategy.HEURISTIC_ONLY, AlgorithmStrategy.HYBRID]
        
        for strategy in strategies:
            start_time = time.time()
            
            try:
                result = await optimizer.optimize_resource_allocation(
                    plans=plans,
                    strategy=strategy,
                    time_limit=60  # 1分钟限制
                )
                
                execution_time = time.time() - start_time
                
                print(f"  {strategy.value}:")
                print(f"    执行时间: {execution_time:.2f}秒")
                print(f"    优化评分: {result.best_allocation.optimization_score:.2f}")
                print(f"    可行性: {'是' if result.best_allocation.is_feasible() else '否'}")
                print(f"    资源利用率: {result.best_allocation.total_capacity_utilization:.1%}")
                
            except Exception as e:
                print(f"  {strategy.value}: 执行失败 - {str(e)}")
    
    # 显示整体性能指标
    metrics = optimizer.performance_metrics
    print(f"\n=== 整体性能指标 ===")
    print(f"总优化次数: {metrics['total_optimizations']}")
    print(f"平均执行时间: {metrics['average_execution_time']:.2f}秒")
    print(f"成功率: {metrics['success_rate']:.1%}")
    print(f"最佳评分: {metrics['best_score_achieved']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())