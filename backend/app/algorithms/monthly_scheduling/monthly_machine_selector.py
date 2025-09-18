#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度机台选择算法模块 T022

本模块实现 MonthlyMachineSelector 类，提供基于月度容量的最优机台组合选择功能，
支持卷包机和喂丝机的联合选择优化，考虑机台维护计划、产能限制、产品适配性等约束条件。

主要功能：
- 基于月度容量的机台选择算法
- 卷包机和喂丝机联合优化
- 机台维护计划集成
- 产能限制和产品适配性校验
- 工作日历集成和实际可用工作时间计算
- CLI支持和多种输出格式
- 异步数据库查询，性能优化

作者: APS Team
创建时间: 2025-01-17
版本: 1.0.0
"""

import argparse
import asyncio
import json
import math
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict

from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.connection import get_async_session
from app.models.base_models import Machine
from app.models.machine_config_models import MachineSpeed, MachineRelation, MaintenancePlan
from app.models.monthly_plan_models import MonthlyPlan
from app.algorithms.base import AlgorithmBase, AlgorithmResult, ProcessingStage
from app.algorithms.monthly_scheduling.base import MachineType, Priority, MonthlyPlanItem
try:
    from app.algorithms.monthly_scheduling.monthly_capacity_calculator import ProductionRequirement
except ImportError:
    # 如果无法导入，定义一个简化版本
    @dataclass
    class ProductionRequirement:
        article_nr: str
        article_name: str
        target_quantity: Decimal
        priority: int
        planned_start: Optional[datetime] = None
        planned_end: Optional[datetime] = None
        machine_preferences: Optional[List[str]] = None
from app.algorithms.monthly_scheduling.monthly_calendar_service import MonthlyCalendarService, CalendarDay

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class MachineSelectionStrategy(Enum):
    """机台选择策略枚举"""
    CAPACITY_OPTIMAL = "capacity_optimal"          # 产能最优
    EFFICIENCY_OPTIMAL = "efficiency_optimal"     # 效率最优
    BALANCE_OPTIMAL = "balance_optimal"            # 平衡最优
    COST_OPTIMAL = "cost_optimal"                  # 成本最优
    MAINTENANCE_AWARE = "maintenance_aware"        # 维护感知


class SelectionObjective(Enum):
    """选择目标枚举"""
    MAXIMIZE_THROUGHPUT = "maximize_throughput"    # 最大化产出
    MINIMIZE_COST = "minimize_cost"                # 最小化成本
    BALANCE_LOAD = "balance_load"                  # 负载均衡
    MINIMIZE_SETUP = "minimize_setup"              # 最小化换产


@dataclass
class MachineCapability:
    """机台能力信息"""
    machine_code: str
    machine_type: MachineType
    machine_name: str
    equipment_type: str
    production_line: str
    
    # 产能信息
    base_capacity_per_hour: Decimal
    efficiency_factor: Decimal
    current_utilization: Decimal
    
    # 适配性信息
    supported_articles: Set[str]
    preferred_articles: Set[str]
    setup_time_matrix: Dict[str, Decimal]  # 换产时间矩阵
    
    # 可用性信息
    is_available: bool
    availability_score: Decimal
    maintenance_windows: List[Tuple[datetime, datetime]]
    working_time_factor: Decimal
    
    # 关联信息（针对卷包机和喂丝机关系）
    related_machines: List[str]
    preferred_relations: List[str]
    
    def calculate_effective_capacity(
        self, 
        working_days: int, 
        hours_per_day: Decimal = Decimal("16")
    ) -> Decimal:
        """计算有效产能"""
        daily_capacity = self.base_capacity_per_hour * hours_per_day
        monthly_capacity = daily_capacity * working_days
        effective_capacity = (
            monthly_capacity * 
            self.efficiency_factor * 
            self.working_time_factor * 
            self.availability_score
        )
        return effective_capacity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class MachineSelectionCriteria:
    """机台选择标准"""
    article_nr: str
    target_quantity: Decimal
    planned_start: Optional[datetime]
    planned_end: Optional[datetime]
    priority: Priority
    
    # 约束条件
    required_machine_types: List[MachineType]
    preferred_machines: List[str]
    excluded_machines: List[str]
    max_setup_time: Optional[Decimal]
    min_efficiency: Optional[Decimal]
    
    # 优化目标
    selection_strategy: MachineSelectionStrategy
    objective: SelectionObjective


@dataclass
class MachineSelectionResult:
    """机台选择结果"""
    selection_id: str
    criteria: MachineSelectionCriteria
    
    # 选择的机台
    selected_feeder: Optional[str]
    selected_maker: Optional[str]
    backup_feeders: List[str]
    backup_makers: List[str]
    
    # 性能指标
    total_capacity: Decimal
    estimated_completion_time: Optional[datetime]
    efficiency_score: Decimal
    utilization_impact: Dict[str, Decimal]
    
    # 约束满足情况
    constraints_satisfied: bool
    constraint_violations: List[str]
    
    # 详细分析
    selection_reasoning: str
    capacity_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "selection_id": self.selection_id,
            "criteria": {
                "article_nr": self.criteria.article_nr,
                "target_quantity": float(self.criteria.target_quantity),
                "planned_start": self.criteria.planned_start.isoformat() if self.criteria.planned_start else None,
                "planned_end": self.criteria.planned_end.isoformat() if self.criteria.planned_end else None,
                "priority": self.criteria.priority.value,
                "strategy": self.criteria.selection_strategy.value,
                "objective": self.criteria.objective.value
            },
            "selected_machines": {
                "feeder": self.selected_feeder,
                "maker": self.selected_maker,
                "backup_feeders": self.backup_feeders,
                "backup_makers": self.backup_makers
            },
            "performance": {
                "total_capacity": float(self.total_capacity),
                "estimated_completion_time": self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
                "efficiency_score": float(self.efficiency_score),
                "utilization_impact": {k: float(v) for k, v in self.utilization_impact.items()}
            },
            "constraints": {
                "satisfied": self.constraints_satisfied,
                "violations": self.constraint_violations
            },
            "analysis": {
                "reasoning": self.selection_reasoning,
                "capacity_analysis": self.capacity_analysis,
                "risk_assessment": self.risk_assessment
            }
        }


@dataclass
class MonthlyMachineSelectorConfig:
    """月度机台选择器配置"""
    # 产能计算配置
    default_working_hours_per_day: Decimal = Decimal("16")
    overtime_factor: Decimal = Decimal("1.2")
    efficiency_threshold: Decimal = Decimal("0.75")
    utilization_threshold: Decimal = Decimal("0.85")
    
    # 选择算法配置
    capacity_weight: Decimal = Decimal("0.4")
    efficiency_weight: Decimal = Decimal("0.3") 
    availability_weight: Decimal = Decimal("0.2")
    relationship_weight: Decimal = Decimal("0.1")
    
    # 约束配置
    max_selection_candidates: int = 50
    backup_machines_count: int = 2
    setup_time_penalty: Decimal = Decimal("0.1")
    maintenance_buffer_hours: int = 4
    
    # 风险评估配置
    risk_tolerance: Decimal = Decimal("0.2")
    contingency_capacity: Decimal = Decimal("0.15")


class MonthlyMachineSelector(AlgorithmBase):
    """
    月度机台选择算法
    
    基于月度容量选择最优机台组合，支持卷包机和喂丝机的联合选择优化，
    考虑机台维护计划、产能限制、产品适配性等约束条件。
    
    主要特性：
    - 多策略机台选择算法
    - 智能产能计算和预测
    - 维护计划和工作日历集成
    - 机台关系优化
    - 风险评估和备选方案
    - 异步高性能查询
    """
    
    def __init__(
        self, 
        session: AsyncSession, 
        calendar_service: Optional[MonthlyCalendarService] = None,
        config: Optional[MonthlyMachineSelectorConfig] = None
    ):
        """
        初始化月度机台选择器
        
        Args:
            session: 异步数据库会话
            calendar_service: 日历服务实例
            config: 选择器配置
        """
        super().__init__(ProcessingStage.DATA_PREPROCESSING)  # 使用适当的阶段
        self.session = session
        self.calendar_service = calendar_service
        self.config = config or MonthlyMachineSelectorConfig()
        
        # 缓存机制 - 性能优化
        self._machine_cache: Dict[str, MachineCapability] = {}
        self._relationship_cache: Dict[str, List[str]] = {}
        self._speed_cache: Dict[Tuple[str, str], Decimal] = {}
        self._capacity_cache: Dict[Tuple[str, int, int], Dict[str, Any]] = {}  # (machine_code, year, month) -> capacity_info
        
        # 性能监控
        self._performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "queries_executed": 0,
            "batch_operations": 0
        }
        
        self.algorithm_name = "月度机台选择算法"
        self.version = __version__
        
        logger.info(f"初始化 {self.algorithm_name} v{self.version}")
        logger.info(f"性能配置: 最大候选机台={self.config.max_selection_candidates}, 批处理=启用")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        total_cache_ops = self._performance_stats["cache_hits"] + self._performance_stats["cache_misses"]
        cache_hit_rate = (
            self._performance_stats["cache_hits"] / total_cache_ops * 100
            if total_cache_ops > 0 else 0
        )
        
        return {
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "total_queries": self._performance_stats["queries_executed"],
            "batch_operations": self._performance_stats["batch_operations"],
            "cache_size": {
                "machines": len(self._machine_cache),
                "relationships": len(self._relationship_cache),
                "speeds": len(self._speed_cache),
                "capacities": len(self._capacity_cache)
            }
        }
    
    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._machine_cache.clear()
        self._relationship_cache.clear()
        self._speed_cache.clear()
        self._capacity_cache.clear()
        
        # 重置性能统计
        self._performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "queries_executed": 0,
            "batch_operations": 0
        }
        
        logger.info("缓存已清除")
    
    async def batch_calculate_machine_capacity(
        self,
        machine_codes: List[str],
        year: int,
        month: int,
        article_nr: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量计算机台产能 - 性能优化版本
        
        Args:
            machine_codes: 机台代码列表
            year: 年份
            month: 月份
            article_nr: 可选的物料编号
            
        Returns:
            机台产能信息字典 {machine_code: capacity_info}
        """
        try:
            logger.info(f"批量计算机台产能: {len(machine_codes)} 台机台, {year}-{month:02d}")
            self._performance_stats["batch_operations"] += 1
            
            results = {}
            uncached_machines = []
            
            # 1. 检查缓存
            for machine_code in machine_codes:
                cache_key = (machine_code, year, month)
                if cache_key in self._capacity_cache:
                    results[machine_code] = self._capacity_cache[cache_key]
                    self._performance_stats["cache_hits"] += 1
                else:
                    uncached_machines.append(machine_code)
                    self._performance_stats["cache_misses"] += 1
            
            if not uncached_machines:
                logger.info(f"批量产能计算完成 (全部命中缓存): {len(machine_codes)} 台机台")
                return results
            
            # 2. 批量获取机台能力信息
            machine_capabilities = await self._batch_get_machine_capabilities(uncached_machines)
            
            # 3. 批量获取工作日历信息
            if self.calendar_service:
                calendar_days, month_capacity = await self.calendar_service.get_month_calendar(year, month)
                working_days = len([day for day in calendar_days if day.is_working])
                total_capacity_factor = month_capacity.total_capacity_factor
            else:
                from calendar import monthrange
                _, days_in_month = monthrange(year, month)
                working_days = days_in_month * 5 // 7
                total_capacity_factor = Decimal(str(working_days))
            
            # 4. 批量计算产能
            for machine_code in uncached_machines:
                capability = machine_capabilities.get(machine_code)
                if not capability:
                    continue
                
                # 计算基础产能
                base_hourly_capacity = capability.base_capacity_per_hour
                if article_nr:
                    speed_factor = await self._get_machine_speed_factor(machine_code, article_nr)
                    base_hourly_capacity *= speed_factor
                
                # 计算月度产能
                effective_capacity = capability.calculate_effective_capacity(
                    working_days, 
                    self.config.default_working_hours_per_day
                )
                
                # 维护计划影响
                maintenance_impact = await self._calculate_maintenance_impact(
                    machine_code, year, month
                )
                effective_capacity *= (Decimal("1.0") - maintenance_impact)
                
                # 当前利用率影响
                current_load = await self._get_current_machine_load(machine_code, year, month)
                available_capacity = effective_capacity * (Decimal("1.0") - current_load)
                
                capacity_info = {
                    "machine_code": machine_code,
                    "period": f"{year}-{month:02d}",
                    "working_days": working_days,
                    "base_hourly_capacity": float(base_hourly_capacity),
                    "effective_monthly_capacity": float(effective_capacity),
                    "maintenance_impact": float(maintenance_impact),
                    "current_utilization": float(current_load),
                    "available_capacity": float(available_capacity),
                    "capacity_factors": {
                        "efficiency_factor": float(capability.efficiency_factor),
                        "working_time_factor": float(capability.working_time_factor),
                        "availability_score": float(capability.availability_score)
                    },
                    "estimated_max_output": float(available_capacity * Decimal("0.9"))
                }
                
                # 缓存结果
                cache_key = (machine_code, year, month)
                self._capacity_cache[cache_key] = capacity_info
                results[machine_code] = capacity_info
            
            logger.info(f"批量产能计算完成: {len(uncached_machines)} 台新计算, {len(results)} 台总计")
            return results
            
        except Exception as e:
            logger.error(f"批量计算机台产能失败: {e}")
            raise
    
    async def _batch_get_machine_capabilities(
        self, 
        machine_codes: List[str]
    ) -> Dict[str, Optional[MachineCapability]]:
        """批量获取机台能力信息"""
        try:
            results = {}
            uncached_codes = []
            
            # 检查缓存
            for machine_code in machine_codes:
                if machine_code in self._machine_cache:
                    results[machine_code] = self._machine_cache[machine_code]
                    self._performance_stats["cache_hits"] += 1
                else:
                    uncached_codes.append(machine_code)
                    self._performance_stats["cache_misses"] += 1
            
            if not uncached_codes:
                return results
            
            # 批量查询机台基础信息
            stmt = select(Machine).where(
                and_(
                    Machine.machine_code.in_(uncached_codes),
                    Machine.status == 'ACTIVE'
                )
            )
            result = await self.session.execute(stmt)
            machines = {m.machine_code: m for m in result.scalars().all()}
            self._performance_stats["queries_executed"] += 1
            
            # 批量查询机台速度配置
            speed_stmt = select(MachineSpeed).where(
                and_(
                    MachineSpeed.machine_code.in_(uncached_codes),
                    MachineSpeed.status == 'ACTIVE',
                    MachineSpeed.effective_from <= datetime.now(),
                    or_(
                        MachineSpeed.effective_to.is_(None),
                        MachineSpeed.effective_to >= datetime.now()
                    )
                )
            )
            speed_result = await self.session.execute(speed_stmt)
            speeds_by_machine = defaultdict(list)
            for speed in speed_result.scalars().all():
                speeds_by_machine[speed.machine_code].append(speed)
            self._performance_stats["queries_executed"] += 1
            
            # 批量查询机台关系
            relation_stmt = select(MachineRelation).where(
                or_(
                    MachineRelation.feeder_code.in_(uncached_codes),
                    MachineRelation.maker_code.in_(uncached_codes)
                )
            )
            relation_result = await self.session.execute(relation_stmt)
            relations_by_machine = defaultdict(list)
            for relation in relation_result.scalars().all():
                relations_by_machine[relation.feeder_code].append(relation)
                relations_by_machine[relation.maker_code].append(relation)
            self._performance_stats["queries_executed"] += 1
            
            # 批量查询维护计划
            maintenance_stmt = select(MaintenancePlan).where(
                and_(
                    MaintenancePlan.machine_code.in_(uncached_codes),
                    MaintenancePlan.plan_status.in_(['PLANNED', 'IN_PROGRESS']),
                    MaintenancePlan.maint_start_time >= datetime.now() - timedelta(days=30),
                    MaintenancePlan.maint_start_time <= datetime.now() + timedelta(days=60)
                )
            )
            maintenance_result = await self.session.execute(maintenance_stmt)
            maintenances_by_machine = defaultdict(list)
            for maint in maintenance_result.scalars().all():
                maintenances_by_machine[maint.machine_code].append(maint)
            self._performance_stats["queries_executed"] += 1
            
            # 构建机台能力对象
            for machine_code in uncached_codes:
                machine = machines.get(machine_code)
                if not machine:
                    results[machine_code] = None
                    continue
                
                speeds = speeds_by_machine.get(machine_code, [])
                relations = relations_by_machine.get(machine_code, [])
                maintenances = maintenances_by_machine.get(machine_code, [])
                
                # 计算基础产能和支持的物料
                if speeds:
                    avg_speed = sum(speed.speed for speed in speeds) / len(speeds)
                    avg_efficiency = sum(speed.efficiency_rate for speed in speeds) / len(speeds) / 100
                    supported_articles = {speed.article_nr for speed in speeds}
                    setup_time_matrix = {speed.article_nr: Decimal("0.5") for speed in speeds}
                else:
                    avg_speed = Decimal("100")
                    avg_efficiency = Decimal("0.85")
                    supported_articles = set()
                    setup_time_matrix = {}
                
                # 处理机台关系
                related_machines = []
                preferred_relations = []
                
                for relation in relations:
                    if relation.feeder_code == machine_code:
                        related_machines.append(relation.maker_code)
                        if relation.priority <= 2:
                            preferred_relations.append(relation.maker_code)
                    else:
                        related_machines.append(relation.feeder_code)
                        if relation.priority <= 2:
                            preferred_relations.append(relation.feeder_code)
                
                # 维护窗口
                maintenance_windows = [
                    (maint.maint_start_time, maint.maint_end_time) 
                    for maint in maintenances
                ]
                
                # 计算可用性分数
                availability_score = await self._calculate_availability_score(
                    machine_code, maintenance_windows
                )
                
                # 计算当前利用率
                current_utilization = await self._get_current_machine_load(
                    machine_code, datetime.now().year, datetime.now().month
                )
                
                # 构建机台能力对象
                machine_type = MachineType.FEEDER if machine.machine_type == 'FEEDING' else MachineType.MAKER
                
                capability = MachineCapability(
                    machine_code=machine_code,
                    machine_type=machine_type,
                    machine_name=machine.machine_name,
                    equipment_type=machine.equipment_type or "Unknown",
                    production_line=machine.production_line or "Main",
                    base_capacity_per_hour=Decimal(str(avg_speed)),
                    efficiency_factor=Decimal(str(avg_efficiency)),
                    current_utilization=current_utilization,
                    supported_articles=supported_articles,
                    preferred_articles=supported_articles,
                    setup_time_matrix=setup_time_matrix,
                    is_available=machine.status == 'ACTIVE',
                    availability_score=availability_score,
                    maintenance_windows=maintenance_windows,
                    working_time_factor=Decimal("0.95"),
                    related_machines=related_machines,
                    preferred_relations=preferred_relations
                )
                
                # 缓存结果
                self._machine_cache[machine_code] = capability
                results[machine_code] = capability
            
            logger.info(f"批量获取机台能力完成: {len(uncached_codes)} 台新查询")
            return results
            
        except Exception as e:
            logger.error(f"批量获取机台能力失败: {e}")
            # 返回部分结果
            return {code: None for code in machine_codes}
    
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        处理算法请求 - 实现 AlgorithmBase 接口
        
        Args:
            input_data: 输入数据列表
            **kwargs: 额外参数
            
        Returns:
            算法执行结果
        """
        result = self.create_result()
        
        try:
            if not input_data:
                raise ValueError("输入数据不能为空")
            
            # 从输入数据构建选择标准
            first_item = input_data[0]
            criteria = MachineSelectionCriteria(
                article_nr=first_item.get("article_nr", ""),
                target_quantity=Decimal(str(first_item.get("target_quantity", "0"))),
                planned_start=first_item.get("planned_start"),
                planned_end=first_item.get("planned_end"),
                priority=Priority(first_item.get("priority", "MEDIUM")),
                required_machine_types=[
                    MachineType(t) for t in first_item.get("required_machine_types", ["FEEDER", "MAKER"])
                ],
                preferred_machines=first_item.get("preferred_machines", []),
                excluded_machines=first_item.get("excluded_machines", []),
                max_setup_time=Decimal(str(first_item.get("max_setup_time", "0"))) if first_item.get("max_setup_time") else None,
                min_efficiency=Decimal(str(first_item.get("min_efficiency", "0"))) if first_item.get("min_efficiency") else None,
                selection_strategy=MachineSelectionStrategy(first_item.get("selection_strategy", "balance_optimal")),
                objective=SelectionObjective(first_item.get("objective", "maximize_throughput"))
            )
            
            # 执行机台选择
            selection_result = await self.select_optimal_machines(criteria)
            
            # 构建输出数据
            result.output_data = [selection_result.to_dict()]
            result.success = True
            result.metrics.processed_records = 1
            result.custom_data = {
                "selection_id": selection_result.selection_id,
                "constraints_satisfied": selection_result.constraints_satisfied
            }
            
        except Exception as e:
            result.success = False
            result.add_error(f"机台选择处理失败: {str(e)}")
            result.metrics.error_records = 1
            logger.error(f"处理失败: {e}")
        
        return self.finalize_result(result)
    
    async def select_optimal_machines(
        self, 
        criteria: MachineSelectionCriteria
    ) -> MachineSelectionResult:
        """
        选择最优机台组合
        
        Args:
            criteria: 选择标准
            
        Returns:
            机台选择结果
        """
        try:
            logger.info(f"开始机台选择: 物料={criteria.article_nr}, 策略={criteria.selection_strategy.value}")
            
            # 1. 获取候选机台
            candidate_machines = await self._get_candidate_machines(criteria)
            logger.info(f"找到 {len(candidate_machines)} 个候选机台")
            
            # 2. 计算机台产能
            await self._calculate_machine_capacities(candidate_machines, criteria)
            
            # 3. 评估机台适配性
            await self._evaluate_machine_compatibility(candidate_machines, criteria)
            
            # 4. 应用选择策略
            selected_machines = await self._apply_selection_strategy(candidate_machines, criteria)
            
            # 5. 生成选择结果
            result = await self._generate_selection_result(selected_machines, criteria)
            
            logger.info(f"机台选择完成: 主选机台={result.selected_feeder or 'N/A'}/{result.selected_maker or 'N/A'}")
            return result
            
        except Exception as e:
            logger.error(f"机台选择失败: {e}")
            raise
    
    async def allocate_feeder_maker_pairs(
        self, 
        production_requirements: List[ProductionRequirement],
        target_month: Tuple[int, int] = None
    ) -> Dict[str, Any]:
        """
        分配喂丝机-卷包机配对组合
        
        实现智能的喂丝机和卷包机配对逻辑，考虑容量匹配、关系优先级、
        负载均衡和生产效率等因素。
        
        Args:
            production_requirements: 生产需求列表
            target_month: 目标月份 (年, 月)，默认为当前月份
            
        Returns:
            配对分配结果，包含配对方案、负载分析和优化建议
        """
        try:
            if target_month is None:
                now = datetime.now()
                target_month = (now.year, now.month)
            
            year, month = target_month
            logger.info(f"开始喂丝机-卷包机配对分配: {year}-{month:02d}, {len(production_requirements)} 个需求")
            
            # 1. 获取可用的喂丝机和卷包机
            feeders = await self.get_available_machines(machine_type=MachineType.FEEDER)
            makers = await self.get_available_machines(machine_type=MachineType.MAKER)
            
            logger.info(f"可用机台: {len(feeders)} 个喂丝机, {len(makers)} 个卷包机")
            
            # 2. 获取机台关系矩阵
            relationship_matrix = await self._build_machine_relationship_matrix(feeders, makers)
            
            # 3. 计算各机台的月度产能
            feeder_capacities = {}
            maker_capacities = {}
            
            for feeder in feeders:
                capacity_info = await self.calculate_machine_capacity(
                    feeder["machine_code"], year, month
                )
                feeder_capacities[feeder["machine_code"]] = capacity_info
            
            for maker in makers:
                capacity_info = await self.calculate_machine_capacity(
                    maker["machine_code"], year, month
                )
                maker_capacities[maker["machine_code"]] = capacity_info
            
            # 4. 按优先级排序需求
            sorted_requirements = sorted(
                production_requirements,
                key=lambda x: (x.priority, -float(x.target_quantity))
            )
            
            # 5. 执行配对分配算法
            allocation_result = await self._execute_pairing_algorithm(
                sorted_requirements,
                feeders,
                makers,
                feeder_capacities,
                maker_capacities,
                relationship_matrix
            )
            
            # 6. 生成负载分析
            load_analysis = await self._analyze_machine_loads(
                allocation_result["pairs"],
                feeder_capacities,
                maker_capacities
            )
            
            # 7. 生成优化建议
            optimization_suggestions = await self._generate_pairing_optimization_suggestions(
                allocation_result,
                load_analysis
            )
            
            result = {
                "allocation_period": f"{year}-{month:02d}",
                "total_requirements": len(production_requirements),
                "total_feeders": len(feeders),
                "total_makers": len(makers),
                "successful_pairs": len(allocation_result["pairs"]),
                "unallocated_requirements": len(allocation_result["unallocated"]),
                
                # 配对结果
                "feeder_maker_pairs": allocation_result["pairs"],
                "unallocated_requirements": allocation_result["unallocated"],
                "backup_pairs": allocation_result.get("backup_pairs", []),
                
                # 负载分析
                "load_analysis": load_analysis,
                
                # 优化建议
                "optimization_suggestions": optimization_suggestions,
                
                # 绩效指标
                "performance_metrics": {
                    "allocation_success_rate": (
                        len(allocation_result["pairs"]) / len(production_requirements) * 100
                        if production_requirements else 0
                    ),
                    "average_capacity_utilization": load_analysis.get("average_utilization", 0),
                    "bottleneck_machines": load_analysis.get("bottlenecks", []),
                    "idle_machines": load_analysis.get("idle_machines", [])
                }
            }
            
            logger.info(f"配对分配完成: {len(allocation_result['pairs'])} 个成功配对")
            return result
            
        except Exception as e:
            logger.error(f"配对分配失败: {e}")
            raise
    
    async def check_machine_constraints(
        self,
        machine_code: str,
        article_nr: str,
        target_quantity: Decimal,
        time_window: Tuple[datetime, datetime],
        constraint_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        检查机台约束条件
        
        全面检查机台在指定时间窗口内对特定物料和数量的约束满足情况，
        包括产能约束、维护约束、适配性约束等。
        
        Args:
            machine_code: 机台代码
            article_nr: 物料编号
            target_quantity: 目标产量
            time_window: 时间窗口 (开始时间, 结束时间)
            constraint_types: 要检查的约束类型列表，默认检查所有约束
            
        Returns:
            约束检查结果，包含约束满足情况、违反详情和建议
        """
        try:
            start_time, end_time = time_window
            logger.info(f"检查机台约束: {machine_code}, 物料={article_nr}, "
                       f"数量={target_quantity}, 时间={start_time} 至 {end_time}")
            
            # 默认检查所有约束类型
            if constraint_types is None:
                constraint_types = [
                    "capacity", "maintenance", "compatibility", 
                    "availability", "efficiency", "setup_time",
                    "working_calendar", "load_balance"
                ]
            
            # 初始化检查结果
            constraint_results = {
                "machine_code": machine_code,
                "article_nr": article_nr,
                "target_quantity": float(target_quantity),
                "time_window": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_hours": (end_time - start_time).total_seconds() / 3600
                },
                "overall_satisfaction": True,
                "constraint_checks": {},
                "violations": [],
                "warnings": [],
                "recommendations": []
            }
            
            # 获取机台能力信息
            machine_capability = await self._get_machine_capability(machine_code)
            if not machine_capability:
                constraint_results["overall_satisfaction"] = False
                constraint_results["violations"].append({
                    "type": "machine_not_found",
                    "severity": "error",
                    "message": f"未找到机台: {machine_code}"
                })
                return constraint_results
            
            # 1. 产能约束检查
            if "capacity" in constraint_types:
                capacity_check = await self._check_capacity_constraint(
                    machine_capability, article_nr, target_quantity, time_window
                )
                constraint_results["constraint_checks"]["capacity"] = capacity_check
                if not capacity_check["satisfied"]:
                    constraint_results["overall_satisfaction"] = False
                    constraint_results["violations"].append({
                        "type": "capacity_insufficient",
                        "severity": "error",
                        "message": capacity_check["message"],
                        "details": capacity_check
                    })
            
            # 2. 维护计划约束检查
            if "maintenance" in constraint_types:
                maintenance_check = await self._check_maintenance_constraint(
                    machine_code, time_window
                )
                constraint_results["constraint_checks"]["maintenance"] = maintenance_check
                if not maintenance_check["satisfied"]:
                    if maintenance_check["severity"] == "error":
                        constraint_results["overall_satisfaction"] = False
                        constraint_results["violations"].append({
                            "type": "maintenance_conflict",
                            "severity": "error",
                            "message": maintenance_check["message"],
                            "details": maintenance_check
                        })
                    else:
                        constraint_results["warnings"].append({
                            "type": "maintenance_impact",
                            "severity": "warning",
                            "message": maintenance_check["message"],
                            "details": maintenance_check
                        })
            
            # 3. 适配性约束检查
            if "compatibility" in constraint_types:
                compatibility_check = await self._check_compatibility_constraint(
                    machine_capability, article_nr
                )
                constraint_results["constraint_checks"]["compatibility"] = compatibility_check
                if not compatibility_check["satisfied"]:
                    constraint_results["overall_satisfaction"] = False
                    constraint_results["violations"].append({
                        "type": "article_incompatible",
                        "severity": "error",
                        "message": compatibility_check["message"],
                        "details": compatibility_check
                    })
            
            # 4. 可用性约束检查
            if "availability" in constraint_types:
                availability_check = await self._check_availability_constraint(
                    machine_capability, time_window
                )
                constraint_results["constraint_checks"]["availability"] = availability_check
                if not availability_check["satisfied"]:
                    constraint_results["overall_satisfaction"] = False
                    constraint_results["violations"].append({
                        "type": "machine_unavailable",
                        "severity": "error", 
                        "message": availability_check["message"],
                        "details": availability_check
                    })
            
            # 5. 效率约束检查
            if "efficiency" in constraint_types:
                efficiency_check = await self._check_efficiency_constraint(
                    machine_capability, article_nr, target_quantity
                )
                constraint_results["constraint_checks"]["efficiency"] = efficiency_check
                if not efficiency_check["satisfied"]:
                    constraint_results["warnings"].append({
                        "type": "low_efficiency",
                        "severity": "warning",
                        "message": efficiency_check["message"],
                        "details": efficiency_check
                    })
            
            # 6. 换产时间约束检查
            if "setup_time" in constraint_types:
                setup_check = await self._check_setup_time_constraint(
                    machine_capability, article_nr, time_window
                )
                constraint_results["constraint_checks"]["setup_time"] = setup_check
                if not setup_check["satisfied"]:
                    constraint_results["warnings"].append({
                        "type": "long_setup_time",
                        "severity": "warning",
                        "message": setup_check["message"],
                        "details": setup_check
                    })
            
            # 7. 工作日历约束检查
            if "working_calendar" in constraint_types:
                calendar_check = await self._check_working_calendar_constraint(time_window)
                constraint_results["constraint_checks"]["working_calendar"] = calendar_check
                if not calendar_check["satisfied"]:
                    constraint_results["warnings"].append({
                        "type": "non_working_period",
                        "severity": "warning",
                        "message": calendar_check["message"],
                        "details": calendar_check
                    })
            
            # 8. 负载均衡约束检查
            if "load_balance" in constraint_types:
                load_check = await self._check_load_balance_constraint(
                    machine_code, target_quantity, time_window
                )
                constraint_results["constraint_checks"]["load_balance"] = load_check
                if not load_check["satisfied"]:
                    constraint_results["warnings"].append({
                        "type": "high_load",
                        "severity": "warning", 
                        "message": load_check["message"],
                        "details": load_check
                    })
            
            # 生成建议
            constraint_results["recommendations"] = await self._generate_constraint_recommendations(
                constraint_results, machine_capability, article_nr, target_quantity, time_window
            )
            
            # 计算约束满足率
            total_checks = len(constraint_results["constraint_checks"])
            satisfied_checks = sum(
                1 for check in constraint_results["constraint_checks"].values()
                if check["satisfied"]
            )
            constraint_results["satisfaction_rate"] = (
                satisfied_checks / total_checks * 100 if total_checks > 0 else 0
            )
            
            logger.info(f"约束检查完成: {machine_code}, 满足率={constraint_results['satisfaction_rate']:.1f}%")
            return constraint_results
            
        except Exception as e:
            logger.error(f"约束检查失败: {e}")
            raise
    
    async def calculate_machine_capacity(
        self, 
        machine_code: str, 
        year: int, 
        month: int,
        article_nr: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算机台月度产能
        
        Args:
            machine_code: 机台代码
            year: 年份
            month: 月份
            article_nr: 可选的物料编号（用于精确产能计算）
            
        Returns:
            产能计算结果
        """
        try:
            logger.info(f"计算机台产能: {machine_code} {year}-{month:02d}")
            
            # 获取机台信息
            machine_capability = await self._get_machine_capability(machine_code)
            if not machine_capability:
                raise ValueError(f"未找到机台: {machine_code}")
            
            # 获取工作日历
            if self.calendar_service:
                calendar_days, month_capacity = await self.calendar_service.get_month_calendar(year, month)
                working_days = len([day for day in calendar_days if day.is_working])
                total_capacity_factor = month_capacity.total_capacity_factor
            else:
                # 默认工作日计算
                from calendar import monthrange
                _, days_in_month = monthrange(year, month)
                working_days = days_in_month * 5 // 7  # 简化计算
                total_capacity_factor = Decimal(str(working_days))
            
            # 计算基础产能
            base_hourly_capacity = machine_capability.base_capacity_per_hour
            if article_nr:
                # 获取特定物料的速度配置
                speed_factor = await self._get_machine_speed_factor(machine_code, article_nr)
                base_hourly_capacity *= speed_factor
            
            # 计算月度产能
            effective_capacity = machine_capability.calculate_effective_capacity(
                working_days, 
                self.config.default_working_hours_per_day
            )
            
            # 维护计划影响
            maintenance_impact = await self._calculate_maintenance_impact(
                machine_code, year, month
            )
            
            effective_capacity *= (Decimal("1.0") - maintenance_impact)
            
            # 当前利用率影响
            current_load = await self._get_current_machine_load(machine_code, year, month)
            available_capacity = effective_capacity * (Decimal("1.0") - current_load)
            
            return {
                "machine_code": machine_code,
                "period": f"{year}-{month:02d}",
                "working_days": working_days,
                "base_hourly_capacity": float(base_hourly_capacity),
                "effective_monthly_capacity": float(effective_capacity),
                "maintenance_impact": float(maintenance_impact),
                "current_utilization": float(current_load),
                "available_capacity": float(available_capacity),
                "capacity_factors": {
                    "efficiency_factor": float(machine_capability.efficiency_factor),
                    "working_time_factor": float(machine_capability.working_time_factor),
                    "availability_score": float(machine_capability.availability_score)
                },
                "estimated_max_output": float(available_capacity * Decimal("0.9"))  # 90%容量作为安全边际
            }
            
        except Exception as e:
            logger.error(f"计算机台产能失败: {e}")
            raise
    
    async def get_available_machines(
        self, 
        machine_type: Optional[MachineType] = None,
        article_nr: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可用机台列表
        
        Args:
            machine_type: 机台类型过滤
            article_nr: 物料编号过滤（检查适配性）
            time_range: 时间范围过滤（检查维护计划）
            
        Returns:
            可用机台信息列表
        """
        try:
            logger.info(f"查询可用机台: 类型={machine_type}, 物料={article_nr}")
            
            # 构建查询条件
            conditions = [Machine.status == 'ACTIVE']
            
            if machine_type:
                if machine_type == MachineType.FEEDER:
                    conditions.append(Machine.machine_type == 'FEEDING')
                elif machine_type == MachineType.MAKER:
                    conditions.append(Machine.machine_type == 'PACKING')
            
            # 查询机台基础信息
            stmt = select(Machine).where(and_(*conditions)).order_by(Machine.machine_code)
            result = await self.session.execute(stmt)
            machines = result.scalars().all()
            
            available_machines = []
            
            for machine in machines:
                try:
                    # 获取机台详细能力信息
                    capability = await self._get_machine_capability(machine.machine_code)
                    if not capability or not capability.is_available:
                        continue
                    
                    # 物料适配性检查
                    if article_nr and article_nr not in capability.supported_articles:
                        continue
                    
                    # 时间可用性检查
                    if time_range and not await self._is_machine_available_in_timerange(
                        machine.machine_code, time_range[0], time_range[1]
                    ):
                        continue
                    
                    machine_info = {
                        "machine_code": machine.machine_code,
                        "machine_name": machine.machine_name,
                        "machine_type": machine.machine_type,
                        "equipment_type": machine.equipment_type,
                        "production_line": machine.production_line,
                        "capability": {
                            "base_capacity": float(capability.base_capacity_per_hour),
                            "efficiency_factor": float(capability.efficiency_factor),
                            "availability_score": float(capability.availability_score),
                            "current_utilization": float(capability.current_utilization)
                        },
                        "compatibility": {
                            "supported_articles_count": len(capability.supported_articles),
                            "is_compatible": article_nr in capability.supported_articles if article_nr else True,
                            "setup_time": float(capability.setup_time_matrix.get(article_nr, Decimal("0"))) if article_nr else 0
                        },
                        "relationships": {
                            "related_machines": capability.related_machines,
                            "preferred_relations": capability.preferred_relations
                        }
                    }
                    
                    available_machines.append(machine_info)
                    
                except Exception as e:
                    logger.warning(f"处理机台 {machine.machine_code} 时出错: {e}")
                    continue
            
            logger.info(f"找到 {len(available_machines)} 个可用机台")
            return available_machines
            
        except Exception as e:
            logger.error(f"获取可用机台失败: {e}")
            raise
    
    async def _get_candidate_machines(self, criteria: MachineSelectionCriteria) -> List[MachineCapability]:
        """获取候选机台"""
        try:
            candidates = []
            
            # 根据需要的机台类型查询
            for machine_type in criteria.required_machine_types:
                db_machine_type = 'FEEDING' if machine_type == MachineType.FEEDER else 'PACKING'
                
                stmt = select(Machine).where(
                    and_(
                        Machine.machine_type == db_machine_type,
                        Machine.status == 'ACTIVE'
                    )
                ).limit(self.config.max_selection_candidates)
                
                result = await self.session.execute(stmt)
                machines = result.scalars().all()
                
                for machine in machines:
                    # 排除指定的机台
                    if machine.machine_code in criteria.excluded_machines:
                        continue
                    
                    capability = await self._get_machine_capability(machine.machine_code)
                    if capability and capability.is_available:
                        # 基础适配性检查
                        if criteria.article_nr in capability.supported_articles:
                            candidates.append(capability)
            
            return candidates
            
        except Exception as e:
            logger.error(f"获取候选机台失败: {e}")
            raise
    
    async def _get_machine_capability(self, machine_code: str) -> Optional[MachineCapability]:
        """获取机台能力信息"""
        try:
            # 检查缓存
            if machine_code in self._machine_cache:
                return self._machine_cache[machine_code]
            
            # 查询机台基础信息
            stmt = select(Machine).where(Machine.machine_code == machine_code)
            result = await self.session.execute(stmt)
            machine = result.scalars().first()
            
            if not machine:
                return None
            
            # 查询机台速度配置
            speed_stmt = select(MachineSpeed).where(
                and_(
                    MachineSpeed.machine_code == machine_code,
                    MachineSpeed.status == 'ACTIVE',
                    MachineSpeed.effective_from <= datetime.now(),
                    or_(
                        MachineSpeed.effective_to.is_(None),
                        MachineSpeed.effective_to >= datetime.now()
                    )
                )
            )
            speed_result = await self.session.execute(speed_stmt)
            speeds = speed_result.scalars().all()
            
            # 计算基础产能和支持的物料
            if speeds:
                avg_speed = sum(speed.speed for speed in speeds) / len(speeds)
                avg_efficiency = sum(speed.efficiency_rate for speed in speeds) / len(speeds) / 100
                supported_articles = {speed.article_nr for speed in speeds}
                setup_time_matrix = {speed.article_nr: Decimal("0.5") for speed in speeds}  # 默认换产时间
            else:
                avg_speed = Decimal("100")  # 默认产能
                avg_efficiency = Decimal("0.85")  # 默认效率
                supported_articles = set()
                setup_time_matrix = {}
            
            # 查询机台关系
            relation_stmt = select(MachineRelation).where(
                or_(
                    MachineRelation.feeder_code == machine_code,
                    MachineRelation.maker_code == machine_code
                )
            )
            relation_result = await self.session.execute(relation_stmt)
            relations = relation_result.scalars().all()
            
            related_machines = []
            preferred_relations = []
            
            for relation in relations:
                if relation.feeder_code == machine_code:
                    related_machines.append(relation.maker_code)
                    if relation.priority <= 2:  # 高优先级关系
                        preferred_relations.append(relation.maker_code)
                else:
                    related_machines.append(relation.feeder_code)
                    if relation.priority <= 2:
                        preferred_relations.append(relation.feeder_code)
            
            # 查询维护计划
            maintenance_stmt = select(MaintenancePlan).where(
                and_(
                    MaintenancePlan.machine_code == machine_code,
                    MaintenancePlan.plan_status.in_(['PLANNED', 'IN_PROGRESS']),
                    MaintenancePlan.maint_start_time >= datetime.now() - timedelta(days=30),
                    MaintenancePlan.maint_start_time <= datetime.now() + timedelta(days=60)
                )
            )
            maintenance_result = await self.session.execute(maintenance_stmt)
            maintenances = maintenance_result.scalars().all()
            
            maintenance_windows = [
                (maint.maint_start_time, maint.maint_end_time) 
                for maint in maintenances
            ]
            
            # 计算可用性分数
            availability_score = await self._calculate_availability_score(
                machine_code, maintenance_windows
            )
            
            # 计算当前利用率
            current_utilization = await self._get_current_machine_load(
                machine_code, datetime.now().year, datetime.now().month
            )
            
            # 构建机台能力对象
            machine_type = MachineType.FEEDER if machine.machine_type == 'FEEDING' else MachineType.MAKER
            
            capability = MachineCapability(
                machine_code=machine_code,
                machine_type=machine_type,
                machine_name=machine.machine_name,
                equipment_type=machine.equipment_type or "Unknown",
                production_line=machine.production_line or "Main",
                base_capacity_per_hour=Decimal(str(avg_speed)),
                efficiency_factor=Decimal(str(avg_efficiency)),
                current_utilization=current_utilization,
                supported_articles=supported_articles,
                preferred_articles=supported_articles,  # 简化处理
                setup_time_matrix=setup_time_matrix,
                is_available=machine.status == 'ACTIVE',
                availability_score=availability_score,
                maintenance_windows=maintenance_windows,
                working_time_factor=Decimal("0.95"),  # 默认95%工作时间因子
                related_machines=related_machines,
                preferred_relations=preferred_relations
            )
            
            # 缓存结果
            self._machine_cache[machine_code] = capability
            
            return capability
            
        except Exception as e:
            logger.error(f"获取机台能力失败: {e}")
            return None
    
    async def _get_machine_speed_factor(self, machine_code: str, article_nr: str) -> Decimal:
        """获取机台对特定物料的速度因子"""
        try:
            cache_key = (machine_code, article_nr)
            if cache_key in self._speed_cache:
                return self._speed_cache[cache_key]
            
            stmt = select(MachineSpeed).where(
                and_(
                    MachineSpeed.machine_code == machine_code,
                    MachineSpeed.article_nr == article_nr,
                    MachineSpeed.status == 'ACTIVE',
                    MachineSpeed.effective_from <= datetime.now(),
                    or_(
                        MachineSpeed.effective_to.is_(None),
                        MachineSpeed.effective_to >= datetime.now()
                    )
                )
            ).order_by(MachineSpeed.effective_from.desc())
            
            result = await self.session.execute(stmt)
            speed_config = result.scalars().first()
            
            if speed_config:
                factor = Decimal(str(speed_config.efficiency_rate)) / 100
            else:
                factor = Decimal("0.85")  # 默认效率因子
            
            self._speed_cache[cache_key] = factor
            return factor
            
        except Exception as e:
            logger.error(f"获取速度因子失败: {e}")
            return Decimal("0.85")
    
    async def _calculate_availability_score(
        self, 
        machine_code: str, 
        maintenance_windows: List[Tuple[datetime, datetime]]
    ) -> Decimal:
        """计算机台可用性分数"""
        try:
            # 基础可用性分数
            base_score = Decimal("1.0")
            
            # 维护计划影响
            total_maintenance_hours = Decimal("0")
            now = datetime.now()
            next_month = now + timedelta(days=30)
            
            for start_time, end_time in maintenance_windows:
                if start_time <= next_month and end_time >= now:
                    # 计算影响时间
                    overlap_start = max(start_time, now)
                    overlap_end = min(end_time, next_month)
                    if overlap_start < overlap_end:
                        hours = (overlap_end - overlap_start).total_seconds() / 3600
                        total_maintenance_hours += Decimal(str(hours))
            
            # 假设每月720小时工作时间（30天 * 24小时）
            total_hours = Decimal("720")
            if total_maintenance_hours > 0:
                maintenance_impact = total_maintenance_hours / total_hours
                base_score = max(Decimal("0.1"), base_score - maintenance_impact)
            
            return base_score
            
        except Exception as e:
            logger.error(f"计算可用性分数失败: {e}")
            return Decimal("0.8")  # 默认可用性
    
    async def _get_current_machine_load(self, machine_code: str, year: int, month: int) -> Decimal:
        """获取机台当前负载"""
        try:
            # 查询月度计划中该机台的使用情况
            stmt = select(MonthlyPlan).where(
                and_(
                    MonthlyPlan.monthly_plan_year == year,
                    MonthlyPlan.monthly_plan_month == month,
                    MonthlyPlan.monthly_validation_status == 'VALID',
                    or_(
                        MonthlyPlan.monthly_feeder_codes.like(f"%{machine_code}%"),
                        MonthlyPlan.monthly_maker_codes.like(f"%{machine_code}%")
                    )
                )
            )
            
            result = await self.session.execute(stmt)
            plans = result.scalars().all()
            
            total_planned_quantity = sum(
                plan.monthly_target_quantity or Decimal("0") 
                for plan in plans
            )
            
            # 获取机台理论月产能
            capability = await self._get_machine_capability(machine_code)
            if not capability:
                return Decimal("0")
            
            # 计算工作日数
            if self.calendar_service:
                _, month_capacity = await self.calendar_service.get_month_calendar(year, month)
                working_days = month_capacity.total_working_days
            else:
                from calendar import monthrange
                _, days_in_month = monthrange(year, month)
                working_days = days_in_month * 5 // 7
            
            theoretical_capacity = capability.calculate_effective_capacity(
                working_days, self.config.default_working_hours_per_day
            )
            
            if theoretical_capacity > 0:
                load_ratio = total_planned_quantity / (theoretical_capacity / 1000)  # 转换为万支
                return min(Decimal("0.95"), load_ratio)  # 最大95%负载
            
            return Decimal("0")
            
        except Exception as e:
            logger.error(f"获取机台负载失败: {e}")
            return Decimal("0")
    
    async def _calculate_maintenance_impact(self, machine_code: str, year: int, month: int) -> Decimal:
        """计算维护计划对产能的影响"""
        try:
            # 获取指定月份的维护计划
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            stmt = select(MaintenancePlan).where(
                and_(
                    MaintenancePlan.machine_code == machine_code,
                    MaintenancePlan.plan_status.in_(['PLANNED', 'IN_PROGRESS']),
                    MaintenancePlan.maint_start_time >= start_date,
                    MaintenancePlan.maint_start_time <= end_date
                )
            )
            
            result = await self.session.execute(stmt)
            maintenances = result.scalars().all()
            
            total_maintenance_hours = Decimal("0")
            for maintenance in maintenances:
                if maintenance.estimated_duration:
                    hours = Decimal(str(maintenance.estimated_duration)) / 60  # 分钟转小时
                else:
                    # 基于开始和结束时间计算
                    duration = maintenance.maint_end_time - maintenance.maint_start_time
                    hours = Decimal(str(duration.total_seconds())) / 3600
                
                total_maintenance_hours += hours
            
            # 计算影响百分比（假设每月工作480小时，即30天*16小时）
            monthly_working_hours = Decimal(str(30 * 16))
            if total_maintenance_hours > 0:
                impact = total_maintenance_hours / monthly_working_hours
                return min(Decimal("0.5"), impact)  # 最大50%影响
            
            return Decimal("0")
            
        except Exception as e:
            logger.error(f"计算维护影响失败: {e}")
            return Decimal("0")
    
    async def _is_machine_available_in_timerange(
        self, 
        machine_code: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> bool:
        """检查机台在指定时间范围内是否可用"""
        try:
            # 查询时间范围内的维护计划
            stmt = select(MaintenancePlan).where(
                and_(
                    MaintenancePlan.machine_code == machine_code,
                    MaintenancePlan.plan_status.in_(['PLANNED', 'IN_PROGRESS']),
                    or_(
                        and_(
                            MaintenancePlan.maint_start_time >= start_time,
                            MaintenancePlan.maint_start_time <= end_time
                        ),
                        and_(
                            MaintenancePlan.maint_end_time >= start_time,
                            MaintenancePlan.maint_end_time <= end_time
                        ),
                        and_(
                            MaintenancePlan.maint_start_time <= start_time,
                            MaintenancePlan.maint_end_time >= end_time
                        )
                    )
                )
            )
            
            result = await self.session.execute(stmt)
            conflicts = result.scalars().all()
            
            # 如果有冲突的维护计划，则不可用
            return len(conflicts) == 0
            
        except Exception as e:
            logger.error(f"检查机台时间可用性失败: {e}")
            return False
    
    async def _calculate_machine_capacities(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> None:
        """计算候选机台产能"""
        try:
            for candidate in candidates:
                # 获取特定物料的速度因子
                speed_factor = await self._get_machine_speed_factor(
                    candidate.machine_code, criteria.article_nr
                )
                
                # 更新产能计算
                candidate.base_capacity_per_hour *= speed_factor
                
                # 计算换产时间影响
                setup_time = candidate.setup_time_matrix.get(criteria.article_nr, Decimal("0"))
                if setup_time > 0:
                    setup_penalty = min(
                        self.config.setup_time_penalty,
                        setup_time / self.config.default_working_hours_per_day
                    )
                    candidate.efficiency_factor *= (Decimal("1.0") - setup_penalty)
                
        except Exception as e:
            logger.error(f"计算机台产能失败: {e}")
            raise
    
    async def _evaluate_machine_compatibility(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> None:
        """评估机台适配性"""
        try:
            for candidate in candidates:
                # 检查效率要求
                if (criteria.min_efficiency and 
                    candidate.efficiency_factor < criteria.min_efficiency):
                    candidate.availability_score *= Decimal("0.5")  # 降低分数
                
                # 检查优先机台
                if criteria.preferred_machines and candidate.machine_code in criteria.preferred_machines:
                    candidate.availability_score *= Decimal("1.2")  # 提升分数
                
                # 检查换产时间限制
                setup_time = candidate.setup_time_matrix.get(criteria.article_nr, Decimal("0"))
                if (criteria.max_setup_time and 
                    setup_time > criteria.max_setup_time):
                    candidate.availability_score *= Decimal("0.3")  # 严重降低分数
                
        except Exception as e:
            logger.error(f"评估机台适配性失败: {e}")
            raise
    
    async def _apply_selection_strategy(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> Dict[str, List[MachineCapability]]:
        """应用选择策略"""
        try:
            strategy = criteria.selection_strategy
            
            if strategy == MachineSelectionStrategy.CAPACITY_OPTIMAL:
                return await self._capacity_optimal_selection(candidates, criteria)
            elif strategy == MachineSelectionStrategy.EFFICIENCY_OPTIMAL:
                return await self._efficiency_optimal_selection(candidates, criteria)
            elif strategy == MachineSelectionStrategy.BALANCE_OPTIMAL:
                return await self._balance_optimal_selection(candidates, criteria)
            elif strategy == MachineSelectionStrategy.MAINTENANCE_AWARE:
                return await self._maintenance_aware_selection(candidates, criteria)
            else:
                # 默认使用平衡策略
                return await self._balance_optimal_selection(candidates, criteria)
                
        except Exception as e:
            logger.error(f"应用选择策略失败: {e}")
            raise
    
    async def _capacity_optimal_selection(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> Dict[str, List[MachineCapability]]:
        """产能最优选择策略"""
        feeders = [c for c in candidates if c.machine_type == MachineType.FEEDER]
        makers = [c for c in candidates if c.machine_type == MachineType.MAKER]
        
        # 按产能排序
        feeders.sort(key=lambda x: x.base_capacity_per_hour * x.efficiency_factor, reverse=True)
        makers.sort(key=lambda x: x.base_capacity_per_hour * x.efficiency_factor, reverse=True)
        
        return {"feeders": feeders, "makers": makers}
    
    async def _efficiency_optimal_selection(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> Dict[str, List[MachineCapability]]:
        """效率最优选择策略"""
        feeders = [c for c in candidates if c.machine_type == MachineType.FEEDER]
        makers = [c for c in candidates if c.machine_type == MachineType.MAKER]
        
        # 按效率排序
        feeders.sort(key=lambda x: x.efficiency_factor * x.availability_score, reverse=True)
        makers.sort(key=lambda x: x.efficiency_factor * x.availability_score, reverse=True)
        
        return {"feeders": feeders, "makers": makers}
    
    async def _balance_optimal_selection(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> Dict[str, List[MachineCapability]]:
        """平衡最优选择策略"""
        feeders = [c for c in candidates if c.machine_type == MachineType.FEEDER]
        makers = [c for c in candidates if c.machine_type == MachineType.MAKER]
        
        # 计算综合评分
        def calculate_score(machine: MachineCapability) -> Decimal:
            capacity_score = machine.base_capacity_per_hour / 1000  # 标准化
            efficiency_score = machine.efficiency_factor
            availability_score = machine.availability_score
            utilization_score = Decimal("1.0") - machine.current_utilization
            
            return (
                capacity_score * self.config.capacity_weight +
                efficiency_score * self.config.efficiency_weight +
                availability_score * self.config.availability_weight +
                utilization_score * Decimal("0.1")
            )
        
        feeders.sort(key=calculate_score, reverse=True)
        makers.sort(key=calculate_score, reverse=True)
        
        return {"feeders": feeders, "makers": makers}
    
    async def _maintenance_aware_selection(
        self, 
        candidates: List[MachineCapability], 
        criteria: MachineSelectionCriteria
    ) -> Dict[str, List[MachineCapability]]:
        """维护感知选择策略"""
        feeders = [c for c in candidates if c.machine_type == MachineType.FEEDER]
        makers = [c for c in candidates if c.machine_type == MachineType.MAKER]
        
        # 优先选择维护窗口较少的机台
        def maintenance_score(machine: MachineCapability) -> Decimal:
            maintenance_penalty = Decimal(str(len(machine.maintenance_windows))) * Decimal("0.1")
            base_score = machine.efficiency_factor * machine.availability_score
            return base_score - maintenance_penalty
        
        feeders.sort(key=maintenance_score, reverse=True)
        makers.sort(key=maintenance_score, reverse=True)
        
        return {"feeders": feeders, "makers": makers}
    
    async def _generate_selection_result(
        self, 
        selected_machines: Dict[str, List[MachineCapability]], 
        criteria: MachineSelectionCriteria
    ) -> MachineSelectionResult:
        """生成选择结果"""
        try:
            feeders = selected_machines.get("feeders", [])
            makers = selected_machines.get("makers", [])
            
            # 选择主要机台
            selected_feeder = feeders[0].machine_code if feeders else None
            selected_maker = makers[0].machine_code if makers else None
            
            # 选择备用机台
            backup_feeders = [f.machine_code for f in feeders[1:self.config.backup_machines_count + 1]]
            backup_makers = [m.machine_code for m in makers[1:self.config.backup_machines_count + 1]]
            
            # 计算性能指标
            total_capacity = Decimal("0")
            if feeders and makers:
                feeder_capacity = feeders[0].calculate_effective_capacity(22)  # 假设22个工作日
                maker_capacity = makers[0].calculate_effective_capacity(22)
                total_capacity = min(feeder_capacity, maker_capacity)  # 取瓶颈产能
            
            # 计算完成时间
            estimated_completion_time = None
            if (total_capacity > 0 and criteria.target_quantity > 0 and 
                criteria.planned_start):
                days_needed = float(criteria.target_quantity) / float(total_capacity / 22)
                estimated_completion_time = criteria.planned_start + timedelta(days=days_needed)
            
            # 计算效率分数
            efficiency_score = Decimal("0")
            if feeders and makers:
                efficiency_score = (feeders[0].efficiency_factor + makers[0].efficiency_factor) / 2
            
            # 计算利用率影响
            utilization_impact = {}
            if selected_feeder:
                utilization_impact[selected_feeder] = feeders[0].current_utilization
            if selected_maker:
                utilization_impact[selected_maker] = makers[0].current_utilization
            
            # 约束检查
            constraints_satisfied = True
            constraint_violations = []
            
            if criteria.min_efficiency:
                if efficiency_score < criteria.min_efficiency:
                    constraints_satisfied = False
                    constraint_violations.append(f"效率不满足要求: {efficiency_score} < {criteria.min_efficiency}")
            
            # 生成选择推理
            selection_reasoning = self._generate_selection_reasoning(
                selected_feeder, selected_maker, feeders, makers, criteria
            )
            
            # 容量分析
            capacity_analysis = {
                "feeder_capacity": float(feeders[0].calculate_effective_capacity(22)) if feeders else 0,
                "maker_capacity": float(makers[0].calculate_effective_capacity(22)) if makers else 0,
                "bottleneck": "feeder" if feeders and makers and feeders[0].calculate_effective_capacity(22) < makers[0].calculate_effective_capacity(22) else "maker",
                "capacity_utilization": float(criteria.target_quantity / total_capacity * 100) if total_capacity > 0 else 0
            }
            
            # 风险评估
            risk_assessment = {
                "maintenance_risk": "low" if not (feeders and feeders[0].maintenance_windows) else "medium",
                "capacity_risk": "low" if total_capacity > criteria.target_quantity * Decimal("1.2") else "high",
                "efficiency_risk": "low" if efficiency_score > Decimal("0.8") else "medium"
            }
            
            # 生成选择ID
            selection_id = f"SELECTOR_{criteria.article_nr}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return MachineSelectionResult(
                selection_id=selection_id,
                criteria=criteria,
                selected_feeder=selected_feeder,
                selected_maker=selected_maker,
                backup_feeders=backup_feeders,
                backup_makers=backup_makers,
                total_capacity=total_capacity,
                estimated_completion_time=estimated_completion_time,
                efficiency_score=efficiency_score,
                utilization_impact=utilization_impact,
                constraints_satisfied=constraints_satisfied,
                constraint_violations=constraint_violations,
                selection_reasoning=selection_reasoning,
                capacity_analysis=capacity_analysis,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            logger.error(f"生成选择结果失败: {e}")
            raise
    
    def _generate_selection_reasoning(
        self, 
        selected_feeder: Optional[str],
        selected_maker: Optional[str],
        feeders: List[MachineCapability],
        makers: List[MachineCapability],
        criteria: MachineSelectionCriteria
    ) -> str:
        """生成选择推理说明"""
        reasoning_parts = []
        
        if selected_feeder and feeders:
            feeder = feeders[0]
            reasoning_parts.append(
                f"选择喂丝机 {selected_feeder}: 产能{feeder.base_capacity_per_hour}箱/h, "
                f"效率{feeder.efficiency_factor:.2%}, 可用性{feeder.availability_score:.2%}"
            )
        
        if selected_maker and makers:
            maker = makers[0]
            reasoning_parts.append(
                f"选择卷包机 {selected_maker}: 产能{maker.base_capacity_per_hour}箱/h, "
                f"效率{maker.efficiency_factor:.2%}, 可用性{maker.availability_score:.2%}"
            )
        
        reasoning_parts.append(f"选择策略: {criteria.selection_strategy.value}")
        reasoning_parts.append(f"优化目标: {criteria.objective.value}")
        
        return "; ".join(reasoning_parts)
    
    # 支持方法 - 配对分配算法
    async def _build_machine_relationship_matrix(
        self, 
        feeders: List[Dict[str, Any]], 
        makers: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """构建机台关系矩阵"""
        try:
            matrix = {}
            
            # 查询所有机台关系
            stmt = select(MachineRelation)
            result = await self.session.execute(stmt)
            relations = result.scalars().all()
            
            # 构建关系矩阵
            for feeder in feeders:
                feeder_code = feeder["machine_code"]
                matrix[feeder_code] = {}
                
                for maker in makers:
                    maker_code = maker["machine_code"]
                    
                    # 查找关系记录
                    relation = next(
                        (r for r in relations 
                         if r.feeder_code == feeder_code and r.maker_code == maker_code),
                        None
                    )
                    
                    if relation:
                        # 转换优先级为关系分数 (优先级越低分数越高)
                        score = max(0.0, 1.0 - (relation.priority - 1) * 0.2)
                    else:
                        # 默认关系分数
                        score = 0.3
                    
                    matrix[feeder_code][maker_code] = score
            
            return matrix
            
        except Exception as e:
            logger.error(f"构建机台关系矩阵失败: {e}")
            # 返回默认矩阵
            matrix = {}
            for feeder in feeders:
                matrix[feeder["machine_code"]] = {
                    maker["machine_code"]: 0.5 for maker in makers
                }
            return matrix
    
    async def _execute_pairing_algorithm(
        self,
        requirements: List[ProductionRequirement],
        feeders: List[Dict[str, Any]],
        makers: List[Dict[str, Any]],
        feeder_capacities: Dict[str, Dict[str, Any]],
        maker_capacities: Dict[str, Dict[str, Any]],
        relationship_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """执行配对分配算法"""
        try:
            pairs = []
            unallocated = []
            backup_pairs = []
            
            # 跟踪机台使用情况
            feeder_utilization = {f["machine_code"]: Decimal("0") for f in feeders}
            maker_utilization = {m["machine_code"]: Decimal("0") for m in makers}
            
            for requirement in requirements:
                best_pair = None
                best_score = Decimal("-1")
                
                # 为每个需求寻找最佳配对
                for feeder in feeders:
                    feeder_code = feeder["machine_code"]
                    feeder_capacity = feeder_capacities.get(feeder_code, {})
                    feeder_available = feeder_capacity.get("available_capacity", 0)
                    
                    # 检查喂丝机是否有足够容量
                    if feeder_available <= 0:
                        continue
                    
                    for maker in makers:
                        maker_code = maker["machine_code"]
                        maker_capacity = maker_capacities.get(maker_code, {})
                        maker_available = maker_capacity.get("available_capacity", 0)
                        
                        # 检查卷包机是否有足够容量
                        if maker_available <= 0:
                            continue
                        
                        # 检查是否支持该物料
                        feeder_compatible = requirement.article_nr in feeder.get("compatibility", {}).get("supported_articles", set()) if hasattr(feeder.get("compatibility", {}), "__getitem__") else True
                        maker_compatible = requirement.article_nr in maker.get("compatibility", {}).get("supported_articles", set()) if hasattr(maker.get("compatibility", {}), "__getitem__") else True
                        
                        if not (feeder_compatible and maker_compatible):
                            continue
                        
                        # 计算配对分数
                        pair_score = await self._calculate_pairing_score(
                            requirement,
                            feeder_code,
                            maker_code,
                            feeder_capacity,
                            maker_capacity,
                            feeder_utilization[feeder_code],
                            maker_utilization[maker_code],
                            relationship_matrix.get(feeder_code, {}).get(maker_code, 0.5)
                        )
                        
                        if pair_score > best_score:
                            best_score = pair_score
                            best_pair = {
                                "requirement": requirement,
                                "feeder_code": feeder_code,
                                "maker_code": maker_code,
                                "feeder_capacity": feeder_capacity,
                                "maker_capacity": maker_capacity,
                                "pair_score": float(pair_score),
                                "relationship_score": relationship_matrix.get(feeder_code, {}).get(maker_code, 0.5)
                            }
                
                # 分配最佳配对
                if best_pair and best_score > Decimal("0.3"):  # 最低分数阈值
                    pairs.append(best_pair)
                    
                    # 更新机台利用率
                    allocated_quantity = requirement.target_quantity
                    feeder_utilization[best_pair["feeder_code"]] += allocated_quantity
                    maker_utilization[best_pair["maker_code"]] += allocated_quantity
                    
                    # 减少可用容量
                    feeder_capacities[best_pair["feeder_code"]]["available_capacity"] -= float(allocated_quantity)
                    maker_capacities[best_pair["maker_code"]]["available_capacity"] -= float(allocated_quantity)
                    
                else:
                    unallocated.append({
                        "requirement": requirement,
                        "reason": "无法找到合适的机台配对" if not best_pair else "配对分数过低"
                    })
            
            return {
                "pairs": pairs,
                "unallocated": unallocated,
                "backup_pairs": backup_pairs,
                "final_utilization": {
                    "feeders": {k: float(v) for k, v in feeder_utilization.items()},
                    "makers": {k: float(v) for k, v in maker_utilization.items()}
                }
            }
            
        except Exception as e:
            logger.error(f"执行配对算法失败: {e}")
            raise
    
    async def _calculate_pairing_score(
        self,
        requirement: ProductionRequirement,
        feeder_code: str,
        maker_code: str,
        feeder_capacity: Dict[str, Any],
        maker_capacity: Dict[str, Any],
        feeder_current_load: Decimal,
        maker_current_load: Decimal,
        relationship_score: float
    ) -> Decimal:
        """计算配对分数"""
        try:
            score = Decimal("0")
            
            # 1. 产能匹配分数 (40%)
            feeder_available = Decimal(str(feeder_capacity.get("available_capacity", 0)))
            maker_available = Decimal(str(maker_capacity.get("available_capacity", 0)))
            min_available = min(feeder_available, maker_available)
            
            if min_available >= requirement.target_quantity:
                capacity_score = Decimal("1.0")
            elif min_available > 0:
                capacity_score = min_available / requirement.target_quantity
            else:
                capacity_score = Decimal("0")
            
            score += capacity_score * self.config.capacity_weight
            
            # 2. 效率分数 (30%)
            feeder_efficiency = Decimal(str(feeder_capacity.get("capacity_factors", {}).get("efficiency_factor", 0.85)))
            maker_efficiency = Decimal(str(maker_capacity.get("capacity_factors", {}).get("efficiency_factor", 0.85)))
            avg_efficiency = (feeder_efficiency + maker_efficiency) / 2
            
            score += avg_efficiency * self.config.efficiency_weight
            
            # 3. 负载均衡分数 (20%)
            feeder_load_factor = Decimal("1.0") - (feeder_current_load / max(Decimal(str(feeder_capacity.get("effective_monthly_capacity", 1))), Decimal("1")))
            maker_load_factor = Decimal("1.0") - (maker_current_load / max(Decimal(str(maker_capacity.get("effective_monthly_capacity", 1))), Decimal("1")))
            avg_load_factor = (feeder_load_factor + maker_load_factor) / 2
            
            score += max(Decimal("0"), avg_load_factor) * self.config.availability_weight
            
            # 4. 关系分数 (10%)
            score += Decimal(str(relationship_score)) * self.config.relationship_weight
            
            return score.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"计算配对分数失败: {e}")
            return Decimal("0")
    
    async def _analyze_machine_loads(
        self,
        pairs: List[Dict[str, Any]],
        feeder_capacities: Dict[str, Dict[str, Any]],
        maker_capacities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析机台负载"""
        try:
            # 统计各机台使用情况
            feeder_loads = defaultdict(Decimal)
            maker_loads = defaultdict(Decimal)
            
            for pair in pairs:
                requirement = pair["requirement"]
                feeder_loads[pair["feeder_code"]] += requirement.target_quantity
                maker_loads[pair["maker_code"]] += requirement.target_quantity
            
            # 计算利用率
            feeder_utilization = {}
            for feeder_code, capacity_info in feeder_capacities.items():
                total_capacity = Decimal(str(capacity_info.get("effective_monthly_capacity", 0)))
                used_capacity = feeder_loads.get(feeder_code, Decimal("0"))
                utilization = (used_capacity / total_capacity * 100) if total_capacity > 0 else Decimal("0")
                feeder_utilization[feeder_code] = float(utilization)
            
            maker_utilization = {}
            for maker_code, capacity_info in maker_capacities.items():
                total_capacity = Decimal(str(capacity_info.get("effective_monthly_capacity", 0)))
                used_capacity = maker_loads.get(maker_code, Decimal("0"))
                utilization = (used_capacity / total_capacity * 100) if total_capacity > 0 else Decimal("0")
                maker_utilization[maker_code] = float(utilization)
            
            # 识别瓶颈和空闲机台
            all_utilization = {**feeder_utilization, **maker_utilization}
            avg_utilization = sum(all_utilization.values()) / len(all_utilization) if all_utilization else 0
            
            bottlenecks = [code for code, util in all_utilization.items() if util > 90]
            idle_machines = [code for code, util in all_utilization.items() if util < 30]
            
            return {
                "feeder_utilization": feeder_utilization,
                "maker_utilization": maker_utilization,
                "average_utilization": avg_utilization,
                "bottlenecks": bottlenecks,
                "idle_machines": idle_machines,
                "utilization_distribution": {
                    "high_load": len([u for u in all_utilization.values() if u > 80]),
                    "medium_load": len([u for u in all_utilization.values() if 50 <= u <= 80]),
                    "low_load": len([u for u in all_utilization.values() if u < 50])
                }
            }
            
        except Exception as e:
            logger.error(f"分析机台负载失败: {e}")
            return {"error": str(e)}
    
    async def _generate_pairing_optimization_suggestions(
        self,
        allocation_result: Dict[str, Any],
        load_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成配对优化建议"""
        suggestions = []
        
        try:
            # 分析未分配需求
            unallocated_count = len(allocation_result.get("unallocated", []))
            if unallocated_count > 0:
                suggestions.append(f"有 {unallocated_count} 个需求未能分配，建议检查机台容量或扩展机台资源")
            
            # 分析负载不均衡
            bottlenecks = load_analysis.get("bottlenecks", [])
            if bottlenecks:
                suggestions.append(f"机台 {', '.join(bottlenecks)} 负载过高，建议优化生产计划或增加维护窗口")
            
            idle_machines = load_analysis.get("idle_machines", [])
            if idle_machines:
                suggestions.append(f"机台 {', '.join(idle_machines)} 利用率较低，可考虑承接更多订单或调整维护计划")
            
            # 分析配对质量
            pairs = allocation_result.get("pairs", [])
            if pairs:
                avg_score = sum(pair.get("pair_score", 0) for pair in pairs) / len(pairs)
                if avg_score < 0.6:
                    suggestions.append("配对质量较低，建议检查机台关系配置或调整选择策略")
            
            # 分析容量利用
            avg_utilization = load_analysis.get("average_utilization", 0)
            if avg_utilization < 60:
                suggestions.append("整体机台利用率较低，可考虑增加生产任务或优化排产计划")
            elif avg_utilization > 90:
                suggestions.append("整体机台利用率过高，建议增加设备或延长生产周期")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return ["生成优化建议时出错"]
    
    # 支持方法 - 约束检查
    async def _check_capacity_constraint(
        self,
        machine_capability: MachineCapability,
        article_nr: str,
        target_quantity: Decimal,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查产能约束"""
        try:
            start_time, end_time = time_window
            duration_hours = (end_time - start_time).total_seconds() / 3600
            
            # 计算时间窗口内的可用产能
            hourly_capacity = machine_capability.base_capacity_per_hour
            efficiency_factor = machine_capability.efficiency_factor
            availability_factor = machine_capability.availability_score
            
            total_capacity = (
                hourly_capacity * Decimal(str(duration_hours)) * 
                efficiency_factor * availability_factor
            )
            
            satisfied = total_capacity >= target_quantity
            
            return {
                "satisfied": satisfied,
                "total_capacity": float(total_capacity),
                "required_capacity": float(target_quantity),
                "capacity_utilization": float(target_quantity / total_capacity * 100) if total_capacity > 0 else 0,
                "message": (
                    f"产能充足: 可用{total_capacity:.2f}箱, 需求{target_quantity:.2f}箱" if satisfied
                    else f"产能不足: 可用{total_capacity:.2f}箱, 需求{target_quantity:.2f}箱"
                )
            }
            
        except Exception as e:
            logger.error(f"检查产能约束失败: {e}")
            return {
                "satisfied": False,
                "message": f"产能约束检查失败: {str(e)}"
            }
    
    async def _check_maintenance_constraint(
        self,
        machine_code: str,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查维护计划约束"""
        try:
            start_time, end_time = time_window
            
            # 查询时间窗口内的维护计划
            stmt = select(MaintenancePlan).where(
                and_(
                    MaintenancePlan.machine_code == machine_code,
                    MaintenancePlan.plan_status.in_(['PLANNED', 'IN_PROGRESS']),
                    or_(
                        and_(
                            MaintenancePlan.maint_start_time >= start_time,
                            MaintenancePlan.maint_start_time <= end_time
                        ),
                        and_(
                            MaintenancePlan.maint_end_time >= start_time,
                            MaintenancePlan.maint_end_time <= end_time
                        ),
                        and_(
                            MaintenancePlan.maint_start_time <= start_time,
                            MaintenancePlan.maint_end_time >= end_time
                        )
                    )
                )
            )
            
            result = await self.session.execute(stmt)
            maintenances = result.scalars().all()
            
            if not maintenances:
                return {
                    "satisfied": True,
                    "message": "时间窗口内无维护计划冲突"
                }
            
            # 计算维护影响
            total_maintenance_hours = Decimal("0")
            maintenance_details = []
            
            for maint in maintenances:
                overlap_start = max(maint.maint_start_time, start_time)
                overlap_end = min(maint.maint_end_time, end_time)
                
                if overlap_start < overlap_end:
                    overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                    total_maintenance_hours += Decimal(str(overlap_hours))
                    
                    maintenance_details.append({
                        "plan_no": maint.maint_plan_no,
                        "start": overlap_start.isoformat(),
                        "end": overlap_end.isoformat(),
                        "duration_hours": overlap_hours,
                        "type": maint.maint_type
                    })
            
            window_hours = (end_time - start_time).total_seconds() / 3600
            impact_ratio = float(total_maintenance_hours) / window_hours if window_hours > 0 else 0
            
            # 判断严重程度
            if impact_ratio > 0.5:  # 维护时间超过50%
                severity = "error"
                satisfied = False
            elif impact_ratio > 0.2:  # 维护时间超过20%
                severity = "warning"
                satisfied = False
            else:
                severity = "info"
                satisfied = True
            
            return {
                "satisfied": satisfied,
                "severity": severity,
                "total_maintenance_hours": float(total_maintenance_hours),
                "impact_ratio": impact_ratio,
                "maintenance_details": maintenance_details,
                "message": f"维护计划影响: {impact_ratio:.1%}的时间窗口"
            }
            
        except Exception as e:
            logger.error(f"检查维护约束失败: {e}")
            return {
                "satisfied": False,
                "severity": "error",
                "message": f"维护约束检查失败: {str(e)}"
            }
    
    async def _check_compatibility_constraint(
        self,
        machine_capability: MachineCapability,
        article_nr: str
    ) -> Dict[str, Any]:
        """检查适配性约束"""
        try:
            supported = article_nr in machine_capability.supported_articles
            preferred = article_nr in machine_capability.preferred_articles
            
            if supported:
                setup_time = machine_capability.setup_time_matrix.get(article_nr, Decimal("0"))
                compatibility_score = 1.0 if preferred else 0.8
                
                return {
                    "satisfied": True,
                    "is_preferred": preferred,
                    "setup_time_hours": float(setup_time),
                    "compatibility_score": compatibility_score,
                    "message": f"物料兼容: {'首选' if preferred else '支持'}物料, 换产时间{setup_time:.1f}小时"
                }
            else:
                return {
                    "satisfied": False,
                    "message": f"物料不兼容: 机台不支持物料 {article_nr}"
                }
                
        except Exception as e:
            logger.error(f"检查适配性约束失败: {e}")
            return {
                "satisfied": False,
                "message": f"适配性约束检查失败: {str(e)}"
            }
    
    async def _check_availability_constraint(
        self,
        machine_capability: MachineCapability,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查可用性约束"""
        try:
            if not machine_capability.is_available:
                return {
                    "satisfied": False,
                    "message": "机台当前不可用"
                }
            
            availability_score = machine_capability.availability_score
            if availability_score < Decimal("0.5"):
                return {
                    "satisfied": False,
                    "availability_score": float(availability_score),
                    "message": f"机台可用性过低: {availability_score:.1%}"
                }
            
            return {
                "satisfied": True,
                "availability_score": float(availability_score),
                "message": f"机台可用: 可用性分数{availability_score:.1%}"
            }
            
        except Exception as e:
            logger.error(f"检查可用性约束失败: {e}")
            return {
                "satisfied": False,
                "message": f"可用性约束检查失败: {str(e)}"
            }
    
    async def _check_efficiency_constraint(
        self,
        machine_capability: MachineCapability,
        article_nr: str,
        target_quantity: Decimal
    ) -> Dict[str, Any]:
        """检查效率约束"""
        try:
            efficiency_factor = machine_capability.efficiency_factor
            threshold = self.config.efficiency_threshold
            
            satisfied = efficiency_factor >= threshold
            
            # 计算效率影响
            efficiency_impact = float(efficiency_factor) if satisfied else float(efficiency_factor / threshold)
            
            return {
                "satisfied": satisfied,
                "efficiency_factor": float(efficiency_factor),
                "threshold": float(threshold),
                "efficiency_impact": efficiency_impact,
                "message": (
                    f"效率满足要求: {efficiency_factor:.1%} >= {threshold:.1%}" if satisfied
                    else f"效率偏低: {efficiency_factor:.1%} < {threshold:.1%}"
                )
            }
            
        except Exception as e:
            logger.error(f"检查效率约束失败: {e}")
            return {
                "satisfied": False,
                "message": f"效率约束检查失败: {str(e)}"
            }
    
    async def _check_setup_time_constraint(
        self,
        machine_capability: MachineCapability,
        article_nr: str,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查换产时间约束"""
        try:
            setup_time = machine_capability.setup_time_matrix.get(article_nr, Decimal("0"))
            window_hours = (time_window[1] - time_window[0]).total_seconds() / 3600
            
            setup_ratio = float(setup_time) / window_hours if window_hours > 0 else 0
            
            # 换产时间不应超过时间窗口的20%
            satisfied = setup_ratio <= 0.2
            
            return {
                "satisfied": satisfied,
                "setup_time_hours": float(setup_time),
                "window_hours": window_hours,
                "setup_ratio": setup_ratio,
                "message": (
                    f"换产时间合理: {setup_time:.1f}小时 ({setup_ratio:.1%})" if satisfied
                    else f"换产时间过长: {setup_time:.1f}小时 ({setup_ratio:.1%})"
                )
            }
            
        except Exception as e:
            logger.error(f"检查换产时间约束失败: {e}")
            return {
                "satisfied": False,
                "message": f"换产时间约束检查失败: {str(e)}"
            }
    
    async def _check_working_calendar_constraint(
        self,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查工作日历约束"""
        try:
            start_time, end_time = time_window
            
            if self.calendar_service:
                # 检查时间窗口内的工作日
                current_date = start_time.date()
                end_date = end_time.date()
                
                working_days = 0
                total_days = 0
                
                while current_date <= end_date:
                    total_days += 1
                    _, calendar_day = await self.calendar_service.calculate_capacity(current_date)
                    if calendar_day.is_working:
                        working_days += 1
                    current_date += timedelta(days=1)
                
                working_ratio = working_days / total_days if total_days > 0 else 0
                satisfied = working_ratio > 0
                
                return {
                    "satisfied": satisfied,
                    "working_days": working_days,
                    "total_days": total_days,
                    "working_ratio": working_ratio,
                    "message": f"工作日历: {working_days}/{total_days} 工作日 ({working_ratio:.1%})"
                }
            else:
                # 简化检查: 假设周一到周五为工作日
                return {
                    "satisfied": True,
                    "message": "使用默认工作日历 (周一至周五)"
                }
                
        except Exception as e:
            logger.error(f"检查工作日历约束失败: {e}")
            return {
                "satisfied": True,  # 默认通过
                "message": f"工作日历约束检查失败: {str(e)}"
            }
    
    async def _check_load_balance_constraint(
        self,
        machine_code: str,
        target_quantity: Decimal,
        time_window: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """检查负载均衡约束"""
        try:
            start_time, end_time = time_window
            year, month = start_time.year, start_time.month
            
            # 获取当前机台负载
            current_load = await self._get_current_machine_load(machine_code, year, month)
            
            # 计算新增负载后的总负载
            machine_capability = await self._get_machine_capability(machine_code)
            if not machine_capability:
                return {
                    "satisfied": False,
                    "message": "无法获取机台信息"
                }
            
            # 计算理论容量
            from calendar import monthrange
            _, days_in_month = monthrange(year, month)
            working_days = days_in_month * 5 // 7  # 简化计算
            
            theoretical_capacity = machine_capability.calculate_effective_capacity(
                working_days, self.config.default_working_hours_per_day
            )
            
            # 转换为同一单位
            current_load_quantity = current_load * theoretical_capacity / 1000  # 万支转箱
            new_total_load = (current_load_quantity + target_quantity) / theoretical_capacity
            
            # 负载均衡阈值
            threshold = self.config.utilization_threshold
            satisfied = new_total_load <= threshold
            
            return {
                "satisfied": satisfied,
                "current_load_ratio": float(current_load),
                "new_total_load_ratio": float(new_total_load),
                "threshold": float(threshold),
                "theoretical_capacity": float(theoretical_capacity),
                "message": (
                    f"负载均衡: 总负载{new_total_load:.1%} <= {threshold:.1%}" if satisfied
                    else f"负载过高: 总负载{new_total_load:.1%} > {threshold:.1%}"
                )
            }
            
        except Exception as e:
            logger.error(f"检查负载均衡约束失败: {e}")
            return {
                "satisfied": True,  # 默认通过
                "message": f"负载均衡约束检查失败: {str(e)}"
            }
    
    async def _generate_constraint_recommendations(
        self,
        constraint_results: Dict[str, Any],
        machine_capability: MachineCapability,
        article_nr: str,
        target_quantity: Decimal,
        time_window: Tuple[datetime, datetime]
    ) -> List[str]:
        """生成约束建议"""
        recommendations = []
        
        try:
            # 基于约束检查结果生成建议
            for violation in constraint_results.get("violations", []):
                violation_type = violation.get("type", "")
                
                if violation_type == "capacity_insufficient":
                    recommendations.append("建议: 延长生产时间窗口或减少目标产量")
                    recommendations.append("建议: 考虑使用多台机台并行生产")
                
                elif violation_type == "maintenance_conflict":
                    recommendations.append("建议: 调整生产时间避开维护窗口")
                    recommendations.append("建议: 考虑提前或延后维护计划")
                
                elif violation_type == "article_incompatible":
                    recommendations.append("建议: 选择支持该物料的其他机台")
                    recommendations.append("建议: 检查物料编号是否正确")
                
                elif violation_type == "machine_unavailable":
                    recommendations.append("建议: 等待机台可用或选择备用机台")
            
            # 基于警告生成建议
            for warning in constraint_results.get("warnings", []):
                warning_type = warning.get("type", "")
                
                if warning_type == "low_efficiency":
                    recommendations.append("建议: 考虑机台维护或操作培训提升效率")
                
                elif warning_type == "long_setup_time":
                    recommendations.append("建议: 优化换产流程或考虑批量生产")
                
                elif warning_type == "high_load":
                    recommendations.append("建议: 平衡机台负载或增加生产时间")
            
            # 通用优化建议
            satisfaction_rate = constraint_results.get("satisfaction_rate", 100)
            if satisfaction_rate < 80:
                recommendations.append("建议: 重新评估生产计划或机台配置")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成约束建议失败: {e}")
            return ["建议生成过程中出现错误"]


async def create_machine_selector(
    session: Optional[AsyncSession] = None,
    calendar_service: Optional[MonthlyCalendarService] = None
) -> MonthlyMachineSelector:
    """
    创建机台选择器实例
    
    Args:
        session: 可选的数据库会话
        calendar_service: 可选的日历服务
        
    Returns:
        机台选择器实例
    """
    if session is None:
        session = await get_async_session().__anext__()
    
    return MonthlyMachineSelector(session, calendar_service)


# CLI 支持
def create_cli_parser() -> argparse.ArgumentParser:
    """创建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        description="月度机台选择算法 - 基于月度容量选择最优机台组合",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --select 123456 1000 --strategy capacity_optimal     # 机台选择
  %(prog)s --capacity M001 2025 1                               # 计算产能
  %(prog)s --batch-capacity M001,M002,F001 2025 1               # 批量计算产能
  %(prog)s --available feeder --article 123456                  # 查询可用机台
  %(prog)s --pair-allocation requirements.json 2025 1           # 配对分配
  %(prog)s --check-constraints M001 123456 1000 "2025-01-01 08:00" "2025-01-01 16:00"  # 约束检查
  %(prog)s --performance                                        # 性能统计
  %(prog)s --clear-cache                                        # 清除缓存
        """
    )
    
    parser.add_argument("--version", action="version", version=f"月度机台选择器 v{__version__}")
    
    # 输出格式选项
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    parser.add_argument("--format", choices=["table", "csv", "json"], default="table", 
                       help="输出格式 (默认: table)")
    
    # 功能选项
    parser.add_argument("--select", nargs=2, metavar=("ARTICLE_NR", "QUANTITY"),
                       help="选择机台 (物料编号 目标数量)")
    parser.add_argument("--strategy", choices=[s.value for s in MachineSelectionStrategy],
                       default="balance_optimal", help="选择策略")
    parser.add_argument("--objective", choices=[o.value for o in SelectionObjective],
                       default="maximize_throughput", help="优化目标")
    
    parser.add_argument("--capacity", nargs=3, metavar=("MACHINE_CODE", "YEAR", "MONTH"),
                       help="计算机台产能")
    parser.add_argument("--batch-capacity", nargs=3, metavar=("MACHINE_CODES", "YEAR", "MONTH"),
                       help="批量计算机台产能 (机台代码用逗号分隔)")
    parser.add_argument("--available", choices=["feeder", "maker", "all"], 
                       help="查询可用机台")
    parser.add_argument("--article", help="物料编号（用于适配性过滤）")
    parser.add_argument("--machines", action="store_true", help="列出所有机台")
    
    # 新增功能
    parser.add_argument("--pair-allocation", nargs=3, metavar=("REQUIREMENTS_FILE", "YEAR", "MONTH"),
                       help="执行喂丝机-卷包机配对分配")
    parser.add_argument("--check-constraints", nargs=5, 
                       metavar=("MACHINE_CODE", "ARTICLE_NR", "QUANTITY", "START_TIME", "END_TIME"),
                       help="检查机台约束条件")
    parser.add_argument("--constraint-types", help="约束类型列表（逗号分隔）")
    
    # 性能和缓存选项
    parser.add_argument("--performance", action="store_true", help="显示性能统计")
    parser.add_argument("--clear-cache", action="store_true", help="清除所有缓存")
    
    return parser


async def main():
    """CLI 主函数"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    try:
        # 创建服务实例
        selector = await create_machine_selector()
        
        # 处理缓存和性能命令
        if args.clear_cache:
            selector.clear_cache()
            print("缓存已清除")
            return 0
        
        if args.performance:
            stats = selector.get_performance_stats()
            if args.json or args.format == "json":
                print(json.dumps(stats, ensure_ascii=False, indent=2))
            else:
                print("性能统计:")
                print("-" * 40)
                print(f"缓存命中率: {stats['cache_hit_rate']}")
                print(f"总查询数: {stats['total_queries']}")
                print(f"批处理操作数: {stats['batch_operations']}")
                print("缓存大小:")
                for key, value in stats['cache_size'].items():
                    print(f"  {key}: {value}")
            return 0
        
        # 处理不同的命令
        if args.select:
            article_nr, quantity = args.select
            
            # 构建选择标准
            criteria = MachineSelectionCriteria(
                article_nr=article_nr,
                target_quantity=Decimal(quantity),
                planned_start=datetime.now(),
                planned_end=None,
                priority=Priority.MEDIUM,
                required_machine_types=[MachineType.FEEDER, MachineType.MAKER],
                preferred_machines=[],
                excluded_machines=[],
                max_setup_time=None,
                min_efficiency=None,
                selection_strategy=MachineSelectionStrategy(args.strategy),
                objective=SelectionObjective(args.objective)
            )
            
            result = await selector.select_optimal_machines(criteria)
            
            if args.json or args.format == "json":
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
            else:
                print(f"机台选择结果:")
                print("-" * 60)
                print(f"物料编号: {article_nr}")
                print(f"目标数量: {quantity}")
                print(f"选择策略: {args.strategy}")
                print(f"主选机台: 喂丝机={result.selected_feeder or 'N/A'}, 卷包机={result.selected_maker or 'N/A'}")
                print(f"总产能: {result.total_capacity}")
                print(f"效率分数: {result.efficiency_score:.2%}")
                print(f"约束满足: {'是' if result.constraints_satisfied else '否'}")
                if result.constraint_violations:
                    print(f"约束违反: {'; '.join(result.constraint_violations)}")
        
        elif args.capacity:
            machine_code, year, month = args.capacity
            capacity_info = await selector.calculate_machine_capacity(
                machine_code, int(year), int(month), args.article
            )
            
            if args.json or args.format == "json":
                print(json.dumps(capacity_info, ensure_ascii=False, indent=2))
            else:
                print(f"机台产能信息:")
                print("-" * 50)
                print(f"机台代码: {capacity_info['machine_code']}")
                print(f"计算期间: {capacity_info['period']}")
                print(f"工作日数: {capacity_info['working_days']}")
                print(f"有效月产能: {capacity_info['effective_monthly_capacity']:.2f}")
                print(f"可用产能: {capacity_info['available_capacity']:.2f}")
                print(f"当前利用率: {capacity_info['current_utilization']:.2%}")
        
        elif args.batch_capacity:
            machine_codes_str, year, month = args.batch_capacity
            machine_codes = [code.strip() for code in machine_codes_str.split(",")]
            
            capacity_results = await selector.batch_calculate_machine_capacity(
                machine_codes, int(year), int(month), args.article
            )
            
            if args.json or args.format == "json":
                print(json.dumps(capacity_results, ensure_ascii=False, indent=2))
            else:
                print(f"批量机台产能信息 ({year}-{month:02d}):")
                print("-" * 80)
                for machine_code, capacity_info in capacity_results.items():
                    print(f"{machine_code}: 有效产能={capacity_info.get('effective_monthly_capacity', 0):.2f}, "
                          f"可用产能={capacity_info.get('available_capacity', 0):.2f}, "
                          f"利用率={capacity_info.get('current_utilization', 0):.2%}")
        
        elif args.available:
            machine_type = None
            if args.available == "feeder":
                machine_type = MachineType.FEEDER
            elif args.available == "maker":
                machine_type = MachineType.MAKER
            
            machines = await selector.get_available_machines(
                machine_type=machine_type,
                article_nr=args.article
            )
            
            if args.json or args.format == "json":
                print(json.dumps(machines, ensure_ascii=False, indent=2))
            else:
                print(f"可用机台列表 ({args.available}):")
                print("-" * 80)
                for machine in machines:
                    print(f"{machine['machine_code']} | {machine['machine_name']} | "
                          f"产能: {machine['capability']['base_capacity']:.2f} | "
                          f"效率: {machine['capability']['efficiency_factor']:.2%} | "
                          f"利用率: {machine['capability']['current_utilization']:.2%}")
        
        elif args.machines:
            all_machines = await selector.get_available_machines()
            
            if args.json or args.format == "json":
                print(json.dumps(all_machines, ensure_ascii=False, indent=2))
            else:
                print(f"所有机台信息:")
                print("-" * 100)
                for machine in all_machines:
                    print(f"{machine['machine_code']} | {machine['machine_type']} | "
                          f"{machine['machine_name']} | 产能: {machine['capability']['base_capacity']:.2f} | "
                          f"效率: {machine['capability']['efficiency_factor']:.2%}")
        
        elif args.pair_allocation:
            requirements_file, year, month = args.pair_allocation
            
            # 读取需求文件
            try:
                with open(requirements_file, 'r', encoding='utf-8') as f:
                    requirements_data = json.load(f)
                
                requirements = []
                for req_data in requirements_data:
                    requirement = ProductionRequirement(
                        article_nr=req_data['article_nr'],
                        article_name=req_data.get('article_name', ''),
                        target_quantity=Decimal(str(req_data['target_quantity'])),
                        priority=req_data.get('priority', 5)
                    )
                    requirements.append(requirement)
                
                allocation_result = await selector.allocate_feeder_maker_pairs(
                    requirements, (int(year), int(month))
                )
                
                if args.json or args.format == "json":
                    print(json.dumps(allocation_result, ensure_ascii=False, indent=2, default=str))
                else:
                    print(f"机台配对分配结果 ({year}-{month:02d}):")
                    print("-" * 80)
                    print(f"总需求数: {allocation_result['total_requirements']}")
                    print(f"成功配对: {allocation_result['successful_pairs']}")
                    print(f"未分配需求: {allocation_result['unallocated_requirements']}")
                    print(f"分配成功率: {allocation_result['performance_metrics']['allocation_success_rate']:.1f}%")
                    print(f"平均利用率: {allocation_result['performance_metrics']['average_capacity_utilization']:.1f}%")
                    
                    if allocation_result.get('optimization_suggestions'):
                        print("\n优化建议:")
                        for suggestion in allocation_result['optimization_suggestions']:
                            print(f"  - {suggestion}")
                
            except FileNotFoundError:
                print(f"错误: 找不到需求文件 {requirements_file}")
                return 1
            except json.JSONDecodeError:
                print(f"错误: 需求文件格式不正确")
                return 1
        
        elif args.check_constraints:
            machine_code, article_nr, quantity, start_time_str, end_time_str = args.check_constraints
            
            # 解析时间
            start_time = datetime.fromisoformat(start_time_str.replace(' ', 'T'))
            end_time = datetime.fromisoformat(end_time_str.replace(' ', 'T'))
            
            # 解析约束类型
            constraint_types = None
            if args.constraint_types:
                constraint_types = [t.strip() for t in args.constraint_types.split(",")]
            
            constraint_result = await selector.check_machine_constraints(
                machine_code, article_nr, Decimal(quantity), (start_time, end_time), constraint_types
            )
            
            if args.json or args.format == "json":
                print(json.dumps(constraint_result, ensure_ascii=False, indent=2, default=str))
            else:
                print(f"机台约束检查结果:")
                print("-" * 60)
                print(f"机台代码: {constraint_result['machine_code']}")
                print(f"物料编号: {constraint_result['article_nr']}")
                print(f"目标数量: {constraint_result['target_quantity']}")
                print(f"总体满足: {'是' if constraint_result['overall_satisfaction'] else '否'}")
                print(f"满足率: {constraint_result['satisfaction_rate']:.1f}%")
                
                if constraint_result['violations']:
                    print("\n约束违反:")
                    for violation in constraint_result['violations']:
                        print(f"  - {violation['type']}: {violation['message']}")
                
                if constraint_result['warnings']:
                    print("\n警告:")
                    for warning in constraint_result['warnings']:
                        print(f"  - {warning['type']}: {warning['message']}")
                
                if constraint_result['recommendations']:
                    print("\n建议:")
                    for recommendation in constraint_result['recommendations']:
                        print(f"  - {recommendation}")
        
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"CLI 执行失败: {e}")
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    sys.exit(asyncio.run(main()))