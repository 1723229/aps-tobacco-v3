"""
APS智慧排产系统 - 工单生成算法（MES规范重构版）

基于排产结果生成符合MES接口规范的卷包机和喂丝机工单
完全符合MES接口文档要求，支持工单号序列生成和InputBatch结构
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
from app.services.work_order_sequence_service import WorkOrderSequenceService
import logging

logger = logging.getLogger(__name__)


def _format_datetime(dt, format_str='%Y/%m/%d %H:%M:%S'):
    """安全的时间格式化函数"""
    if dt is None:
        return None
    
    if isinstance(dt, str):
        # 尝试解析字符串时间
        try:
            # 尝试常见格式
            if 'T' in dt:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            elif ' ' in dt:
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(dt, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"无法解析时间字符串: {dt}")
            return None
    
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    
    return None


class WorkOrderGeneration(AlgorithmBase):
    """工单生成算法 - MES规范版"""
    
    def __init__(self):
        super().__init__(ProcessingStage.WORK_ORDER_GENERATION)
        
    async def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行MES规范工单生成
        
        核心逻辑：
        1. 按工单号分组，确保同一工单的不同机台关联
        2. 为每个喂丝机生成一个HWS工单（H+WS+9位序列号）
        3. 为每个卷包机生成一个HJB工单（H+JB+9位序列号）
        4. 建立InputBatch关联关系
        
        Args:
            input_data: 并行处理后的工单数据
            
        Returns:
            AlgorithmResult: 工单生成结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 按工单号分组
        work_order_groups = self._group_by_work_order_number(input_data)
        
        generated_work_orders = []
        work_order_schedules = []  # 用于aps_work_order_schedule表
        
        for work_order_nr, orders in work_order_groups.items():
            try:
                # 为每组生成MES规范的工单对
                mes_orders = await self._generate_mes_work_order_pair(work_order_nr, orders)
                generated_work_orders.extend(mes_orders)
                
                # 生成工单调度记录（用于甘特图显示）- 只为卷包工单生成
                schedule_record = None
                if orders and orders[0].get('work_order_type') == 'PACKING':
                    schedule_record = self._generate_work_order_schedule(work_order_nr, orders)
                    if schedule_record:
                        work_order_schedules.append(schedule_record)
                
                logger.info(f"为工单组{work_order_nr}生成{len(mes_orders)}个MES工单 + {'1' if schedule_record else '0'}个调度记录")
                
            except Exception as e:
                logger.error(f"MES工单生成失败 - 工单组{work_order_nr}: {str(e)}")
                result.add_error(f"MES工单生成失败: {str(e)}", {'work_order_group': work_order_nr})
                
                # 生成基础工单以免中断流程
                for order_data in orders:
                    fallback_order = self._generate_fallback_mes_order(order_data)
                    generated_work_orders.append(fallback_order)
        
        # 将work_order_schedules添加到结果中
        result.output_data = generated_work_orders
        result.custom_data = {
            'work_order_schedules': work_order_schedules
        }
        
        # 计算生成统计
        feeding_orders = len([wo for wo in generated_work_orders if wo.get('plan_id', '').startswith('HWS')])
        packing_orders = len([wo for wo in generated_work_orders if wo.get('plan_id', '').startswith('HJB')])
        
        result.metrics.custom_metrics = {
            'feeding_work_orders': feeding_orders,
            'packing_work_orders': packing_orders,
            'total_work_orders': len(generated_work_orders),
            'generation_success_rate': len(generated_work_orders) / len(input_data) if input_data else 0,
            'work_order_groups_processed': len(work_order_groups)
        }
        
        logger.info(f"MES工单生成完成: 喂丝机{feeding_orders}个，卷包机{packing_orders}个")
        return self.finalize_result(result)
    
    def _group_by_work_order_number(self, input_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按工单号分组
        
        Args:
            input_data: 输入工单数据
            
        Returns:
            Dict: {工单号: [工单列表]}
        """
        from collections import defaultdict
        
        groups = defaultdict(list)
        
        for order_data in input_data:
            work_order_nr = order_data.get('work_order_nr', 'UNKNOWN')
            groups[work_order_nr].append(order_data)
        
        return dict(groups)
    
    async def _generate_mes_work_order_pair(self, work_order_nr: str, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为一个工单组生成MES规范的工单对
        
        Args:
            work_order_nr: 工单号
            orders: 同一工单的不同机台订单
            
        Returns:
            List[Dict[str, Any]]: MES规范的工单列表
        """
        if not orders:
            return []
        
        mes_orders = []
        
        # 获取喂丝机和卷包机信息
        feeder_codes = list(set(order.get('feeder_code') for order in orders if order.get('feeder_code')))
        maker_codes = list(set(order.get('maker_code') for order in orders if order.get('maker_code')))
        
        # 为每个喂丝机生成一个HWS工单
        for feeder_code in feeder_codes:
            if feeder_code:
                feeding_order = await self._generate_mes_feeding_order(work_order_nr, feeder_code, orders)
                mes_orders.append(feeding_order)
        
        # 为每个卷包机生成一个HJB工单，并关联到喂丝机工单
        for maker_code in maker_codes:
            if maker_code:
                # 找到对应的喂丝机
                corresponding_orders = [o for o in orders if o.get('maker_code') == maker_code]
                if corresponding_orders:
                    feeding_plan_ids = [fo.get('plan_id') for fo in mes_orders if fo.get('plan_id', '').startswith('HWS')]
                    packing_order = await self._generate_mes_packing_order(
                        work_order_nr, maker_code, corresponding_orders[0], feeding_plan_ids
                    )
                    mes_orders.append(packing_order)
        
        return mes_orders
    
    async def _generate_mes_feeding_order(
        self, 
        work_order_nr: str, 
        feeder_code: str, 
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成MES规范的喂丝机工单
        
        Args:
            work_order_nr: 原工单号
            feeder_code: 喂丝机代码
            orders: 相关订单列表
            
        Returns:
            Dict[str, Any]: MES规范的喂丝机工单
        """
        # 获取基础信息
        first_order = orders[0]
        
        # 计算总数量和时间
        total_final_quantity = sum(o.get('final_quantity', 0) for o in orders)
        earliest_start = min(o.get('planned_start') for o in orders if o.get('planned_start'))
        latest_end = max(o.get('planned_end') for o in orders if o.get('planned_end'))
        
        # 生成MES规范的喂丝机工单
        feeding_order = {
            # MES核心字段
            'plan_id': await self._generate_mes_plan_id('HWS'),
            'production_line': feeder_code,  # 单个喂丝机代码
            'batch_code': None,  # 喂丝机通常为空
            'material_code': first_order.get('article_nr', ''),  # 成品烟牌号作为物料代码
            'bom_revision': None,  # 喂丝机没有版本号
            'quantity': None,  # 喂丝机通常为空
            'plan_start_time': _format_datetime(earliest_start),
            'plan_end_time': _format_datetime(latest_end),
            'sequence': 1,
            'shift': None,  # 喂丝机没有班次
            
            # 工艺控制字段
            'is_vaccum': False,
            'is_sh93': False,
            'is_hdt': False,
            'is_flavor': False,
            'unit': '公斤',
            'plan_date': _format_datetime(earliest_start, '%Y/%m/%d'),
            'plan_output_quantity': None,  # 通常为空
            'is_outsourcing': False,
            'is_backup': first_order.get('is_backup', False),
            
            # 内部字段（非MES接口字段）
            'original_work_order_nr': work_order_nr,
            'feeder_code': feeder_code,
            'final_quantity': total_final_quantity,
            'related_orders': [o.get('work_order_nr') for o in orders],
            'generation_timestamp': datetime.now(),
            'order_type': 'FEEDING'
        }
        
        return feeding_order
    
    async def _generate_mes_packing_order(
        self, 
        work_order_nr: str, 
        maker_code: str, 
        order: Dict[str, Any],
        feeding_plan_ids: List[str]
    ) -> Dict[str, Any]:
        """
        生成MES规范的卷包机工单
        
        Args:
            work_order_nr: 原工单号
            maker_code: 卷包机代码
            order: 订单数据
            feeding_plan_ids: 关联的喂丝机计划ID列表
            
        Returns:
            Dict[str, Any]: MES规范的卷包机工单
        """
        # 生成InputBatch结构
        input_batch = None
        if feeding_plan_ids:
            input_batch = {
                'input_plan_id': feeding_plan_ids[0],  # 关联的喂丝机计划号
                'input_batch_code': None,
                'quantity': None,  # 卷包机没有投入数量
                'batch_sequence': None,
                'is_whole_batch': None,
                'is_main_channel': True,
                'is_deleted': False,
                'is_last_one': None,
                'material_code': order.get('article_nr', ''),  # 投入物料代码
                'bom_revision': None,
                'tiled': None,
                'remark1': None,
                'remark2': None
            }
        
        # 生成MES规范的卷包机工单
        packing_order = {
            # MES核心字段
            'plan_id': await self._generate_mes_plan_id('HJB'),
            'production_line': maker_code,  # 单个卷包机代码
            'batch_code': None,
            'material_code': order.get('article_nr', ''),  # 成品烟牌号
            'bom_revision': None,
            'quantity': order.get('final_quantity', 0),  # 成品烟产量（箱）
            'plan_start_time': _format_datetime(order.get('planned_start')),
            'plan_end_time': _format_datetime(order.get('planned_end')),
            'sequence': 1,
            'shift': None,
            
            # InputBatch前工序批次信息
            'input_batch': input_batch,
            
            # 工艺控制字段
            'is_vaccum': False,
            'is_sh93': False,
            'is_hdt': False,
            'is_flavor': False,
            'unit': '箱',
            'plan_date': _format_datetime(order.get('planned_start'), '%Y/%m/%d'),
            'plan_output_quantity': None,
            'is_outsourcing': False,
            'is_backup': order.get('is_backup', False),
            
            # 内部字段（非MES接口字段）
            'original_work_order_nr': work_order_nr,
            'maker_code': maker_code,
            'feeder_code': order.get('feeder_code', ''),
            'final_quantity': order.get('final_quantity', 0),
            'related_feeding_plan_ids': feeding_plan_ids,
            'generation_timestamp': datetime.now(),
            'order_type': 'PACKING'
        }
        
        return packing_order
    
    async def _generate_mes_plan_id(self, order_type: str) -> str:
        """
        生成MES规范的计划ID（使用数据库序列服务）
        
        格式：H + 工单类型（2位）+ 9位流水号
        例：HWS000000001（喂丝机）、HJB000000001（卷包机）
        
        Args:
            order_type: 工单类型 'HWS' 或 'HJB'
            
        Returns:
            str: MES规范的计划ID
        """
        try:
            # 使用序列服务生成ID
            plan_id = await WorkOrderSequenceService.generate_plan_id(order_type)
            logger.info(f"生成MES计划ID: {plan_id}")
            return plan_id
        except Exception as e:
            logger.error(f"MES计划ID生成失败，使用备用方案: {str(e)}")
            # 备用方案：使用随机数
            import random
            sequence = random.randint(1, 999999999)
            return f"H{order_type}{sequence:09d}"
    
    def _generate_fallback_mes_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成备用MES工单（同步版本，使用随机ID）
        
        Args:
            order_data: 订单数据
            
        Returns:
            Dict[str, Any]: 备用MES工单
        """
        import random
        fallback_plan_id = f"HJB{random.randint(1, 999999999):09d}"
        
        return {
            'plan_id': fallback_plan_id,
            'production_line': order_data.get('maker_code', 'UNKNOWN'),
            'batch_code': None,
            'material_code': order_data.get('article_nr', 'UNKNOWN'),
            'bom_revision': None,
            'quantity': order_data.get('final_quantity', 0),
            'plan_start_time': _format_datetime(datetime.now()),
            'plan_end_time': _format_datetime(datetime.now() + timedelta(hours=8)),
            'sequence': 1,
            'shift': None,
            'is_vaccum': False,
            'is_sh93': False,
            'is_hdt': False,
            'is_flavor': False,
            'unit': '箱',
            'plan_date': _format_datetime(datetime.now(), '%Y/%m/%d'),
            'plan_output_quantity': None,
            'is_outsourcing': False,
            'is_backup': True,
            'original_work_order_nr': order_data.get('work_order_nr', 'UNKNOWN'),
            'generation_timestamp': datetime.now(),
            'order_type': 'FALLBACK'
        }

    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行MES规范工单生成
        
        Args:
            input_data: 并行处理后的工单数据
            
        Returns:
            AlgorithmResult: 工单生成结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        if not input_data:
            result.output_data = []
            return self.finalize_result(result)
        
        # 查询机台关系和速度配置
        machine_relations = await DatabaseQueryService.get_machine_relations()
        machine_speeds = await DatabaseQueryService.get_machine_speeds()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'mes_compliant': True,
            'machine_relations_count': len(machine_relations),
            'machine_speeds_count': len(machine_speeds)
        }
        
        # 拆分算法已经生成了正确的MES格式工单，直接使用无需重新生成
        generated_work_orders = input_data
        
        logger.info(f"使用拆分算法生成的{len(generated_work_orders)}个MES工单，避免重复生成")
        
        # 虽然直接使用拆分算法结果，但仍需要生成工单调度记录
        work_order_groups = self._group_by_work_order_number(input_data)
        work_order_schedules = []
        
        for work_order_nr, orders in work_order_groups.items():
            # 只为卷包工单（PACKING类型）生成调度记录，喂丝工单不需要单独的调度记录
            if orders and orders[0].get('work_order_type') == 'PACKING':
                schedule_record = self._generate_work_order_schedule(work_order_nr, orders)
                if schedule_record:
                    work_order_schedules.append(schedule_record)
        
        result.output_data = generated_work_orders
        result.custom_data = {
            'work_order_schedules': work_order_schedules
        }
        
        # 计算生成统计 - 匹配拆分算法的字段格式
        feeding_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'FEEDING'])
        packing_orders = len([wo for wo in generated_work_orders if wo.get('work_order_type') == 'PACKING'])
        
        result.metrics.custom_metrics.update({
            'feeding_work_orders': feeding_orders,
            'packing_work_orders': packing_orders,
            'total_work_orders': len(generated_work_orders),
            'work_order_schedules_generated': len(work_order_schedules),
            'generation_success_rate': 1.0 if generated_work_orders else 0.0,
            'direct_passthrough': True  # 标记直接使用拆分算法结果
        })
        
        logger.info(f"MES工单生成完成(真实数据): 喂丝机{feeding_orders}个，卷包机{packing_orders}个")
        return self.finalize_result(result)
    
    def _validate_machine_relations_for_orders(
        self, 
        orders: List[Dict[str, Any]], 
        machine_relations: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        验证工单中的机台关系是否合法
        
        Args:
            orders: 工单列表
            machine_relations: 机台关系映射
            
        Returns:
            List[Dict[str, Any]]: 验证后的工单列表
        """
        validated_orders = []
        
        for order in orders:
            feeder_code = order.get('feeder_code', '')
            maker_code = order.get('maker_code', '')
            
            if feeder_code and maker_code:
                # 检查机台关系是否存在
                if feeder_code in machine_relations:
                    allowed_makers = machine_relations[feeder_code]
                    if maker_code not in allowed_makers:
                        logger.warning(
                            f"MES工单生成警告: 工单{order.get('work_order_nr')}中的机台关系不匹配 - "
                            f"喂丝机{feeder_code}不支持卷包机{maker_code}"
                        )
                        # 添加警告信息但不阻断生成
                        order = order.copy()
                        order['machine_relation_warning'] = f"机台关系不匹配: {feeder_code}->{maker_code}"
                        order['suggested_makers'] = allowed_makers
                else:
                    logger.warning(f"喂丝机{feeder_code}未在机台关系配置中找到")
                    order = order.copy()
                    order['machine_relation_missing'] = f"喂丝机{feeder_code}未配置"
            
            validated_orders.append(order)
        
        return validated_orders
    
    def _generate_work_order_schedule(self, work_order_nr: str, orders: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        生成工单调度记录（用于aps_work_order_schedule表和甘特图显示）
        
        Args:
            work_order_nr: 工单号
            orders: 同一工单号的订单列表（已经过并行处理）
            
        Returns:
            Dict: 工单调度记录
        """
        if not orders:
            return None
        
        # 获取第一个订单作为基础信息（同一工单号的订单应该有相同的基础信息）
        base_order = orders[0]
        
        # 合并所有机台信息
        maker_codes = set()
        feeder_codes = set()
        
        total_final_quantity = 0
        total_quantity = 0
        
        # 获取最早开始时间和最晚结束时间
        start_times = []
        end_times = []
        
        for order in orders:
            # 收集机台代码
            if order.get('maker_code'):
                maker_codes.add(order['maker_code'])
            if order.get('feeder_code'):
                feeder_codes.add(order['feeder_code'])
            
            # 累计数量
            total_final_quantity += order.get('final_quantity', 0)
            total_quantity += order.get('quantity_total', 0)
            
            # 收集时间
            if order.get('planned_start'):
                start_times.append(order['planned_start'])
            if order.get('planned_end'):
                end_times.append(order['planned_end'])
        
        # 构建调度记录
        schedule_record = {
            'work_order_nr': work_order_nr,
            'article_nr': base_order.get('article_nr', 'UNKNOWN'),
            'final_quantity': total_final_quantity,
            'quantity_total': total_quantity,
            'maker_code': ','.join(sorted(maker_codes)) if maker_codes else None,
            'feeder_code': ','.join(sorted(feeder_codes)) if feeder_codes else None,
            'planned_start': min(start_times) if start_times else None,
            'planned_end': max(end_times) if end_times else None,
            'schedule_status': 'COMPLETED',  # 经过并行处理后的状态
            'sync_group_id': base_order.get('sync_group_id'),
            'is_backup': base_order.get('is_backup', False),
            'backup_reason': base_order.get('backup_reason'),
            'generated_from_stage': 'work_order_generation',  # 标记来源
            'created_time': datetime.now()
        }
        
        logger.info(f"生成工单调度记录: {work_order_nr} - 机台组合: {schedule_record['maker_code']}+{schedule_record['feeder_code']}")
        
        return schedule_record


def create_work_order_generation() -> WorkOrderGeneration:
    """
    创建工单生成算法实例
    
    Returns:
        WorkOrderGeneration: 工单生成算法实例
    """
    return WorkOrderGeneration()


def generate_mes_work_orders(parallel_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    快速MES工单生成
    
    Args:
        parallel_orders: 并行处理后的工单数据
        
    Returns:
        List[Dict]: 生成的MES规范工单列表
    """
    generator = create_work_order_generation()
    result = generator.process(parallel_orders)
    return result.output_data
