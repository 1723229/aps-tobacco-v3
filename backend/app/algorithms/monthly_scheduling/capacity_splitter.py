"""
产能拆分算法 (ALG-008增强版)

本模块实现智能的产能拆分逻辑：
1. ALG-008: 产能拆分算法 - 当订单超过单台机台产能时智能拆分
2. 负载均衡分配 - 确保机台间负载均衡
3. 优先级加权分配 - 基于机台性能和优先级分配
4. 动态分配调整 - 根据实际情况动态调整分配策略
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import math

from app.models.monthly_plan_models import MonthlyPlan

logger = logging.getLogger(__name__)


class MonthlyCapacitySplitter:
    """产能拆分算法 - 处理大订单分解"""
    
    def __init__(self):
        # 拆分配置
        self.split_configs = {
            "max_single_allocation_ratio": 0.80,  # 单台机台最大分配比例
            "min_split_quantity": 10,             # 最小拆分数量（箱）
            "load_balance_weight": 0.40,          # 负载均衡权重
            "performance_weight": 0.35,           # 性能权重
            "priority_weight": 0.25,              # 优先级权重
            "efficiency_threshold": 0.85          # 效率阈值
        }
    
    async def analyze_splitting_requirement(
        self,
        plan: MonthlyPlan,
        available_machines: List[Dict[str, Any]],
        work_calendar: Dict[str, Any],
        time_calculator: Any,  # MonthlyTimeCalculator实例
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]] = None
    ) -> Dict[str, Any]:
        """
        分析是否需要拆分以及拆分策略
        
        Args:
            plan: 月度计划
            available_machines: 可用机台列表
            work_calendar: 工作日历
            time_calculator: 时间计算器
            existing_allocations: 已分配时间
        
        Returns:
            拆分需求分析结果
        """
        analysis_result = {
            "needs_splitting": False,
            "splitting_reason": "",
            "recommended_strategy": "single_machine",
            "capacity_analysis": {},
            "machine_rankings": [],
            "split_recommendations": []
        }
        
        try:
            target_quantity = plan.target_quantity_boxes
            
            logger.info(f"分析产品 {plan.article_nr} 拆分需求: 目标产量 {target_quantity} 箱")
            
            if not available_machines:
                analysis_result["splitting_reason"] = "无可用机台"
                return analysis_result
            
            # 1. 计算各机台的月产能
            machine_capacities = []
            
            for machine in available_machines:
                if machine["machine_type"] != "PACKING":
                    continue  # 只考虑卷包机
                
                capacity_info = time_calculator.calculate_monthly_capacity(
                    machine["speed"], 
                    machine["efficiency_rate"], 
                    work_calendar
                )
                
                # 计算当前负载
                current_load = self._calculate_current_load(
                    machine["machine_code"], existing_allocations, work_calendar
                )
                
                machine_capacities.append({
                    "machine_code": machine["machine_code"],
                    "speed": machine["speed"],
                    "efficiency_rate": machine["efficiency_rate"],
                    "monthly_capacity": capacity_info["monthly_capacity_boxes"],
                    "available_capacity": max(0, capacity_info["monthly_capacity_boxes"] - current_load),
                    "current_load": current_load,
                    "load_ratio": current_load / capacity_info["monthly_capacity_boxes"] if capacity_info["monthly_capacity_boxes"] > 0 else 0,
                    "capacity_details": capacity_info
                })
            
            if not machine_capacities:
                analysis_result["splitting_reason"] = "无可用卷包机"
                return analysis_result
            
            # 2. 按可用产能排序
            machine_capacities.sort(key=lambda x: x["available_capacity"], reverse=True)
            analysis_result["machine_rankings"] = machine_capacities
            
            # 3. 分析是否需要拆分
            max_single_capacity = machine_capacities[0]["available_capacity"]
            total_available_capacity = sum(m["available_capacity"] for m in machine_capacities)
            
            analysis_result["capacity_analysis"] = {
                "target_quantity": target_quantity,
                "max_single_capacity": max_single_capacity,
                "total_available_capacity": total_available_capacity,
                "capacity_utilization": target_quantity / total_available_capacity if total_available_capacity > 0 else float('inf'),
                "machines_count": len(machine_capacities)
            }
            
            # 4. 决定拆分策略
            if target_quantity <= max_single_capacity * self.split_configs["max_single_allocation_ratio"]:
                # 单机台可以处理
                analysis_result["recommended_strategy"] = "single_machine"
                analysis_result["split_recommendations"] = [{
                    "machine_code": machine_capacities[0]["machine_code"],
                    "allocated_quantity": target_quantity,
                    "allocation_ratio": target_quantity / machine_capacities[0]["available_capacity"],
                    "split_reason": "单机台足够"
                }]
            elif target_quantity <= total_available_capacity:
                # 需要拆分但总产能足够
                analysis_result["needs_splitting"] = True
                analysis_result["splitting_reason"] = f"单机台产能不足 ({max_single_capacity} < {target_quantity})，需要多机台协作"
                analysis_result["recommended_strategy"] = "multi_machine_balanced"
                
                # 生成拆分建议
                analysis_result["split_recommendations"] = self._generate_split_recommendations(
                    target_quantity, machine_capacities
                )
            else:
                # 总产能不足
                analysis_result["needs_splitting"] = True
                analysis_result["splitting_reason"] = f"总产能不足 ({total_available_capacity} < {target_quantity})，需要调整计划"
                analysis_result["recommended_strategy"] = "capacity_insufficient"
                
                # 生成最大可能的分配建议
                analysis_result["split_recommendations"] = self._generate_max_allocation_recommendations(
                    machine_capacities
                )
            
            logger.info(f"产品 {plan.article_nr} 拆分分析完成: "
                       f"策略={analysis_result['recommended_strategy']}, "
                       f"需要拆分={analysis_result['needs_splitting']}")
            
        except Exception as e:
            logger.error(f"拆分需求分析失败: {str(e)}")
            analysis_result["error"] = str(e)
        
        return analysis_result
    
    async def execute_capacity_splitting(
        self,
        plan: MonthlyPlan,
        split_analysis: Dict[str, Any],
        available_machines: List[Dict[str, Any]],
        work_calendar: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        执行产能拆分
        
        Args:
            plan: 月度计划
            split_analysis: 拆分分析结果
            available_machines: 可用机台列表
            work_calendar: 工作日历
        
        Returns:
            拆分后的分配列表
        """
        split_allocations = []
        
        try:
            recommendations = split_analysis.get("split_recommendations", [])
            
            if not recommendations:
                logger.warning(f"产品 {plan.article_nr} 无拆分建议")
                return split_allocations
            
            total_allocated = 0
            
            for i, recommendation in enumerate(recommendations):
                machine_code = recommendation["machine_code"]
                allocated_quantity = recommendation["allocated_quantity"]
                
                # 查找机台详细信息
                machine_info = next(
                    (m for m in available_machines if m["machine_code"] == machine_code),
                    None
                )
                
                if not machine_info:
                    logger.warning(f"未找到机台 {machine_code} 的详细信息")
                    continue
                
                # 创建拆分分配记录
                allocation = {
                    "split_index": i + 1,
                    "machine_code": machine_code,
                    "machine_type": machine_info["machine_type"],
                    "allocated_quantity": allocated_quantity,
                    "machine_speed": machine_info["speed"],
                    "efficiency_rate": machine_info["efficiency_rate"],
                    "allocation_ratio": recommendation.get("allocation_ratio", 0),
                    "split_reason": recommendation.get("split_reason", "拆分分配"),
                    "priority_score": recommendation.get("priority_score", 0),
                    "original_plan_id": plan.monthly_plan_id,
                    "split_total": len(recommendations)
                }
                
                split_allocations.append(allocation)
                total_allocated += allocated_quantity
            
            # 验证分配总量
            if abs(total_allocated - plan.target_quantity_boxes) > 1:  # 允许1箱误差
                logger.warning(f"产品 {plan.article_nr} 分配总量不匹配: "
                              f"目标 {plan.target_quantity_boxes}, 分配 {total_allocated}")
                
                # 调整最后一个分配
                if split_allocations:
                    adjustment = plan.target_quantity_boxes - total_allocated
                    split_allocations[-1]["allocated_quantity"] += adjustment
                    split_allocations[-1]["split_reason"] += f" (调整{adjustment:+d}箱)"
            
            logger.info(f"产品 {plan.article_nr} 拆分执行完成: "
                       f"{len(split_allocations)} 个分配，总量 {total_allocated} 箱")
            
        except Exception as e:
            logger.error(f"产能拆分执行失败: {str(e)}")
        
        return split_allocations
    
    def _calculate_current_load(
        self,
        machine_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]] = None,
        work_calendar: Dict[str, Any] = None
    ) -> int:
        """计算机台当前负载（箱数）"""
        
        if not existing_allocations or machine_code not in existing_allocations:
            return 0
        
        # 简化计算：假设平均速度为7箱/小时
        average_speed = 7.0
        total_hours = 0.0
        
        for start_time, end_time in existing_allocations[machine_code]:
            duration = (end_time - start_time).total_seconds() / 3600
            total_hours += duration
        
        # 估算已分配的产量
        estimated_load = int(total_hours * average_speed)
        return estimated_load
    
    def _generate_split_recommendations(
        self,
        target_quantity: int,
        machine_capacities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成智能拆分建议"""
        
        recommendations = []
        remaining_quantity = target_quantity
        
        # 计算机台权重评分
        machine_scores = []
        for machine in machine_capacities:
            if machine["available_capacity"] <= 0:
                continue
            
            # 综合评分
            load_score = (1 - machine["load_ratio"]) * self.split_configs["load_balance_weight"]
            performance_score = (machine["speed"] / 8.0) * self.split_configs["performance_weight"]  # 标准化到8箱/小时
            efficiency_score = (machine["efficiency_rate"] / 100.0) * self.split_configs["priority_weight"]
            
            total_score = load_score + performance_score + efficiency_score
            
            machine_scores.append({
                "machine_code": machine["machine_code"],
                "available_capacity": machine["available_capacity"],
                "total_score": total_score,
                "load_ratio": machine["load_ratio"],
                "machine_info": machine
            })
        
        # 按评分排序
        machine_scores.sort(key=lambda x: x["total_score"], reverse=True)
        
        # 分配策略：优先使用高评分机台，但保持负载均衡
        for i, machine_score in enumerate(machine_scores):
            if remaining_quantity <= 0:
                break
            
            machine_info = machine_score["machine_info"]
            available_capacity = machine_score["available_capacity"]
            
            if available_capacity <= 0:
                continue
            
            # 计算分配量
            if i == len(machine_scores) - 1:
                # 最后一台机台，分配所有剩余量
                allocated = min(remaining_quantity, available_capacity)
            else:
                # 非最后一台，按比例分配，但不超过最大分配比例
                max_allocation = int(available_capacity * self.split_configs["max_single_allocation_ratio"])
                
                # 基于剩余机台数量的智能分配
                remaining_machines = len(machine_scores) - i
                average_allocation = remaining_quantity // remaining_machines
                
                allocated = min(remaining_quantity, max_allocation, average_allocation + 20)  # 增加20箱缓冲
            
            if allocated >= self.split_configs["min_split_quantity"]:
                recommendations.append({
                    "machine_code": machine_info["machine_code"],
                    "allocated_quantity": allocated,
                    "allocation_ratio": allocated / available_capacity,
                    "priority_score": machine_score["total_score"],
                    "split_reason": f"智能拆分 {i+1}/{len(machine_scores)} (评分: {machine_score['total_score']:.2f})",
                    "capacity_utilization": allocated / machine_info["monthly_capacity"]
                })
                
                remaining_quantity -= allocated
        
        # 验证和调整
        if remaining_quantity > 0:
            # 如果还有剩余，分配给评分最高的机台
            if recommendations and recommendations[0]["allocation_ratio"] < 0.95:
                additional = min(remaining_quantity, 
                               int(machine_scores[0]["available_capacity"] * 0.95) - recommendations[0]["allocated_quantity"])
                if additional > 0:
                    recommendations[0]["allocated_quantity"] += additional
                    recommendations[0]["split_reason"] += f" (+{additional}箱剩余分配)"
                    remaining_quantity -= additional
        
        return recommendations
    
    def _generate_max_allocation_recommendations(
        self,
        machine_capacities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成最大可能分配建议（产能不足时）"""
        
        recommendations = []
        
        for i, machine in enumerate(machine_capacities):
            if machine["available_capacity"] <= 0:
                continue
            
            # 使用95%的可用产能
            allocated = int(machine["available_capacity"] * 0.95)
            
            if allocated >= self.split_configs["min_split_quantity"]:
                recommendations.append({
                    "machine_code": machine["machine_code"],
                    "allocated_quantity": allocated,
                    "allocation_ratio": 0.95,
                    "priority_score": 1.0,
                    "split_reason": f"产能不足-最大分配 {i+1}",
                    "capacity_utilization": 0.95
                })
        
        return recommendations
    
    def optimize_split_balance(
        self,
        split_allocations: List[Dict[str, Any]],
        target_quantity: int,
        optimization_goal: str = "balanced"
    ) -> List[Dict[str, Any]]:
        """
        优化拆分分配的平衡性
        
        Args:
            split_allocations: 当前分配列表
            target_quantity: 目标总量
            optimization_goal: 优化目标 (balanced, performance, load_balanced)
        
        Returns:
            优化后的分配列表
        """
        if not split_allocations or len(split_allocations) <= 1:
            return split_allocations
        
        optimized_allocations = split_allocations.copy()
        
        try:
            if optimization_goal == "balanced":
                # 均衡分配：尽量让各机台分配量接近
                avg_allocation = target_quantity / len(split_allocations)
                
                for allocation in optimized_allocations:
                    # 向平均值调整，但不超过机台产能限制
                    current_qty = allocation["allocated_quantity"]
                    target_qty = int(avg_allocation)
                    
                    # 保守调整：最多调整20%
                    max_adjustment = max(10, int(current_qty * 0.2))
                    adjustment = max(-max_adjustment, min(max_adjustment, target_qty - current_qty))
                    
                    allocation["allocated_quantity"] = current_qty + adjustment
                    allocation["split_reason"] += f" (均衡调整{adjustment:+d})"
            
            elif optimization_goal == "performance":
                # 性能优化：更多分配给高性能机台
                total_speed = sum(alloc["machine_speed"] for alloc in optimized_allocations)
                
                for allocation in optimized_allocations:
                    speed_ratio = allocation["machine_speed"] / total_speed
                    target_qty = int(target_quantity * speed_ratio)
                    
                    # 渐进调整
                    current_qty = allocation["allocated_quantity"]
                    adjustment = int((target_qty - current_qty) * 0.3)  # 30%调整
                    
                    allocation["allocated_quantity"] = current_qty + adjustment
                    allocation["split_reason"] += f" (性能优化{adjustment:+d})"
            
            # 确保总量匹配
            total_allocated = sum(alloc["allocated_quantity"] for alloc in optimized_allocations)
            if total_allocated != target_quantity:
                # 调整最大分配的机台
                max_allocation = max(optimized_allocations, key=lambda x: x["allocated_quantity"])
                adjustment = target_quantity - total_allocated
                max_allocation["allocated_quantity"] += adjustment
                max_allocation["split_reason"] += f" (总量调整{adjustment:+d})"
            
            logger.debug(f"拆分优化完成: 目标={optimization_goal}, "
                        f"分配数={len(optimized_allocations)}")
            
        except Exception as e:
            logger.error(f"拆分优化失败: {str(e)}")
            return split_allocations  # 返回原始分配
        
        return optimized_allocations
    
    def validate_split_feasibility(
        self,
        split_allocations: List[Dict[str, Any]],
        machine_capacities: List[Dict[str, Any]],
        work_calendar: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证拆分方案的可行性"""
        
        validation_result = {
            "feasible": True,
            "warnings": [],
            "errors": [],
            "capacity_check": {},
            "time_estimation": {},
            "risk_assessment": {}
        }
        
        try:
            # 1. 产能验证
            for allocation in split_allocations:
                machine_code = allocation["machine_code"]
                allocated_qty = allocation["allocated_quantity"]
                
                # 查找机台产能
                machine_capacity = next(
                    (m for m in machine_capacities if m["machine_code"] == machine_code),
                    None
                )
                
                if not machine_capacity:
                    validation_result["errors"].append(
                        f"机台 {machine_code} 无产能信息"
                    )
                    validation_result["feasible"] = False
                    continue
                
                available_capacity = machine_capacity["available_capacity"]
                
                if allocated_qty > available_capacity:
                    validation_result["errors"].append(
                        f"机台 {machine_code} 分配量 {allocated_qty} 超过可用产能 {available_capacity}"
                    )
                    validation_result["feasible"] = False
                elif allocated_qty > available_capacity * 0.95:
                    validation_result["warnings"].append(
                        f"机台 {machine_code} 利用率过高 ({allocated_qty/available_capacity:.1%})"
                    )
            
            # 2. 时间估算
            total_time_hours = 0
            for allocation in split_allocations:
                machine_speed = allocation.get("machine_speed", 7.0)
                efficiency = allocation.get("efficiency_rate", 100.0) / 100.0
                
                effective_speed = machine_speed * efficiency
                time_needed = allocation["allocated_quantity"] / effective_speed
                total_time_hours += time_needed
                
                allocation["estimated_time_hours"] = time_needed
            
            validation_result["time_estimation"] = {
                "total_parallel_time": max(alloc["estimated_time_hours"] for alloc in split_allocations),
                "total_sequential_time": total_time_hours,
                "average_machine_time": total_time_hours / len(split_allocations) if split_allocations else 0
            }
            
            # 3. 风险评估
            max_utilization = max(
                alloc["allocation_ratio"] for alloc in split_allocations
            ) if split_allocations else 0
            
            avg_utilization = sum(
                alloc["allocation_ratio"] for alloc in split_allocations
            ) / len(split_allocations) if split_allocations else 0
            
            risk_level = "LOW"
            if max_utilization > 0.9:
                risk_level = "HIGH"
            elif max_utilization > 0.8 or avg_utilization > 0.7:
                risk_level = "MEDIUM"
            
            validation_result["risk_assessment"] = {
                "risk_level": risk_level,
                "max_utilization": max_utilization,
                "average_utilization": avg_utilization,
                "machines_count": len(split_allocations)
            }
            
        except Exception as e:
            logger.error(f"拆分方案验证失败: {str(e)}")
            validation_result["errors"].append(f"验证异常: {str(e)}")
            validation_result["feasible"] = False
        
        return validation_result
