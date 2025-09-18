"""
T014 测试助手工具

提供Excel解析集成测试的辅助功能：
- 测试数据验证
- 性能监控
- 并发测试管理
- 错误模拟
"""

import time
import threading
import psutil
import gc
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    execution_time: float
    memory_usage_mb: float
    memory_peak_mb: float
    cpu_usage_percent: float
    records_processed: int
    records_per_second: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_time': self.execution_time,
            'memory_usage_mb': self.memory_usage_mb,
            'memory_peak_mb': self.memory_peak_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'records_processed': self.records_processed,
            'records_per_second': self.records_per_second
        }


@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool
    error_count: int
    warning_count: int
    missing_fields: List[str]
    invalid_values: List[str]
    format_errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'missing_fields': self.missing_fields,
            'invalid_values': self.invalid_values,
            'format_errors': self.format_errors
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time: Optional[float] = None
        self.start_memory: Optional[float] = None
        self.peak_memory: float = 0
        self.cpu_samples: List[float] = []
    
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.cpu_samples = []
        
        # 启动CPU监控线程
        self._start_cpu_monitoring()
    
    def _start_cpu_monitoring(self):
        """启动CPU监控线程"""
        def monitor_cpu():
            while self.start_time and time.time() - self.start_time < 300:  # 最多监控5分钟
                try:
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    self.cpu_samples.append(cpu_percent)
                    
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    self.peak_memory = max(self.peak_memory, current_memory)
                    
                    time.sleep(0.5)
                except:
                    break
        
        thread = threading.Thread(target=monitor_cpu, daemon=True)
        thread.start()
    
    def stop_monitoring(self, records_processed: int = 0) -> PerformanceMetrics:
        """停止监控并返回结果"""
        if not self.start_time or not self.start_memory:
            raise ValueError("监控未启动")
        
        end_time = time.time()
        execution_time = end_time - self.start_time
        
        end_memory = self.process.memory_info().rss / 1024 / 1024
        memory_usage = end_memory - self.start_memory
        
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        
        records_per_second = records_processed / execution_time if execution_time > 0 else 0
        
        # 重置监控状态
        self.start_time = None
        self.start_memory = None
        
        return PerformanceMetrics(
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            memory_peak_mb=self.peak_memory,
            cpu_usage_percent=avg_cpu,
            records_processed=records_processed,
            records_per_second=records_per_second
        )


class DataValidator:
    """数据验证器"""
    
    # 杭州厂必需字段
    REQUIRED_FIELDS = [
        'monthly_work_order_nr',
        'monthly_article_nr', 
        'monthly_article_name',
        'monthly_target_quantity',
        'monthly_plan_year',
        'monthly_plan_month'
    ]
    
    # 可选字段
    OPTIONAL_FIELDS = [
        'monthly_specification',
        'monthly_package_type',
        'monthly_planned_boxes',
        'monthly_feeder_codes',
        'monthly_maker_codes',
        'monthly_planned_start',
        'monthly_planned_end',
        'monthly_extraction_notes'
    ]
    
    @classmethod
    def validate_record(cls, record: Dict[str, Any]) -> ValidationResult:
        """验证单条记录"""
        missing_fields = []
        invalid_values = []
        format_errors = []
        
        # 检查必需字段
        for field in cls.REQUIRED_FIELDS:
            if field not in record or record[field] is None:
                missing_fields.append(field)
        
        # 验证数据格式
        if 'monthly_work_order_nr' in record:
            work_order = record['monthly_work_order_nr']
            if work_order and not work_order.startswith('HZWO'):
                format_errors.append(f"工单号格式错误: {work_order}")
        
        if 'monthly_article_nr' in record:
            article_nr = record['monthly_article_nr']
            if article_nr and not article_nr.startswith('HNZJHYLC'):
                format_errors.append(f"牌号代码格式错误: {article_nr}")
        
        if 'monthly_target_quantity' in record:
            quantity = record['monthly_target_quantity']
            if quantity is not None:
                try:
                    float_quantity = float(quantity)
                    if float_quantity <= 0:
                        invalid_values.append(f"目标产量必须大于0: {quantity}")
                except (ValueError, TypeError):
                    format_errors.append(f"目标产量格式错误: {quantity}")
        
        if 'monthly_plan_year' in record:
            year = record['monthly_plan_year']
            if year is not None:
                try:
                    int_year = int(year)
                    if not (2020 <= int_year <= 2030):
                        invalid_values.append(f"计划年份超出范围: {year}")
                except (ValueError, TypeError):
                    format_errors.append(f"计划年份格式错误: {year}")
        
        if 'monthly_plan_month' in record:
            month = record['monthly_plan_month']
            if month is not None:
                try:
                    int_month = int(month)
                    if not (1 <= int_month <= 12):
                        invalid_values.append(f"计划月份超出范围: {month}")
                except (ValueError, TypeError):
                    format_errors.append(f"计划月份格式错误: {month}")
        
        # 验证机台代码格式
        for field_name, prefix in [('monthly_feeder_codes', 'F'), ('monthly_maker_codes', 'M')]:
            if field_name in record and record[field_name]:
                codes = record[field_name].split(',')
                for code in codes:
                    code = code.strip()
                    if code and not code.startswith(prefix):
                        format_errors.append(f"{field_name}格式错误: {code}")
        
        # 计算结果
        is_valid = len(missing_fields) == 0 and len(invalid_values) == 0 and len(format_errors) == 0
        error_count = len(missing_fields) + len(invalid_values) + len(format_errors)
        warning_count = 0  # 可以根据需要添加警告逻辑
        
        return ValidationResult(
            is_valid=is_valid,
            error_count=error_count,
            warning_count=warning_count,
            missing_fields=missing_fields,
            invalid_values=invalid_values,
            format_errors=format_errors
        )
    
    @classmethod
    def validate_batch(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证记录批次"""
        results = []
        total_errors = 0
        total_warnings = 0
        
        for i, record in enumerate(records):
            result = cls.validate_record(record)
            results.append({
                'record_index': i,
                'validation_result': result.to_dict()
            })
            total_errors += result.error_count
            total_warnings += result.warning_count
        
        valid_records = sum(1 for r in results if r['validation_result']['is_valid'])
        
        return {
            'total_records': len(records),
            'valid_records': valid_records,
            'invalid_records': len(records) - valid_records,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'validation_details': results
        }


class ConcurrentTestManager:
    """并发测试管理器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.lock = threading.Lock()
    
    def run_concurrent_tests(
        self, 
        test_functions: List[Callable],
        test_data: List[Any]
    ) -> Dict[str, Any]:
        """运行并发测试"""
        if len(test_functions) != len(test_data):
            raise ValueError("测试函数和测试数据数量不匹配")
        
        threads = []
        start_time = time.time()
        
        for i, (test_func, data) in enumerate(zip(test_functions, test_data)):
            thread = threading.Thread(
                target=self._run_single_test,
                args=(f"test_{i}", test_func, data)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        return {
            'total_tests': len(test_functions),
            'successful_tests': len([r for r in self.results.values() if r.get('success', False)]),
            'failed_tests': len(self.errors),
            'execution_time': end_time - start_time,
            'results': self.results,
            'errors': self.errors
        }
    
    def _run_single_test(self, test_id: str, test_func: Callable, data: Any):
        """运行单个测试"""
        try:
            result = test_func(data)
            with self.lock:
                self.results[test_id] = {
                    'success': True,
                    'result': result,
                    'thread_id': threading.current_thread().ident
                }
        except Exception as e:
            with self.lock:
                self.errors.append(f"{test_id}: {str(e)}")
                self.results[test_id] = {
                    'success': False,
                    'error': str(e),
                    'thread_id': threading.current_thread().ident
                }


class ErrorSimulator:
    """错误模拟器"""
    
    @staticmethod
    def simulate_file_corruption(file_path: str) -> str:
        """模拟文件损坏"""
        corrupted_path = file_path.replace('.xlsx', '_corrupted.xlsx')
        
        # 创建损坏的文件（只复制部分内容）
        with open(file_path, 'rb') as original:
            content = original.read()
            # 只保留前50%的内容
            corrupted_content = content[:len(content)//2]
        
        with open(corrupted_path, 'wb') as corrupted:
            corrupted.write(corrupted_content)
        
        return corrupted_path
    
    @staticmethod
    def simulate_permission_error(file_path: str) -> str:
        """模拟权限错误（在支持的系统上）"""
        try:
            os.chmod(file_path, 0o000)  # 移除所有权限
            return file_path
        except:
            # 如果无法修改权限，返回原文件
            return file_path
    
    @staticmethod
    def simulate_memory_pressure():
        """模拟内存压力"""
        # 分配大量内存以模拟内存压力
        memory_hog = []
        try:
            for i in range(1000):
                memory_hog.append([0] * 100000)  # 分配约100MB
                if i % 100 == 0:
                    time.sleep(0.01)  # 给其他线程机会
        except MemoryError:
            pass
        finally:
            # 清理内存
            del memory_hog
            gc.collect()


class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.test_results: List[Dict[str, Any]] = []
        self.performance_data: List[PerformanceMetrics] = []
    
    def add_test_result(
        self, 
        test_name: str, 
        success: bool, 
        details: Dict[str, Any],
        performance: Optional[PerformanceMetrics] = None
    ):
        """添加测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        
        if performance:
            result['performance'] = performance.to_dict()
            self.performance_data.append(performance)
        
        self.test_results.append(result)
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        successful_tests = [r for r in self.test_results if r['success']]
        failed_tests = [r for r in self.test_results if not r['success']]
        
        # 性能统计
        performance_summary = {}
        if self.performance_data:
            performance_summary = {
                'avg_execution_time': sum(p.execution_time for p in self.performance_data) / len(self.performance_data),
                'max_execution_time': max(p.execution_time for p in self.performance_data),
                'avg_memory_usage': sum(p.memory_usage_mb for p in self.performance_data) / len(self.performance_data),
                'max_memory_usage': max(p.memory_usage_mb for p in self.performance_data),
                'total_records_processed': sum(p.records_processed for p in self.performance_data),
                'avg_records_per_second': sum(p.records_per_second for p in self.performance_data) / len(self.performance_data)
            }
        
        return {
            'test_session': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_duration_seconds': total_duration
            },
            'summary': {
                'total_tests': len(self.test_results),
                'successful_tests': len(successful_tests),
                'failed_tests': len(failed_tests),
                'success_rate': len(successful_tests) / len(self.test_results) if self.test_results else 0
            },
            'performance_summary': performance_summary,
            'test_details': self.test_results,
            'failed_test_details': failed_tests
        }
    
    def save_report(self, file_path: str):
        """保存报告到文件"""
        report = self.generate_report()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# 测试助手功能
if __name__ == "__main__":
    print("🔧 测试T014助手工具...")
    
    # 测试性能监控
    print("\n📊 测试性能监控器:")
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    # 模拟一些工作
    time.sleep(1)
    test_data = [i for i in range(10000)]
    
    metrics = monitor.stop_monitoring(records_processed=len(test_data))
    print(f"   执行时间: {metrics.execution_time:.2f}秒")
    print(f"   内存使用: {metrics.memory_usage_mb:.1f}MB")
    print(f"   处理速度: {metrics.records_per_second:.0f}记录/秒")
    
    # 测试数据验证
    print("\n✅ 测试数据验证器:")
    test_record = {
        'monthly_work_order_nr': 'HZWO202412001',
        'monthly_article_nr': 'HNZJHYLC001',
        'monthly_article_name': '利群（阳光）',
        'monthly_target_quantity': 120.5,
        'monthly_plan_year': 2024,
        'monthly_plan_month': 12
    }
    
    validation_result = DataValidator.validate_record(test_record)
    print(f"   验证结果: {'通过' if validation_result.is_valid else '失败'}")
    print(f"   错误数量: {validation_result.error_count}")
    
    # 测试报告生成
    print("\n📄 测试报告生成器:")
    reporter = TestReporter()
    reporter.add_test_result("示例测试", True, {"记录数": 100}, metrics)
    
    report = reporter.generate_report()
    print(f"   测试总数: {report['summary']['total_tests']}")
    print(f"   成功率: {report['summary']['success_rate']:.1%}")
    
    print("\n✅ T014助手工具测试完成")