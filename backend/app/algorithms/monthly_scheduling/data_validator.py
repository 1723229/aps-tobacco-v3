"""
月度数据验证和预处理算法 (ALG-015增强版)

本模块实现完整的数据验证和预处理逻辑，解决实际数据库中发现的问题：
1. 速度配置通配符匹配处理
2. 工作日历缺失的自动生成
3. 维护计划空表的处理
4. 产品规格标准化
5. 数据完整性检查
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import calendar

from app.models.monthly_plan_models import MonthlyPlan
from app.models.base_models import Machine
from app.models.machine_config_models import MachineSpeed, MachineRelation, MaintenancePlan

logger = logging.getLogger(__name__)


class MonthlyDataValidator:
    """月度数据验证器 - 处理数据质量问题"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.standardization_rules = {
            "利群(软长嘴英文)": "利群_软长嘴英文",
            "利群(软长嘴国际版)": "利群_软长嘴国际版", 
            "利群(硬红)": "利群_硬红",
            "利群(软红)": "利群_软红",
            "利群(新版)": "利群_新版",
            "利群(阳光)": "利群_阳光"
        }
    
    async def validate_and_prepare_data(
        self, 
        monthly_batch_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        全面的数据验证和预处理
        
        处理发现的数据质量问题：
        1. 速度配置通配符匹配
        2. 工作日历缺失的处理
        3. 维护计划空表的处理
        4. 产品规格标准化
        
        Args:
            monthly_batch_id: 月度批次ID
            db: 数据库会话
            
        Returns:
            验证和预处理结果
        """
        validation_result = {
            "valid_plans": [],
            "speed_mappings": {},
            "work_calendar": {},
            "machine_relations": [],
            "maintenance_plans": [],
            "warnings": [],
            "errors": [],
            "statistics": {}
        }
        
        try:
            # 1. 获取并验证月度计划数据
            logger.info(f"开始验证月度批次数据: {monthly_batch_id}")
            
            plans_query = select(MonthlyPlan).where(
                MonthlyPlan.monthly_batch_id == monthly_batch_id
            )
            plans_result = await db.execute(plans_query)
            plans = plans_result.scalars().all()
            
            if not plans:
                validation_result["errors"].append(f"批次 {monthly_batch_id} 无计划数据")
                return validation_result
            
            # 2. 验证和标准化产品规格
            valid_plans = []
            for plan in plans:
                if await self._validate_single_plan(plan, validation_result):
                    # 标准化产品规格
                    plan.standardized_article_nr = self._standardize_article_nr(plan.article_nr)
                    valid_plans.append(plan)
            
            validation_result["valid_plans"] = valid_plans
            
            # 3. 构建速度映射表（处理通配符问题）
            validation_result["speed_mappings"] = await self._build_speed_mappings(db)
            
            # 4. 获取机台关系配置
            validation_result["machine_relations"] = await self._get_machine_relations(db)
            
            # 5. 生成工作日历（处理缺失问题）
            if valid_plans:
                first_plan = valid_plans[0]
                validation_result["work_calendar"] = await self._generate_work_calendar(
                    first_plan.plan_year, first_plan.plan_month, db
                )
            
            # 6. 获取维护计划（处理空表）
            validation_result["maintenance_plans"] = await self._get_maintenance_plans(db)
            
            # 7. 生成统计信息
            validation_result["statistics"] = {
                "total_plans": len(plans),
                "valid_plans": len(valid_plans),
                "invalid_plans": len(plans) - len(valid_plans),
                "validation_rate": len(valid_plans) / len(plans) if plans else 0,
                "total_quantity": sum(p.target_quantity_boxes for p in valid_plans),
                "plan_year": valid_plans[0].plan_year if valid_plans else None,
                "plan_month": valid_plans[0].plan_month if valid_plans else None
            }
            
            logger.info(f"数据验证完成: {validation_result['statistics']}")
            
        except Exception as e:
            logger.error(f"数据验证失败: {str(e)}")
            validation_result["errors"].append(f"数据验证异常: {str(e)}")
        
        return validation_result
    
    async def _validate_single_plan(
        self, 
        plan: MonthlyPlan, 
        validation_result: Dict[str, Any]
    ) -> bool:
        """验证单个计划的有效性"""
        
        # 1. 检查目标产量
        if plan.target_quantity_boxes is None or plan.target_quantity_boxes <= 0:
            validation_result["warnings"].append(
                f"产品 {plan.article_nr} 目标产量无效: {plan.target_quantity_boxes}，已跳过"
            )
            return False
        
        # 2. 检查产品规格
        if not plan.article_nr or plan.article_nr.strip() == "":
            validation_result["warnings"].append(
                f"计划ID {plan.monthly_plan_id} 产品规格为空，已跳过"
            )
            return False
        
        # 3. 检查计划年月
        if not plan.plan_year or not plan.plan_month:
            validation_result["warnings"].append(
                f"产品 {plan.article_nr} 计划年月无效，已跳过"
            )
            return False
        
        # 4. 检查是否为合计行
        clean_article = plan.article_nr.replace(' ', '').replace('\t', '').replace('\u3000', '')
        if "合计" in clean_article or "总计" in clean_article:
            validation_result["warnings"].append(
                f"跳过合计行: {plan.article_nr}"
            )
            return False
        
        return True
    
    def _standardize_article_nr(self, article_nr: str) -> str:
        """
        标准化产品规格名称
        处理Excel中的不规范命名
        """
        # 应用预定义的标准化规则
        if article_nr in self.standardization_rules:
            return self.standardization_rules[article_nr]
        
        # 通用标准化处理
        standardized = article_nr.replace("(", "_").replace(")", "")
        standardized = standardized.replace("（", "_").replace("）", "")
        standardized = standardized.strip()
        
        return standardized
    
    async def _build_speed_mappings(self, db: AsyncSession) -> Dict[str, List[Dict]]:
        """
        构建速度映射表，处理通配符"*"问题
        为每个产品找到可用的机台和速度
        """
        try:
            # 获取所有活跃的速度配置
            speed_query = select(MachineSpeed).where(
                and_(
                    MachineSpeed.status == 'ACTIVE',
                    MachineSpeed.effective_to.is_(None)  # 未过期的配置
                )
            )
            speed_result = await db.execute(speed_query)
            speeds = speed_result.scalars().all()
            
            # 获取所有活跃机台
            machine_query = select(Machine).where(Machine.status == 'ACTIVE')
            machine_result = await db.execute(machine_query)
            machines = machine_result.scalars().all()
            
            # 建立机台类型映射
            machine_type_map = {m.machine_code: m.machine_type for m in machines}
            
            speed_mappings = {
                "ALL_PRODUCTS": [],  # 通配符配置适用的所有产品
                "SPECIFIC": {}       # 特定产品的配置
            }
            
            for speed_config in speeds:
                machine_info = {
                    "machine_code": speed_config.machine_code,
                    "speed": float(speed_config.speed),
                    "efficiency_rate": float(speed_config.efficiency_rate),
                    "machine_type": machine_type_map.get(speed_config.machine_code, "UNKNOWN"),
                    "article_nr": speed_config.article_nr,
                    "effective_from": speed_config.effective_from,
                    "config_id": speed_config.id
                }
                
                if speed_config.article_nr == "*":
                    # 通配符配置，适用于所有产品
                    speed_mappings["ALL_PRODUCTS"].append(machine_info)
                else:
                    # 特定产品配置
                    if speed_config.article_nr not in speed_mappings["SPECIFIC"]:
                        speed_mappings["SPECIFIC"][speed_config.article_nr] = []
                    speed_mappings["SPECIFIC"][speed_config.article_nr].append(machine_info)
            
            logger.info(f"构建速度映射表完成: 通配符配置 {len(speed_mappings['ALL_PRODUCTS'])} 个，"
                       f"特定配置 {len(speed_mappings['SPECIFIC'])} 个产品")
            
            return speed_mappings
            
        except Exception as e:
            logger.error(f"构建速度映射表失败: {str(e)}")
            return {"ALL_PRODUCTS": [], "SPECIFIC": {}}
    
    async def _get_machine_relations(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取机台关系配置"""
        try:
            relations_query = select(MachineRelation)
            relations_result = await db.execute(relations_query)
            relations = relations_result.scalars().all()
            
            return [
                {
                    "feeder_code": r.feeder_code,
                    "maker_code": r.maker_code,
                    "relation_type": r.relation_type,
                    "priority": r.priority,
                    "id": r.id
                }
                for r in relations
            ]
            
        except Exception as e:
            logger.error(f"获取机台关系失败: {str(e)}")
            return []
    
    async def _get_maintenance_plans(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取维护计划（处理空表情况）"""
        try:
            maintenance_query = select(MaintenancePlan).where(
                MaintenancePlan.plan_status == 'PLANNED'
            )
            maintenance_result = await db.execute(maintenance_query)
            maintenance_plans = maintenance_result.scalars().all()
            
            plans = []
            for plan in maintenance_plans:
                plans.append({
                    "machine_code": plan.machine_code,
                    "maintenance_start": plan.maint_start_time,
                    "maintenance_end": plan.maint_end_time,
                    "maintenance_type": getattr(plan, 'maint_type', 'REGULAR'),
                    "description": getattr(plan, 'description', ''),
                    "id": plan.id
                })
            
            if not plans:
                logger.warning("维护计划表为空，算法将忽略维护约束")
            else:
                logger.info(f"获取到 {len(plans)} 个维护计划")
            
            return plans
            
        except Exception as e:
            logger.error(f"获取维护计划失败: {str(e)}")
            return []
    
    async def _get_shift_configs(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        从aps_shift_config表获取班次配置
        
        Args:
            db: 数据库会话
            
        Returns:
            班次配置列表
        """
        try:
            from app.models.machine_config_models import ShiftConfig
            from sqlalchemy import select
            
            # 查询活动状态的班次配置
            query = select(ShiftConfig).where(
                ShiftConfig.status == 'ACTIVE'
            ).order_by(ShiftConfig.start_time)
            
            result = await db.execute(query)
            shift_configs_raw = result.scalars().all()
            
            if not shift_configs_raw:
                # 如果数据库中没有配置，使用默认配置
                logger.warning("aps_shift_config表中没有找到班次配置，使用默认配置")
                return [
                    {"name": "早班", "start": "06:40", "end": "15:40", "hours": 9.0},
                    {"name": "中班", "start": "15:40", "end": "00:00", "hours": 8.33}
                ]
            
            # 转换为算法需要的格式
            shift_configs = []
            for config in shift_configs_raw:
                # 计算班次时长
                start_time = config.start_time
                end_time = config.end_time
                
                # 处理跨日班次
                if end_time <= start_time:
                    # 跨日班次：加24小时
                    from datetime import datetime, timedelta
                    start_dt = datetime.combine(date.today(), start_time)
                    end_dt = datetime.combine(date.today() + timedelta(days=1), end_time)
                    hours = (end_dt - start_dt).total_seconds() / 3600
                else:
                    # 同日班次
                    from datetime import datetime
                    start_dt = datetime.combine(date.today(), start_time)
                    end_dt = datetime.combine(date.today(), end_time)
                    hours = (end_dt - start_dt).total_seconds() / 3600
                
                shift_configs.append({
                    "name": config.shift_name,
                    "start": start_time.strftime("%H:%M"),
                    "end": end_time.strftime("%H:%M") if end_time.strftime("%H:%M") != "00:00" else "00:00",
                    "hours": round(hours, 2),
                    "machine_name": config.machine_name,
                    "is_ot_needed": config.is_ot_needed,
                    "max_ot_duration": config.max_ot_duration.strftime("%H:%M") if config.max_ot_duration else None
                })
            
            logger.info(f"从数据库获取到 {len(shift_configs)} 个班次配置")
            return shift_configs
            
        except Exception as e:
            logger.error(f"获取班次配置失败: {str(e)}")
            # 返回默认配置
            return [
                {"name": "早班", "start": "06:40", "end": "15:40", "hours": 9.0},
                {"name": "中班", "start": "15:40", "end": "00:00", "hours": 8.33}
            ]
    
    async def _generate_work_calendar(self, year: int, month: int, db: AsyncSession) -> Dict[str, Any]:
        """
        生成工作日历，处理工作日历表缺失的问题
        基于中国标准工作日规则和实际班次配置
        """
        try:
            # 生成该月的所有日期
            month_start = date(year, month, 1)
            month_end = date(year, month, calendar.monthrange(year, month)[1])
            
            work_days = []
            current_date = month_start
            
            # 从aps_shift_config表获取班次配置
            shift_configs = await self._get_shift_configs(db)
            
            while current_date <= month_end:
                # 周一到周五为工作日（1-5），周六周日为休息日（6-7）
                weekday = current_date.isoweekday()
                
                if weekday <= 5:  # 工作日
                    daily_hours = sum(shift["hours"] for shift in shift_configs)
                    work_days.append({
                        "date": current_date,
                        "is_working": True,
                        "day_type": "WORKDAY",
                        "total_hours": daily_hours,
                        "shifts": shift_configs.copy()
                    })
                else:  # 周末
                    work_days.append({
                        "date": current_date,
                        "is_working": False,
                        "day_type": "WEEKEND",
                        "total_hours": 0,
                        "shifts": []
                    })
                
                current_date += timedelta(days=1)
            
            total_work_days = len([d for d in work_days if d["is_working"]])
            total_work_hours = sum(d["total_hours"] for d in work_days if d["is_working"])
            
            calendar_data = {
                "year": year,
                "month": month,
                "total_work_days": total_work_days,
                "total_work_hours": total_work_hours,
                "calendar": work_days,
                "generated": True,  # 标记为自动生成
                "shift_configs": shift_configs
            }
            
            logger.info(f"生成工作日历: {year}年{month}月，{total_work_days}个工作日，{total_work_hours}小时")
            
            return calendar_data
            
        except Exception as e:
            logger.error(f"生成工作日历失败: {str(e)}")
            return {
                "year": year,
                "month": month,
                "total_work_days": 0,
                "total_work_hours": 0,
                "calendar": [],
                "error": str(e)
            }
    
    def get_machine_configs_for_product(
        self, 
        standardized_article_nr: str, 
        speed_mappings: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """
        获取特定产品的机台配置
        
        优先使用特定产品配置，回退到通配符配置
        """
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
        
        # 3. 无可用配置
        logger.warning(f"产品 {standardized_article_nr} 无可用机台配置")
        return []
