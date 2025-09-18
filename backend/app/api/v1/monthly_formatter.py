"""
月度结果格式化 API 集成示例

展示如何在 FastAPI 路由中集成 MonthlyResultFormatter
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from app.algorithms.monthly_scheduling.monthly_result_formatter import (
    MonthlyResultFormatter,
    FormatterConfig,
    OutputFormat,
    LocaleType,
    ChartType
)
from app.models.monthly_schedule_result_models import MonthlyScheduleResult
from app.services.database_query_service import DatabaseQueryService


class ResponseFormat(str, Enum):
    """API响应格式枚举"""
    gantt = "gantt"
    orders = "orders"
    report = "report"
    excel = "excel"
    pdf = "pdf"
    json = "json"
    csv = "csv"
    echarts = "echarts"
    vue_ganttastic = "vue_ganttastic"


class ChartTypeAPI(str, Enum):
    """API图表类型枚举"""
    timeline = "timeline"
    machine_utilization = "machine_utilization"
    production_progress = "production_progress"
    capacity_analysis = "capacity_analysis"
    priority_distribution = "priority_distribution"


router = APIRouter(prefix="/api/v1/monthly/formatter", tags=["月度结果格式化"])


async def get_formatter_service(
    locale: LocaleType = LocaleType.ZH_CN,
    enable_compression: bool = True,
    color_scheme: str = "default"
) -> MonthlyResultFormatter:
    """获取格式化服务实例"""
    config = FormatterConfig(
        locale=locale,
        enable_compression=enable_compression,
        color_scheme=color_scheme,
        include_metadata=True
    )
    return MonthlyResultFormatter(config)


@router.get("/formats", summary="获取支持的输出格式")
async def get_supported_formats() -> Dict[str, Any]:
    """获取所有支持的输出格式和选项"""
    return {
        "output_formats": [f.value for f in OutputFormat],
        "chart_types": [c.value for c in ChartType],
        "locales": [l.value for l in LocaleType],
        "color_schemes": ["default", "dark", "pastel"]
    }


@router.post("/gantt", summary="生成甘特图数据")
async def format_gantt_chart(
    task_id: str,
    include_dependencies: bool = Query(True, description="包含依赖关系"),
    time_scale: str = Query("hour", description="时间刻度 (hour/day/week)"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    为指定任务生成甘特图数据
    
    Args:
        task_id: 排产任务ID
        include_dependencies: 是否包含任务依赖关系
        time_scale: 时间刻度
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        甘特图数据
    """
    try:
        # 查询排产结果
        schedule_results = await db_service.get_schedule_results_by_task(task_id)
        
        if not schedule_results:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id} 的排产结果")
        
        # 更新格式化器配置
        formatter.formatter_config.gantt_time_scale = time_scale
        
        # 生成甘特图数据
        result = await formatter.execute(
            schedule_results,
            format_type=OutputFormat.VUE_GANTTASTIC,
            include_dependencies=include_dependencies
        )
        
        return {
            "code": 200,
            "message": "甘特图数据生成成功",
            "data": result["data"],
            "metadata": {
                "task_id": task_id,
                "total_tasks": len(schedule_results),
                "generation_time": result["metadata"]["processing_time_seconds"],
                "time_scale": time_scale
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"甘特图生成失败: {str(e)}")


@router.post("/work-orders", summary="生成工单数据")
async def format_work_orders(
    task_id: str,
    group_by: str = Query("machine", description="分组方式 (machine/date/priority/status)"),
    include_summary: bool = Query(True, description="包含统计摘要"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    生成工单列表和统计数据
    
    Args:
        task_id: 排产任务ID
        group_by: 分组方式
        include_summary: 是否包含统计摘要
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        工单数据
    """
    try:
        schedule_results = await db_service.get_schedule_results_by_task(task_id)
        
        if not schedule_results:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id} 的排产结果")
        
        result = await formatter.execute(
            schedule_results,
            format_type=OutputFormat.WORK_ORDERS,
            group_by=group_by,
            include_summary=include_summary
        )
        
        return {
            "code": 200,
            "message": "工单数据生成成功",
            "data": result["data"],
            "metadata": {
                "task_id": task_id,
                "grouping": group_by,
                "total_work_orders": result["data"]["total_count"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工单数据生成失败: {str(e)}")


@router.post("/report", summary="生成统计分析报告")
async def format_statistical_report(
    task_id: str,
    detail_level: str = Query("standard", description="详细级别 (basic/standard/detailed)"),
    include_charts: bool = Query(True, description="包含图表数据"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    生成统计分析报告
    
    Args:
        task_id: 排产任务ID
        detail_level: 分析详细级别
        include_charts: 是否包含图表数据
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        统计报告数据
    """
    try:
        schedule_results = await db_service.get_schedule_results_by_task(task_id)
        
        if not schedule_results:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id} 的排产结果")
        
        result = await formatter.execute(
            schedule_results,
            format_type=OutputFormat.STATISTICAL_REPORT,
            detail_level=detail_level,
            include_charts=include_charts
        )
        
        return {
            "code": 200,
            "message": "统计报告生成成功",
            "data": result["data"],
            "metadata": {
                "task_id": task_id,
                "detail_level": detail_level,
                "charts_included": include_charts
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计报告生成失败: {str(e)}")


@router.post("/charts/{chart_type}", summary="生成ECharts图表数据")
async def format_echarts_data(
    task_id: str,
    chart_type: ChartTypeAPI,
    width: int = Query(1200, description="图表宽度"),
    height: int = Query(600, description="图表高度"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    生成指定类型的ECharts图表数据
    
    Args:
        task_id: 排产任务ID
        chart_type: 图表类型
        width: 图表宽度
        height: 图表高度
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        ECharts图表配置
    """
    try:
        schedule_results = await db_service.get_schedule_results_by_task(task_id)
        
        if not schedule_results:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id} 的排产结果")
        
        # 更新图表尺寸配置
        formatter.formatter_config.chart_width = width
        formatter.formatter_config.chart_height = height
        
        # 转换图表类型
        chart_type_enum = ChartType(chart_type.value)
        
        result = await formatter.execute(
            schedule_results,
            format_type=OutputFormat.ECHARTS_DATA,
            chart_type=chart_type_enum
        )
        
        return {
            "code": 200,
            "message": f"{chart_type.value}图表数据生成成功",
            "data": result["data"],
            "metadata": {
                "task_id": task_id,
                "chart_type": chart_type.value,
                "dimensions": {"width": width, "height": height}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图表数据生成失败: {str(e)}")


@router.post("/export/{format_type}", summary="导出数据文件")
async def export_data(
    task_id: str,
    format_type: ResponseFormat,
    compression_level: str = Query("standard", description="压缩级别 (none/basic/standard/high)"),
    include_metadata: bool = Query(True, description="包含元数据"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    导出指定格式的数据文件
    
    Args:
        task_id: 排产任务ID
        format_type: 导出格式
        compression_level: 压缩级别
        include_metadata: 是否包含元数据
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        导出文件数据
    """
    try:
        schedule_results = await db_service.get_schedule_results_by_task(task_id)
        
        if not schedule_results:
            raise HTTPException(status_code=404, detail=f"未找到任务 {task_id} 的排产结果")
        
        # 格式映射
        format_mapping = {
            ResponseFormat.json: OutputFormat.JSON_EXPORT,
            ResponseFormat.csv: OutputFormat.CSV_EXPORT,
            ResponseFormat.excel: OutputFormat.EXCEL_EXPORT,
            ResponseFormat.pdf: OutputFormat.PDF_REPORT
        }
        
        if format_type not in format_mapping:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format_type}")
        
        output_format = format_mapping[format_type]
        
        result = await formatter.execute(
            schedule_results,
            format_type=output_format,
            compression_level=compression_level,
            include_metadata=include_metadata
        )
        
        return {
            "code": 200,
            "message": f"{format_type}文件生成成功",
            "data": result["data"],
            "metadata": {
                "task_id": task_id,
                "format": format_type.value,
                "compression_level": compression_level,
                "file_size_estimate": len(str(result["data"]))
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件导出失败: {str(e)}")


@router.get("/batch", summary="批量格式化多个任务")
async def batch_format(
    task_ids: List[str] = Query(..., description="任务ID列表"),
    output_format: ResponseFormat = Query(ResponseFormat.gantt, description="输出格式"),
    formatter: MonthlyResultFormatter = Depends(get_formatter_service),
    db_service: DatabaseQueryService = Depends()
) -> Dict[str, Any]:
    """
    批量格式化多个任务的排产结果
    
    Args:
        task_ids: 任务ID列表
        output_format: 输出格式
        formatter: 格式化服务
        db_service: 数据库查询服务
    
    Returns:
        批量格式化结果
    """
    try:
        batch_results = {}
        
        for task_id in task_ids:
            try:
                schedule_results = await db_service.get_schedule_results_by_task(task_id)
                
                if not schedule_results:
                    batch_results[task_id] = {
                        "status": "error",
                        "message": f"未找到任务 {task_id} 的排产结果"
                    }
                    continue
                
                # 根据格式类型选择输出格式
                if output_format == ResponseFormat.gantt:
                    format_enum = OutputFormat.VUE_GANTTASTIC
                elif output_format == ResponseFormat.orders:
                    format_enum = OutputFormat.WORK_ORDERS
                elif output_format == ResponseFormat.json:
                    format_enum = OutputFormat.JSON_EXPORT
                else:
                    format_enum = OutputFormat.GANTT_CHART
                
                result = await formatter.execute(
                    schedule_results,
                    format_type=format_enum
                )
                
                batch_results[task_id] = {
                    "status": "success",
                    "data": result["data"],
                    "metadata": result["metadata"]
                }
                
            except Exception as e:
                batch_results[task_id] = {
                    "status": "error",
                    "message": str(e)
                }
        
        success_count = sum(1 for r in batch_results.values() if r["status"] == "success")
        
        return {
            "code": 200,
            "message": f"批量处理完成，成功: {success_count}/{len(task_ids)}",
            "data": batch_results,
            "metadata": {
                "total_tasks": len(task_ids),
                "successful": success_count,
                "failed": len(task_ids) - success_count,
                "format": output_format.value
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")


@router.get("/performance", summary="获取性能统计")
async def get_performance_stats(
    formatter: MonthlyResultFormatter = Depends(get_formatter_service)
) -> Dict[str, Any]:
    """获取格式化器性能统计信息"""
    return {
        "code": 200,
        "message": "性能统计获取成功",
        "data": formatter.performance_stats,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "formatter_version": formatter.version
        }
    }


@router.post("/config", summary="更新格式化器配置")
async def update_formatter_config(
    locale: Optional[LocaleType] = None,
    color_scheme: Optional[str] = None,
    enable_compression: Optional[bool] = None,
    gantt_time_scale: Optional[str] = None,
    formatter: MonthlyResultFormatter = Depends(get_formatter_service)
) -> Dict[str, Any]:
    """
    动态更新格式化器配置
    
    Args:
        locale: 本地化语言
        color_scheme: 颜色方案
        enable_compression: 启用压缩
        gantt_time_scale: 甘特图时间刻度
        formatter: 格式化服务
    
    Returns:
        更新结果
    """
    try:
        config_updates = {}
        
        if locale is not None:
            formatter.formatter_config.locale = locale
            config_updates["locale"] = locale.value
        
        if color_scheme is not None:
            formatter.formatter_config.color_scheme = color_scheme
            config_updates["color_scheme"] = color_scheme
        
        if enable_compression is not None:
            formatter.formatter_config.enable_compression = enable_compression
            config_updates["enable_compression"] = enable_compression
        
        if gantt_time_scale is not None:
            formatter.formatter_config.gantt_time_scale = gantt_time_scale
            config_updates["gantt_time_scale"] = gantt_time_scale
        
        # 重新加载本地化字符串
        if locale is not None:
            formatter.locale_strings = formatter._load_locale_strings()
        
        return {
            "code": 200,
            "message": "配置更新成功",
            "data": {
                "updated_fields": config_updates,
                "current_config": {
                    "locale": formatter.formatter_config.locale.value,
                    "color_scheme": formatter.formatter_config.color_scheme,
                    "enable_compression": formatter.formatter_config.enable_compression,
                    "gantt_time_scale": formatter.formatter_config.gantt_time_scale
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


# 添加到主路由器
def include_formatter_routes(main_router: APIRouter):
    """将格式化器路由添加到主路由器"""
    main_router.include_router(router)