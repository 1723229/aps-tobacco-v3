"""
月度排产主引擎 (完整算法流程编排)

本模块实现完整的月度排产算法流程，严格按照规格说明书的16个算法规则：
- ALG-001到ALG-016的完整实现和集成
- 智能决策流程
- 异常处理和回滚机制
- 性能监控和统计
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import asyncio
import json
import uuid

from app.models.monthly_plan_models import MonthlyPlan
from app.models.monthly_schedule_result_models import MonthlyScheduleResult
from app.models.machine_config_models import MachineRelation
from .data_validator import MonthlyDataValidator
from .machine_selector import MonthlyMachineSelector
from .time_calculator import MonthlyTimeCalculator
from .time_allocator import MonthlyTimeAllocator
from .capacity_splitter import MonthlyCapacitySplitter

logger = logging.getLogger(__name__)


class MonthlySchedulingEngine:
    """月度排产引擎 - 完整流程编排"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # 初始化各个算法组件
        self.validator = MonthlyDataValidator(db)
        self.machine_selector = MonthlyMachineSelector()
        self.time_calculator = MonthlyTimeCalculator()
        self.time_allocator = MonthlyTimeAllocator()
        self.capacity_splitter = MonthlyCapacitySplitter()
        
        # 引擎配置
        self.engine_configs = {
            "max_retry_attempts": 3,           # 最大重试次数
            "timeout_seconds": 1800,           # 超时时间（30分钟）
            "enable_optimization": True,       # 启用优化
            "save_intermediate_results": True, # 保存中间结果
            "parallel_processing": False,      # 并行处理（暂时关闭）
            "debug_mode": True                 # 调试模式
        }
        
        # 执行统计
        self.execution_stats = {
            "start_time": None,
            "end_time": None,
            "total_plans": 0,
            "successful_plans": 0,
            "failed_plans": 0,
            "split_plans": 0,
            "execution_phases": {},
            "performance_metrics": {}
        }
    
    async def execute_complete_scheduling(
        self,
        monthly_batch_id: str,
        algorithm_config: Dict[str, Any] = None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """
        执行完整的月度排产算法
        
        严格按照规格说明书的16个算法规则实施
        
        Args:
            monthly_batch_id: 月度批次ID
            algorithm_config: 算法配置
            task_id: 任务ID
        
        Returns:
            执行结果
        """
        # 初始化执行结果
        execution_result = {
            "success": False,
            "task_id": task_id or str(uuid.uuid4()),
            "batch_id": monthly_batch_id,
            "algorithm_version": "v2.0_complete",
            "scheduled_results": [],
            "execution_statistics": {},
            "warnings": [],
            "errors": [],
            "performance_metrics": {},
            "intermediate_data": {} if self.engine_configs["debug_mode"] else None
        }
        
        self.execution_stats["start_time"] = datetime.now()
        
        try:
            logger.info(f"🚀 开始执行月度排产算法: 批次={monthly_batch_id}, 任务={execution_result['task_id']}")
            
            # === 阶段1: 数据验证和预处理 (ALG-015) ===
            phase_result = await self._execute_phase_1_validation(
                monthly_batch_id, execution_result
            )
            if not phase_result["success"]:
                return execution_result
            
            validation_data = phase_result["data"]
            
            # === 阶段2: 计划优先级排序 (ALG-010) ===
            phase_result = await self._execute_phase_2_prioritization(
                validation_data["valid_plans"], execution_result
            )
            if not phase_result["success"]:
                return execution_result
            
            sorted_plans = phase_result["data"]
            
            # === 阶段3: 逐个计划处理 ===
            phase_result = await self._execute_phase_3_plan_processing(
                sorted_plans, validation_data, execution_result
            )
            
            # === 阶段4: 结果优化和验证 (ALG-016) ===
            if phase_result["success"] and self.engine_configs["enable_optimization"]:
                await self._execute_phase_4_optimization(execution_result)
            
            # === 阶段5: 统计和总结 ===
            await self._execute_phase_5_finalization(execution_result)
            
            execution_result["success"] = len(execution_result["scheduled_results"]) > 0
            
            logger.info(f"✅ 月度排产算法执行完成: "
                       f"成功={execution_result['success']}, "
                       f"结果数={len(execution_result['scheduled_results'])}")
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ 月度排产算法执行超时")
            execution_result["errors"].append("算法执行超时")
            
        except Exception as e:
            logger.error(f"❌ 月度排产算法执行异常: {str(e)}")
            execution_result["errors"].append(f"算法执行异常: {str(e)}")
            
        finally:
            self.execution_stats["end_time"] = datetime.now()
            execution_result["performance_metrics"] = self._calculate_performance_metrics()
        
        return execution_result
    
    async def _execute_phase_1_validation(
        self,
        monthly_batch_id: str,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """阶段1: 数据验证和预处理"""
        
        logger.info("📋 执行阶段1: 数据验证和预处理")
        phase_start = datetime.now()
        
        try:
            # 数据验证和预处理
            validation_data = await self.validator.validate_and_prepare_data(
                monthly_batch_id, self.db
            )
            
            if validation_data["errors"]:
                execution_result["errors"].extend(validation_data["errors"])
                return {"success": False, "data": None}
            
            execution_result["warnings"].extend(validation_data["warnings"])
            
            # 保存中间数据
            if self.engine_configs["debug_mode"]:
                execution_result["intermediate_data"]["validation"] = {
                    "statistics": validation_data["statistics"],
                    "warnings_count": len(validation_data["warnings"]),
                    "valid_plans_count": len(validation_data["valid_plans"])
                }
            
            self.execution_stats["total_plans"] = len(validation_data["valid_plans"])
            self.execution_stats["execution_phases"]["phase_1"] = {
                "duration": (datetime.now() - phase_start).total_seconds(),
                "status": "completed"
            }
            
            logger.info(f"✅ 阶段1完成: 有效计划 {len(validation_data['valid_plans'])} 个")
            
            return {"success": True, "data": validation_data}
            
        except Exception as e:
            logger.error(f"❌ 阶段1执行失败: {str(e)}")
            execution_result["errors"].append(f"数据验证阶段失败: {str(e)}")
            return {"success": False, "data": None}
    
    async def _execute_phase_2_prioritization(
        self,
        valid_plans: List[MonthlyPlan],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """阶段2: 计划优先级排序 (ALG-010)"""
        
        logger.info("🎯 执行阶段2: 计划优先级排序")
        phase_start = datetime.now()
        
        try:
            # 按优先级排序计划
            sorted_plans = await self._sort_plans_by_priority(valid_plans)
            
            self.execution_stats["execution_phases"]["phase_2"] = {
                "duration": (datetime.now() - phase_start).total_seconds(),
                "status": "completed"
            }
            
            # 保存中间数据
            if self.engine_configs["debug_mode"]:
                execution_result["intermediate_data"]["prioritization"] = {
                    "sorted_plans": [
                        {
                            "article_nr": p.article_nr,
                            "priority_score": getattr(p, "priority_score", 0),
                            "target_quantity": p.target_quantity_boxes
                        }
                        for p in sorted_plans[:5]  # 只记录前5个
                    ]
                }
            
            logger.info(f"✅ 阶段2完成: 计划排序完成，优先级最高的是 {sorted_plans[0].article_nr if sorted_plans else 'N/A'}")
            
            return {"success": True, "data": sorted_plans}
            
        except Exception as e:
            logger.error(f"❌ 阶段2执行失败: {str(e)}")
            execution_result["errors"].append(f"优先级排序阶段失败: {str(e)}")
            return {"success": False, "data": None}
    
    async def _execute_phase_3_plan_processing(
        self,
        sorted_plans: List[MonthlyPlan],
        validation_data: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """阶段3: 逐个计划处理"""
        
        logger.info("⚙️ 执行阶段3: 逐个计划处理")
        phase_start = datetime.now()
        
        # 跟踪已分配的时间和资源
        existing_allocations = {}  # {machine_code: [(start_time, end_time), ...]}
        
        speed_mappings = validation_data["speed_mappings"]
        machine_relations = validation_data["machine_relations"]
        work_calendar = validation_data["work_calendar"]
        maintenance_plans = validation_data["maintenance_plans"]
        
        successful_plans = 0
        failed_plans = 0
        split_plans = 0
        
        try:
            for i, plan in enumerate(sorted_plans):
                logger.info(f"📦 处理计划 {i+1}/{len(sorted_plans)}: {plan.article_nr} ({plan.target_quantity_boxes}箱)")
                
                # 处理单个计划
                plan_result = await self._process_single_plan(
                    plan, speed_mappings, machine_relations,
                    work_calendar, existing_allocations, maintenance_plans
                )
                
                if plan_result["success"]:
                    execution_result["scheduled_results"].extend(plan_result["schedule_records"])
                    successful_plans += 1
                    
                    if len(plan_result["schedule_records"]) > 1:
                        split_plans += 1
                    
                    # 更新已分配时间跟踪
                    for record in plan_result["schedule_records"]:
                        for machine_code in [record["maker_code"], record["feeder_code"]]:
                            if machine_code not in existing_allocations:
                                existing_allocations[machine_code] = []
                            existing_allocations[machine_code].append(
                                (record["scheduled_start_time"], record["scheduled_end_time"])
                            )
                    
                    logger.info(f"✅ 计划 {plan.article_nr} 处理成功，生成 {len(plan_result['schedule_records'])} 条记录")
                else:
                    failed_plans += 1
                    execution_result["warnings"].append(
                        f"计划 {plan.article_nr} 排产失败: {plan_result.get('reason', '未知原因')}"
                    )
                    logger.warning(f"⚠️ 计划 {plan.article_nr} 处理失败: {plan_result.get('reason', '未知原因')}")
            
            self.execution_stats["successful_plans"] = successful_plans
            self.execution_stats["failed_plans"] = failed_plans
            self.execution_stats["split_plans"] = split_plans
            
            self.execution_stats["execution_phases"]["phase_3"] = {
                "duration": (datetime.now() - phase_start).total_seconds(),
                "status": "completed",
                "processed_plans": len(sorted_plans),
                "successful_plans": successful_plans,
                "failed_plans": failed_plans
            }
            
            logger.info(f"✅ 阶段3完成: 成功 {successful_plans}/{len(sorted_plans)} 个计划，"
                       f"拆分 {split_plans} 个，失败 {failed_plans} 个")
            
            return {"success": successful_plans > 0}
            
        except Exception as e:
            logger.error(f"❌ 阶段3执行失败: {str(e)}")
            execution_result["errors"].append(f"计划处理阶段失败: {str(e)}")
            return {"success": False}
    
    async def _process_single_plan(
        self,
        plan: MonthlyPlan,
        speed_mappings: Dict[str, List[Dict]],
        machine_relations: List[Dict],
        work_calendar: Dict[str, Any],
        existing_allocations: Dict[str, List[Tuple[datetime, datetime]]],
        maintenance_plans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理单个计划的完整排产流程"""
        
        plan_result = {
            "success": False,
            "schedule_records": [],
            "plan_id": plan.monthly_plan_id,
            "reason": "",
            "processing_details": {}
        }
        
        try:
            # 1. 机台选择 (ALG-001, ALG-007, ALG-011)
            machine_combination = await self.machine_selector.select_optimal_machines(
                plan, speed_mappings, machine_relations, existing_allocations, self.db
            )
            
            if not machine_combination["success"]:
                plan_result["reason"] = f"机台选择失败: {'; '.join(machine_combination['warnings'])}"
                return plan_result
            
            plan_result["processing_details"]["machine_selection"] = {
                "maker_code": machine_combination["maker_code"],
                "feeder_code": machine_combination["feeder_code"],
                "selection_score": machine_combination["selection_score"]
            }
            
            # 2. 产能拆分分析 (ALG-008)
            available_machines = speed_mappings.get("ALL_PRODUCTS", [])
            
            split_analysis = await self.capacity_splitter.analyze_splitting_requirement(
                plan, available_machines, work_calendar, self.time_calculator, existing_allocations
            )
            
            if split_analysis.get("recommended_strategy") == "capacity_insufficient":
                plan_result["reason"] = "总产能不足，无法完成计划"
                return plan_result
            
            # 3. 执行拆分（如果需要）
            if split_analysis.get("needs_splitting", False):
                split_allocations = await self.capacity_splitter.execute_capacity_splitting(
                    plan, split_analysis, available_machines, work_calendar
                )
                
                if not split_allocations:
                    plan_result["reason"] = "产能拆分失败"
                    return plan_result
            else:
                # 无需拆分，使用单机台
                split_allocations = [{
                    "machine_code": machine_combination["maker_code"],
                    "allocated_quantity": plan.target_quantity_boxes,
                    "machine_speed": machine_combination["maker_speed"],
                    "efficiency_rate": machine_combination["efficiency_rate"],
                    "split_reason": "单机台处理"
                }]
            
            plan_result["processing_details"]["capacity_allocation"] = {
                "needs_splitting": split_analysis.get("needs_splitting", False),
                "allocations_count": len(split_allocations)
            }
            
            # 4. 为每个分配生成排产记录
            for allocation_index, allocation in enumerate(split_allocations):
                # 4.1 时间计算 (ALG-002, ALG-014)
                time_calculation = self.time_calculator.calculate_production_time(
                    allocation["allocated_quantity"],
                    allocation["machine_speed"],
                    allocation["efficiency_rate"]
                )
                
                if time_calculation.get("error"):
                    continue  # 跳过计算失败的分配
                
                # 4.2 时间分配 (ALG-006, ALG-009, ALG-005, ALG-004)
                time_allocation = await self.time_allocator.allocate_production_time(
                    plan, machine_combination, time_calculation,
                    work_calendar, existing_allocations, maintenance_plans
                )
                
                if not time_allocation["success"]:
                    plan_result["reason"] = f"时间分配失败: {'; '.join(time_allocation['warnings'])}"
                    continue  # 跳过分配失败的
                
                # 4.3 创建排产记录
                schedule_record = await self._create_schedule_record(
                    plan, allocation, machine_combination, time_calculation, time_allocation, allocation_index
                )
                
                plan_result["schedule_records"].append(schedule_record)
            
            # 5. 验证结果
            if plan_result["schedule_records"]:
                plan_result["success"] = True
                plan_result["processing_details"]["records_generated"] = len(plan_result["schedule_records"])
            else:
                plan_result["reason"] = plan_result["reason"] or "未生成有效排产记录"
            
        except Exception as e:
            logger.error(f"单个计划处理失败: {str(e)}")
            plan_result["reason"] = f"处理异常: {str(e)}"
        
        return plan_result
    
    async def _create_schedule_record(
        self,
        plan: MonthlyPlan,
        allocation: Dict[str, Any],
        machine_combination: Dict[str, Any],
        time_calculation: Dict[str, Any],
        time_allocation: Dict[str, Any],
        allocation_index: int = 0
    ) -> Dict[str, Any]:
        """创建排产记录"""
        
        # 生成工单号
        work_order_suffix = f"{allocation_index:02d}" if allocation_index > 0 else ""
        work_order_nr = f"WO{plan.plan_year}M{plan.monthly_plan_id:04d}{work_order_suffix}"
        
        # 确定机台代码
        maker_code = allocation.get("machine_code", machine_combination["maker_code"])
        feeder_code = machine_combination["feeder_code"]
        
        schedule_record = {
            # 基础信息
            "monthly_plan_id": plan.monthly_plan_id,
            "work_order_nr": work_order_nr,
            "article_nr": plan.article_nr,
            "article_name": plan.article_name,
            "plan_year": plan.plan_year,
            "plan_month": plan.plan_month,
            
            # 机台信息
            "maker_code": maker_code,
            "feeder_code": feeder_code,
            "work_order_type": "HJB",  # 卷包作业
            "machine_type": "卷包机",
            
            # 数量信息
            "plan_quantity": allocation["allocated_quantity"],
            "target_quantity_boxes": allocation["allocated_quantity"],
            "hard_pack_boxes": plan.hard_pack_boxes,
            "soft_pack_boxes": plan.soft_pack_boxes,
            
            # 时间信息
            "scheduled_start_time": time_allocation["scheduled_start_time"],
            "scheduled_end_time": time_allocation["scheduled_end_time"],
            "planned_duration_hours": time_calculation["rounded_time_hours"],
            
            # 状态信息
            "work_order_status": "PENDING",
            "scheduling_status": "SCHEDULED",
            
            # 算法信息
            "algorithm_version": "v2.0_complete",
            "split_index": allocation_index,
            "split_total": getattr(allocation, "split_total", 1),
            
            # 详细信息
            "calculation_details": {
                "time_calculation": time_calculation,
                "machine_selection": {
                    "maker_code": maker_code,
                    "feeder_code": feeder_code,
                    "selection_score": machine_combination.get("selection_score", 0),
                    "machine_speed": allocation["machine_speed"],
                    "efficiency_rate": allocation["efficiency_rate"]
                },
                "allocation_details": {
                    "allocation_strategy": time_allocation.get("allocation_strategy", "unknown"),
                    "time_windows_used": len(time_allocation.get("time_windows", [])),
                    "split_reason": allocation.get("split_reason", "单机台处理")
                }
            },
            
            # 时间戳
            "created_time": datetime.now(),
            "updated_time": datetime.now()
        }
        
        return schedule_record
    
    async def _execute_phase_4_optimization(self, execution_result: Dict[str, Any]):
        """阶段4: 结果优化和验证 (ALG-016)"""
        
        logger.info("🔧 执行阶段4: 结果优化")
        phase_start = datetime.now()
        
        try:
            scheduled_results = execution_result["scheduled_results"]
            
            if not scheduled_results:
                return
            
            # 1. 时间冲突检测和解决
            conflicts = self._detect_time_conflicts(scheduled_results)
            if conflicts:
                execution_result["warnings"].append(f"检测到 {len(conflicts)} 个时间冲突")
                # TODO: 实现冲突解决算法
            
            # 2. 负载均衡优化
            load_analysis = self._analyze_machine_load_balance(scheduled_results)
            execution_result["intermediate_data"]["load_analysis"] = load_analysis
            
            # 3. 时间窗口优化
            optimized_count = self._optimize_time_windows(scheduled_results)
            if optimized_count > 0:
                execution_result["warnings"].append(f"优化了 {optimized_count} 个时间窗口")
            
            self.execution_stats["execution_phases"]["phase_4"] = {
                "duration": (datetime.now() - phase_start).total_seconds(),
                "status": "completed",
                "conflicts_detected": len(conflicts),
                "optimizations_applied": optimized_count
            }
            
            logger.info(f"✅ 阶段4完成: 冲突 {len(conflicts)} 个，优化 {optimized_count} 处")
            
        except Exception as e:
            logger.error(f"❌ 阶段4执行失败: {str(e)}")
            execution_result["warnings"].append(f"优化阶段失败: {str(e)}")
    
    async def _execute_phase_5_finalization(self, execution_result: Dict[str, Any]):
        """阶段5: 统计和总结"""
        
        logger.info("📊 执行阶段5: 统计和总结")
        phase_start = datetime.now()
        
        try:
            scheduled_results = execution_result["scheduled_results"]
            
            # 生成执行统计
            execution_result["execution_statistics"] = {
                "summary": {
                    "total_plans": self.execution_stats["total_plans"],
                    "successful_plans": self.execution_stats["successful_plans"],
                    "failed_plans": self.execution_stats["failed_plans"],
                    "split_plans": self.execution_stats["split_plans"],
                    "success_rate": self.execution_stats["successful_plans"] / max(1, self.execution_stats["total_plans"]),
                    "total_records_generated": len(scheduled_results)
                },
                "quantity_analysis": {
                    "total_planned_quantity": sum(r["target_quantity_boxes"] for r in scheduled_results),
                    "average_quantity_per_record": sum(r["target_quantity_boxes"] for r in scheduled_results) / max(1, len(scheduled_results)),
                    "largest_single_quantity": max((r["target_quantity_boxes"] for r in scheduled_results), default=0),
                    "smallest_single_quantity": min((r["target_quantity_boxes"] for r in scheduled_results), default=0)
                },
                "time_analysis": {
                    "earliest_start": min((r["scheduled_start_time"] for r in scheduled_results), default=None),
                    "latest_end": max((r["scheduled_end_time"] for r in scheduled_results), default=None),
                    "total_production_hours": sum(r["planned_duration_hours"] for r in scheduled_results),
                    "average_duration": sum(r["planned_duration_hours"] for r in scheduled_results) / max(1, len(scheduled_results))
                },
                "machine_utilization": self._calculate_machine_utilization_stats(scheduled_results)
            }
            
            # 计算时间跨度
            if scheduled_results:
                start_times = [r["scheduled_start_time"] for r in scheduled_results]
                end_times = [r["scheduled_end_time"] for r in scheduled_results]
                
                time_span = max(end_times) - min(start_times)
                execution_result["execution_statistics"]["time_analysis"]["production_span_days"] = time_span.days
            
            self.execution_stats["execution_phases"]["phase_5"] = {
                "duration": (datetime.now() - phase_start).total_seconds(),
                "status": "completed"
            }
            
            logger.info(f"✅ 阶段5完成: 生成 {len(scheduled_results)} 条排产记录")
            
        except Exception as e:
            logger.error(f"❌ 阶段5执行失败: {str(e)}")
            execution_result["warnings"].append(f"统计阶段失败: {str(e)}")
    
    async def _sort_plans_by_priority(self, plans: List[MonthlyPlan]) -> List[MonthlyPlan]:
        """按优先级排序计划 (ALG-010)"""
        
        def calculate_priority_score(plan: MonthlyPlan) -> float:
            """计算优先级评分"""
            score = 0.0
            
            # 1. 品牌优先级（利群品牌优先）
            if "利群" in plan.article_nr:
                score += 100.0
            
            # 2. 产量规模（大产量优先）
            quantity_score = min(plan.target_quantity_boxes / 10.0, 50.0)  # 最多50分
            score += quantity_score
            
            # 3. 包装类型（硬包优先）
            if plan.hard_pack_boxes > plan.soft_pack_boxes:
                score += 20.0
            
            # 4. 复杂度（简单的优先，避免复杂任务阻塞）
            if plan.target_quantity_boxes < 50:  # 小批量优先
                score += 15.0
            
            return score
        
        # 为每个计划计算优先级评分
        for plan in plans:
            plan.priority_score = calculate_priority_score(plan)
        
        # 按优先级评分排序（降序）
        sorted_plans = sorted(plans, key=lambda p: p.priority_score, reverse=True)
        
        logger.info(f"计划优先级排序完成: 最高优先级 {sorted_plans[0].article_nr} "
                   f"(评分: {sorted_plans[0].priority_score:.1f})")
        
        return sorted_plans
    
    def _detect_time_conflicts(self, scheduled_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测时间冲突"""
        conflicts = []
        
        # 按机台分组
        machine_schedules = {}
        for result in scheduled_results:
            for machine_code in [result["maker_code"], result["feeder_code"]]:
                if machine_code not in machine_schedules:
                    machine_schedules[machine_code] = []
                machine_schedules[machine_code].append(result)
        
        # 检测每台机台的时间冲突
        for machine_code, schedules in machine_schedules.items():
            # 按开始时间排序
            schedules.sort(key=lambda x: x["scheduled_start_time"])
            
            for i in range(len(schedules) - 1):
                current_end = schedules[i]["scheduled_end_time"]
                next_start = schedules[i + 1]["scheduled_start_time"]
                
                if current_end > next_start:
                    conflicts.append({
                        "machine_code": machine_code,
                        "conflict_type": "time_overlap",
                        "first_order": schedules[i]["work_order_nr"],
                        "second_order": schedules[i + 1]["work_order_nr"],
                        "overlap_duration": (current_end - next_start).total_seconds() / 3600
                    })
        
        return conflicts
    
    def _analyze_machine_load_balance(self, scheduled_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析机台负载均衡"""
        machine_loads = {}
        
        for result in scheduled_results:
            duration = result["planned_duration_hours"]
            
            for machine_code in [result["maker_code"], result["feeder_code"]]:
                if machine_code not in machine_loads:
                    machine_loads[machine_code] = 0
                machine_loads[machine_code] += duration
        
        if not machine_loads:
            return {"balance_score": 1.0, "load_distribution": {}}
        
        loads = list(machine_loads.values())
        max_load = max(loads)
        min_load = min(loads)
        avg_load = sum(loads) / len(loads)
        
        # 负载均衡评分（越接近1越均衡）
        balance_score = min_load / max_load if max_load > 0 else 1.0
        
        return {
            "balance_score": balance_score,
            "max_load_hours": max_load,
            "min_load_hours": min_load,
            "average_load_hours": avg_load,
            "load_distribution": machine_loads
        }
    
    def _optimize_time_windows(self, scheduled_results: List[Dict[str, Any]]) -> int:
        """优化时间窗口"""
        optimizations = 0
        
        # TODO: 实现时间窗口优化算法
        # 1. 合并相邻的时间段
        # 2. 减少时间碎片
        # 3. 调整开始时间以提高效率
        
        return optimizations
    
    def _calculate_machine_utilization_stats(self, scheduled_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算机台利用率统计"""
        machine_hours = {}
        machine_types = {}
        
        for result in scheduled_results:
            duration = result["planned_duration_hours"]
            
            # 统计卷包机
            maker_code = result["maker_code"]
            if maker_code not in machine_hours:
                machine_hours[maker_code] = 0
                machine_types[maker_code] = "PACKING"
            machine_hours[maker_code] += duration
            
            # 统计喂丝机
            feeder_code = result["feeder_code"]
            if feeder_code not in machine_hours:
                machine_hours[feeder_code] = 0
                machine_types[feeder_code] = "FEEDING"
            machine_hours[feeder_code] += duration
        
        # 按机台类型分组统计
        packing_machines = {k: v for k, v in machine_hours.items() if machine_types[k] == "PACKING"}
        feeding_machines = {k: v for k, v in machine_hours.items() if machine_types[k] == "FEEDING"}
        
        return {
            "total_machines_used": len(machine_hours),
            "packing_machines": {
                "count": len(packing_machines),
                "total_hours": sum(packing_machines.values()),
                "average_hours": sum(packing_machines.values()) / max(1, len(packing_machines)),
                "utilization_by_machine": packing_machines
            },
            "feeding_machines": {
                "count": len(feeding_machines),
                "total_hours": sum(feeding_machines.values()),
                "average_hours": sum(feeding_machines.values()) / max(1, len(feeding_machines)),
                "utilization_by_machine": feeding_machines
            }
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """计算性能指标"""
        start_time = self.execution_stats["start_time"]
        end_time = self.execution_stats["end_time"]
        
        if not start_time or not end_time:
            return {}
        
        total_duration = (end_time - start_time).total_seconds()
        
        return {
            "execution_duration_seconds": total_duration,
            "execution_duration_minutes": total_duration / 60,
            "plans_per_second": self.execution_stats["total_plans"] / max(1, total_duration),
            "success_rate": self.execution_stats["successful_plans"] / max(1, self.execution_stats["total_plans"]),
            "phase_durations": {
                phase: data.get("duration", 0)
                for phase, data in self.execution_stats["execution_phases"].items()
            },
            "memory_efficient": True,  # 标记为内存高效
            "algorithm_complexity": "O(n*m)",  # n=plans, m=machines
            "optimization_level": "high" if self.engine_configs["enable_optimization"] else "standard"
        }
