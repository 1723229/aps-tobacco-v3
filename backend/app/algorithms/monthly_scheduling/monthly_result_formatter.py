"""
APS智慧排产系统 - 月度结果格式化算法模块 (T027)

月度排产结果格式化算法，将排产结果转换为各种业务需要的格式，
支持前端展示、业务分析、报告生成和数据导出等多种应用场景。

主要功能：
- 甘特图数据格式化（Vue Ganttastic 和 ECharts 兼容）
- 工单数据格式化和批量导出
- 统计报告生成和可视化数据
- Excel/PDF 报告生成
- 多语言和本地化支持
- 可视化数据和分析洞察
- CLI 支持和数据验证

技术特性：
- 基于BaseAlgorithm的异步算法架构
- 支持多种输出格式和样式定制
- 智能数据压缩和性能优化
- 完整的数据验证和错误处理
- 符合月度排产特化设计

依赖：
- app.algorithms.monthly_scheduling.base.BaseAlgorithm
- app.models.monthly_schedule_result_models.MonthlyScheduleResult
- app.models.monthly_plan_models.MonthlyPlan
"""

import asyncio
import json
import csv
import io
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import logging
import argparse
import base64
from collections import defaultdict, Counter
import statistics

from app.algorithms.monthly_scheduling.base import (
    BaseAlgorithm, AlgorithmType, Priority, MachineType,
    MonthlyPlanItem, ScheduleResult, MonthlySchedulingError
)


class OutputFormat(Enum):
    """输出格式枚举"""
    GANTT_CHART = "gantt_chart"           # 甘特图格式
    WORK_ORDERS = "work_orders"           # 工单格式
    STATISTICAL_REPORT = "statistical_report"  # 统计报告
    EXCEL_EXPORT = "excel_export"         # Excel导出
    PDF_REPORT = "pdf_report"             # PDF报告
    JSON_EXPORT = "json_export"           # JSON导出
    CSV_EXPORT = "csv_export"             # CSV导出
    ECHARTS_DATA = "echarts_data"         # ECharts数据格式
    VUE_GANTTASTIC = "vue_ganttastic"     # Vue Ganttastic格式


class ChartType(Enum):
    """图表类型枚举"""
    TIMELINE = "timeline"                 # 时间线图
    MACHINE_UTILIZATION = "machine_utilization"  # 机台利用率
    PRODUCTION_PROGRESS = "production_progress"  # 生产进度
    CAPACITY_ANALYSIS = "capacity_analysis"      # 容量分析
    PRIORITY_DISTRIBUTION = "priority_distribution"  # 优先级分布


class LocaleType(Enum):
    """本地化类型枚举"""
    ZH_CN = "zh_CN"  # 简体中文
    EN_US = "en_US"  # 英文
    ZH_TW = "zh_TW"  # 繁体中文


@dataclass
class FormatterConfig:
    """格式化器配置"""
    locale: LocaleType = LocaleType.ZH_CN
    time_zone: str = "Asia/Shanghai"
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_places: int = 2
    currency_symbol: str = "¥"
    enable_compression: bool = True
    include_metadata: bool = True
    color_scheme: str = "default"
    chart_width: int = 1200
    chart_height: int = 600
    
    # 甘特图特定配置
    gantt_bar_height: int = 30
    gantt_time_scale: str = "hour"  # hour, day, week
    gantt_show_dependencies: bool = True
    gantt_show_progress: bool = True
    
    # Excel 配置
    excel_sheet_name: str = "月度排产结果"
    excel_include_charts: bool = True
    excel_freeze_panes: bool = True
    
    # PDF 配置
    pdf_page_size: str = "A4"
    pdf_orientation: str = "landscape"  # portrait, landscape
    pdf_include_summary: bool = True


@dataclass
class GanttTask:
    """甘特图任务数据结构"""
    id: str
    name: str
    start: datetime
    end: datetime
    duration: float  # 小时
    progress: float = 0.0  # 0-100
    color: str = "#3498db"
    machine_code: str = ""
    article_nr: str = ""
    priority: str = "NORMAL"
    dependencies: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    is_milestone: bool = False
    
    def to_vue_ganttastic(self) -> Dict[str, Any]:
        """转换为Vue Ganttastic格式"""
        return {
            "id": self.id,
            "label": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "progress": self.progress,
            "style": {
                "backgroundColor": self.color,
                "borderColor": self.color,
                "color": "white"
            },
            "parentId": self.parent_id,
            "isMilestone": self.is_milestone,
            "dependencies": self.dependencies
        }
    
    def to_echarts_format(self) -> Dict[str, Any]:
        """转换为ECharts格式"""
        return {
            "name": self.name,
            "value": [
                self.machine_code,
                self.start.timestamp() * 1000,
                self.end.timestamp() * 1000,
                self.duration
            ],
            "itemStyle": {
                "normal": {
                    "color": self.color
                }
            }
        }


@dataclass
class WorkOrderData:
    """工单数据结构"""
    work_order_nr: str
    article_nr: str
    article_name: str
    quantity: Decimal
    machine_feeder: str
    machine_maker: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    priority: str
    duration_hours: float
    progress: float = 0.0
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "work_order_nr": self.work_order_nr,
            "article_nr": self.article_nr,
            "article_name": self.article_name,
            "quantity": float(self.quantity),
            "machine_feeder": self.machine_feeder,
            "machine_maker": self.machine_maker,
            "scheduled_start": self.scheduled_start.isoformat(),
            "scheduled_end": self.scheduled_end.isoformat(),
            "status": self.status,
            "priority": self.priority,
            "duration_hours": self.duration_hours,
            "progress": self.progress,
            "notes": self.notes or ""
        }


@dataclass
class StatisticalSummary:
    """统计摘要数据结构"""
    total_tasks: int
    total_work_orders: int
    total_production_hours: float
    total_quantity: Decimal
    makespan_hours: float
    machine_utilization: Dict[str, float]
    priority_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    avg_task_duration: float
    peak_concurrent_tasks: int
    start_date: datetime
    end_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_tasks": self.total_tasks,
            "total_work_orders": self.total_work_orders,
            "total_production_hours": self.total_production_hours,
            "total_quantity": float(self.total_quantity),
            "makespan_hours": self.makespan_hours,
            "machine_utilization": self.machine_utilization,
            "priority_distribution": self.priority_distribution,
            "status_distribution": self.status_distribution,
            "avg_task_duration": self.avg_task_duration,
            "peak_concurrent_tasks": self.peak_concurrent_tasks,
            "efficiency_rate": self.total_production_hours / self.makespan_hours if self.makespan_hours > 0 else 0,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }


class MonthlyResultFormatter(BaseAlgorithm):
    """
    月度结果格式化算法类
    
    负责将月度排产结果转换为各种业务需要的格式，
    支持前端展示、业务分析、报告生成和数据导出。
    """
    
    def __init__(self, config: Optional[FormatterConfig] = None):
        """
        初始化月度结果格式化器
        
        Args:
            config: 格式化器配置
        """
        super().__init__(AlgorithmType.MONTHLY_ENGINE, config)
        self.formatter_config = config or FormatterConfig()
        
        # 本地化配置
        self.locale_strings = self._load_locale_strings()
        
        # 颜色方案配置
        self.color_schemes = self._load_color_schemes()
        
        # 性能统计
        self.performance_stats = {
            "formats_generated": 0,
            "total_records_processed": 0,
            "average_processing_time": 0.0,
            "cache_hits": 0,
            "errors_handled": 0
        }
        
        # 结果缓存
        self.result_cache: Dict[str, Any] = {}
    
    async def execute(self, input_data: Any, **kwargs) -> Any:
        """
        执行格式化算法
        
        Args:
            input_data: 排产结果数据
            **kwargs: 额外参数（format_type, chart_type等）
            
        Returns:
            格式化后的结果
        """
        start_time = datetime.now()
        
        try:
            format_type = kwargs.get('format_type', OutputFormat.GANTT_CHART)
            if isinstance(format_type, str):
                format_type = OutputFormat(format_type)
            
            self.logger.info(f"开始格式化月度排产结果，格式：{format_type.value}")
            
            # 验证输入数据
            if not self.validate_input(input_data):
                raise ValueError("无效的输入数据")
            
            # 根据格式类型分发处理
            if format_type == OutputFormat.GANTT_CHART:
                result = await self.format_gantt_data(input_data, **kwargs)
            elif format_type == OutputFormat.WORK_ORDERS:
                result = await self.format_work_orders(input_data, **kwargs)
            elif format_type == OutputFormat.STATISTICAL_REPORT:
                result = await self.format_reports(input_data, **kwargs)
            elif format_type == OutputFormat.EXCEL_EXPORT:
                result = await self.format_excel_export(input_data, **kwargs)
            elif format_type == OutputFormat.PDF_REPORT:
                result = await self.format_pdf_report(input_data, **kwargs)
            elif format_type == OutputFormat.JSON_EXPORT:
                result = await self.format_json_export(input_data, **kwargs)
            elif format_type == OutputFormat.CSV_EXPORT:
                result = await self.format_csv_export(input_data, **kwargs)
            elif format_type == OutputFormat.ECHARTS_DATA:
                result = await self.format_echarts_data(input_data, **kwargs)
            elif format_type == OutputFormat.VUE_GANTTASTIC:
                result = await self.format_vue_ganttastic(input_data, **kwargs)
            else:
                raise ValueError(f"不支持的格式类型：{format_type}")
            
            # 更新性能统计
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(len(input_data) if isinstance(input_data, list) else 1, processing_time)
            
            return {
                "status": "success",
                "format_type": format_type.value,
                "data": result,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "processing_time_seconds": processing_time,
                    "record_count": len(input_data) if isinstance(input_data, list) else 1,
                    "formatter_version": self.version
                }
            }
            
        except Exception as e:
            self.logger.error(f"格式化失败: {str(e)}")
            self.performance_stats["errors_handled"] += 1
            raise MonthlySchedulingError(f"格式化失败: {str(e)}")
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            是否有效
        """
        if not input_data:
            return False
        
        # 如果是列表，检查每个元素
        if isinstance(input_data, list):
            if not input_data:
                return False
            # 检查第一个元素的结构
            sample = input_data[0]
            required_fields = ["monthly_schedule_id", "work_order_nr", "scheduled_start_time"]
            return all(hasattr(sample, field) for field in required_fields)
        
        # 如果是单个对象，检查必要字段
        if hasattr(input_data, 'monthly_schedule_id'):
            return True
        
        return False
    
    async def format_gantt_data(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化甘特图数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            甘特图数据字典
        """
        chart_type = kwargs.get('chart_type', ChartType.TIMELINE)
        include_dependencies = kwargs.get('include_dependencies', True)
        
        gantt_tasks = []
        machine_groups = defaultdict(list)
        
        for result in results:
            # 创建甘特图任务
            task = GanttTask(
                id=str(result.monthly_schedule_id),
                name=f"{result.article_nr} - {result.work_order_nr}",
                start=result.scheduled_start_time,
                end=result.scheduled_end_time,
                duration=float(result.scheduled_duration_hours or 0),
                machine_code=f"{result.assigned_feeder_code}/{result.assigned_maker_code}",
                article_nr=result.article_nr,
                priority=result.monthly_schedule_status or "NORMAL",
                progress=float(result.monthly_execution_progress or 0),
                color=self._get_priority_color(result.priority_score)
            )
            
            gantt_tasks.append(task)
            
            # 按机台分组
            machine_key = f"{result.assigned_feeder_code}+{result.assigned_maker_code}"
            machine_groups[machine_key].append(task)
        
        # 如果需要依赖关系，计算依赖
        if include_dependencies:
            self._calculate_dependencies(gantt_tasks)
        
        # 生成甘特图数据
        gantt_data = {
            "tasks": [task.to_vue_ganttastic() for task in gantt_tasks],
            "machine_groups": {k: [t.id for t in v] for k, v in machine_groups.items()},
            "timeline": {
                "start": min(task.start for task in gantt_tasks).isoformat(),
                "end": max(task.end for task in gantt_tasks).isoformat(),
                "scale": self.formatter_config.gantt_time_scale
            },
            "config": {
                "bar_height": self.formatter_config.gantt_bar_height,
                "show_dependencies": self.formatter_config.gantt_show_dependencies,
                "show_progress": self.formatter_config.gantt_show_progress,
                "locale": self.formatter_config.locale.value
            }
        }
        
        return gantt_data
    
    async def format_work_orders(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化工单数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            工单数据字典
        """
        include_summary = kwargs.get('include_summary', True)
        group_by = kwargs.get('group_by', 'machine')  # machine, date, priority
        
        work_orders = []
        
        for result in results:
            work_order = WorkOrderData(
                work_order_nr=result.work_order_nr,
                article_nr=result.article_nr,
                article_name=getattr(result, 'article_name', result.article_nr),
                quantity=result.allocated_quantity,
                machine_feeder=result.assigned_feeder_code,
                machine_maker=result.assigned_maker_code,
                scheduled_start=result.scheduled_start_time,
                scheduled_end=result.scheduled_end_time,
                status=result.monthly_schedule_status,
                priority=getattr(result, 'priority', 'NORMAL'),
                duration_hours=float(result.scheduled_duration_hours or 0),
                progress=float(result.monthly_execution_progress or 0),
                notes=result.optimization_notes
            )
            work_orders.append(work_order)
        
        # 按指定字段分组
        grouped_orders = self._group_work_orders(work_orders, group_by)
        
        # 生成摘要
        summary = None
        if include_summary:
            summary = self._generate_work_order_summary(work_orders)
        
        return {
            "work_orders": [wo.to_dict() for wo in work_orders],
            "grouped_orders": grouped_orders,
            "summary": summary,
            "total_count": len(work_orders),
            "grouping": group_by
        }
    
    async def format_reports(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化统计报告
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            统计报告字典
        """
        include_charts = kwargs.get('include_charts', True)
        detail_level = kwargs.get('detail_level', 'standard')  # basic, standard, detailed
        
        # 生成统计摘要
        summary = await self._generate_statistical_summary(results)
        
        # 生成详细分析
        analysis = await self._generate_detailed_analysis(results, detail_level)
        
        # 生成图表数据
        charts = {}
        if include_charts:
            charts = await self._generate_chart_data(results)
        
        # 生成趋势分析
        trends = await self._generate_trend_analysis(results)
        
        # 生成建议和洞察
        insights = await self._generate_insights(results, analysis)
        
        return {
            "summary": summary.to_dict(),
            "analysis": analysis,
            "charts": charts,
            "trends": trends,
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "locale": self.formatter_config.locale.value
        }
    
    async def format_excel_export(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化Excel导出数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            Excel导出数据字典
        """
        include_charts = kwargs.get('include_charts', self.formatter_config.excel_include_charts)
        
        # 生成工作表数据
        worksheets = {
            "summary": await self._generate_excel_summary_sheet(results),
            "work_orders": await self._generate_excel_work_orders_sheet(results),
            "machine_utilization": await self._generate_excel_machine_sheet(results),
            "timeline": await self._generate_excel_timeline_sheet(results)
        }
        
        # 生成图表数据
        charts_data = {}
        if include_charts:
            charts_data = await self._generate_excel_charts(results)
        
        return {
            "file_name": f"月度排产结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "worksheets": worksheets,
            "charts": charts_data,
            "config": {
                "freeze_panes": self.formatter_config.excel_freeze_panes,
                "include_charts": include_charts
            }
        }
    
    async def format_pdf_report(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化PDF报告数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            PDF报告数据字典
        """
        include_summary = kwargs.get('include_summary', self.formatter_config.pdf_include_summary)
        
        # 生成报告章节
        sections = []
        
        if include_summary:
            summary_section = await self._generate_pdf_summary_section(results)
            sections.append(summary_section)
        
        # 甘特图章节
        gantt_section = await self._generate_pdf_gantt_section(results)
        sections.append(gantt_section)
        
        # 分析章节
        analysis_section = await self._generate_pdf_analysis_section(results)
        sections.append(analysis_section)
        
        # 附录章节
        appendix_section = await self._generate_pdf_appendix_section(results)
        sections.append(appendix_section)
        
        return {
            "file_name": f"月度排产报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "sections": sections,
            "config": {
                "page_size": self.formatter_config.pdf_page_size,
                "orientation": self.formatter_config.pdf_orientation,
                "include_summary": include_summary
            },
            "metadata": {
                "title": "月度排产分析报告",
                "author": "APS智慧排产系统",
                "subject": "生产计划与调度分析",
                "created": datetime.now().isoformat()
            }
        }
    
    async def format_json_export(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化JSON导出数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            JSON导出数据字典
        """
        compression_level = kwargs.get('compression_level', 'standard')  # none, basic, standard, high
        include_metadata = kwargs.get('include_metadata', True)
        
        # 基础数据转换
        json_data = []
        for result in results:
            item = {
                "schedule_id": result.monthly_schedule_id,
                "task_id": result.monthly_task_id,
                "work_order_nr": result.work_order_nr,
                "article_nr": result.article_nr,
                "quantity": float(result.allocated_quantity),
                "feeder_code": result.assigned_feeder_code,
                "maker_code": result.assigned_maker_code,
                "start_time": result.scheduled_start_time.isoformat(),
                "end_time": result.scheduled_end_time.isoformat(),
                "duration_hours": float(result.scheduled_duration_hours or 0),
                "status": result.monthly_schedule_status,
                "progress": float(result.monthly_execution_progress or 0)
            }
            
            # 根据压缩级别添加额外字段
            if compression_level in ['none', 'basic']:
                item.update({
                    "priority_score": float(result.priority_score or 0),
                    "algorithm_version": result.algorithm_version,
                    "optimization_notes": result.optimization_notes,
                    "constraint_violations": result.constraint_violations
                })
            
            if compression_level == 'none':
                item.update({
                    "created_time": result.created_time.isoformat() if result.created_time else None,
                    "updated_time": result.updated_time.isoformat() if result.updated_time else None,
                    "calendar_constraints": result.get_calendar_constraints_info()
                })
            
            json_data.append(item)
        
        export_data = {
            "data": json_data,
            "count": len(json_data)
        }
        
        if include_metadata:
            export_data["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "compression_level": compression_level,
                "locale": self.formatter_config.locale.value,
                "version": self.version,
                "source": "monthly_result_formatter"
            }
        
        return export_data
    
    async def format_csv_export(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化CSV导出数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            CSV导出数据字典
        """
        delimiter = kwargs.get('delimiter', ',')
        include_header = kwargs.get('include_header', True)
        encoding = kwargs.get('encoding', 'utf-8-sig')  # 支持Excel的中文
        
        # 定义CSV列
        columns = [
            'schedule_id', 'work_order_nr', 'article_nr', 'quantity',
            'feeder_code', 'maker_code', 'start_time', 'end_time',
            'duration_hours', 'status', 'progress'
        ]
        
        # 本地化列标题
        headers = [self._get_localized_string(f'csv.header.{col}', col) for col in columns]
        
        # 生成CSV数据
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer, delimiter=delimiter)
        
        if include_header:
            writer.writerow(headers)
        
        for result in results:
            row = [
                result.monthly_schedule_id,
                result.work_order_nr,
                result.article_nr,
                float(result.allocated_quantity),
                result.assigned_feeder_code,
                result.assigned_maker_code,
                result.scheduled_start_time.strftime(self.formatter_config.datetime_format),
                result.scheduled_end_time.strftime(self.formatter_config.datetime_format),
                float(result.scheduled_duration_hours or 0),
                result.monthly_schedule_status,
                float(result.monthly_execution_progress or 0)
            ]
            writer.writerow(row)
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        return {
            "content": csv_content,
            "file_name": f"月度排产结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "encoding": encoding,
            "delimiter": delimiter,
            "record_count": len(results)
        }
    
    async def format_echarts_data(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化ECharts数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            ECharts数据字典
        """
        chart_type = kwargs.get('chart_type', ChartType.TIMELINE)
        
        if chart_type == ChartType.TIMELINE:
            return await self._generate_echarts_timeline(results)
        elif chart_type == ChartType.MACHINE_UTILIZATION:
            return await self._generate_echarts_machine_utilization(results)
        elif chart_type == ChartType.PRODUCTION_PROGRESS:
            return await self._generate_echarts_production_progress(results)
        elif chart_type == ChartType.CAPACITY_ANALYSIS:
            return await self._generate_echarts_capacity_analysis(results)
        elif chart_type == ChartType.PRIORITY_DISTRIBUTION:
            return await self._generate_echarts_priority_distribution(results)
        else:
            raise ValueError(f"不支持的图表类型：{chart_type}")
    
    async def format_vue_ganttastic(self, results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        格式化Vue Ganttastic数据
        
        Args:
            results: 排产结果列表
            **kwargs: 额外参数
            
        Returns:
            Vue Ganttastic格式数据字典
        """
        # 生成甘特图任务
        gantt_data = await self.format_gantt_data(results, **kwargs)
        
        # 转换为Vue Ganttastic特定格式
        gantt_rows = []
        
        # 按机台分组创建行
        machine_groups = gantt_data["machine_groups"]
        for machine_code, task_ids in machine_groups.items():
            row_tasks = []
            for task_id in task_ids:
                # 查找任务数据
                task_data = next((t for t in gantt_data["tasks"] if t["id"] == task_id), None)
                if task_data:
                    row_tasks.append(task_data)
            
            if row_tasks:
                gantt_rows.append({
                    "id": f"machine_{machine_code}",
                    "label": machine_code,
                    "bars": row_tasks
                })
        
        return {
            "rows": gantt_rows,
            "config": {
                "chart_start": gantt_data["timeline"]["start"],
                "chart_end": gantt_data["timeline"]["end"],
                "precision": "hour",
                "colors": self.color_schemes[self.formatter_config.color_scheme],
                "locale": self.formatter_config.locale.value
            },
            "metadata": {
                "total_tasks": len(gantt_data["tasks"]),
                "total_machines": len(machine_groups),
                "timeline_span_hours": self._calculate_timeline_span(gantt_data["timeline"])
            }
        }
    
    # 辅助方法
    
    def _load_locale_strings(self) -> Dict[str, Dict[str, str]]:
        """加载本地化字符串"""
        return {
            "zh_CN": {
                "csv.header.schedule_id": "排产ID",
                "csv.header.work_order_nr": "工单号",
                "csv.header.article_nr": "牌号",
                "csv.header.quantity": "数量",
                "csv.header.feeder_code": "喂丝机",
                "csv.header.maker_code": "卷包机",
                "csv.header.start_time": "开始时间",
                "csv.header.end_time": "结束时间",
                "csv.header.duration_hours": "时长(小时)",
                "csv.header.status": "状态",
                "csv.header.progress": "进度",
                "status.PENDING": "待排产",
                "status.SCHEDULED": "已排产",
                "status.EXECUTING": "执行中",
                "status.COMPLETED": "已完成",
                "status.FAILED": "已失败"
            },
            "en_US": {
                "csv.header.schedule_id": "Schedule ID",
                "csv.header.work_order_nr": "Work Order",
                "csv.header.article_nr": "Article",
                "csv.header.quantity": "Quantity",
                "csv.header.feeder_code": "Feeder",
                "csv.header.maker_code": "Maker",
                "csv.header.start_time": "Start Time",
                "csv.header.end_time": "End Time",
                "csv.header.duration_hours": "Duration (Hours)",
                "csv.header.status": "Status",
                "csv.header.progress": "Progress",
                "status.PENDING": "Pending",
                "status.SCHEDULED": "Scheduled",
                "status.EXECUTING": "Executing",
                "status.COMPLETED": "Completed",
                "status.FAILED": "Failed"
            }
        }
    
    def _load_color_schemes(self) -> Dict[str, Dict[str, str]]:
        """加载颜色方案"""
        return {
            "default": {
                "primary": "#3498db",
                "success": "#2ecc71",
                "warning": "#f39c12",
                "danger": "#e74c3c",
                "info": "#9b59b6"
            },
            "dark": {
                "primary": "#34495e",
                "success": "#27ae60",
                "warning": "#e67e22",
                "danger": "#c0392b",
                "info": "#8e44ad"
            },
            "pastel": {
                "primary": "#74b9ff",
                "success": "#55efc4",
                "warning": "#fdcb6e",
                "danger": "#fd79a8",
                "info": "#a29bfe"
            }
        }
    
    def _get_localized_string(self, key: str, default: str = "") -> str:
        """获取本地化字符串"""
        locale_dict = self.locale_strings.get(self.formatter_config.locale.value, {})
        return locale_dict.get(key, default)
    
    def _get_priority_color(self, priority_score: Optional[float]) -> str:
        """根据优先级分数获取颜色"""
        if not priority_score:
            return self.color_schemes[self.formatter_config.color_scheme]["info"]
        
        score = float(priority_score)
        colors = self.color_schemes[self.formatter_config.color_scheme]
        
        if score >= 80:
            return colors["danger"]
        elif score >= 60:
            return colors["warning"]
        elif score >= 40:
            return colors["primary"]
        else:
            return colors["success"]
    
    def _calculate_dependencies(self, gantt_tasks: List[GanttTask]) -> None:
        """计算任务依赖关系"""
        # 简化的依赖计算逻辑
        # 同一机台的任务按时间顺序形成依赖
        machine_tasks = defaultdict(list)
        
        for task in gantt_tasks:
            machine_tasks[task.machine_code].append(task)
        
        for machine_code, tasks in machine_tasks.items():
            sorted_tasks = sorted(tasks, key=lambda t: t.start)
            for i in range(1, len(sorted_tasks)):
                sorted_tasks[i].dependencies.append(sorted_tasks[i-1].id)
    
    def _group_work_orders(self, work_orders: List[WorkOrderData], group_by: str) -> Dict[str, List[Dict[str, Any]]]:
        """按指定字段分组工单"""
        groups = defaultdict(list)
        
        for wo in work_orders:
            if group_by == 'machine':
                key = f"{wo.machine_feeder}+{wo.machine_maker}"
            elif group_by == 'date':
                key = wo.scheduled_start.date().isoformat()
            elif group_by == 'priority':
                key = wo.priority
            elif group_by == 'status':
                key = wo.status
            else:
                key = 'default'
            
            groups[key].append(wo.to_dict())
        
        return dict(groups)
    
    def _generate_work_order_summary(self, work_orders: List[WorkOrderData]) -> Dict[str, Any]:
        """生成工单摘要"""
        if not work_orders:
            return {}
        
        total_quantity = sum(wo.quantity for wo in work_orders)
        total_hours = sum(wo.duration_hours for wo in work_orders)
        avg_progress = statistics.mean(wo.progress for wo in work_orders) if work_orders else 0
        
        status_counts = Counter(wo.status for wo in work_orders)
        priority_counts = Counter(wo.priority for wo in work_orders)
        machine_counts = Counter(f"{wo.machine_feeder}+{wo.machine_maker}" for wo in work_orders)
        
        return {
            "total_work_orders": len(work_orders),
            "total_quantity": float(total_quantity),
            "total_duration_hours": total_hours,
            "average_progress": avg_progress,
            "status_distribution": dict(status_counts),
            "priority_distribution": dict(priority_counts),
            "machine_distribution": dict(machine_counts),
            "date_range": {
                "start": min(wo.scheduled_start for wo in work_orders).isoformat(),
                "end": max(wo.scheduled_end for wo in work_orders).isoformat()
            }
        }
    
    async def _generate_statistical_summary(self, results: List[Any]) -> StatisticalSummary:
        """生成统计摘要"""
        if not results:
            return StatisticalSummary(
                total_tasks=0, total_work_orders=0, total_production_hours=0.0,
                total_quantity=Decimal('0'), makespan_hours=0.0,
                machine_utilization={}, priority_distribution={}, status_distribution={},
                avg_task_duration=0.0, peak_concurrent_tasks=0,
                start_date=datetime.now(), end_date=datetime.now()
            )
        
        total_quantity = sum(result.allocated_quantity for result in results)
        total_hours = sum(float(result.scheduled_duration_hours or 0) for result in results)
        
        start_times = [result.scheduled_start_time for result in results]
        end_times = [result.scheduled_end_time for result in results]
        
        start_date = min(start_times)
        end_date = max(end_times)
        makespan_hours = (end_date - start_date).total_seconds() / 3600
        
        # 机台利用率计算
        machine_hours = defaultdict(float)
        for result in results:
            duration = float(result.scheduled_duration_hours or 0)
            if result.assigned_feeder_code:
                machine_hours[result.assigned_feeder_code] += duration
            if result.assigned_maker_code:
                machine_hours[result.assigned_maker_code] += duration
        
        machine_utilization = {k: v/makespan_hours for k, v in machine_hours.items() if makespan_hours > 0}
        
        # 状态分布
        status_dist = Counter(result.monthly_schedule_status for result in results)
        
        # 优先级分布（模拟）
        priority_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        return StatisticalSummary(
            total_tasks=len(results),
            total_work_orders=len(results),
            total_production_hours=total_hours,
            total_quantity=total_quantity,
            makespan_hours=makespan_hours,
            machine_utilization=machine_utilization,
            priority_distribution=priority_dist,
            status_distribution=dict(status_dist),
            avg_task_duration=total_hours/len(results) if results else 0,
            peak_concurrent_tasks=self._calculate_peak_concurrent_tasks(results),
            start_date=start_date,
            end_date=end_date
        )
    
    def _calculate_peak_concurrent_tasks(self, results: List[Any]) -> int:
        """计算峰值并发任务数"""
        # 创建时间点事件列表
        events = []
        for result in results:
            events.append((result.scheduled_start_time, 1))  # 开始事件
            events.append((result.scheduled_end_time, -1))   # 结束事件
        
        # 按时间排序
        events.sort(key=lambda x: x[0])
        
        # 计算最大并发数
        current_concurrent = 0
        max_concurrent = 0
        
        for time, delta in events:
            current_concurrent += delta
            max_concurrent = max(max_concurrent, current_concurrent)
        
        return max_concurrent
    
    async def _generate_detailed_analysis(self, results: List[Any], detail_level: str) -> Dict[str, Any]:
        """生成详细分析"""
        analysis = {
            "efficiency_analysis": await self._analyze_efficiency(results),
            "bottleneck_analysis": await self._analyze_bottlenecks(results)
        }
        
        if detail_level in ['standard', 'detailed']:
            analysis.update({
                "machine_analysis": await self._analyze_machines(results),
                "time_analysis": await self._analyze_time_patterns(results)
            })
        
        if detail_level == 'detailed':
            analysis.update({
                "optimization_opportunities": await self._identify_optimization_opportunities(results),
                "constraint_analysis": await self._analyze_constraints(results)
            })
        
        return analysis
    
    async def _analyze_efficiency(self, results: List[Any]) -> Dict[str, Any]:
        """分析效率"""
        if not results:
            return {"overall_efficiency": 0.0, "insights": []}
        
        total_duration = sum(float(r.scheduled_duration_hours or 0) for r in results)
        start_time = min(r.scheduled_start_time for r in results)
        end_time = max(r.scheduled_end_time for r in results)
        makespan = (end_time - start_time).total_seconds() / 3600
        
        efficiency = total_duration / makespan if makespan > 0 else 0
        
        insights = []
        if efficiency < 0.7:
            insights.append("整体效率较低，存在较多空闲时间")
        elif efficiency > 0.9:
            insights.append("整体效率很高，时间利用充分")
        else:
            insights.append("整体效率正常，仍有优化空间")
        
        return {
            "overall_efficiency": efficiency,
            "total_production_hours": total_duration,
            "makespan_hours": makespan,
            "idle_time_hours": makespan - total_duration,
            "insights": insights
        }
    
    async def _analyze_bottlenecks(self, results: List[Any]) -> Dict[str, Any]:
        """分析瓶颈"""
        machine_load = defaultdict(float)
        machine_count = defaultdict(int)
        
        for result in results:
            duration = float(result.scheduled_duration_hours or 0)
            if result.assigned_feeder_code:
                machine_load[result.assigned_feeder_code] += duration
                machine_count[result.assigned_feeder_code] += 1
            if result.assigned_maker_code:
                machine_load[result.assigned_maker_code] += duration
                machine_count[result.assigned_maker_code] += 1
        
        # 识别高负载机台
        avg_load = statistics.mean(machine_load.values()) if machine_load else 0
        bottlenecks = [machine for machine, load in machine_load.items() if load > avg_load * 1.2]
        
        return {
            "bottleneck_machines": bottlenecks,
            "machine_loads": dict(machine_load),
            "average_load": avg_load,
            "load_variance": statistics.variance(machine_load.values()) if len(machine_load) > 1 else 0
        }
    
    async def _analyze_machines(self, results: List[Any]) -> Dict[str, Any]:
        """分析机台"""
        # 机台使用统计
        feeder_stats = defaultdict(list)
        maker_stats = defaultdict(list)
        
        for result in results:
            duration = float(result.scheduled_duration_hours or 0)
            if result.assigned_feeder_code:
                feeder_stats[result.assigned_feeder_code].append(duration)
            if result.assigned_maker_code:
                maker_stats[result.assigned_maker_code].append(duration)
        
        # 计算机台效率
        feeder_efficiency = {}
        for machine, durations in feeder_stats.items():
            feeder_efficiency[machine] = {
                "total_hours": sum(durations),
                "avg_task_duration": statistics.mean(durations),
                "task_count": len(durations)
            }
        
        maker_efficiency = {}
        for machine, durations in maker_stats.items():
            maker_efficiency[machine] = {
                "total_hours": sum(durations),
                "avg_task_duration": statistics.mean(durations),
                "task_count": len(durations)
            }
        
        return {
            "feeder_efficiency": feeder_efficiency,
            "maker_efficiency": maker_efficiency,
            "total_feeders_used": len(feeder_stats),
            "total_makers_used": len(maker_stats)
        }
    
    async def _analyze_time_patterns(self, results: List[Any]) -> Dict[str, Any]:
        """分析时间模式"""
        # 按小时统计任务开始数量
        hourly_starts = defaultdict(int)
        daily_loads = defaultdict(float)
        
        for result in results:
            hour = result.scheduled_start_time.hour
            day = result.scheduled_start_time.date()
            duration = float(result.scheduled_duration_hours or 0)
            
            hourly_starts[hour] += 1
            daily_loads[day] += duration
        
        # 找出高峰时段
        peak_hour = max(hourly_starts.items(), key=lambda x: x[1])[0] if hourly_starts else 0
        peak_day = max(daily_loads.items(), key=lambda x: x[1])[0] if daily_loads else date.today()
        
        return {
            "hourly_distribution": dict(hourly_starts),
            "daily_loads": {str(k): v for k, v in daily_loads.items()},
            "peak_hour": peak_hour,
            "peak_day": str(peak_day),
            "working_span_days": len(daily_loads)
        }
    
    async def _identify_optimization_opportunities(self, results: List[Any]) -> List[str]:
        """识别优化机会"""
        opportunities = []
        
        # 检查负载不均衡
        machine_loads = defaultdict(float)
        for result in results:
            duration = float(result.scheduled_duration_hours or 0)
            machine_loads[result.assigned_feeder_code] += duration
        
        if machine_loads:
            max_load = max(machine_loads.values())
            min_load = min(machine_loads.values())
            if max_load > min_load * 2:
                opportunities.append("存在机台负载不均衡，建议重新分配任务")
        
        # 检查空闲时间
        total_duration = sum(float(r.scheduled_duration_hours or 0) for r in results)
        start_time = min(r.scheduled_start_time for r in results)
        end_time = max(r.scheduled_end_time for r in results)
        makespan = (end_time - start_time).total_seconds() / 3600
        
        if makespan > total_duration * 1.5:
            opportunities.append("存在较多空闲时间，可考虑紧凑化排产")
        
        return opportunities
    
    async def _analyze_constraints(self, results: List[Any]) -> Dict[str, Any]:
        """分析约束"""
        constraint_violations = []
        
        for result in results:
            if result.constraint_violations:
                constraint_violations.append({
                    "schedule_id": result.monthly_schedule_id,
                    "violations": result.constraint_violations
                })
        
        return {
            "total_violations": len(constraint_violations),
            "violation_details": constraint_violations,
            "violation_rate": len(constraint_violations) / len(results) if results else 0
        }
    
    async def _generate_chart_data(self, results: List[Any]) -> Dict[str, Any]:
        """生成图表数据"""
        return {
            "timeline": await self._generate_echarts_timeline(results),
            "machine_utilization": await self._generate_echarts_machine_utilization(results),
            "production_progress": await self._generate_echarts_production_progress(results)
        }
    
    async def _generate_echarts_timeline(self, results: List[Any]) -> Dict[str, Any]:
        """生成ECharts时间线图数据"""
        machines = set()
        data = []
        
        for result in results:
            machine = f"{result.assigned_feeder_code}+{result.assigned_maker_code}"
            machines.add(machine)
            
            data.append({
                "name": result.work_order_nr,
                "value": [
                    machine,
                    result.scheduled_start_time.timestamp() * 1000,
                    result.scheduled_end_time.timestamp() * 1000,
                    float(result.allocated_quantity)
                ],
                "itemStyle": {
                    "normal": {
                        "color": self._get_priority_color(result.priority_score)
                    }
                }
            })
        
        return {
            "title": {
                "text": "生产时间线",
                "left": "center"
            },
            "tooltip": {
                "formatter": "{b}: {c[3]}万支<br/>开始: {c[1]|yyyy-MM-dd hh:mm}<br/>结束: {c[2]|yyyy-MM-dd hh:mm}"
            },
            "xAxis": {
                "type": "time",
                "name": "时间"
            },
            "yAxis": {
                "type": "category",
                "data": list(machines),
                "name": "机台"
            },
            "series": [{
                "type": "custom",
                "data": data,
                "renderItem": "function(params, api) { /* 自定义渲染逻辑 */ }"
            }]
        }
    
    async def _generate_echarts_machine_utilization(self, results: List[Any]) -> Dict[str, Any]:
        """生成机台利用率图表数据"""
        machine_hours = defaultdict(float)
        
        for result in results:
            duration = float(result.scheduled_duration_hours or 0)
            machine_hours[result.assigned_feeder_code] += duration
            machine_hours[result.assigned_maker_code] += duration
        
        machines = list(machine_hours.keys())
        hours = list(machine_hours.values())
        
        return {
            "title": {
                "text": "机台利用率",
                "left": "center"
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "shadow"
                }
            },
            "xAxis": {
                "type": "category",
                "data": machines,
                "name": "机台"
            },
            "yAxis": {
                "type": "value",
                "name": "工作时长(小时)"
            },
            "series": [{
                "type": "bar",
                "data": hours,
                "itemStyle": {
                    "color": self.color_schemes[self.formatter_config.color_scheme]["primary"]
                }
            }]
        }
    
    async def _generate_echarts_production_progress(self, results: List[Any]) -> Dict[str, Any]:
        """生成生产进度图表数据"""
        status_counts = Counter(result.monthly_schedule_status for result in results)
        
        data = [
            {"value": count, "name": self._get_localized_string(f"status.{status}", status)}
            for status, count in status_counts.items()
        ]
        
        return {
            "title": {
                "text": "生产进度分布",
                "left": "center"
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{a} <br/>{b}: {c} ({d}%)"
            },
            "legend": {
                "orient": "vertical",
                "left": "left"
            },
            "series": [{
                "name": "任务状态",
                "type": "pie",
                "radius": "50%",
                "data": data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }
    
    async def _generate_echarts_capacity_analysis(self, results: List[Any]) -> Dict[str, Any]:
        """生成容量分析图表数据"""
        # 按日期统计产量
        daily_quantity = defaultdict(float)
        
        for result in results:
            day = result.scheduled_start_time.date()
            daily_quantity[day] += float(result.allocated_quantity)
        
        dates = sorted(daily_quantity.keys())
        quantities = [daily_quantity[date] for date in dates]
        
        return {
            "title": {
                "text": "日产量分析",
                "left": "center"
            },
            "tooltip": {
                "trigger": "axis"
            },
            "xAxis": {
                "type": "category",
                "data": [date.strftime("%m-%d") for date in dates],
                "name": "日期"
            },
            "yAxis": {
                "type": "value",
                "name": "产量(万支)"
            },
            "series": [{
                "type": "line",
                "data": quantities,
                "smooth": True,
                "itemStyle": {
                    "color": self.color_schemes[self.formatter_config.color_scheme]["success"]
                }
            }]
        }
    
    async def _generate_echarts_priority_distribution(self, results: List[Any]) -> Dict[str, Any]:
        """生成优先级分布图表数据"""
        # 根据优先级分数分类
        priority_ranges = {
            "高优先级": 0,
            "中优先级": 0,
            "低优先级": 0,
            "未设置": 0
        }
        
        for result in results:
            score = float(result.priority_score or 0)
            if score >= 70:
                priority_ranges["高优先级"] += 1
            elif score >= 40:
                priority_ranges["中优先级"] += 1
            elif score > 0:
                priority_ranges["低优先级"] += 1
            else:
                priority_ranges["未设置"] += 1
        
        return {
            "title": {
                "text": "任务优先级分布",
                "left": "center"
            },
            "tooltip": {
                "trigger": "item"
            },
            "series": [{
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": [
                    {"value": count, "name": priority}
                    for priority, count in priority_ranges.items()
                    if count > 0
                ]
            }]
        }
    
    async def _generate_trend_analysis(self, results: List[Any]) -> Dict[str, Any]:
        """生成趋势分析"""
        if not results:
            return {}
        
        # 按日期分组分析趋势
        daily_stats = defaultdict(lambda: {"count": 0, "quantity": 0, "duration": 0})
        
        for result in results:
            day = result.scheduled_start_time.date()
            daily_stats[day]["count"] += 1
            daily_stats[day]["quantity"] += float(result.allocated_quantity)
            daily_stats[day]["duration"] += float(result.scheduled_duration_hours or 0)
        
        # 计算趋势
        dates = sorted(daily_stats.keys())
        if len(dates) > 1:
            # 简单的线性趋势计算
            count_trend = "stable"
            quantity_trend = "stable"
            
            first_day = daily_stats[dates[0]]
            last_day = daily_stats[dates[-1]]
            
            if last_day["count"] > first_day["count"] * 1.1:
                count_trend = "increasing"
            elif last_day["count"] < first_day["count"] * 0.9:
                count_trend = "decreasing"
            
            if last_day["quantity"] > first_day["quantity"] * 1.1:
                quantity_trend = "increasing"
            elif last_day["quantity"] < first_day["quantity"] * 0.9:
                quantity_trend = "decreasing"
        else:
            count_trend = quantity_trend = "insufficient_data"
        
        return {
            "task_count_trend": count_trend,
            "quantity_trend": quantity_trend,
            "daily_statistics": {str(k): v for k, v in daily_stats.items()},
            "analysis_period_days": len(dates)
        }
    
    async def _generate_insights(self, results: List[Any], analysis: Dict[str, Any]) -> List[str]:
        """生成洞察和建议"""
        insights = []
        
        # 基于效率分析的洞察
        efficiency = analysis.get("efficiency_analysis", {}).get("overall_efficiency", 0)
        if efficiency < 0.7:
            insights.append("🔍 整体排产效率偏低，建议优化任务安排以减少空闲时间")
        elif efficiency > 0.9:
            insights.append("✅ 排产效率很高，时间利用充分")
        
        # 基于瓶颈分析的洞察
        bottlenecks = analysis.get("bottleneck_analysis", {}).get("bottleneck_machines", [])
        if bottlenecks:
            insights.append(f"⚠️ 发现瓶颈机台：{', '.join(bottlenecks)}，建议考虑负载均衡")
        
        # 基于时间分析的洞察
        time_analysis = analysis.get("time_analysis", {})
        peak_hour = time_analysis.get("peak_hour")
        if peak_hour is not None:
            if peak_hour < 8 or peak_hour > 18:
                insights.append(f"🕐 任务主要集中在非正常工作时间（{peak_hour}点），建议调整排产时间")
        
        # 基于约束分析的洞察
        constraints = analysis.get("constraint_analysis", {})
        violation_rate = constraints.get("violation_rate", 0)
        if violation_rate > 0.1:
            insights.append(f"⚡ 约束违反率较高（{violation_rate:.1%}），建议检查排产规则")
        
        return insights
    
    # Excel相关方法
    
    async def _generate_excel_summary_sheet(self, results: List[Any]) -> Dict[str, Any]:
        """生成Excel摘要工作表"""
        summary = await self._generate_statistical_summary(results)
        
        return {
            "name": "摘要",
            "data": [
                ["指标", "数值"],
                ["总任务数", summary.total_tasks],
                ["总工单数", summary.total_work_orders],
                ["总生产时长(小时)", summary.total_production_hours],
                ["总产量(万支)", float(summary.total_quantity)],
                ["时间跨度(小时)", summary.makespan_hours],
                ["平均任务时长(小时)", summary.avg_task_duration],
                ["峰值并发任务数", summary.peak_concurrent_tasks]
            ]
        }
    
    async def _generate_excel_work_orders_sheet(self, results: List[Any]) -> Dict[str, Any]:
        """生成Excel工单工作表"""
        headers = ["排产ID", "工单号", "牌号", "数量", "喂丝机", "卷包机", "开始时间", "结束时间", "状态", "进度"]
        
        data = [headers]
        for result in results:
            row = [
                result.monthly_schedule_id,
                result.work_order_nr,
                result.article_nr,
                float(result.allocated_quantity),
                result.assigned_feeder_code,
                result.assigned_maker_code,
                result.scheduled_start_time.strftime(self.formatter_config.datetime_format),
                result.scheduled_end_time.strftime(self.formatter_config.datetime_format),
                result.monthly_schedule_status,
                f"{float(result.monthly_execution_progress or 0):.1f}%"
            ]
            data.append(row)
        
        return {
            "name": "工单明细",
            "data": data
        }
    
    async def _generate_excel_machine_sheet(self, results: List[Any]) -> Dict[str, Any]:
        """生成Excel机台工作表"""
        machine_stats = await self._analyze_machines(results)
        
        headers = ["机台代码", "总工作时长", "平均任务时长", "任务数量"]
        data = [headers]
        
        # 喂丝机数据
        for machine, stats in machine_stats.get("feeder_efficiency", {}).items():
            row = [
                f"{machine}(喂丝机)",
                stats["total_hours"],
                stats["avg_task_duration"],
                stats["task_count"]
            ]
            data.append(row)
        
        # 卷包机数据
        for machine, stats in machine_stats.get("maker_efficiency", {}).items():
            row = [
                f"{machine}(卷包机)",
                stats["total_hours"],
                stats["avg_task_duration"],
                stats["task_count"]
            ]
            data.append(row)
        
        return {
            "name": "机台分析",
            "data": data
        }
    
    async def _generate_excel_timeline_sheet(self, results: List[Any]) -> Dict[str, Any]:
        """生成Excel时间线工作表"""
        headers = ["时间点", "事件类型", "工单号", "机台", "操作"]
        data = [headers]
        
        # 生成时间点事件
        events = []
        for result in results:
            events.append((result.scheduled_start_time, "开始", result.work_order_nr,
                          f"{result.assigned_feeder_code}+{result.assigned_maker_code}", "生产开始"))
            events.append((result.scheduled_end_time, "结束", result.work_order_nr,
                          f"{result.assigned_feeder_code}+{result.assigned_maker_code}", "生产结束"))
        
        # 按时间排序
        events.sort(key=lambda x: x[0])
        
        for event in events:
            row = [
                event[0].strftime(self.formatter_config.datetime_format),
                event[1],
                event[2],
                event[3],
                event[4]
            ]
            data.append(row)
        
        return {
            "name": "时间线",
            "data": data
        }
    
    async def _generate_excel_charts(self, results: List[Any]) -> Dict[str, Any]:
        """生成Excel图表数据"""
        # 生成专业图表配置，支持机台利用率和生产时间线可视化
        return {
            "machine_utilization_chart": {
                "type": "column",
                "title": "机台利用率",
                "data_range": "机台分析!A1:D10"
            },
            "timeline_chart": {
                "type": "timeline",
                "title": "生产时间线",
                "data_range": "时间线!A1:E100"
            }
        }
    
    # PDF相关方法
    
    async def _generate_pdf_summary_section(self, results: List[Any]) -> Dict[str, Any]:
        """生成PDF摘要章节"""
        summary = await self._generate_statistical_summary(results)
        
        return {
            "title": "排产摘要",
            "content": [
                f"本次月度排产共涉及 {summary.total_tasks} 个任务，",
                f"生成 {summary.total_work_orders} 个工单，",
                f"总生产时长 {summary.total_production_hours:.1f} 小时，",
                f"预计产量 {float(summary.total_quantity):,.0f} 万支。",
                f"",
                f"排产时间跨度 {summary.makespan_hours:.1f} 小时，",
                f"整体效率 {(summary.total_production_hours/summary.makespan_hours*100):.1f}%。"
            ]
        }
    
    async def _generate_pdf_gantt_section(self, results: List[Any]) -> Dict[str, Any]:
        """生成PDF甘特图章节"""
        return {
            "title": "生产甘特图",
            "content": [
                "以下展示了月度排产的详细时间安排：",
                "[甘特图占位符 - 实际实现中应生成图表图像]"
            ]
        }
    
    async def _generate_pdf_analysis_section(self, results: List[Any]) -> Dict[str, Any]:
        """生成PDF分析章节"""
        analysis = await self._generate_detailed_analysis(results, "standard")
        insights = await self._generate_insights(results, analysis)
        
        content = ["分析结果："]
        content.extend(insights)
        
        return {
            "title": "分析报告",
            "content": content
        }
    
    async def _generate_pdf_appendix_section(self, results: List[Any]) -> Dict[str, Any]:
        """生成PDF附录章节"""
        return {
            "title": "附录",
            "content": [
                "详细工单列表：",
                f"共 {len(results)} 个工单，详细信息请参考Excel导出文件。"
            ]
        }
    
    def _calculate_timeline_span(self, timeline: Dict[str, str]) -> float:
        """计算时间线跨度（小时）"""
        start = datetime.fromisoformat(timeline["start"].replace('Z', '+00:00'))
        end = datetime.fromisoformat(timeline["end"].replace('Z', '+00:00'))
        return (end - start).total_seconds() / 3600
    
    def _update_performance_stats(self, record_count: int, processing_time: float):
        """更新性能统计"""
        self.performance_stats["formats_generated"] += 1
        self.performance_stats["total_records_processed"] += record_count
        
        # 更新平均处理时间
        total_generations = self.performance_stats["formats_generated"]
        current_avg = self.performance_stats["average_processing_time"]
        new_avg = (current_avg * (total_generations - 1) + processing_time) / total_generations
        self.performance_stats["average_processing_time"] = new_avg


# CLI 支持
def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description="月度结果格式化算法模块")
    parser.add_argument("--format", choices=["gantt", "orders", "report", "excel", "pdf", "json", "csv"],
                       default="gantt", help="输出格式")
    parser.add_argument("--locale", choices=["zh_CN", "en_US", "zh_TW"],
                       default="zh_CN", help="本地化语言")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--compress", action="store_true", help="启用压缩")
    
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(demo_format_results(args))
    else:
        parser.print_help()


async def demo_format_results(args):
    """演示结果格式化"""
    print(f"🎨 月度结果格式化算法演示")
    print(f"📊 格式：{args.format}")
    print(f"🌍 语言：{args.locale}")
    
    # 创建配置
    config = FormatterConfig(
        locale=LocaleType(args.locale),
        enable_compression=args.compress
    )
    
    # 创建格式化器
    formatter = MonthlyResultFormatter(config)
    
    # 创建模拟数据
    mock_results = []
    base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    for i in range(5):
        mock_result = type('MockResult', (), {
            'monthly_schedule_id': i + 1,
            'monthly_task_id': f'TASK_{i+1:03d}',
            'work_order_nr': f'WO_{i+1:04d}',
            'article_nr': f'HN{i+1:04d}',
            'allocated_quantity': Decimal(str(1000 + i * 200)),
            'assigned_feeder_code': f'FEEDER_{(i % 3) + 1:02d}',
            'assigned_maker_code': f'MAKER_{(i % 3) + 1:02d}',
            'scheduled_start_time': base_time + timedelta(hours=i * 2),
            'scheduled_end_time': base_time + timedelta(hours=i * 2 + 1.5),
            'scheduled_duration_hours': Decimal('1.5'),
            'monthly_schedule_status': ['PENDING', 'SCHEDULED', 'EXECUTING', 'COMPLETED'][i % 4],
            'monthly_execution_progress': Decimal(str(i * 25)),
            'priority_score': Decimal(str(80 - i * 10)),
            'algorithm_version': 'v1.0',
            'optimization_notes': f'任务{i+1}优化说明',
            'constraint_violations': None,
            'created_time': datetime.now(),
            'updated_time': datetime.now(),
            'get_calendar_constraints_info': lambda: {}
        })()
        mock_results.append(mock_result)
    
    # 执行格式化
    format_map = {
        "gantt": OutputFormat.GANTT_CHART,
        "orders": OutputFormat.WORK_ORDERS,
        "report": OutputFormat.STATISTICAL_REPORT,
        "excel": OutputFormat.EXCEL_EXPORT,
        "pdf": OutputFormat.PDF_REPORT,
        "json": OutputFormat.JSON_EXPORT,
        "csv": OutputFormat.CSV_EXPORT
    }
    
    format_type = format_map[args.format]
    
    try:
        result = await formatter.execute(mock_results, format_type=format_type)
        
        print(f"✅ 格式化成功!")
        
        if args.verbose:
            print(f"📊 处理统计:")
            metadata = result.get("metadata", {})
            for key, value in metadata.items():
                print(f"   {key}: {value}")
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"💾 结果已保存到: {args.output}")
        else:
            # 显示部分结果
            data = result.get("data", {})
            if args.format == "csv":
                print(f"📝 CSV内容预览:")
                print(data.get("content", "")[:500] + "...")
            elif args.format == "gantt":
                tasks = data.get("tasks", [])
                print(f"📊 甘特图任务数: {len(tasks)}")
                if tasks:
                    print(f"   首个任务: {tasks[0].get('label', 'N/A')}")
            elif args.format == "report":
                summary = data.get("summary", {})
                print(f"📈 统计摘要:")
                print(f"   总任务数: {summary.get('total_tasks', 0)}")
                print(f"   总时长: {summary.get('total_production_hours', 0):.1f} 小时")
                print(f"   效率: {summary.get('efficiency_rate', 0):.1%}")
            else:
                print(json.dumps(data, ensure_ascii=False, indent=2, default=str)[:1000] + "...")
        
        print(f"🎯 性能统计: {formatter.performance_stats}")
        
    except Exception as e:
        print(f"❌ 格式化失败: {str(e)}")


if __name__ == "__main__":
    main()