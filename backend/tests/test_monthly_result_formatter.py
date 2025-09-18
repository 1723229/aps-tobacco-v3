"""
月度结果格式化算法模块测试

测试 MonthlyResultFormatter 的各种格式化功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from app.algorithms.monthly_scheduling.monthly_result_formatter import (
    MonthlyResultFormatter,
    FormatterConfig,
    OutputFormat,
    LocaleType,
    ChartType,
    GanttTask,
    WorkOrderData,
    StatisticalSummary
)


class TestMonthlyResultFormatter:
    """月度结果格式化器测试类"""
    
    @pytest.fixture
    def mock_schedule_results(self):
        """创建模拟排产结果数据"""
        results = []
        base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        for i in range(3):
            mock_result = Mock()
            mock_result.monthly_schedule_id = i + 1
            mock_result.monthly_task_id = f'TASK_{i+1:03d}'
            mock_result.monthly_work_order_nr = f'WO_{i+1:04d}'
            mock_result.monthly_article_nr = f'HN{i+1:04d}'
            mock_result.allocated_quantity = Decimal(str(1000 + i * 200))
            mock_result.assigned_feeder_code = f'FEEDER_{(i % 2) + 1:02d}'
            mock_result.assigned_maker_code = f'MAKER_{(i % 2) + 1:02d}'
            mock_result.scheduled_start_time = base_time + timedelta(hours=i * 2)
            mock_result.scheduled_end_time = base_time + timedelta(hours=i * 2 + 1.5)
            mock_result.scheduled_duration_hours = Decimal('1.5')
            mock_result.monthly_schedule_status = ['PENDING', 'SCHEDULED', 'EXECUTING'][i]
            mock_result.monthly_execution_progress = Decimal(str(i * 30))
            mock_result.priority_score = Decimal(str(80 - i * 10))
            mock_result.algorithm_version = 'v1.0'
            mock_result.optimization_notes = f'任务{i+1}优化说明'
            mock_result.constraint_violations = None
            mock_result.created_time = datetime.now()
            mock_result.updated_time = datetime.now()
            mock_result.get_calendar_constraints_info = MagicMock(return_value={})
            
            results.append(mock_result)
        
        return results
    
    @pytest.fixture
    def formatter(self):
        """创建格式化器实例"""
        config = FormatterConfig(
            locale=LocaleType.ZH_CN,
            enable_compression=True
        )
        return MonthlyResultFormatter(config)
    
    def test_formatter_initialization(self, formatter):
        """测试格式化器初始化"""
        assert formatter is not None
        assert formatter.formatter_config.locale == LocaleType.ZH_CN
        assert formatter.formatter_config.enable_compression is True
        assert len(formatter.locale_strings) > 0
        assert len(formatter.color_schemes) > 0
    
    def test_validate_input_with_valid_data(self, formatter, mock_schedule_results):
        """测试有效输入数据验证"""
        assert formatter.validate_input(mock_schedule_results) is True
        assert formatter.validate_input(mock_schedule_results[0]) is True
    
    def test_validate_input_with_invalid_data(self, formatter):
        """测试无效输入数据验证"""
        assert formatter.validate_input([]) is False
        assert formatter.validate_input(None) is False
        assert formatter.validate_input("invalid") is False
    
    @pytest.mark.asyncio
    async def test_format_gantt_data(self, formatter, mock_schedule_results):
        """测试甘特图数据格式化"""
        result = await formatter.format_gantt_data(mock_schedule_results)
        
        assert "tasks" in result
        assert "machine_groups" in result
        assert "timeline" in result
        assert "config" in result
        
        assert len(result["tasks"]) == 3
        assert len(result["machine_groups"]) > 0
        
        # 检查任务格式
        task = result["tasks"][0]
        assert "id" in task
        assert "label" in task
        assert "start" in task
        assert "end" in task
    
    @pytest.mark.asyncio
    async def test_format_work_orders(self, formatter, mock_schedule_results):
        """测试工单数据格式化"""
        result = await formatter.format_work_orders(mock_schedule_results, include_summary=True)
        
        assert "work_orders" in result
        assert "grouped_orders" in result
        assert "summary" in result
        assert "total_count" in result
        
        assert len(result["work_orders"]) == 3
        assert result["total_count"] == 3
        
        # 检查工单格式
        work_order = result["work_orders"][0]
        assert "work_order_nr" in work_order
        assert "article_nr" in work_order
        assert "quantity" in work_order
        assert "machine_feeder" in work_order
        assert "machine_maker" in work_order
    
    @pytest.mark.asyncio
    async def test_format_reports(self, formatter, mock_schedule_results):
        """测试统计报告格式化"""
        result = await formatter.format_reports(mock_schedule_results, include_charts=True)
        
        assert "summary" in result
        assert "analysis" in result
        assert "charts" in result
        assert "trends" in result
        assert "insights" in result
        
        # 检查摘要数据
        summary = result["summary"]
        assert "total_tasks" in summary
        assert "total_work_orders" in summary
        assert "total_production_hours" in summary
        assert summary["total_tasks"] == 3
    
    @pytest.mark.asyncio
    async def test_format_json_export(self, formatter, mock_schedule_results):
        """测试JSON导出格式化"""
        result = await formatter.format_json_export(
            mock_schedule_results, 
            compression_level="standard",
            include_metadata=True
        )
        
        assert "data" in result
        assert "count" in result
        assert "metadata" in result
        
        assert len(result["data"]) == 3
        assert result["count"] == 3
        
        # 检查数据格式
        item = result["data"][0]
        assert "schedule_id" in item
        assert "work_order_nr" in item
        assert "article_nr" in item
    
    @pytest.mark.asyncio
    async def test_format_csv_export(self, formatter, mock_schedule_results):
        """测试CSV导出格式化"""
        result = await formatter.format_csv_export(
            mock_schedule_results,
            delimiter=",",
            include_header=True
        )
        
        assert "content" in result
        assert "file_name" in result
        assert "encoding" in result
        assert "record_count" in result
        
        assert result["record_count"] == 3
        assert "schedule_id" in result["content"]  # 检查标题行
        
        # 检查CSV格式
        lines = result["content"].split('\n')
        assert len(lines) >= 4  # 标题行 + 3个数据行
    
    @pytest.mark.asyncio
    async def test_format_excel_export(self, formatter, mock_schedule_results):
        """测试Excel导出格式化"""
        result = await formatter.format_excel_export(
            mock_schedule_results,
            include_charts=True
        )
        
        assert "file_name" in result
        assert "worksheets" in result
        assert "charts" in result
        assert "config" in result
        
        # 检查工作表
        worksheets = result["worksheets"]
        assert "summary" in worksheets
        assert "work_orders" in worksheets
        assert "machine_utilization" in worksheets
        assert "timeline" in worksheets
    
    @pytest.mark.asyncio
    async def test_format_vue_ganttastic(self, formatter, mock_schedule_results):
        """测试Vue Ganttastic格式化"""
        result = await formatter.format_vue_ganttastic(mock_schedule_results)
        
        assert "rows" in result
        assert "config" in result
        assert "metadata" in result
        
        # 检查甘特图行
        rows = result["rows"]
        assert len(rows) > 0
        
        row = rows[0]
        assert "id" in row
        assert "label" in row
        assert "bars" in row
    
    @pytest.mark.asyncio
    async def test_format_echarts_data(self, formatter, mock_schedule_results):
        """测试ECharts数据格式化"""
        # 测试时间线图
        result = await formatter.format_echarts_data(
            mock_schedule_results,
            chart_type=ChartType.TIMELINE
        )
        
        assert "title" in result
        assert "xAxis" in result
        assert "yAxis" in result
        assert "series" in result
        
        # 测试机台利用率图
        result = await formatter.format_echarts_data(
            mock_schedule_results,
            chart_type=ChartType.MACHINE_UTILIZATION
        )
        
        assert "title" in result
        assert "series" in result
    
    @pytest.mark.asyncio
    async def test_execute_method(self, formatter, mock_schedule_results):
        """测试execute方法"""
        result = await formatter.execute(
            mock_schedule_results,
            format_type=OutputFormat.GANTT_CHART
        )
        
        assert result["status"] == "success"
        assert result["format_type"] == OutputFormat.GANTT_CHART.value
        assert "data" in result
        assert "metadata" in result
        
        # 检查元数据
        metadata = result["metadata"]
        assert "generated_at" in metadata
        assert "processing_time_seconds" in metadata
        assert "record_count" in metadata
        assert metadata["record_count"] == 3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, formatter):
        """测试错误处理"""
        with pytest.raises(Exception):
            await formatter.execute(None, format_type="invalid_format")
        
        # 测试无效数据
        with pytest.raises(Exception):
            await formatter.execute([], format_type=OutputFormat.GANTT_CHART)
    
    def test_gantt_task_conversion(self):
        """测试甘特图任务转换"""
        task = GanttTask(
            id="test_1",
            name="测试任务",
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=2),
            duration=2.0,
            machine_code="FEEDER_01+MAKER_01",
            article_nr="HN0001"
        )
        
        # 测试Vue Ganttastic格式
        vue_format = task.to_vue_ganttastic()
        assert vue_format["id"] == "test_1"
        assert vue_format["label"] == "测试任务"
        assert "start" in vue_format
        assert "end" in vue_format
        
        # 测试ECharts格式
        echarts_format = task.to_echarts_format()
        assert echarts_format["name"] == "测试任务"
        assert len(echarts_format["value"]) == 4
    
    def test_work_order_data_conversion(self):
        """测试工单数据转换"""
        work_order = WorkOrderData(
            work_order_nr="WO_0001",
            article_nr="HN0001",
            article_name="测试产品",
            quantity=Decimal("1000.0"),
            machine_feeder="FEEDER_01",
            machine_maker="MAKER_01",
            scheduled_start=datetime.now(),
            scheduled_end=datetime.now() + timedelta(hours=2),
            status="SCHEDULED",
            priority="HIGH",
            duration_hours=2.0
        )
        
        data = work_order.to_dict()
        assert data["work_order_nr"] == "WO_0001"
        assert data["article_nr"] == "HN0001"
        assert data["quantity"] == 1000.0
        assert data["status"] == "SCHEDULED"
    
    def test_localization(self, formatter):
        """测试本地化功能"""
        # 测试中文本地化
        zh_string = formatter._get_localized_string("csv.header.work_order_nr", "默认")
        assert zh_string == "工单号"
        
        # 测试英文本地化
        formatter.formatter_config.locale = LocaleType.EN_US
        formatter.locale_strings = formatter._load_locale_strings()
        en_string = formatter._get_localized_string("csv.header.work_order_nr", "default")
        assert en_string == "Work Order"
    
    def test_color_schemes(self, formatter):
        """测试颜色方案"""
        # 测试优先级颜色
        high_priority_color = formatter._get_priority_color(Decimal("85.0"))
        medium_priority_color = formatter._get_priority_color(Decimal("65.0"))
        low_priority_color = formatter._get_priority_color(Decimal("25.0"))
        
        assert high_priority_color != medium_priority_color
        assert medium_priority_color != low_priority_color
        
        # 测试不同颜色方案
        default_colors = formatter.color_schemes["default"]
        dark_colors = formatter.color_schemes["dark"]
        
        assert "primary" in default_colors
        assert "success" in default_colors
        assert default_colors["primary"] != dark_colors["primary"]
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, formatter, mock_schedule_results):
        """测试性能统计跟踪"""
        initial_stats = formatter.performance_stats.copy()
        
        await formatter.execute(
            mock_schedule_results,
            format_type=OutputFormat.JSON_EXPORT
        )
        
        final_stats = formatter.performance_stats
        
        assert final_stats["formats_generated"] > initial_stats["formats_generated"]
        assert final_stats["total_records_processed"] > initial_stats["total_records_processed"]
        assert final_stats["average_processing_time"] >= 0


# 集成测试
@pytest.mark.asyncio
async def test_integration_multiple_formats(mock_schedule_results):
    """测试多种格式的集成转换"""
    formatter = MonthlyResultFormatter()
    
    formats_to_test = [
        OutputFormat.GANTT_CHART,
        OutputFormat.WORK_ORDERS,
        OutputFormat.JSON_EXPORT,
        OutputFormat.CSV_EXPORT
    ]
    
    results = {}
    
    for format_type in formats_to_test:
        result = await formatter.execute(
            mock_schedule_results,
            format_type=format_type
        )
        results[format_type.value] = result
        assert result["status"] == "success"
    
    # 验证不同格式包含相同数量的记录
    gantt_tasks = len(results["gantt_chart"]["data"]["tasks"])
    work_orders = len(results["work_orders"]["data"]["work_orders"])
    json_records = results["json_export"]["data"]["count"]
    csv_records = results["csv_export"]["data"]["record_count"]
    
    assert gantt_tasks == work_orders == json_records == csv_records


if __name__ == "__main__":
    # 简单的手动测试
    async def manual_test():
        # 创建模拟数据
        results = []
        base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        for i in range(2):
            mock_result = type('MockResult', (), {
                'monthly_schedule_id': i + 1,
                'monthly_task_id': f'TASK_{i+1:03d}',
                'monthly_work_order_nr': f'WO_{i+1:04d}',
                'monthly_article_nr': f'HN{i+1:04d}',
                'allocated_quantity': Decimal(str(1000 + i * 200)),
                'assigned_feeder_code': f'FEEDER_{(i % 2) + 1:02d}',
                'assigned_maker_code': f'MAKER_{(i % 2) + 1:02d}',
                'scheduled_start_time': base_time + timedelta(hours=i * 2),
                'scheduled_end_time': base_time + timedelta(hours=i * 2 + 1.5),
                'scheduled_duration_hours': Decimal('1.5'),
                'monthly_schedule_status': ['PENDING', 'SCHEDULED'][i],
                'monthly_execution_progress': Decimal(str(i * 50)),
                'priority_score': Decimal(str(80 - i * 10)),
                'algorithm_version': 'v1.0',
                'optimization_notes': f'任务{i+1}优化说明',
                'constraint_violations': None,
                'created_time': datetime.now(),
                'updated_time': datetime.now(),
                'get_calendar_constraints_info': lambda: {}
            })()
            results.append(mock_result)
        
        # 测试格式化器
        formatter = MonthlyResultFormatter()
        
        print("🧪 月度结果格式化器手动测试")
        
        # 测试甘特图格式
        print("📊 测试甘特图格式...")
        gantt_result = await formatter.execute(results, format_type=OutputFormat.GANTT_CHART)
        print(f"   甘特图任务数: {len(gantt_result['data']['tasks'])}")
        
        # 测试工单格式
        print("📋 测试工单格式...")
        orders_result = await formatter.execute(results, format_type=OutputFormat.WORK_ORDERS)
        print(f"   工单数量: {orders_result['data']['total_count']}")
        
        # 测试JSON导出
        print("💾 测试JSON导出...")
        json_result = await formatter.execute(results, format_type=OutputFormat.JSON_EXPORT)
        print(f"   JSON记录数: {json_result['data']['count']}")
        
        print("✅ 所有测试通过!")
        print(f"📊 性能统计: {formatter.performance_stats}")
    
    asyncio.run(manual_test())