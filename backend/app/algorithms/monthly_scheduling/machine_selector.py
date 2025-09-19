"""
智能机台选择算法 (ALG-001, ALG-007, ALG-011增强版)

本模块实现智能的机台选择逻辑：
1. ALG-001: 根据产品规格匹配最优机台
2. ALG-007: 负载均衡，优先选择空闲机台
3. ALG-011: 机台关系约束，确保喂丝机-卷包机配对
4. 综合评分机制，选择最优机台组合
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import math

from app.models.monthly_plan_models import MonthlyPlan

logger = logging.getLogger(__name__)


class MonthlyMachineSelector:
    """智能机台选择算法 - 处理复杂的机台分配"""
    
    def __init__(self):
        # 机台选择权重配置
        self.selection_weights = {
            "speed": 0.25,          # 机台速度权重 25%
            "load_balance": 0.35,   # 负载均衡权重 35%
            "efficiency": 0.20,     # 效率权重 20%
            "product_match": 0.10,  # 产品适配性权重 10%
            "relation_priority": 0.10  # 关系优先级权重 10%
        }
    
    async def select_optimal_machines(
        self,
        plan: MonthlyPlan,
        speed_mappings: Dict[str, List[Dict]],
        machine_relations: List[Dict],
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        选择最优机台组合
        
        Args:
            plan: 月度计划
            speed_mappings: 速度映射表
            machine_relations: 机台关系配置
            existing_allocations: 已分配时间跟踪
            db: 数据库会话
            
        Returns:
            机台选择结果
        """
        selection_result = {
            "success": False,
            "maker_code": None,
            "feeder_code": None,
            "maker_speed": 0.0,
            "efficiency_rate": 100.0,
            "selection_score": 0.0,
            "selection_reasons": [],
            "alternative_options": [],
            "warnings": []
        }
        
        try:
            logger.info(f"开始为产品 {plan.article_nr} 选择机台组合")
            
            # 1. 获取该产品可用的机台配置
            available_machines = self._get_available_machines_for_product(
                getattr(plan, 'standardized_article_nr', plan.article_nr),
                speed_mappings
            )
            
            if not available_machines:
                selection_result["warnings"].append(f"产品 {plan.article_nr} 无可用机台配置")
                return selection_result
            
            # 2. 筛选卷包机（用于生产）
            packing_machines = [
                m for m in available_machines 
                if m["machine_type"] == "PACKING"
            ]
            
            if not packing_machines:
                selection_result["warnings"].append(f"产品 {plan.article_nr} 无可用卷包机")
                return selection_result
            
            # 3. 为每个卷包机评估选择分数
            machine_evaluations = []
            
            for packing_machine in packing_machines:
                evaluation = await self._evaluate_machine_combination(
                    packing_machine, plan, machine_relations, existing_allocations
                )
                
                if evaluation["success"]:
                    machine_evaluations.append(evaluation)
            
            if not machine_evaluations:
                selection_result["warnings"].append(f"产品 {plan.article_nr} 无可用机台组合")
                return selection_result
            
            # 4. 按评分排序，选择最优组合
            machine_evaluations.sort(key=lambda x: x["total_score"], reverse=True)
            
            best_evaluation = machine_evaluations[0]
            selection_result.update({
                "success": True,
                "maker_code": best_evaluation["maker_code"],
                "feeder_code": best_evaluation["feeder_code"],
                "maker_speed": best_evaluation["maker_speed"],
                "efficiency_rate": best_evaluation["efficiency_rate"],
                "selection_score": best_evaluation["total_score"],
                "selection_reasons": best_evaluation["score_breakdown"],
                "alternative_options": machine_evaluations[1:3] if len(machine_evaluations) > 1 else []
            })
            
            logger.info(f"产品 {plan.article_nr} 选择机台组合: "
                       f"{selection_result['maker_code']}-{selection_result['feeder_code']}, "
                       f"评分: {selection_result['selection_score']:.2f}")
            
        except Exception as e:
            logger.error(f"机台选择失败: {str(e)}")
            selection_result["warnings"].append(f"机台选择异常: {str(e)}")
        
        return selection_result
    
    def _get_available_machines_for_product(
        self, 
        standardized_article_nr: str,
        speed_mappings: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """获取产品可用的机台配置"""
        
        # 1. 首先查找特定产品配置
        specific_configs = speed_mappings.get("SPECIFIC", {}).get(standardized_article_nr, [])
        
        if specific_configs:
            logger.debug(f"产品 {standardized_article_nr} 使用特定配置: {len(specific_configs)} 个机台")
            return specific_configs
        
        # 2. 回退到通配符配置
        general_configs = speed_mappings.get("ALL_PRODUCTS", [])
        
        if general_configs:
            logger.debug(f"产品 {standardized_article_nr} 使用通配符配置: {len(general_configs)} 个机台")
            return general_configs
        
        return []
    
    async def _evaluate_machine_combination(
        self,
        packing_machine: Dict[str, Any],
        plan: MonthlyPlan,
        machine_relations: List[Dict],
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]]
    ) -> Dict[str, Any]:
        """评估机台组合的适用性"""
        
        evaluation = {
            "success": False,
            "maker_code": packing_machine["machine_code"],
            "feeder_code": None,
            "maker_speed": packing_machine["speed"],
            "efficiency_rate": packing_machine["efficiency_rate"],
            "total_score": 0.0,
            "score_breakdown": {},
            "warnings": []
        }
        
        try:
            # 1. 查找配对的喂丝机（ALG-011: 机台关系约束）
            feeder_info = self._find_paired_feeder(packing_machine["machine_code"], machine_relations)
            
            if not feeder_info:
                evaluation["warnings"].append(f"卷包机 {packing_machine['machine_code']} 无配对喂丝机")
                return evaluation
            
            evaluation["feeder_code"] = feeder_info["feeder_code"]
            
            # 2. 计算各项评分
            scores = {}
            
            # 2.1 速度评分 (ALG-001: 机台选择算法)
            scores["speed"] = self._calculate_speed_score(packing_machine["speed"])
            
            # 2.2 负载均衡评分 (ALG-007: 负载均衡算法)
            scores["load_balance"] = self._calculate_load_balance_score(
                packing_machine["machine_code"], feeder_info["feeder_code"], existing_allocations
            )
            
            # 2.3 效率评分
            scores["efficiency"] = self._calculate_efficiency_score(packing_machine["efficiency_rate"])
            
            # 2.4 产品适配性评分
            scores["product_match"] = self._calculate_product_match_score(
                plan, packing_machine
            )
            
            # 2.5 关系优先级评分
            scores["relation_priority"] = self._calculate_relation_priority_score(feeder_info)
            
            # 3. 计算加权总分
            total_score = sum(
                scores[key] * self.selection_weights[key] 
                for key in scores.keys()
            )
            
            evaluation.update({
                "success": True,
                "total_score": total_score,
                "score_breakdown": scores
            })
            
        except Exception as e:
            evaluation["warnings"].append(f"机台组合评估失败: {str(e)}")
        
        return evaluation
    
    def _find_paired_feeder(
        self, 
        maker_code: str, 
        machine_relations: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """查找与卷包机配对的喂丝机"""
        
        # 按优先级排序查找
        sorted_relations = sorted(
            machine_relations, 
            key=lambda x: x.get("priority", 999)
        )
        
        for relation in sorted_relations:
            if relation["maker_code"] == maker_code:
                return {
                    "feeder_code": relation["feeder_code"],
                    "relation_type": relation["relation_type"],
                    "priority": relation["priority"]
                }
        
        return None
    
    def _calculate_speed_score(self, speed: float) -> float:
        """
        计算速度评分 (0-10分)
        
        速度越高分数越高，基于当前系统的速度范围 6.1-7.15
        """
        # 基于实际数据范围标准化
        min_speed = 6.0
        max_speed = 8.0
        
        # 线性标准化到 0-10 分
        normalized_score = ((speed - min_speed) / (max_speed - min_speed)) * 10
        return max(0, min(10, normalized_score))
    
    def _calculate_load_balance_score(
        self,
        maker_code: str,
        feeder_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]]
    ) -> float:
        """
        计算负载均衡评分 (0-10分)
        
        负载越低分数越高，促进机台负载均衡
        """
        # 计算机台当前负载
        maker_load = self._calculate_machine_load(maker_code, existing_allocations)
        feeder_load = self._calculate_machine_load(feeder_code, existing_allocations)
        
        # 总负载（小时）
        total_load = maker_load + feeder_load
        
        # 假设月最大负载为 300小时 (约17小时/天 * 22天)
        max_monthly_load = 300.0
        
        # 负载评分：负载越低分数越高
        load_ratio = min(total_load / max_monthly_load, 1.0)
        score = (1.0 - load_ratio) * 10
        
        return max(0, score)
    
    def _calculate_machine_load(
        self, 
        machine_code: str, 
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]]
    ) -> float:
        """计算机台当前负载（小时数）"""
        if machine_code not in existing_allocations:
            return 0.0
        
        total_hours = 0.0
        for start_time, end_time in existing_allocations[machine_code]:
            duration = (end_time - start_time).total_seconds() / 3600
            total_hours += duration
        
        return total_hours
    
    def _calculate_efficiency_score(self, efficiency_rate: float) -> float:
        """
        计算效率评分 (0-10分)
        
        效率率越高分数越高
        """
        # 效率率通常在 80-100% 之间
        return min(efficiency_rate / 10.0, 10.0)
    
    def _calculate_product_match_score(
        self, 
        plan: MonthlyPlan, 
        machine_config: Dict[str, Any]
    ) -> float:
        """
        计算产品适配性评分 (0-10分)
        
        考虑产品特性与机台的匹配度
        """
        score = 5.0  # 基础分
        
        # 1. 利群品牌加分
        if "利群" in plan.article_nr:
            score += 2.0
        
        # 2. 特定产品配置加分
        if machine_config.get("article_nr") != "*":
            score += 2.0
        
        # 3. 产量规模适配性
        if plan.target_quantity_boxes > 100:  # 大批量生产
            if machine_config["speed"] > 7.0:  # 高速机台适合大批量
                score += 1.0
        elif plan.target_quantity_boxes < 20:  # 小批量生产
            if machine_config["speed"] < 6.5:  # 低速机台适合小批量
                score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_relation_priority_score(self, feeder_info: Dict[str, Any]) -> float:
        """
        计算关系优先级评分 (0-10分)
        
        优先级越高分数越高
        """
        priority = feeder_info.get("priority", 999)
        
        # 优先级1最高，分数10分；优先级越大分数越低
        if priority == 1:
            return 10.0
        elif priority <= 3:
            return 8.0
        elif priority <= 5:
            return 6.0
        else:
            return 4.0
    
    def get_machine_capacity_utilization(
        self,
        machine_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        total_work_hours: float
    ) -> float:
        """
        计算机台产能利用率
        
        Args:
            machine_code: 机台代码
            existing_allocations: 已分配时间
            total_work_hours: 月总工作时间
            
        Returns:
            利用率 (0.0-1.0)
        """
        used_hours = self._calculate_machine_load(machine_code, existing_allocations)
        return min(used_hours / total_work_hours, 1.0) if total_work_hours > 0 else 0.0
    
    def get_available_time_windows(
        self,
        machine_code: str,
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        work_calendar: Dict[str, Any]
    ) -> List[Tuple[datetime, datetime]]:
        """
        获取机台可用时间窗口
        
        Args:
            machine_code: 机台代码
            existing_allocations: 已分配时间
            work_calendar: 工作日历
            
        Returns:
            可用时间窗口列表
        """
        available_windows = []
        
        if machine_code not in existing_allocations:
            # 机台完全空闲，返回所有工作时间
            for day in work_calendar.get("calendar", []):
                if day["is_working"]:
                    for shift in day["shifts"]:
                        start_time = datetime.combine(day["date"], datetime.strptime(shift["start"], "%H:%M").time())
                        
                        # 处理跨日班次
                        if shift["end"] == "00:00":
                            end_time = datetime.combine(day["date"] + timedelta(days=1), datetime.strptime("00:00", "%H:%M").time())
                        else:
                            end_time = datetime.combine(day["date"], datetime.strptime(shift["end"], "%H:%M").time())
                        
                        available_windows.append((start_time, end_time))
            
            return available_windows
        
        # TODO: 实现复杂的时间窗口计算，考虑已分配时间的间隙
        # 这里先返回简化结果
        return available_windows
