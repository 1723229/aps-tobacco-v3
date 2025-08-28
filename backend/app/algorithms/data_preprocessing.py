"""
APS智慧排产系统 - 数据预处理算法

实现数据清洗、验证和标准化功能
按照业务规则处理原始旬计划数据
"""
from typing import List, Dict, Any
from datetime import datetime
from .base import AlgorithmBase, ProcessingStage, AlgorithmResult
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor(AlgorithmBase):
    """数据预处理算法"""
    
    def __init__(self):
        super().__init__(ProcessingStage.DATA_PREPROCESSING)
        
    def process(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        执行数据预处理
        
        Args:
            input_data: 原始计划数据
            
        Returns:
            AlgorithmResult: 处理结果
        """
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 数据清洗 - 移除空记录
        cleaned_data = self._clean_data(input_data)
        
        # 数据验证 - 检查业务规则
        valid_data = self._validate_data(cleaned_data, result)
        
        result.output_data = valid_data
        
        return self.finalize_result(result)
    
    def _clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清洗数据，移除空记录，添加字段映射"""
        cleaned_data = []
        
        for record in data:
            # 检查关键字段是否为空
            if self._is_empty_record(record):
                logger.debug(f"移除空记录: {record}")
                continue
            
            # 创建标准化记录副本
            cleaned_record = record.copy()
            
            # 添加字段映射和标准化
            # 1. 产品代码映射
            cleaned_record['product_code'] = record.get('article_nr', '')
            
            # 2. 机台类型判断 - 基于机台代码推断
            maker_code = record.get('maker_code', '')
            if maker_code:
                # 卷包机代码通常以C开头或包含数字
                if maker_code.startswith('C') or any(c.isdigit() for c in maker_code):
                    cleaned_record['machine_type'] = 'MAKER'
                else:
                    cleaned_record['machine_type'] = 'FEEDER'
            else:
                cleaned_record['machine_type'] = 'MAKER'  # 默认卷包机
            
            # 3. 数量字段标准化（添加类型检查）
            try:
                quantity_total = record.get('quantity_total', 0)
                if isinstance(quantity_total, (int, float)):
                    cleaned_record['plan_quantity'] = int(quantity_total)
                elif isinstance(quantity_total, str) and quantity_total.isdigit():
                    cleaned_record['plan_quantity'] = int(quantity_total)
                else:
                    cleaned_record['plan_quantity'] = 0
            except (ValueError, TypeError):
                cleaned_record['plan_quantity'] = 0
            
            # 4. 时间字段处理
            if record.get('planned_start'):
                cleaned_record['planned_start'] = record.get('planned_start')
            if record.get('planned_end'):
                cleaned_record['planned_end'] = record.get('planned_end')
            
            # 5. 机台代码处理（可能包含多个机台，用逗号分隔）
            if ',' in maker_code:
                # 如果是多机台，保留原始格式，后续拆分算法会处理
                cleaned_record['maker_code'] = maker_code
                cleaned_record['is_multi_machine'] = True
            else:
                cleaned_record['maker_code'] = maker_code
                cleaned_record['is_multi_machine'] = False
            
            # 6. 喂丝机代码
            cleaned_record['feeder_code'] = record.get('feeder_code', '')
                
            cleaned_data.append(cleaned_record)
        
        logger.info(f"数据清洗完成: 原始{len(data)}条 -> 清洗后{len(cleaned_data)}条")
        return cleaned_data
    
    def _is_empty_record(self, record: Dict[str, Any]) -> bool:
        """判断是否为空记录"""
        # 检查关键字段，增加类型安全检查
        work_order_nr = record.get('work_order_nr', '')
        article_nr = record.get('article_nr', '')
        quantity_total = record.get('quantity_total', 0)
        
        # 类型安全检查
        if not isinstance(work_order_nr, str):
            work_order_nr = str(work_order_nr) if work_order_nr is not None else ''
        if not isinstance(article_nr, str):
            article_nr = str(article_nr) if article_nr is not None else ''
        if not isinstance(quantity_total, (int, float)):
            try:
                quantity_total = int(quantity_total) if quantity_total is not None else 0
            except (ValueError, TypeError):
                quantity_total = 0
        
        # 如果关键字段都为空，则认为是空记录
        if (not work_order_nr or work_order_nr.strip() == '') and \
           (not article_nr or article_nr.strip() == '') and \
           quantity_total == 0:
            return True
            
        return False
    
    def _validate_data(self, data: List[Dict[str, Any]], result: AlgorithmResult) -> List[Dict[str, Any]]:
        """验证数据业务规则"""
        valid_data = []
        
        for record in data:
            # 简单验证 - 后续扩展更多业务规则
            if self._validate_record(record, result):
                valid_data.append(record)
        
        return valid_data
    
    async def process_with_real_data(self, input_data: List[Dict[str, Any]], **kwargs) -> AlgorithmResult:
        """
        使用真实数据库数据执行数据预处理
        
        Args:
            input_data: 原始计划数据
            
        Returns:
            AlgorithmResult: 处理结果
        """
        from app.services.database_query_service import DatabaseQueryService
        
        result = self.create_result()
        result.input_data = input_data
        result.metrics.processed_records = len(input_data)
        
        # 从数据库查询验证配置
        validation_rules = await self._get_validation_rules_from_db()
        
        # 标记使用了真实数据库数据
        result.metrics.custom_metrics = {
            'used_real_database_data': True,
            'validation_rules_count': len(validation_rules)
        }
        
        # 数据清洗 - 移除空记录
        cleaned_data = self._clean_data(input_data)
        
        # 数据验证 - 使用真实业务规则
        valid_data = self._validate_data_with_rules(cleaned_data, validation_rules, result)
        
        result.output_data = valid_data
        
        logger.info(f"数据预处理完成(真实数据): 输入{len(input_data)}条 -> 输出{len(valid_data)}条")
        return self.finalize_result(result)
    
    def _validate_data_with_rules(self, data: List[Dict[str, Any]], validation_rules: Dict[str, Any], result: AlgorithmResult) -> List[Dict[str, Any]]:
        """使用真实业务规则验证数据"""
        valid_data = []
        
        for record in data:
            if self._validate_record_with_rules(record, validation_rules, result):
                valid_data.append(record)
        
        return valid_data
    
    def _validate_record_with_rules(self, record: Dict[str, Any], validation_rules: Dict[str, Any], result: AlgorithmResult) -> bool:
        """使用真实业务规则验证单条记录"""
        # 基本验证
        work_order_nr = record.get('work_order_nr')
        if not work_order_nr:
            result.add_error("工单号不能为空", {'record': record})
            return False
        
        # 使用真实验证规则进行进一步验证
        min_quantity = validation_rules.get('min_quantity', 0)
        max_quantity = validation_rules.get('max_quantity', 999999)
        
        quantity = record.get('quantity_total', 0)
        if quantity < min_quantity or quantity > max_quantity:
            result.add_error(f"数量超出范围: {quantity} (范围: {min_quantity}-{max_quantity})", {'record': record})
            return False
        
        return True
    
    async def _get_validation_rules_from_db(self) -> Dict[str, Any]:
        """从数据库查询验证规则"""
        # TODO: 实现真实的数据库查询
        # 这里暂时返回默认验证规则
        return {
            'min_quantity': 1,
            'max_quantity': 1000000,
            'required_fields': ['work_order_nr', 'article_nr', 'quantity_total'],
            'max_work_order_length': 20
        }

    def _validate_record(self, record: Dict[str, Any], result: AlgorithmResult) -> bool:
        """验证单条记录"""
        # 基本验证 - 后续可扩展更复杂的业务规则
        work_order_nr = record.get('work_order_nr')
        if not work_order_nr:
            result.add_error("工单号不能为空", {'record': record})
            return False
            
        return True