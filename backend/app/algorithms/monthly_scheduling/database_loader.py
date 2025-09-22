"""
APS智慧排产系统 - 数据库访问层

负责从9个数据表加载所有排产所需数据，实现完整的数据预处理和缓存机制。

数据表映射：
1. aps_monthly_plan - 月度计划数据（核心输入）
2. aps_machine - 机台基础信息（区分PACKING/FEEDING类型）
3. aps_machine_speed - 机台速度配置（支持通配符*匹配）
4. aps_machine_relation - 机台关系映射（1喂丝机→多卷包机）
5. aps_shift_config - 班次配置（计算每日可用工作时间）
6. aps_monthly_work_calendar - 工作日历（确定有效生产日期）
7. aps_maintenance_plan - 维护计划（时间窗口约束）
8. aps_monthly_schedule_result - 排产结果保存（输出）
9. aps_monthly_scheduling_task - 任务状态管理（进度跟踪）

核心特性：
- 直接数据库查询，不使用硬编码数据
- 通配符匹配优先级处理
- 数据完整性验证
- 高效的内存缓存机制
- 完善的异常处理
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, time
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from decimal import Decimal

from app.models.monthly_plan_models import MonthlyPlan
from app.models.base_models import Machine
from app.models.machine_config_models import MachineSpeed, MachineRelation, MaintenancePlan, ShiftConfig
from app.models.monthly_schedule_result_models import MonthlyScheduleResult
from app.models.monthly_task_models import MonthlySchedulingTask

logger = logging.getLogger(__name__)


class DatabaseLoader:
    """
    数据库访问层
    
    职责：
    1. 从9个数据表加载所有排产所需数据
    2. 实现数据预处理和验证
    3. 提供高效的数据缓存机制
    4. 处理通配符匹配和优先级
    5. 确保数据完整性和一致性
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache = {}
        self._initialized = False
        
    async def load_all_data(self, monthly_batch_id: str) -> Dict[str, Any]:
        """
        加载所有排产所需数据
        
        Args:
            monthly_batch_id: 月度批次ID
            
        Returns:
            包含所有数据的字典
        """
        logger.info(f"开始加载月度批次数据: {monthly_batch_id}")
        
        data = {
            'monthly_plans': [],
            'machines': {'packing': [], 'feeding': []},
            'speed_configs': {'specific': {}, 'wildcard': []},
            'machine_relations': {'maker_to_feeder': {}, 'feeder_to_makers': {}},
            'shift_configs': [],
            'work_calendar': {},
            'maintenance_plans': [],
            'batch_info': {'batch_id': monthly_batch_id}
        }
        
        try:
            # 1. 加载月度计划数据
            data['monthly_plans'] = await self.load_monthly_plans(monthly_batch_id)
            logger.info(f"加载月度计划: {len(data['monthly_plans'])} 条记录")
            
            # 2. 加载机台基础信息
            data['machines'] = await self.load_machine_data()
            logger.info(f"加载机台信息: 卷包机 {len(data['machines']['packing'])} 台, "
                       f"喂丝机 {len(data['machines']['feeding'])} 台")
            
            # 3. 加载机台速度配置
            data['speed_configs'] = await self.load_speed_configs()
            logger.info(f"加载速度配置: 特定配置 {len(data['speed_configs']['specific'])} 项, "
                       f"通配符配置 {len(data['speed_configs']['wildcard'])} 项")
            
            # 4. 加载机台关系映射
            data['machine_relations'] = await self.load_machine_relations()
            logger.info(f"加载机台关系: {len(data['machine_relations']['maker_to_feeder'])} 对关系")
            
            # 5. 加载班次配置
            data['shift_configs'] = await self.load_shift_configs()
            logger.info(f"加载班次配置: {len(data['shift_configs'])} 个班次")
            
            # 6. 加载工作日历
            if data['monthly_plans']:
                year = data['monthly_plans'][0].plan_year
                month = data['monthly_plans'][0].plan_month
                data['work_calendar'] = await self.load_work_calendar(year, month)
                logger.info(f"加载工作日历: {year}年{month}月")
            
            # 7. 加载维护计划
            data['maintenance_plans'] = await self.load_maintenance_plans()
            logger.info(f"加载维护计划: {len(data['maintenance_plans'])} 个计划")
            
            # 8. 验证数据完整性
            await self.validate_data_integrity(data)
            
            # 9. 构建数据缓存
            self._cache[monthly_batch_id] = data
            self._initialized = True
            
            logger.info("所有数据加载完成")
            return data
            
        except Exception as e:
            logger.error(f"数据加载失败: {str(e)}")
            raise Exception(f"数据库数据加载失败: {str(e)}")
    
    async def load_monthly_plans(self, monthly_batch_id: str) -> List[MonthlyPlan]:
        """
        加载月度计划数据 (aps_monthly_plan表)
        
        Args:
            monthly_batch_id: 月度批次ID
            
        Returns:
            月度计划列表
        """
        try:
            query = select(MonthlyPlan).where(
                MonthlyPlan.monthly_batch_id == monthly_batch_id
            ).order_by(MonthlyPlan.article_nr)
            
            result = await self.db.execute(query)
            plans = result.scalars().all()
            
            # 数据验证
            valid_plans = []
            for plan in plans:
                if self._validate_monthly_plan(plan):
                    valid_plans.append(plan)
            
            if not valid_plans:
                raise Exception(f"批次 {monthly_batch_id} 无有效的月度计划数据")
                
            return valid_plans
            
        except Exception as e:
            logger.error(f"加载月度计划数据失败: {str(e)}")
            raise
    
    async def load_machine_data(self) -> Dict[str, List[Machine]]:
        """
        加载机台基础信息 (aps_machine表)
        
        严格区分PACKING（卷包机）和FEEDING（喂丝机）类型
        
        Returns:
            分类的机台信息字典
        """
        try:
            query = select(Machine).where(
                Machine.status == 'ACTIVE'
            ).order_by(Machine.machine_code)
            
            result = await self.db.execute(query)
            machines = result.scalars().all()
            
            categorized = {'packing': [], 'feeding': []}
            
            for machine in machines:
                if machine.machine_type == 'PACKING':
                    categorized['packing'].append(machine)
                elif machine.machine_type == 'FEEDING':
                    categorized['feeding'].append(machine)
                else:
                    logger.warning(f"未知机台类型: {machine.machine_code} - {machine.machine_type}")
            
            # 验证数据有效性
            if not categorized['packing']:
                raise Exception("未找到有效的卷包机数据")
            if not categorized['feeding']:
                raise Exception("未找到有效的喂丝机数据")
                
            return categorized
            
        except Exception as e:
            logger.error(f"加载机台数据失败: {str(e)}")
            raise
    
    async def load_speed_configs(self) -> Dict[str, Any]:
        """
        加载机台速度配置 (aps_machine_speed表)
        
        处理通配符"*"匹配优先级：
        - 具体产品配置优先级高于通配符配置
        - 具体机台配置优先级高于通配符机台配置
        
        Returns:
            速度配置字典，分为specific和wildcard两类
        """
        try:
            query = select(MachineSpeed).where(
                and_(
                    MachineSpeed.status == 'ACTIVE',
                    or_(
                        MachineSpeed.effective_to.is_(None),
                        MachineSpeed.effective_to >= datetime.now()
                    )
                )
            ).order_by(MachineSpeed.machine_code, MachineSpeed.article_nr)
            
            result = await self.db.execute(query)
            speeds = result.scalars().all()
            
            configs = {
                'specific': {},  # {(machine_code, article_nr): config}
                'wildcard': []   # 通配符配置列表
            }
            
            for speed in speeds:
                config = {
                    'machine_code': speed.machine_code,
                    'article_nr': speed.article_nr,
                    'speed_per_hour': float(speed.speed),  # 统一使用speed_per_hour字段名
                    'efficiency': float(speed.efficiency_rate) if speed.efficiency_rate else 100.0,  # 统一使用efficiency字段名
                    'effective_from': speed.effective_from,
                    'effective_to': speed.effective_to
                }
                
                if speed.machine_code == '*' and speed.article_nr == '*':
                    # 完全通配符配置 (*×*)
                    configs['wildcard'].append(config)
                else:
                    # 具体配置和部分通配符配置 (A1×*, *×product, A1×product)
                    key = (speed.machine_code, speed.article_nr)
                    configs['specific'][key] = config
            
            return configs
            
        except Exception as e:
            logger.error(f"加载速度配置失败: {str(e)}")
            raise
    
    async def load_machine_relations(self) -> Dict[str, Dict]:
        """
        加载机台关系映射 (aps_machine_relation表)
        
        正确理解：1喂丝机 → 多卷包机关系
        
        Returns:
            机台关系字典，包含双向映射
        """
        try:
            query = select(MachineRelation).order_by(
                MachineRelation.feeder_code, 
                MachineRelation.priority
            )
            
            result = await self.db.execute(query)
            relations = result.scalars().all()
            
            mappings = {
                'maker_to_feeder': {},    # {卷包机: 喂丝机}
                'feeder_to_makers': {}    # {喂丝机: [卷包机列表]}
            }
            
            for relation in relations:
                feeder_code = str(relation.feeder_code)
                maker_code = str(relation.maker_code)
                
                # 卷包机 → 喂丝机映射（一对一）
                mappings['maker_to_feeder'][maker_code] = feeder_code
                
                # 喂丝机 → 卷包机映射（一对多）
                if feeder_code not in mappings['feeder_to_makers']:
                    mappings['feeder_to_makers'][feeder_code] = []
                mappings['feeder_to_makers'][feeder_code].append({
                    'maker_code': maker_code,
                    'priority': relation.priority,
                    'relation_type': relation.relation_type
                })
            
            # 验证关系完整性
            if not mappings['maker_to_feeder']:
                raise Exception("未找到有效的机台关系数据")
                
            return mappings
            
        except Exception as e:
            logger.error(f"加载机台关系失败: {str(e)}")
            raise
    
    async def load_shift_configs(self) -> List[Dict[str, Any]]:
        """
        加载班次配置 (aps_shift_config表)
        
        Returns:
            班次配置列表
        """
        try:
            query = select(ShiftConfig).where(
                and_(
                    ShiftConfig.status == 'ACTIVE',
                    or_(
                        ShiftConfig.effective_to.is_(None),
                        ShiftConfig.effective_to >= datetime.now()
                    )
                )
            ).order_by(ShiftConfig.start_time)
            
            result = await self.db.execute(query)
            shifts = result.scalars().all()
            
            configs = []
            for shift in shifts:
                # 计算班次时长
                start_time = shift.start_time
                end_time = shift.end_time
                
                # 处理跨日班次
                if end_time <= start_time:
                    # 跨日班次，加24小时
                    from datetime import timedelta
                    hours = 24 - (start_time.hour + start_time.minute/60) + (end_time.hour + end_time.minute/60)
                else:
                    # 同日班次
                    hours = (end_time.hour + end_time.minute/60) - (start_time.hour + start_time.minute/60)
                
                configs.append({
                    'shift_name': shift.shift_name,
                    'machine_name': shift.machine_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_hours': round(hours, 2),
                    'is_ot_needed': shift.is_ot_needed,
                    'max_ot_duration': shift.max_ot_duration
                })
            
            # 如果没有班次配置，不使用硬编码，而是抛出错误要求配置数据库
            if not configs:
                logger.error("未找到班次配置数据，请在aps_shift_config表中配置班次信息")
                raise Exception("aps_shift_config表中缺少班次配置数据，无法继续排产算法")
                # 移除硬编码的默认配置，强制要求从数据库获取正确的班次配置
            
            return configs
            
        except Exception as e:
            logger.error(f"加载班次配置失败: {str(e)}")
            raise
    
    async def load_work_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """
        加载工作日历 (aps_monthly_work_calendar表)
        
        如果表中没有数据，则生成基于标准工作日的日历
        
        Args:
            year: 计划年份
            month: 计划月份
            
        Returns:
            工作日历数据
        """
        try:
            # 尝试从数据库加载
            from app.models.monthly_work_calendar_models import MonthlyWorkCalendar
            
            query = select(MonthlyWorkCalendar).where(
                and_(
                    MonthlyWorkCalendar.calendar_year == year,
                    MonthlyWorkCalendar.calendar_month == month
                )
            ).order_by(MonthlyWorkCalendar.calendar_date)
            
            result = await self.db.execute(query)
            calendar_records = result.scalars().all()
            
            if calendar_records:
                # 使用数据库中的工作日历
                calendar_data = {
                    'year': year,
                    'month': month,
                    'work_days': [],
                    'total_work_days': 0,
                    'total_work_hours': 0.0,
                    'source': 'database'
                }
                
                for record in calendar_records:
                    day_data = {
                        'date': record.calendar_date,
                        'is_working': record.monthly_is_working,
                        'day_type': record.monthly_day_type or 'WORKDAY' if record.monthly_is_working else 'HOLIDAY',
                        'total_hours': float(record.monthly_total_hours) if record.monthly_total_hours else 0.0
                    }
                    calendar_data['work_days'].append(day_data)
                    
                    if record.monthly_is_working:
                        calendar_data['total_work_days'] += 1
                        calendar_data['total_work_hours'] += day_data['total_hours']
                
            else:
                # 生成标准工作日历
                logger.warning(f"未找到{year}年{month}月的工作日历数据，生成标准工作日历")
                calendar_data = await self._generate_standard_calendar(year, month)
            
            return calendar_data
            
        except Exception as e:
            logger.error(f"加载工作日历失败: {str(e)}")
            # 生成标准工作日历作为备用
            return await self._generate_standard_calendar(year, month)
    
    async def load_maintenance_plans(self) -> List[Dict[str, Any]]:
        """
        加载维护计划 (aps_maintenance_plan表)
        
        Returns:
            维护计划列表
        """
        try:
            query = select(MaintenancePlan).where(
                MaintenancePlan.plan_status == 'PLANNED'
            ).order_by(MaintenancePlan.maint_start_time)
            
            result = await self.db.execute(query)
            plans = result.scalars().all()
            
            maintenance_plans = []
            for plan in plans:
                maintenance_plans.append({
                    'plan_no': plan.maint_plan_no,
                    'machine_code': plan.machine_code,
                    'start_time': plan.maint_start_time,
                    'end_time': plan.maint_end_time,
                    'duration_minutes': plan.estimated_duration,
                    'maintenance_type': plan.maint_type,
                    'maintenance_level': plan.maint_level,
                    'description': plan.maint_description
                })
            
            if not maintenance_plans:
                logger.warning("维护计划表为空，算法将忽略维护约束")
            else:
                logger.info(f"加载维护计划: {len(maintenance_plans)} 个计划")
            
            return maintenance_plans
            
        except Exception as e:
            logger.error(f"加载维护计划失败: {str(e)}")
            return []  # 维护计划可以为空
    
    async def _generate_standard_calendar(self, year: int, month: int) -> Dict[str, Any]:
        """
        生成标准工作日历
        
        基于中国标准工作日规则：周一到周五为工作日
        """
        import calendar as cal
        from datetime import datetime, timedelta
        
        # 获取班次配置用于计算每日工作时间
        shift_configs = await self.load_shift_configs()
        daily_hours = sum(shift['duration_hours'] for shift in shift_configs)
        
        calendar_data = {
            'year': year,
            'month': month,
            'work_days': [],
            'total_work_days': 0,
            'total_work_hours': 0.0,
            'source': 'generated'
        }
        
        # 生成该月的所有日期
        month_start = date(year, month, 1)
        month_end = date(year, month, cal.monthrange(year, month)[1])
        
        current_date = month_start
        while current_date <= month_end:
            # 周一到周五为工作日（1-5）
            weekday = current_date.isoweekday()
            is_working = weekday <= 5
            
            day_data = {
                'date': current_date,
                'is_working': is_working,
                'day_type': 'WORKDAY' if is_working else 'WEEKEND',
                'total_hours': daily_hours if is_working else 0.0
            }
            
            calendar_data['work_days'].append(day_data)
            
            if is_working:
                calendar_data['total_work_days'] += 1
                calendar_data['total_work_hours'] += daily_hours
            
            current_date += timedelta(days=1)
        
        return calendar_data
    
    def _validate_monthly_plan(self, plan: MonthlyPlan) -> bool:
        """
        验证单个月度计划的有效性
        
        Args:
            plan: 月度计划记录
            
        Returns:
            是否有效
        """
        # 1. 检查目标产量
        if not plan.target_quantity_boxes or plan.target_quantity_boxes <= 0:
            logger.warning(f"产品 {plan.article_nr} 目标产量无效: {plan.target_quantity_boxes}")
            return False
        
        # 2. 检查产品规格
        if not plan.article_nr or plan.article_nr.strip() == "":
            logger.warning(f"计划ID {plan.monthly_plan_id} 产品规格为空")
            return False
        
        # 3. 检查计划年月
        if not plan.plan_year or not plan.plan_month:
            logger.warning(f"产品 {plan.article_nr} 计划年月无效")
            return False
        
        # 4. 检查是否为合计行
        clean_article = plan.article_nr.replace(' ', '').replace('\t', '').replace('\u3000', '')
        if "合计" in clean_article or "总计" in clean_article:
            logger.debug(f"跳过合计行: {plan.article_nr}")
            return False
        
        return True
    
    async def validate_data_integrity(self, data: Dict[str, Any]) -> None:
        """
        验证数据完整性
        
        Args:
            data: 加载的数据字典
        """
        errors = []
        
        # 1. 验证月度计划数据
        if not data['monthly_plans']:
            errors.append("月度计划数据为空")
        
        # 2. 验证机台数据
        if not data['machines']['packing']:
            errors.append("未找到卷包机数据")
        if not data['machines']['feeding']:
            errors.append("未找到喂丝机数据")
        
        # 3. 验证机台关系
        if not data['machine_relations']['maker_to_feeder']:
            errors.append("机台关系数据为空")
        
        # 4. 验证速度配置
        if not data['speed_configs']['specific'] and not data['speed_configs']['wildcard']:
            errors.append("机台速度配置为空")
        
        # 5. 验证班次配置
        if not data['shift_configs']:
            errors.append("班次配置为空")
        
        # 6. 验证工作日历
        if not data['work_calendar'] or not data['work_calendar'].get('work_days'):
            errors.append("工作日历数据为空")
        
        if errors:
            raise Exception(f"数据完整性验证失败: {'; '.join(errors)}")
        
        logger.info("数据完整性验证通过")
    
    def get_speed_for_machine_product(
        self, 
        machine_code: str, 
        article_nr: str, 
        speed_configs: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定机台和产品的速度配置
        
        优先级：具体配置 > 通配符配置
        
        Args:
            machine_code: 机台代码
            article_nr: 产品规格
            speed_configs: 速度配置数据
            
        Returns:
            速度配置信息
        """
        # 1. 优先查找具体配置
        specific_key = (machine_code, article_nr)
        if specific_key in speed_configs['specific']:
            return speed_configs['specific'][specific_key]
        
        # 2. 查找机台通配符配置
        machine_wildcard_key = (machine_code, '*')
        if machine_wildcard_key in speed_configs['specific']:
            return speed_configs['specific'][machine_wildcard_key]
        
        # 3. 查找产品通配符配置
        for config in speed_configs['wildcard']:
            if config['machine_code'] == '*' and config['article_nr'] == article_nr:
                return config
        
        # 4. 查找完全通配符配置
        for config in speed_configs['wildcard']:
            if config['machine_code'] == '*' and config['article_nr'] == '*':
                return config
        
        return None
    
    def get_feeder_for_maker(
        self, 
        maker_code: str, 
        machine_relations: Dict[str, Dict]
    ) -> Optional[str]:
        """
        根据卷包机代码查找对应的喂丝机
        
        Args:
            maker_code: 卷包机代码
            machine_relations: 机台关系数据
            
        Returns:
            喂丝机代码
        """
        return machine_relations['maker_to_feeder'].get(maker_code)
    
    def clear_cache(self) -> None:
        """清除数据缓存"""
        self._cache.clear()
        self._initialized = False
        logger.info("数据缓存已清除")