"""
月度生产容量计算和优化算法模块

该模块实现了烟草生产中的月度容量计算、瓶颈分析和资源优化算法。
支持多产品、多机台的复杂容量平衡计算，提供精确的产能规划支持。

主要功能：
- 月度容量精确计算
- 容量瓶颈识别与分析
- 资源配置优化
- 容量预测与趋势分析
- 产能效率评估
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import argparse
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

# 假设这些模型已存在或将要创建
try:
    from ...models.monthly_plan_models import MonthlyPlan
    from ...models.monthly_work_calendar_models import WorkCalendar
    from ...models.machine_config_models import MachineConfig, MachineSpeed
    from ...models.base_models import Machine, Material
except ImportError:
    # 开发阶段的占位符
    MonthlyPlan = None
    WorkCalendar = None
    MachineConfig = None
    MachineSpeed = None
    Machine = None
    Material = None

logger = logging.getLogger(__name__)


class CapacityCalculationMethod(Enum):
    """容量计算方法枚举"""
    THEORETICAL = "theoretical"  # 理论容量
    PRACTICAL = "practical"      # 实际容量
    OPTIMIZED = "optimized"      # 优化容量
    HISTORICAL = "historical"    # 历史容量


class BottleneckType(Enum):
    """瓶颈类型枚举"""
    MACHINE = "machine"          # 机台瓶颈
    MATERIAL = "material"        # 物料瓶颈
    WORKFORCE = "workforce"      # 人力瓶颈
    TIME = "time"               # 时间瓶颈
    MAINTENANCE = "maintenance"  # 维护瓶颈


@dataclass
class CapacityFactors:
    """容量影响因子数据类"""
    efficiency_factor: float = 0.85      # 效率系数 (0-1)
    availability_factor: float = 0.90    # 可用性系数 (0-1)
    quality_factor: float = 0.95         # 质量系数 (0-1)
    maintenance_factor: float = 0.92     # 维护影响系数 (0-1)
    setup_factor: float = 0.88          # 设置时间系数 (0-1)
    operator_factor: float = 0.93       # 操作员熟练度系数 (0-1)
    material_factor: float = 0.97       # 物料质量系数 (0-1)
    
    def overall_factor(self) -> float:
        """计算综合影响因子"""
        return (self.efficiency_factor * 
                self.availability_factor * 
                self.quality_factor * 
                self.maintenance_factor * 
                self.setup_factor * 
                self.operator_factor * 
                self.material_factor)


@dataclass
class MachineCapacity:
    """机台容量数据类"""
    machine_id: str
    machine_name: str
    product_type: str
    theoretical_capacity: Decimal        # 理论容量 (件/小时)
    practical_capacity: Decimal         # 实际容量 (件/小时)
    available_hours: Decimal            # 可用工时 (小时)
    total_monthly_capacity: Decimal     # 月度总容量 (件)
    utilized_capacity: Decimal          # 已利用容量 (件)
    remaining_capacity: Decimal         # 剩余容量 (件)
    utilization_rate: float            # 利用率 (0-1)
    efficiency_score: float            # 效率评分 (0-100)
    bottleneck_indicators: List[str]    # 瓶颈指标
    capacity_factors: CapacityFactors   # 容量影响因子


@dataclass
class BottleneckAnalysis:
    """瓶颈分析结果数据类"""
    bottleneck_type: BottleneckType
    severity_level: float              # 严重程度 (0-1)
    affected_machines: List[str]       # 受影响机台
    affected_products: List[str]       # 受影响产品
    capacity_loss: Decimal             # 容量损失 (件)
    impact_percentage: float           # 影响百分比
    root_cause: str                    # 根本原因
    recommendations: List[str]         # 优化建议
    estimated_improvement: Decimal     # 预期改进容量


@dataclass
class OptimizationRecommendation:
    """优化建议数据类"""
    recommendation_id: str
    priority: int                      # 优先级 (1-10)
    category: str                      # 类别
    description: str                   # 描述
    expected_benefit: Decimal          # 预期收益 (件)
    implementation_cost: float         # 实施成本
    implementation_time: int           # 实施时间 (天)
    roi_score: float                  # ROI评分
    feasibility_score: float          # 可行性评分


@dataclass
class CapacityForecast:
    """容量预测数据类"""
    forecast_period: str               # 预测期间
    predicted_capacity: Decimal        # 预测容量
    confidence_interval: Tuple[Decimal, Decimal]  # 置信区间
    trend_direction: str              # 趋势方向
    seasonality_factor: float         # 季节性因子
    growth_rate: float               # 增长率
    risk_factors: List[str]          # 风险因子


@dataclass
class CapacityReport:
    """容量报告数据类"""
    report_id: str
    calculation_time: datetime
    calculation_method: CapacityCalculationMethod
    total_theoretical_capacity: Decimal
    total_practical_capacity: Decimal
    total_utilized_capacity: Decimal
    overall_utilization_rate: float
    machine_capacities: List[MachineCapacity]
    bottleneck_analyses: List[BottleneckAnalysis]
    optimization_recommendations: List[OptimizationRecommendation]
    capacity_forecasts: List[CapacityForecast]
    kpi_metrics: Dict[str, Any]
    visualization_data: Dict[str, Any]


class MonthlyCapacityCalculator:
    """
    月度生产容量计算器
    
    实现烟草生产中的月度容量计算、瓶颈分析和资源优化算法。
    支持多种计算方法和优化策略。
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        初始化容量计算器
        
        Args:
            db_session: 数据库会话
        """
        self.db_session = db_session
        self.default_factors = CapacityFactors()
        self.calculation_cache = {}
        self.performance_metrics = {
            'calculations_performed': 0,
            'average_calculation_time': 0.0,
            'cache_hit_rate': 0.0
        }
    
    async def calculate_monthly_capacity(
        self,
        year: int,
        month: int,
        machine_ids: Optional[List[str]] = None,
        product_types: Optional[List[str]] = None,
        calculation_method: CapacityCalculationMethod = CapacityCalculationMethod.PRACTICAL,
        include_forecast: bool = True
    ) -> CapacityReport:
        """
        计算月度生产容量
        
        Args:
            year: 年份
            month: 月份
            machine_ids: 机台ID列表，None表示所有机台
            product_types: 产品类型列表，None表示所有产品
            calculation_method: 计算方法
            include_forecast: 是否包含预测分析
            
        Returns:
            CapacityReport: 容量报告
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始计算 {year}-{month:02d} 月度容量，方法: {calculation_method.value}")
            
            # 生成缓存键
            cache_key = self._generate_cache_key(year, month, machine_ids, product_types, calculation_method)
            
            # 检查缓存
            if cache_key in self.calculation_cache:
                logger.info("使用缓存的计算结果")
                self.performance_metrics['cache_hit_rate'] += 1
                return self.calculation_cache[cache_key]
            
            # 获取工作日历
            work_calendar = await self._get_work_calendar(year, month)
            
            # 获取机台配置
            machines = await self._get_machine_configs(machine_ids)
            
            # 获取月度计划
            monthly_plans = await self._get_monthly_plans(year, month, product_types)
            
            # 计算机台容量
            machine_capacities = []
            for machine in machines:
                capacity = await self._calculate_machine_capacity(
                    machine, work_calendar, monthly_plans, calculation_method
                )
                machine_capacities.append(capacity)
            
            # 分析瓶颈
            bottlenecks = await self.analyze_bottlenecks(machine_capacities)
            
            # 生成优化建议
            recommendations = await self._generate_optimization_recommendations(
                machine_capacities, bottlenecks
            )
            
            # 容量预测
            forecasts = []
            if include_forecast:
                forecasts = await self.generate_capacity_forecast(
                    CapacityReport(
                        report_id="temp",
                        calculation_time=datetime.now(),
                        calculation_method=calculation_method,
                        total_theoretical_capacity=sum(mc.theoretical_capacity * mc.available_hours for mc in machine_capacities),
                        total_practical_capacity=sum(mc.practical_capacity * mc.available_hours for mc in machine_capacities),
                        total_utilized_capacity=sum(mc.utilized_capacity for mc in machine_capacities),
                        overall_utilization_rate=self._calculate_overall_utilization(machine_capacities),
                        machine_capacities=machine_capacities,
                        bottleneck_analyses=[],
                        optimization_recommendations=[],
                        capacity_forecasts=[],
                        kpi_metrics={},
                        visualization_data={}
                    ), 6
                )
            
            # 计算KPI指标
            kpi_metrics = self._calculate_kpi_metrics(machine_capacities)
            
            # 生成可视化数据
            visualization_data = self._generate_visualization_data(machine_capacities, bottlenecks)
            
            # 创建容量报告
            report = CapacityReport(
                report_id=f"CAP_{year}{month:02d}_{int(time.time())}",
                calculation_time=datetime.now(),
                calculation_method=calculation_method,
                total_theoretical_capacity=sum(mc.theoretical_capacity * mc.available_hours for mc in machine_capacities),
                total_practical_capacity=sum(mc.practical_capacity * mc.available_hours for mc in machine_capacities),
                total_utilized_capacity=sum(mc.utilized_capacity for mc in machine_capacities),
                overall_utilization_rate=self._calculate_overall_utilization(machine_capacities),
                machine_capacities=machine_capacities,
                bottleneck_analyses=bottlenecks,
                optimization_recommendations=recommendations,
                capacity_forecasts=forecasts,
                kpi_metrics=kpi_metrics,
                visualization_data=visualization_data
            )
            
            # 缓存结果
            self.calculation_cache[cache_key] = report
            
            # 更新性能指标
            calculation_time = time.time() - start_time
            self._update_performance_metrics(calculation_time)
            
            logger.info(f"容量计算完成，耗时: {calculation_time:.2f}秒")
            return report
            
        except Exception as e:
            logger.error(f"容量计算失败: {str(e)}")
            raise
    
    async def analyze_bottlenecks(
        self,
        machine_capacities: List[MachineCapacity],
        severity_threshold: float = 0.7
    ) -> List[BottleneckAnalysis]:
        """
        分析容量瓶颈
        
        Args:
            machine_capacities: 机台容量列表
            severity_threshold: 严重程度阈值
            
        Returns:
            List[BottleneckAnalysis]: 瓶颈分析结果列表
        """
        logger.info("开始分析容量瓶颈")
        
        bottlenecks = []
        
        # 分析机台利用率瓶颈
        high_utilization_machines = [
            mc for mc in machine_capacities 
            if mc.utilization_rate > severity_threshold
        ]
        
        if high_utilization_machines:
            bottleneck = BottleneckAnalysis(
                bottleneck_type=BottleneckType.MACHINE,
                severity_level=max(mc.utilization_rate for mc in high_utilization_machines),
                affected_machines=[mc.machine_id for mc in high_utilization_machines],
                affected_products=list(set(mc.product_type for mc in high_utilization_machines)),
                capacity_loss=sum(mc.theoretical_capacity * mc.available_hours - mc.total_monthly_capacity 
                                for mc in high_utilization_machines),
                impact_percentage=len(high_utilization_machines) / len(machine_capacities) * 100,
                root_cause="机台利用率过高，接近或超过设计容量",
                recommendations=[
                    "增加机台或班次",
                    "优化生产调度",
                    "提高机台效率",
                    "平衡产品分配"
                ],
                estimated_improvement=sum(mc.remaining_capacity for mc in high_utilization_machines) * Decimal('0.2')
            )
            bottlenecks.append(bottleneck)
        
        # 分析效率瓶颈
        low_efficiency_machines = [
            mc for mc in machine_capacities 
            if mc.efficiency_score < 70.0
        ]
        
        if low_efficiency_machines:
            bottleneck = BottleneckAnalysis(
                bottleneck_type=BottleneckType.MACHINE,
                severity_level=1.0 - min(mc.efficiency_score for mc in low_efficiency_machines) / 100,
                affected_machines=[mc.machine_id for mc in low_efficiency_machines],
                affected_products=list(set(mc.product_type for mc in low_efficiency_machines)),
                capacity_loss=sum((mc.theoretical_capacity - mc.practical_capacity) * mc.available_hours 
                                for mc in low_efficiency_machines),
                impact_percentage=len(low_efficiency_machines) / len(machine_capacities) * 100,
                root_cause="机台效率低下，实际产能远低于理论产能",
                recommendations=[
                    "设备维护和保养",
                    "操作员培训",
                    "工艺参数优化",
                    "质量控制改进"
                ],
                estimated_improvement=sum((mc.theoretical_capacity - mc.practical_capacity) * mc.available_hours 
                                        for mc in low_efficiency_machines) * Decimal('0.3')
            )
            bottlenecks.append(bottleneck)
        
        # 分析时间瓶颈（可用工时不足）
        time_constrained_machines = [
            mc for mc in machine_capacities 
            if mc.available_hours < Decimal('600')  # 假设正常月度可用工时为600小时
        ]
        
        if time_constrained_machines:
            bottleneck = BottleneckAnalysis(
                bottleneck_type=BottleneckType.TIME,
                severity_level=(600 - float(min(mc.available_hours for mc in time_constrained_machines))) / 600,
                affected_machines=[mc.machine_id for mc in time_constrained_machines],
                affected_products=list(set(mc.product_type for mc in time_constrained_machines)),
                capacity_loss=sum((Decimal('600') - mc.available_hours) * mc.practical_capacity 
                                for mc in time_constrained_machines),
                impact_percentage=len(time_constrained_machines) / len(machine_capacities) * 100,
                root_cause="可用工时不足，影响产能发挥",
                recommendations=[
                    "增加班次安排",
                    "减少维护停机时间",
                    "优化换产时间",
                    "提高设备可用性"
                ],
                estimated_improvement=sum((Decimal('600') - mc.available_hours) * mc.practical_capacity 
                                        for mc in time_constrained_machines) * Decimal('0.8')
            )
            bottlenecks.append(bottleneck)
        
        logger.info(f"瓶颈分析完成，识别出 {len(bottlenecks)} 个瓶颈")
        return bottlenecks
    
    async def optimize_resource_allocation(
        self,
        capacity_report: CapacityReport,
        optimization_objectives: Optional[Dict[str, float]] = None
    ) -> List[OptimizationRecommendation]:
        """
        优化资源配置
        
        Args:
            capacity_report: 容量报告
            optimization_objectives: 优化目标权重
            
        Returns:
            List[OptimizationRecommendation]: 优化建议列表
        """
        logger.info("开始资源配置优化")
        
        if optimization_objectives is None:
            optimization_objectives = {
                'capacity_increase': 0.4,    # 容量提升
                'efficiency_improvement': 0.3,  # 效率改进
                'cost_reduction': 0.2,       # 成本降低
                'flexibility_enhancement': 0.1  # 灵活性提升
            }
        
        recommendations = []
        
        # 基于瓶颈分析生成优化建议
        for bottleneck in capacity_report.bottleneck_analyses:
            if bottleneck.bottleneck_type == BottleneckType.MACHINE:
                # 机台瓶颈优化
                rec = OptimizationRecommendation(
                    recommendation_id=f"OPT_MACHINE_{len(recommendations)+1}",
                    priority=int(bottleneck.severity_level * 10),
                    category="机台优化",
                    description=f"针对 {', '.join(bottleneck.affected_machines)} 的机台瓶颈进行优化",
                    expected_benefit=bottleneck.estimated_improvement,
                    implementation_cost=float(bottleneck.estimated_improvement) * 0.1,  # 估算成本
                    implementation_time=30,  # 30天
                    roi_score=float(bottleneck.estimated_improvement) / (float(bottleneck.estimated_improvement) * 0.1),
                    feasibility_score=0.8
                )
                recommendations.append(rec)
            
            elif bottleneck.bottleneck_type == BottleneckType.TIME:
                # 时间瓶颈优化
                rec = OptimizationRecommendation(
                    recommendation_id=f"OPT_TIME_{len(recommendations)+1}",
                    priority=int(bottleneck.severity_level * 10),
                    category="时间优化",
                    description=f"增加 {', '.join(bottleneck.affected_machines)} 的可用工时",
                    expected_benefit=bottleneck.estimated_improvement,
                    implementation_cost=float(bottleneck.estimated_improvement) * 0.05,
                    implementation_time=14,  # 14天
                    roi_score=float(bottleneck.estimated_improvement) / (float(bottleneck.estimated_improvement) * 0.05),
                    feasibility_score=0.9
                )
                recommendations.append(rec)
        
        # 基于机台利用率不平衡生成负载均衡建议
        machine_capacities = capacity_report.machine_capacities
        utilization_variance = self._calculate_utilization_variance(machine_capacities)
        
        if utilization_variance > 0.2:  # 利用率差异大于20%
            overloaded_machines = [mc for mc in machine_capacities if mc.utilization_rate > 0.85]
            underloaded_machines = [mc for mc in machine_capacities if mc.utilization_rate < 0.6]
            
            if overloaded_machines and underloaded_machines:
                potential_transfer = min(
                    sum(mc.utilized_capacity * Decimal('0.2') for mc in overloaded_machines),
                    sum(mc.remaining_capacity for mc in underloaded_machines)
                )
                
                rec = OptimizationRecommendation(
                    recommendation_id=f"OPT_BALANCE_{len(recommendations)+1}",
                    priority=7,
                    category="负载均衡",
                    description="重新分配生产任务以平衡机台利用率",
                    expected_benefit=potential_transfer,
                    implementation_cost=float(potential_transfer) * 0.02,
                    implementation_time=7,  # 7天
                    roi_score=float(potential_transfer) / (float(potential_transfer) * 0.02),
                    feasibility_score=0.95
                )
                recommendations.append(rec)
        
        # 排序建议（按优先级和ROI）
        recommendations.sort(key=lambda x: (x.priority, x.roi_score), reverse=True)
        
        logger.info(f"资源配置优化完成，生成 {len(recommendations)} 条建议")
        return recommendations
    
    async def generate_capacity_forecast(
        self,
        base_capacity_report: CapacityReport,
        forecast_months: int = 6,
        growth_assumptions: Optional[Dict[str, float]] = None
    ) -> List[CapacityForecast]:
        """
        生成容量预测
        
        Args:
            base_capacity_report: 基础容量报告
            forecast_months: 预测月数
            growth_assumptions: 增长假设
            
        Returns:
            List[CapacityForecast]: 容量预测列表
        """
        logger.info(f"开始生成 {forecast_months} 个月的容量预测")
        
        if growth_assumptions is None:
            growth_assumptions = {
                'demand_growth': 0.02,      # 月需求增长率 2%
                'efficiency_improvement': 0.01,  # 月效率改进 1%
                'capacity_expansion': 0.005      # 月容量扩张 0.5%
            }
        
        forecasts = []
        base_capacity = base_capacity_report.total_practical_capacity
        
        for month_offset in range(1, forecast_months + 1):
            # 基础容量增长
            capacity_growth = (1 + growth_assumptions['capacity_expansion']) ** month_offset
            predicted_capacity = base_capacity * Decimal(str(capacity_growth))
            
            # 效率改进影响
            efficiency_improvement = (1 + growth_assumptions['efficiency_improvement']) ** month_offset
            predicted_capacity *= Decimal(str(efficiency_improvement))
            
            # 季节性调整
            seasonality_factor = self._calculate_seasonality_factor(month_offset)
            predicted_capacity *= Decimal(str(seasonality_factor))
            
            # 置信区间计算（假设10%的不确定性）
            uncertainty = predicted_capacity * Decimal('0.1')
            confidence_interval = (
                predicted_capacity - uncertainty,
                predicted_capacity + uncertainty
            )
            
            # 趋势方向
            if capacity_growth > 1.05:
                trend_direction = "strong_growth"
            elif capacity_growth > 1.02:
                trend_direction = "moderate_growth"
            elif capacity_growth > 0.98:
                trend_direction = "stable"
            else:
                trend_direction = "decline"
            
            forecast = CapacityForecast(
                forecast_period=f"{month_offset}个月后",
                predicted_capacity=predicted_capacity,
                confidence_interval=confidence_interval,
                trend_direction=trend_direction,
                seasonality_factor=seasonality_factor,
                growth_rate=capacity_growth - 1,
                risk_factors=[
                    "市场需求波动",
                    "设备老化",
                    "技术更新",
                    "政策变化"
                ]
            )
            forecasts.append(forecast)
        
        logger.info(f"容量预测生成完成，覆盖 {forecast_months} 个月")
        return forecasts
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            Dict[str, Any]: 性能指标
        """
        return self.performance_metrics.copy()
    
    def clear_cache(self):
        """清空计算缓存"""
        self.calculation_cache.clear()
        logger.info("计算缓存已清空")
    
    # === 私有方法 ===
    
    def _generate_cache_key(
        self,
        year: int,
        month: int,
        machine_ids: Optional[List[str]],
        product_types: Optional[List[str]],
        calculation_method: CapacityCalculationMethod
    ) -> str:
        """生成缓存键"""
        machine_str = ",".join(sorted(machine_ids or []))
        product_str = ",".join(sorted(product_types or []))
        return f"{year}_{month}_{machine_str}_{product_str}_{calculation_method.value}"
    
    async def _get_work_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """获取工作日历数据"""
        # 这里应该从数据库获取实际数据
        # 目前返回模拟数据
        working_days = 22  # 假设每月22个工作日
        working_hours_per_day = 24  # 假设24小时作业
        return {
            'year': year,
            'month': month,
            'working_days': working_days,
            'working_hours_per_day': working_hours_per_day,
            'total_working_hours': working_days * working_hours_per_day,
            'maintenance_hours': 48,  # 假设每月48小时维护
            'available_hours': working_days * working_hours_per_day - 48
        }
    
    async def _get_machine_configs(self, machine_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
        """获取机台配置数据"""
        # 这里应该从数据库获取实际数据
        # 目前返回模拟数据
        machines = [
            {
                'machine_id': 'JBJ001',
                'machine_name': '卷包机1号',
                'product_type': '香烟',
                'theoretical_speed': 8000,  # 件/小时
                'practical_speed': 6800,    # 件/小时
                'efficiency_factor': 0.85
            },
            {
                'machine_id': 'JBJ002',
                'machine_name': '卷包机2号',
                'product_type': '香烟',
                'theoretical_speed': 8000,
                'practical_speed': 7200,
                'efficiency_factor': 0.90
            },
            {
                'machine_id': 'WSJ001',
                'machine_name': '喂丝机1号',
                'product_type': '烟丝',
                'theoretical_speed': 12000,
                'practical_speed': 10200,
                'efficiency_factor': 0.85
            }
        ]
        
        if machine_ids:
            machines = [m for m in machines if m['machine_id'] in machine_ids]
        
        return machines
    
    async def _get_monthly_plans(
        self,
        year: int,
        month: int,
        product_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """获取月度计划数据"""
        # 这里应该从数据库获取实际数据
        # 目前返回模拟数据
        plans = [
            {
                'plan_id': 'MP001',
                'product_type': '香烟',
                'target_quantity': 500000,
                'allocated_machines': ['JBJ001', 'JBJ002']
            },
            {
                'plan_id': 'MP002',
                'product_type': '烟丝',
                'target_quantity': 300000,
                'allocated_machines': ['WSJ001']
            }
        ]
        
        if product_types:
            plans = [p for p in plans if p['product_type'] in product_types]
        
        return plans
    
    async def _calculate_machine_capacity(
        self,
        machine: Dict[str, Any],
        work_calendar: Dict[str, Any],
        monthly_plans: List[Dict[str, Any]],
        calculation_method: CapacityCalculationMethod
    ) -> MachineCapacity:
        """计算单台机器的容量"""
        machine_id = machine['machine_id']
        machine_name = machine['machine_name']
        product_type = machine['product_type']
        
        # 计算可用工时
        available_hours = Decimal(str(work_calendar['available_hours']))
        
        # 根据计算方法确定容量
        if calculation_method == CapacityCalculationMethod.THEORETICAL:
            capacity_per_hour = Decimal(str(machine['theoretical_speed']))
        elif calculation_method == CapacityCalculationMethod.PRACTICAL:
            capacity_per_hour = Decimal(str(machine['practical_speed']))
        else:
            # 优化容量考虑各种因子
            base_capacity = Decimal(str(machine['practical_speed']))
            factors = CapacityFactors(efficiency_factor=machine['efficiency_factor'])
            capacity_per_hour = base_capacity * Decimal(str(factors.overall_factor()))
        
        theoretical_capacity = Decimal(str(machine['theoretical_speed']))
        practical_capacity = capacity_per_hour
        total_monthly_capacity = capacity_per_hour * available_hours
        
        # 计算已利用容量（从月度计划中获取）
        utilized_capacity = Decimal('0')
        for plan in monthly_plans:
            if machine_id in plan.get('allocated_machines', []):
                # 假设按机台数量平均分配
                machine_count = len(plan['allocated_machines'])
                allocated_quantity = Decimal(str(plan['target_quantity'])) / machine_count
                utilized_capacity += allocated_quantity
        
        remaining_capacity = max(Decimal('0'), total_monthly_capacity - utilized_capacity)
        utilization_rate = float(utilized_capacity / total_monthly_capacity) if total_monthly_capacity > 0 else 0.0
        
        # 计算效率评分
        efficiency_score = (float(practical_capacity) / float(theoretical_capacity)) * 100
        
        # 瓶颈指标
        bottleneck_indicators = []
        if utilization_rate > 0.9:
            bottleneck_indicators.append("高利用率")
        if efficiency_score < 80:
            bottleneck_indicators.append("低效率")
        if available_hours < Decimal('500'):
            bottleneck_indicators.append("工时不足")
        
        return MachineCapacity(
            machine_id=machine_id,
            machine_name=machine_name,
            product_type=product_type,
            theoretical_capacity=theoretical_capacity,
            practical_capacity=practical_capacity,
            available_hours=available_hours,
            total_monthly_capacity=total_monthly_capacity,
            utilized_capacity=utilized_capacity,
            remaining_capacity=remaining_capacity,
            utilization_rate=utilization_rate,
            efficiency_score=efficiency_score,
            bottleneck_indicators=bottleneck_indicators,
            capacity_factors=CapacityFactors(efficiency_factor=machine['efficiency_factor'])
        )
    
    def _calculate_overall_utilization(self, machine_capacities: List[MachineCapacity]) -> float:
        """计算整体利用率"""
        if not machine_capacities:
            return 0.0
        
        total_capacity = sum(mc.total_monthly_capacity for mc in machine_capacities)
        total_utilized = sum(mc.utilized_capacity for mc in machine_capacities)
        
        return float(total_utilized / total_capacity) if total_capacity > 0 else 0.0
    
    def _calculate_kpi_metrics(self, machine_capacities: List[MachineCapacity]) -> Dict[str, Any]:
        """计算KPI指标"""
        if not machine_capacities:
            return {}
        
        utilization_rates = [mc.utilization_rate for mc in machine_capacities]
        efficiency_scores = [mc.efficiency_score for mc in machine_capacities]
        
        return {
            'average_utilization_rate': sum(utilization_rates) / len(utilization_rates),
            'max_utilization_rate': max(utilization_rates),
            'min_utilization_rate': min(utilization_rates),
            'utilization_variance': self._calculate_variance(utilization_rates),
            'average_efficiency_score': sum(efficiency_scores) / len(efficiency_scores),
            'machines_over_80_utilization': len([r for r in utilization_rates if r > 0.8]),
            'machines_under_60_utilization': len([r for r in utilization_rates if r < 0.6]),
            'total_machines': len(machine_capacities),
            'bottleneck_machines': len([mc for mc in machine_capacities if mc.bottleneck_indicators])
        }
    
    def _generate_visualization_data(
        self,
        machine_capacities: List[MachineCapacity],
        bottlenecks: List[BottleneckAnalysis]
    ) -> Dict[str, Any]:
        """生成可视化数据"""
        return {
            'capacity_by_machine': [
                {
                    'machine_id': mc.machine_id,
                    'machine_name': mc.machine_name,
                    'theoretical_capacity': float(mc.theoretical_capacity * mc.available_hours),
                    'practical_capacity': float(mc.practical_capacity * mc.available_hours),
                    'utilized_capacity': float(mc.utilized_capacity),
                    'utilization_rate': mc.utilization_rate
                }
                for mc in machine_capacities
            ],
            'utilization_distribution': {
                'high_utilization': len([mc for mc in machine_capacities if mc.utilization_rate > 0.8]),
                'medium_utilization': len([mc for mc in machine_capacities if 0.6 <= mc.utilization_rate <= 0.8]),
                'low_utilization': len([mc for mc in machine_capacities if mc.utilization_rate < 0.6])
            },
            'bottleneck_severity': [
                {
                    'type': b.bottleneck_type.value,
                    'severity': b.severity_level,
                    'impact': b.impact_percentage
                }
                for b in bottlenecks
            ],
            'capacity_trends': {
                'total_theoretical': float(sum(mc.theoretical_capacity * mc.available_hours for mc in machine_capacities)),
                'total_practical': float(sum(mc.practical_capacity * mc.available_hours for mc in machine_capacities)),
                'total_utilized': float(sum(mc.utilized_capacity for mc in machine_capacities))
            }
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def _calculate_utilization_variance(self, machine_capacities: List[MachineCapacity]) -> float:
        """计算利用率方差"""
        utilization_rates = [mc.utilization_rate for mc in machine_capacities]
        return self._calculate_variance(utilization_rates)
    
    def _calculate_seasonality_factor(self, month_offset: int) -> float:
        """计算季节性因子"""
        # 简化的季节性模型，实际应用中应该基于历史数据
        # 假设第4季度需求较高，第1季度较低
        month = (month_offset - 1) % 12 + 1
        
        if month in [1, 2, 3]:  # Q1
            return 0.85
        elif month in [4, 5, 6]:  # Q2
            return 0.95
        elif month in [7, 8, 9]:  # Q3
            return 1.05
        else:  # Q4
            return 1.15
    
    def _update_performance_metrics(self, calculation_time: float):
        """更新性能指标"""
        self.performance_metrics['calculations_performed'] += 1
        current_avg = self.performance_metrics['average_calculation_time']
        count = self.performance_metrics['calculations_performed']
        self.performance_metrics['average_calculation_time'] = (
            (current_avg * (count - 1) + calculation_time) / count
        )
    
    async def _generate_optimization_recommendations(
        self,
        machine_capacities: List[MachineCapacity],
        bottlenecks: List[BottleneckAnalysis]
    ) -> List[OptimizationRecommendation]:
        """生成优化建议"""
        recommendations = []
        
        # 基于瓶颈生成建议
        for i, bottleneck in enumerate(bottlenecks):
            rec = OptimizationRecommendation(
                recommendation_id=f"REC_{i+1}",
                priority=int(bottleneck.severity_level * 10),
                category=bottleneck.bottleneck_type.value,
                description=f"解决{bottleneck.bottleneck_type.value}瓶颈: {bottleneck.root_cause}",
                expected_benefit=bottleneck.estimated_improvement,
                implementation_cost=float(bottleneck.estimated_improvement) * 0.1,
                implementation_time=30,
                roi_score=float(bottleneck.estimated_improvement) / (float(bottleneck.estimated_improvement) * 0.1),
                feasibility_score=0.8
            )
            recommendations.append(rec)
        
        return recommendations


# === CLI 支持 ===

async def main():
    """CLI主函数"""
    parser = argparse.ArgumentParser(description="月度容量计算器")
    parser.add_argument('--year', type=int, default=datetime.now().year, help='年份')
    parser.add_argument('--month', type=int, default=datetime.now().month, help='月份')
    parser.add_argument('--machines', nargs='*', help='机台ID列表')
    parser.add_argument('--products', nargs='*', help='产品类型列表')
    parser.add_argument('--method', choices=['theoretical', 'practical', 'optimized'], 
                       default='practical', help='计算方法')
    parser.add_argument('--output', default='console', choices=['console', 'json', 'file'], help='输出格式')
    parser.add_argument('--benchmark', action='store_true', help='运行性能基准测试')
    
    args = parser.parse_args()
    
    if args.benchmark:
        await run_benchmark()
        return
    
    # 创建计算器实例
    calculator = MonthlyCapacityCalculator()
    
    # 执行容量计算
    calculation_method = CapacityCalculationMethod(args.method)
    report = await calculator.calculate_monthly_capacity(
        year=args.year,
        month=args.month,
        machine_ids=args.machines,
        product_types=args.products,
        calculation_method=calculation_method
    )
    
    # 输出结果
    if args.output == 'console':
        print_report_summary(report)
    elif args.output == 'json':
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=str))
    elif args.output == 'file':
        filename = f"capacity_report_{args.year}_{args.month:02d}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2, default=str)
        print(f"报告已保存到: {filename}")


def print_report_summary(report: CapacityReport):
    """打印报告摘要"""
    print(f"\n=== 月度容量计算报告 ===")
    print(f"报告ID: {report.report_id}")
    print(f"计算时间: {report.calculation_time}")
    print(f"计算方法: {report.calculation_method.value}")
    print(f"\n=== 容量概览 ===")
    print(f"理论总容量: {report.total_theoretical_capacity:,.0f} 件")
    print(f"实际总容量: {report.total_practical_capacity:,.0f} 件")
    print(f"已利用容量: {report.total_utilized_capacity:,.0f} 件")
    print(f"整体利用率: {report.overall_utilization_rate:.1%}")
    
    print(f"\n=== 机台容量详情 ===")
    for mc in report.machine_capacities:
        print(f"{mc.machine_name} ({mc.machine_id}):")
        print(f"  产品类型: {mc.product_type}")
        print(f"  月度容量: {mc.total_monthly_capacity:,.0f} 件")
        print(f"  已利用: {mc.utilized_capacity:,.0f} 件")
        print(f"  利用率: {mc.utilization_rate:.1%}")
        print(f"  效率评分: {mc.efficiency_score:.1f}")
        if mc.bottleneck_indicators:
            print(f"  瓶颈指标: {', '.join(mc.bottleneck_indicators)}")
        print()
    
    if report.bottleneck_analyses:
        print(f"=== 瓶颈分析 ===")
        for ba in report.bottleneck_analyses:
            print(f"瓶颈类型: {ba.bottleneck_type.value}")
            print(f"严重程度: {ba.severity_level:.1%}")
            print(f"影响范围: {ba.impact_percentage:.1f}%")
            print(f"容量损失: {ba.capacity_loss:,.0f} 件")
            print(f"根本原因: {ba.root_cause}")
            print()
    
    if report.optimization_recommendations:
        print(f"=== 优化建议 ===")
        for rec in report.optimization_recommendations[:3]:  # 只显示前3条
            print(f"建议 {rec.recommendation_id}:")
            print(f"  类别: {rec.category}")
            print(f"  描述: {rec.description}")
            print(f"  预期收益: {rec.expected_benefit:,.0f} 件")
            print(f"  ROI评分: {rec.roi_score:.1f}")
            print()


async def run_benchmark():
    """运行性能基准测试"""
    print("=== 月度容量计算器性能基准测试 ===")
    
    calculator = MonthlyCapacityCalculator()
    
    # 测试不同规模的计算
    test_cases = [
        ("小规模", 2024, 1, ['JBJ001'], ['香烟']),
        ("中规模", 2024, 2, ['JBJ001', 'JBJ002'], ['香烟']),
        ("大规模", 2024, 3, None, None),
    ]
    
    for test_name, year, month, machines, products in test_cases:
        print(f"\n--- {test_name}测试 ---")
        start_time = time.time()
        
        report = await calculator.calculate_monthly_capacity(
            year=year,
            month=month,
            machine_ids=machines,
            product_types=products
        )
        
        calculation_time = time.time() - start_time
        print(f"计算时间: {calculation_time:.3f}秒")
        print(f"机台数量: {len(report.machine_capacities)}")
        print(f"瓶颈数量: {len(report.bottleneck_analyses)}")
        print(f"建议数量: {len(report.optimization_recommendations)}")
    
    # 显示整体性能指标
    metrics = calculator.get_performance_metrics()
    print(f"\n=== 整体性能指标 ===")
    print(f"总计算次数: {metrics['calculations_performed']}")
    print(f"平均计算时间: {metrics['average_calculation_time']:.3f}秒")
    print(f"缓存命中率: {metrics['cache_hit_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(main())