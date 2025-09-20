"""
APS智慧排产系统 - 结果处理器

负责处理排产结果的最终处理、机台映射、数据保存和结果格式化。

核心职责：
1. 排产结果后处理和格式化
2. 正确的卷包机→喂丝机映射应用
3. 数据保存到aps_monthly_schedule_result表
4. 任务状态更新到aps_monthly_scheduling_task表
5. 结果摘要和统计信息生成
6. API响应格式化
7. 结果验证和数据清理

技术特性：
- 异步数据库操作和事务管理
- 批量数据保存优化
- 完整的错误处理和回滚机制
- 灵活的结果格式化选项
- 详细的操作日志和监控
- 结果导出和报告生成
- 数据一致性保证
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, insert, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import logging
import json
import uuid
from decimal import Decimal

from app.models.monthly_schedule_result_models import MonthlyScheduleResult
from app.models.monthly_task_models import MonthlySchedulingTask

logger = logging.getLogger(__name__)


class ResultProcessor:
    """
    结果处理器
    
    职责：
    1. 处理和格式化排产结果
    2. 应用正确的机台关系映射
    3. 保存结果到数据库
    4. 生成结果摘要和统计
    5. 格式化API响应
    6. 处理结果验证和清理
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._processing_config = {
            'batch_size': 100,              # 批量保存大小
            'enable_validation': True,       # 启用结果验证
            'auto_cleanup': True,           # 自动清理旧结果
            'generate_reports': True,       # 生成详细报告
            'save_intermediate': False      # 保存中间结果
        }
        self._processing_stats = {
            'total_results': 0,
            'saved_results': 0,
            'failed_results': 0,
            'processing_time': 0.0
        }
    
    async def process_scheduling_results(
        self,
        scheduled_results: List[Dict],
        monthly_batch_id: str,
        task_id: str,
        machine_relations: Dict[str, Dict],
        validation_result: Optional[Dict[str, Any]] = None,
        processing_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        处理完整的排产结果
        
        Args:
            scheduled_results: 排产结果列表
            monthly_batch_id: 月度批次ID
            task_id: 任务ID
            machine_relations: 机台关系映射
            validation_result: 验证结果
            processing_config: 处理配置
            
        Returns:
            处理结果报告
        """
        start_time = datetime.now()
        logger.info(f"开始处理排产结果: {len(scheduled_results)} 个结果")
        
        # 更新处理配置
        if processing_config:
            self._processing_config.update(processing_config)
        
        # 初始化统计信息
        self._processing_stats = {
            'total_results': len(scheduled_results),
            'saved_results': 0,
            'failed_results': 0,
            'processing_time': 0.0,
            'task_id': task_id,
            'monthly_batch_id': monthly_batch_id
        }
        
        processing_result = {
            'success': True,
            'task_id': task_id,
            'monthly_batch_id': monthly_batch_id,
            'processed_results': [],
            'processing_summary': {},
            'error_details': [],
            'recommendations': []
        }
        
        try:
            # 1. 清理旧结果（如果启用）
            if self._processing_config['auto_cleanup']:
                await self._cleanup_old_results(monthly_batch_id)
            
            # 2. 预处理排产结果
            processed_results = self._preprocess_results(
                scheduled_results, machine_relations
            )
            logger.info(f"预处理完成: {len(processed_results)} 个结果")
            
            # 3. 验证结果（如果启用）
            if self._processing_config['enable_validation']:
                validation_errors = await self._validate_results_before_save(processed_results)
                if validation_errors:
                    processing_result['error_details'].extend(validation_errors)
                    if any(error['level'] == 'CRITICAL' for error in validation_errors):
                        processing_result['success'] = False
                        logger.error(f"结果验证失败: {len(validation_errors)} 个错误")
                        return processing_result
            
            # 4. 批量保存结果
            saved_count = await self._batch_save_results(processed_results)
            self._processing_stats['saved_results'] = saved_count
            
            # 5. 更新任务状态
            await self._update_task_status(
                task_id, 'COMPLETED', len(processed_results), validation_result
            )
            
            # 6. 生成处理摘要
            processing_result['processing_summary'] = self._generate_processing_summary(
                processed_results, validation_result
            )
            
            # 7. 格式化最终结果
            processing_result['processed_results'] = self._format_api_results(processed_results)
            
            # 8. 生成建议和报告
            if self._processing_config['generate_reports']:
                processing_result['recommendations'] = self._generate_recommendations(
                    processed_results, validation_result
                )
            
            # 计算处理时间
            self._processing_stats['processing_time'] = (
                datetime.now() - start_time
            ).total_seconds()
            
            logger.info(f"排产结果处理完成: 成功保存 {saved_count} 个结果, "
                       f"耗时 {self._processing_stats['processing_time']:.2f} 秒")
            
            return processing_result
            
        except Exception as e:
            logger.error(f"排产结果处理失败: {str(e)}")
            processing_result['success'] = False
            processing_result['error_details'].append({
                'level': 'CRITICAL',
                'type': 'PROCESSING_ERROR',
                'message': f"结果处理失败: {str(e)}"
            })
            
            # 更新任务状态为失败
            await self._update_task_status(task_id, 'FAILED', 0, None, str(e))
            
            return processing_result
    
    def _preprocess_results(
        self, 
        scheduled_results: List[Dict], 
        machine_relations: Dict[str, Dict]
    ) -> List[Dict]:
        """
        预处理排产结果
        
        Args:
            scheduled_results: 原始排产结果
            machine_relations: 机台关系映射
            
        Returns:
            预处理后的结果列表
        """
        processed_results = []
        
        for result in scheduled_results:
            try:
                # 1. 基础数据处理
                processed_result = self._process_single_result(result)
                
                # 2. 应用机台关系映射
                processed_result = self._apply_machine_mapping(
                    processed_result, machine_relations
                )
                
                # 3. 生成唯一标识
                processed_result['result_id'] = str(uuid.uuid4())
                
                # 4. 数据格式标准化
                processed_result = self._standardize_result_format(processed_result)
                
                processed_results.append(processed_result)
                
            except Exception as e:
                logger.error(f"预处理单个结果失败: {str(e)}")
                self._processing_stats['failed_results'] += 1
                continue
        
        return processed_results
    
    def _process_single_result(self, result: Dict) -> Dict:
        """
        处理单个排产结果
        
        Args:
            result: 单个排产结果
            
        Returns:
            处理后的结果
        """
        processed = result.copy()
        
        # 1. 时间格式标准化
        if isinstance(processed.get('scheduled_start_time'), str):
            processed['scheduled_start_time'] = datetime.fromisoformat(
                processed['scheduled_start_time']
            )
        if isinstance(processed.get('scheduled_end_time'), str):
            processed['scheduled_end_time'] = datetime.fromisoformat(
                processed['scheduled_end_time']
            )
        
        # 2. 数值格式处理
        numeric_fields = [
            'target_quantity_boxes', 'scheduled_duration_hours',
            'estimated_speed', 'efficiency_rate', 'utilization_rate'
        ]
        for field in numeric_fields:
            if field in processed and processed[field] is not None:
                processed[field] = float(processed[field])
        
        # 3. 计算衍生字段
        if ('scheduled_start_time' in processed and 
            'scheduled_end_time' in processed):
            duration = processed['scheduled_end_time'] - processed['scheduled_start_time']
            processed['actual_duration_hours'] = duration.total_seconds() / 3600
        
        # 4. 添加状态字段
        processed['schedule_status'] = 'SCHEDULED'
        processed['execution_status'] = 'PENDING'
        
        return processed
    
    def _apply_machine_mapping(
        self, 
        result: Dict, 
        machine_relations: Dict[str, Dict]
    ) -> Dict:
        """
        应用机台关系映射
        
        Args:
            result: 排产结果
            machine_relations: 机台关系映射
            
        Returns:
            应用映射后的结果
        """
        maker_code = result.get('assigned_maker_code')
        
        if maker_code:
            # 查找对应的喂丝机
            expected_feeder = machine_relations['maker_to_feeder'].get(maker_code)
            
            if expected_feeder:
                # 更新或验证喂丝机分配
                if 'assigned_feeder_code' not in result or not result['assigned_feeder_code']:
                    result['assigned_feeder_code'] = expected_feeder
                elif result['assigned_feeder_code'] != expected_feeder:
                    logger.warning(f"机台映射不一致: 卷包机 {maker_code}, "
                                 f"分配喂丝机 {result['assigned_feeder_code']}, "
                                 f"期望喂丝机 {expected_feeder}")
                    # 使用正确的映射关系
                    result['assigned_feeder_code'] = expected_feeder
                    result['mapping_corrected'] = True
                
                # 添加关系信息
                feeder_info = machine_relations['feeder_to_makers'].get(expected_feeder, [])
                for info in feeder_info:
                    if info['maker_code'] == maker_code:
                        result['machine_relation_priority'] = info.get('priority', 1)
                        result['machine_relation_type'] = info.get('relation_type', 'NORMAL')
                        break
            else:
                logger.error(f"未找到卷包机 {maker_code} 的喂丝机映射关系")
                result['mapping_error'] = f"缺少机台关系映射: {maker_code}"
        
        return result
    
    def _standardize_result_format(self, result: Dict) -> Dict:
        """
        标准化结果格式
        
        Args:
            result: 原始结果
            
        Returns:
            标准化后的结果
        """
        # 定义标准字段映射（基于实际数据库模型字段）
        field_mapping = {
            'monthly_task_id': 'monthly_task_id',
            'monthly_plan_id': 'monthly_plan_id', 
            'monthly_batch_id': 'monthly_batch_id',
            'work_order_nr': 'work_order_nr',
            'article_nr': 'article_nr',
            'target_quantity_boxes': 'allocated_boxes',  # 映射到数据库字段allocated_boxes
            'assigned_maker_code': 'assigned_maker_code',
            'assigned_feeder_code': 'assigned_feeder_code',
            'scheduled_start_time': 'scheduled_start_time',
            'scheduled_end_time': 'scheduled_end_time',
            'scheduled_duration_hours': 'scheduled_duration_hours',
            'estimated_speed': 'estimated_speed',
            'algorithm_version': 'algorithm_version',
            'priority_score': 'priority_score'
        }
        
        standardized = {}
        
        # 映射标准字段
        for source_field, target_field in field_mapping.items():
            if source_field in result:
                standardized[target_field] = result[source_field]
        
        # 添加其他必要信息到optimization_notes字段
        optimization_notes = {
            'efficiency_rate': result.get('efficiency_rate'),
            'utilization_rate': result.get('utilization_rate'),
            'calculation_details': result.get('calculation_details', {}),
            'scheduling_timestamp': str(result.get('scheduling_timestamp', datetime.now()))
        }
        
        # 将优化信息保存为JSON字符串（使用数据库中实际存在的字段）
        standardized['optimization_notes'] = json.dumps(optimization_notes, default=str, ensure_ascii=False)
        
        # 添加状态和元数据（使用数据库中实际存在的字段）
        standardized['schedule_status'] = result.get('schedule_status', 'SCHEDULED')
        standardized['created_by'] = 'APS_ALGORITHM'
        
        return standardized
    
    async def _validate_results_before_save(self, results: List[Dict]) -> List[Dict]:
        """
        保存前验证结果
        
        Args:
            results: 待验证的结果列表
            
        Returns:
            验证错误列表
        """
        validation_errors = []
        
        required_fields = [
            'monthly_plan_id', 'article_nr', 'allocated_boxes',
            'assigned_maker_code', 'assigned_feeder_code',
            'scheduled_start_time', 'scheduled_end_time'
        ]
        
        for i, result in enumerate(results):
            # 1. 检查必需字段
            for field in required_fields:
                if field not in result or result[field] is None:
                    validation_errors.append({
                        'level': 'CRITICAL',
                        'type': 'MISSING_REQUIRED_FIELD',
                        'result_index': i,
                        'field': field,
                        'message': f"结果 {i} 缺少必需字段: {field}"
                    })
            
            # 2. 检查数据类型
            if 'target_quantity' in result:
                if not isinstance(result['target_quantity'], (int, float)) or result['target_quantity'] <= 0:
                    validation_errors.append({
                        'level': 'CRITICAL',
                        'type': 'INVALID_QUANTITY',
                        'result_index': i,
                        'value': result['target_quantity'],
                        'message': f"结果 {i} 目标数量无效"
                    })
            
            # 3. 检查时间逻辑
            if ('scheduled_start_time' in result and 
                'scheduled_end_time' in result):
                if result['scheduled_start_time'] >= result['scheduled_end_time']:
                    validation_errors.append({
                        'level': 'CRITICAL',
                        'type': 'INVALID_TIME_RANGE',
                        'result_index': i,
                        'message': f"结果 {i} 时间范围无效"
                    })
            
            # 4. 检查机台映射
            if 'mapping_error' in result:
                validation_errors.append({
                    'level': 'CRITICAL',
                    'type': 'MACHINE_MAPPING_ERROR',
                    'result_index': i,
                    'message': result['mapping_error']
                })
        
        return validation_errors
    
    async def _batch_save_results(self, results: List[Dict]) -> int:
        """
        批量保存结果到数据库
        
        Args:
            results: 要保存的结果列表
            
        Returns:
            成功保存的数量
        """
        if not results:
            return 0
        
        saved_count = 0
        batch_size = self._processing_config['batch_size']
        
        try:
            # 分批处理
            for i in range(0, len(results), batch_size):
                batch = results[i:i + batch_size]
                
                # 准备批量插入数据
                insert_data = []
                for result in batch:
                    # 创建数据库记录，只使用数据库模型中实际存在的字段
                    record_data = {
                        'monthly_task_id': result.get('monthly_task_id'),
                        'monthly_plan_id': result.get('monthly_plan_id'),
                        'monthly_batch_id': result.get('monthly_batch_id'),
                        'work_order_nr': result.get('work_order_nr'),
                        'article_nr': result.get('article_nr'),
                        'allocated_boxes': result.get('allocated_boxes'),  # 使用正确的字段名
                        'assigned_maker_code': result.get('assigned_maker_code'),
                        'assigned_feeder_code': result.get('assigned_feeder_code'),
                        'scheduled_start_time': result.get('scheduled_start_time'),
                        'scheduled_end_time': result.get('scheduled_end_time'),
                        'scheduled_duration_hours': result.get('scheduled_duration_hours'),
                        'estimated_speed': result.get('estimated_speed'),
                        'algorithm_version': result.get('algorithm_version'),
                        'priority_score': result.get('priority_score'),
                        'optimization_notes': result.get('optimization_notes'),
                        'schedule_status': result.get('schedule_status', 'SCHEDULED'),
                        'created_by': result.get('created_by', 'APS_ALGORITHM')
                    }
                    insert_data.append(record_data)
                
                # 执行批量插入
                stmt = insert(MonthlyScheduleResult).values(insert_data)
                await self.db.execute(stmt)
                
                saved_count += len(batch)
                logger.debug(f"批量保存完成: {saved_count}/{len(results)}")
            
            # 提交事务
            await self.db.commit()
            logger.info(f"成功保存 {saved_count} 个排产结果")
            
            return saved_count
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"批量保存失败: {str(e)}")
            raise Exception(f"数据库保存失败: {str(e)}")
    
    async def _cleanup_old_results(self, monthly_batch_id: str) -> None:
        """
        清理旧的排产结果
        
        Args:
            monthly_batch_id: 月度批次ID
        """
        try:
            # 删除该批次的旧结果
            delete_stmt = delete(MonthlyScheduleResult).where(
                MonthlyScheduleResult.monthly_batch_id == monthly_batch_id
            )
            result = await self.db.execute(delete_stmt)
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"清理旧结果: 删除 {deleted_count} 条记录")
            
            await self.db.commit()
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"清理旧结果失败: {str(e)}")
            # 不抛出异常，继续执行
    
    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        result_count: int,
        validation_result: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            result_count: 结果数量
            validation_result: 验证结果
            error_message: 错误信息
        """
        try:
            # 准备更新数据 - 只使用任务模型中实际存在的字段
            update_data = {
                'task_status': status
            }
            
            if error_message:
                update_data['error_message'] = error_message
            
            # 执行更新
            update_stmt = update(MonthlySchedulingTask).where(
                MonthlySchedulingTask.task_id == task_id
            ).values(update_data)
            
            await self.db.execute(update_stmt)
            await self.db.commit()
            
            logger.info(f"任务状态更新: {task_id} -> {status}")
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"任务状态更新失败: {str(e)}")
            # 不抛出异常，避免影响主流程
    
    def _generate_processing_summary(
        self,
        processed_results: List[Dict],
        validation_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        生成处理摘要
        
        Args:
            processed_results: 处理后的结果
            validation_result: 验证结果
            
        Returns:
            处理摘要
        """
        # 基础统计
        summary = {
            'total_processed': len(processed_results),
            'processing_time_seconds': self._processing_stats['processing_time'],
            'success_rate': (
                (len(processed_results) - self._processing_stats['failed_results']) 
                / max(1, self._processing_stats['total_results'])
            ),
            'machine_statistics': {},
            'time_statistics': {},
            'product_statistics': {}
        }
        
        if not processed_results:
            return summary
        
        # 机台统计
        machine_stats = {}
        product_stats = {}
        time_ranges = []
        
        for result in processed_results:
            # 机台统计
            maker_code = result.get('assigned_maker_code')
            if maker_code:
                if maker_code not in machine_stats:
                    machine_stats[maker_code] = {
                        'schedule_count': 0,
                        'total_hours': 0.0,
                        'total_quantity': 0,
                        'products': []
                    }
                machine_stats[maker_code]['schedule_count'] += 1
                machine_stats[maker_code]['total_hours'] += result.get('scheduled_duration_hours', 0)
                machine_stats[maker_code]['total_quantity'] += result.get('allocated_boxes', 0)  # 使用正确的字段名
                machine_stats[maker_code]['products'].append(result.get('article_nr'))
            
            # 产品统计
            article_nr = result.get('article_nr')
            if article_nr:
                if article_nr not in product_stats:
                    product_stats[article_nr] = {
                        'total_quantity': 0,
                        'machine_count': 0,
                        'total_hours': 0.0,
                        'machines': set()
                    }
                product_stats[article_nr]['total_quantity'] += result.get('allocated_boxes', 0)  # 使用正确的字段名
                product_stats[article_nr]['total_hours'] += result.get('scheduled_duration_hours', 0)
                if maker_code:
                    product_stats[article_nr]['machines'].add(maker_code)
        
        # 转换集合为列表以便序列化
        for stats in product_stats.values():
            stats['machine_count'] = len(stats['machines'])
            stats['machines'] = list(stats['machines'])
        
        # 时间统计
        if processed_results:
            start_times = [r['scheduled_start_time'] for r in processed_results 
                          if r.get('scheduled_start_time')]
            end_times = [r['scheduled_end_time'] for r in processed_results 
                        if r.get('scheduled_end_time')]
            
            if start_times and end_times:
                summary['time_statistics'] = {
                    'earliest_start': min(start_times),
                    'latest_end': max(end_times),
                    'total_span_hours': (max(end_times) - min(start_times)).total_seconds() / 3600,
                    'average_duration': sum(
                        r.get('scheduled_duration_hours', 0) for r in processed_results
                    ) / len(processed_results)
                }
        
        summary['machine_statistics'] = machine_stats
        summary['product_statistics'] = product_stats
        
        # 添加验证结果摘要
        if validation_result:
            summary['validation_summary'] = {
                'valid': validation_result.get('valid', False),
                'total_violations': validation_result.get('total_violations', 0),
                'critical_violations': validation_result.get('critical_violations', 0),
                'warning_violations': validation_result.get('warning_violations', 0)
            }
        
        return summary
    
    def _format_api_results(self, processed_results: List[Dict]) -> List[Dict]:
        """
        格式化API响应结果
        
        Args:
            processed_results: 处理后的结果
            
        Returns:
            格式化的API结果
        """
        api_results = []
        
        for result in processed_results:
            # 选择API需要的字段
            api_result = {
                'monthly_plan_id': result.get('monthly_plan_id'),
                'work_order_nr': result.get('work_order_nr'),
                'article_nr': result.get('article_nr'),
                'allocated_boxes': result.get('allocated_boxes'),  # 使用正确的字段名
                'assigned_maker_code': result.get('assigned_maker_code'),
                'assigned_feeder_code': result.get('assigned_feeder_code'),
                'scheduled_start_time': result.get('scheduled_start_time'),
                'scheduled_end_time': result.get('scheduled_end_time'),
                'scheduled_duration_hours': result.get('scheduled_duration_hours'),
                'schedule_status': result.get('schedule_status'),
                'estimated_speed': result.get('estimated_speed'),
                'efficiency_rate': result.get('efficiency_rate')
            }
            
            # 处理时间格式
            for time_field in ['scheduled_start_time', 'scheduled_end_time']:
                if api_result.get(time_field):
                    api_result[time_field] = api_result[time_field].isoformat()
            
            api_results.append(api_result)
        
        return api_results
    
    def _generate_recommendations(
        self,
        processed_results: List[Dict],
        validation_result: Optional[Dict] = None
    ) -> List[str]:
        """
        生成处理建议
        
        Args:
            processed_results: 处理后的结果
            validation_result: 验证结果
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if not processed_results:
            recommendations.append("未生成任何排产结果，建议检查输入数据和算法配置")
            return recommendations
        
        # 基于处理统计的建议
        stats = self._processing_stats
        
        if stats['failed_results'] > 0:
            failure_rate = stats['failed_results'] / stats['total_results']
            if failure_rate > 0.1:  # 失败率超过10%
                recommendations.append(
                    f"结果处理失败率较高 ({failure_rate:.1%})，建议检查数据质量和处理逻辑"
                )
        
        # 基于验证结果的建议
        if validation_result and not validation_result.get('valid', True):
            critical_count = validation_result.get('critical_violations', 0)
            if critical_count > 0:
                recommendations.append(
                    f"发现 {critical_count} 个严重验证错误，建议重新运行算法或检查配置"
                )
        
        # 基于机台利用率的建议
        machine_stats = {}
        for result in processed_results:
            maker_code = result.get('assigned_maker_code')
            if maker_code:
                if maker_code not in machine_stats:
                    machine_stats[maker_code] = 0
                machine_stats[maker_code] += 1
        
        if machine_stats:
            max_usage = max(machine_stats.values())
            min_usage = min(machine_stats.values())
            
            if max_usage / min_usage > 3:  # 负载不均衡
                recommendations.append(
                    "机台负载分布不均衡，建议优化负载均衡算法"
                )
        
        # 基于时间分布的建议
        if len(processed_results) > 0:
            durations = [r.get('scheduled_duration_hours', 0) for r in processed_results]
            avg_duration = sum(durations) / len(durations)
            
            if avg_duration < 1:  # 平均时长过短
                recommendations.append(
                    "平均排产时长较短，可能存在频繁的机台切换，建议合并小批量任务"
                )
        
        if not recommendations:
            recommendations.append("排产结果处理正常，所有检查均通过")
        
        return recommendations
    
    async def get_saved_results(
        self,
        monthly_batch_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取已保存的排产结果
        
        Args:
            monthly_batch_id: 月度批次ID
            limit: 结果数量限制
            
        Returns:
            排产结果列表
        """
        try:
            query = select(MonthlyScheduleResult).where(
                MonthlyScheduleResult.monthly_batch_id == monthly_batch_id
            ).order_by(MonthlyScheduleResult.scheduled_start_time)
            
            if limit:
                query = query.limit(limit)
            
            result = await self.db.execute(query)
            records = result.scalars().all()
            
            # 转换为字典格式
            results = []
            for record in records:
                result_dict = {
                    'monthly_plan_id': record.monthly_plan_id,
                    'work_order_nr': record.work_order_nr,
                    'article_nr': record.article_nr,
                    'allocated_boxes': record.allocated_boxes,  # 使用正确的字段名
                    'assigned_maker_code': record.assigned_maker_code,
                    'assigned_feeder_code': record.assigned_feeder_code,
                    'scheduled_start_time': record.scheduled_start_time,
                    'scheduled_end_time': record.scheduled_end_time,
                    'scheduled_duration_hours': record.scheduled_duration_hours,
                    'schedule_status': record.schedule_status
                }
                
                # 解析优化信息
                if hasattr(record, 'optimization_notes') and record.optimization_notes:
                    try:
                        optimization_details = json.loads(record.optimization_notes)
                        result_dict.update(optimization_details)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                results.append(result_dict)
            
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"获取保存结果失败: {str(e)}")
            return []
    
    async def export_results_report(
        self,
        monthly_batch_id: str,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        导出结果报告
        
        Args:
            monthly_batch_id: 月度批次ID
            include_details: 是否包含详细信息
            
        Returns:
            结果报告
        """
        try:
            # 获取排产结果
            results = await self.get_saved_results(monthly_batch_id)
            
            if not results:
                return {
                    'monthly_batch_id': monthly_batch_id,
                    'export_timestamp': datetime.now(),
                    'total_results': 0,
                    'message': '未找到排产结果'
                }
            
            # 生成报告
            report = {
                'monthly_batch_id': monthly_batch_id,
                'export_timestamp': datetime.now(),
                'total_results': len(results),
                'summary_statistics': self._calculate_result_statistics(results),
                'processing_info': self._processing_stats
            }
            
            if include_details:
                report['detailed_results'] = results
                report['machine_breakdown'] = self._generate_machine_breakdown(results)
                report['time_analysis'] = self._generate_time_analysis(results)
            
            return report
            
        except Exception as e:
            logger.error(f"导出结果报告失败: {str(e)}")
            return {
                'monthly_batch_id': monthly_batch_id,
                'export_timestamp': datetime.now(),
                'error': str(e)
            }
    
    def _calculate_result_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """计算结果统计信息"""
        if not results:
            return {}
        
        total_quantity = sum(r.get('allocated_boxes', 0) for r in results)  # 使用正确的字段名
        total_hours = sum(r.get('scheduled_duration_hours', 0) for r in results)
        
        machines = set(r.get('assigned_maker_code') for r in results if r.get('assigned_maker_code'))
        products = set(r.get('article_nr') for r in results if r.get('article_nr'))
        
        start_times = [r['scheduled_start_time'] for r in results if r.get('scheduled_start_time')]
        end_times = [r['scheduled_end_time'] for r in results if r.get('scheduled_end_time')]
        
        statistics = {
            'total_quantity_boxes': total_quantity,
            'total_scheduled_hours': round(total_hours, 2),
            'unique_machines': len(machines),
            'unique_products': len(products),
            'average_duration_hours': round(total_hours / len(results), 2),
            'average_quantity_per_order': round(total_quantity / len(results), 0)
        }
        
        if start_times and end_times:
            statistics.update({
                'earliest_start': min(start_times),
                'latest_end': max(end_times),
                'total_timespan_hours': round(
                    (max(end_times) - min(start_times)).total_seconds() / 3600, 2
                )
            })
        
        return statistics
    
    def _generate_machine_breakdown(self, results: List[Dict]) -> Dict[str, Dict]:
        """生成机台分解统计"""
        machine_breakdown = {}
        
        for result in results:
            maker_code = result.get('assigned_maker_code')
            if not maker_code:
                continue
            
            if maker_code not in machine_breakdown:
                machine_breakdown[maker_code] = {
                    'total_orders': 0,
                    'total_quantity': 0,
                    'total_hours': 0.0,
                    'products': [],
                    'feeder_code': result.get('assigned_feeder_code')
                }
            
            breakdown = machine_breakdown[maker_code]
            breakdown['total_orders'] += 1
            breakdown['total_quantity'] += result.get('allocated_boxes', 0)  # 使用正确的字段名
            breakdown['total_hours'] += result.get('scheduled_duration_hours', 0)
            breakdown['products'].append(result.get('article_nr'))
        
        return machine_breakdown
    
    def _generate_time_analysis(self, results: List[Dict]) -> Dict[str, Any]:
        """生成时间分析"""
        if not results:
            return {}
        
        # 按日期分组
        daily_stats = {}
        for result in results:
            start_time = result.get('scheduled_start_time')
            if not start_time:
                continue
            
            date_key = start_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'orders': 0,
                    'total_hours': 0.0,
                    'machines': set()
                }
            
            daily_stats[date_key]['orders'] += 1
            daily_stats[date_key]['total_hours'] += result.get('scheduled_duration_hours', 0)
            if result.get('assigned_maker_code'):
                daily_stats[date_key]['machines'].add(result.get('assigned_maker_code'))
        
        # 转换集合为数量
        for stats in daily_stats.values():
            stats['unique_machines'] = len(stats['machines'])
            del stats['machines']
        
        return {
            'daily_breakdown': daily_stats,
            'analysis_period': {
                'total_days': len(daily_stats),
                'average_orders_per_day': round(
                    sum(stats['orders'] for stats in daily_stats.values()) / max(1, len(daily_stats)), 1
                ),
                'average_hours_per_day': round(
                    sum(stats['total_hours'] for stats in daily_stats.values()) / max(1, len(daily_stats)), 2
                )
            }
        }