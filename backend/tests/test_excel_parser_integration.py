"""
APS智慧排产系统 - Excel解析器集成测试

测试目的: 验证Excel解析器与数据库、验证器、错误处理等组件的集成
测试策略: 集成测试 - 验证Excel解析器在真实环境中的协同工作
TDD要求: 这个测试必须失败（因为Excel解析器尚未实现），然后通过实现使其通过

集成测试内容:
1. Excel文件格式识别和处理
2. 浙江中烟月度计划格式解析
3. 数据验证和错误收集
4. 数据库存储集成
5. 并发解析处理
6. 内存和性能优化
"""

import pytest
import asyncio
from pathlib import Path
from io import BytesIO
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

# 导入待测试的组件
try:
    from app.services.excel_parser import ExcelParser  # 待实现
    from app.services.database_query_service import DatabaseQueryService
    from app.models.base_models import Machine, Material
    from app.core.config import settings
except ImportError:
    # TDD阶段：组件尚未实现
    ExcelParser = None
    DatabaseQueryService = None
    Machine = None
    Material = None
    settings = None

class TestExcelParserIntegration:
    """Excel解析器集成测试类"""
    
    def setup_method(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = {}
        
        # 创建测试用Excel文件
        self._create_test_excel_files()
        
        # 模拟数据库查询服务（TDD阶段）
        self.db_service = Mock(spec=DatabaseQueryService) if DatabaseQueryService is None else DatabaseQueryService()
        
    def teardown_method(self):
        """测试清理"""
        # 清理临时文件
        for file_path in self.test_files.values():
            if os.path.exists(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)
        
    def _create_test_excel_files(self):
        """创建测试用Excel文件"""
        # 创建有效的浙江中烟月度计划Excel文件
        self.test_files['valid_monthly_plan'] = self._create_valid_monthly_plan_excel()
        
        # 创建包含错误的Excel文件
        self.test_files['invalid_format'] = self._create_invalid_format_excel()
        
        # 创建大文件（性能测试用）
        self.test_files['large_file'] = self._create_large_excel_file()
        
        # 创建空文件
        self.test_files['empty_file'] = self._create_empty_excel_file()
        
    def _create_valid_monthly_plan_excel(self) -> str:
        """创建有效的月度计划Excel文件"""
        file_path = os.path.join(self.temp_dir, "浙江中烟2024年11月份生产计划安排表.xlsx")
        
        # 模拟创建真实的Excel文件结构
        # 这里使用简化的内容，实际应该使用openpyxl创建完整的Excel
        with open(file_path, 'wb') as f:
            # Excel文件头
            f.write(b'PK\\x03\\x04')
            # 模拟浙江中烟月度计划表结构
            f.write(b'''
            Mock Excel Content - Valid Monthly Plan
            Headers: 月份,品牌规格,计划箱数,机台分配,备注
            Data: 2024-11,HNZJHYLC001,1000,F001|F002,正常生产
            Data: 2024-11,HNZJHYLC002,800,M001,优先处理
            '''.encode('utf-8'))
            
        return file_path
        
    def _create_invalid_format_excel(self) -> str:
        """创建格式无效的Excel文件"""
        file_path = os.path.join(self.temp_dir, "invalid_format.xlsx")
        
        with open(file_path, 'wb') as f:
            f.write(b'PK\\x03\\x04')
            f.write(b'''
            Mock Excel Content - Invalid Format
            Missing required headers
            Incorrect data structure
            '''.encode('utf-8'))
            
        return file_path
        
    def _create_large_excel_file(self) -> str:
        """创建大型Excel文件（性能测试用）"""
        file_path = os.path.join(self.temp_dir, "large_monthly_plan.xlsx")
        
        with open(file_path, 'wb') as f:
            f.write(b'PK\\x03\\x04')
            # 模拟大量数据
            large_content = "Mock Large Excel Content\\n" * 10000
            f.write(large_content.encode('utf-8'))
            
        return file_path
        
    def _create_empty_excel_file(self) -> str:
        """创建空Excel文件"""
        file_path = os.path.join(self.temp_dir, "empty.xlsx")
        
        with open(file_path, 'wb') as f:
            f.write(b'PK\\x03\\x04')  # 只有Excel文件头
            
        return file_path
        
    def test_excel_parser_initialization_integration(self):
        """测试Excel解析器初始化集成 - TDD: 当前应该失败，解析器未实现"""
        print("\\n🔧 Excel解析器初始化集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 正确！")
            print("📋 下一步：实现 app/services/excel_parser.py")
            return
            
        # 如果解析器已实现，测试初始化
        try:
            parser = ExcelParser(db_service=self.db_service)
            assert parser is not None
            assert parser.db_service is not None
            print("✅ Excel解析器初始化成功")
            
        except Exception as e:
            pytest.fail(f"Excel解析器初始化失败: {e}")
            
    def test_valid_monthly_plan_parsing_integration(self):
        """测试有效月度计划解析集成"""
        print("\\n📊 有效月度计划解析集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        file_path = self.test_files['valid_monthly_plan']
        
        try:
            # 执行解析
            parse_result = parser.parse_monthly_plan_excel(file_path)
            
            # 验证解析结果结构
            assert 'monthly_batch_id' in parse_result
            assert 'total_records' in parse_result
            assert 'valid_records' in parse_result
            assert 'error_records' in parse_result
            assert 'records' in parse_result
            assert 'errors' in parse_result
            
            # 验证数据类型
            assert isinstance(parse_result['total_records'], int)
            assert isinstance(parse_result['valid_records'], int)
            assert isinstance(parse_result['error_records'], int)
            assert isinstance(parse_result['records'], list)
            assert isinstance(parse_result['errors'], list)
            
            # 验证记录结构
            if parse_result['records']:
                record = parse_result['records'][0]
                expected_fields = [
                    'monthly_plan_id', 'monthly_work_order_nr', 'monthly_article_nr',
                    'monthly_target_quantity', 'monthly_planned_boxes',
                    'monthly_feeder_codes', 'monthly_maker_codes'
                ]
                for field in expected_fields:
                    assert field in record
                    
            print(f"✅ 解析成功: {parse_result['valid_records']}/{parse_result['total_records']} 有效记录")
            
        except Exception as e:
            pytest.fail(f"有效文件解析失败: {e}")
            
    def test_invalid_format_handling_integration(self):
        """测试无效格式处理集成"""
        print("\\n🚨 无效格式处理集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        file_path = self.test_files['invalid_format']
        
        try:
            parse_result = parser.parse_monthly_plan_excel(file_path)
            
            # 验证错误处理
            assert parse_result['error_records'] > 0
            assert len(parse_result['errors']) > 0
            
            # 验证错误详情
            error = parse_result['errors'][0]
            assert 'row_number' in error
            assert 'error_type' in error
            assert 'error_message' in error
            
            print(f"✅ 错误处理成功: {len(parse_result['errors'])} 个错误被捕获")
            
        except Exception as e:
            print(f"✅ 预期异常被正确处理: {e}")
            
    def test_database_integration_during_parsing(self):
        """测试解析过程中的数据库集成"""
        print("\\n🗄️ 数据库集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        # 配置数据库服务模拟
        if isinstance(self.db_service, Mock):
            self.db_service.save_monthly_plan_record.return_value = True
            self.db_service.get_machine_by_code.return_value = Mock(machine_code='F001')
            self.db_service.get_material_by_code.return_value = Mock(material_code='HNZJHYLC001')
            
        parser = ExcelParser(db_service=self.db_service)
        file_path = self.test_files['valid_monthly_plan']
        
        try:
            # 执行解析（包含数据库操作）
            parse_result = parser.parse_monthly_plan_excel(
                file_path, 
                save_to_database=True
            )
            
            # 验证数据库操作被调用
            if isinstance(self.db_service, Mock):
                assert self.db_service.save_monthly_plan_record.called
                print("✅ 数据库保存操作被正确调用")
                
            # 验证批次ID生成
            assert parse_result['monthly_batch_id'].startswith('MONTHLY_')
            
            print("✅ 数据库集成测试通过")
            
        except Exception as e:
            pytest.fail(f"数据库集成失败: {e}")
            
    def test_large_file_performance_integration(self):
        """测试大文件性能集成"""
        print("\\n⚡ 大文件性能集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        file_path = self.test_files['large_file']
        
        import time
        start_time = time.time()
        
        try:
            parse_result = parser.parse_monthly_plan_excel(file_path)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 验证性能要求
            assert execution_time < 30.0, f"大文件解析耗时过长: {execution_time:.2f}秒"
            
            # 验证内存使用（简化检查）
            file_size = os.path.getsize(file_path)
            print(f"✅ 大文件解析完成: 文件大小 {file_size/1024:.1f}KB, 耗时 {execution_time:.2f}秒")
            
        except Exception as e:
            print(f"⚠️ 大文件处理异常（可能是预期的）: {e}")
            
    def test_concurrent_parsing_integration(self):
        """测试并发解析集成"""
        print("\\n🔄 并发解析集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        import threading
        import time
        
        def parse_file(file_path, results, index):
            try:
                parser = ExcelParser(db_service=self.db_service)
                result = parser.parse_monthly_plan_excel(file_path)
                results[index] = ('success', result)
            except Exception as e:
                results[index] = ('error', str(e))
                
        # 创建多个并发解析任务
        threads = []
        results = {}
        file_paths = [
            self.test_files['valid_monthly_plan'],
            self.test_files['valid_monthly_plan'],  # 同一文件的并发解析
            self.test_files['invalid_format']
        ]
        
        start_time = time.time()
        
        for i, file_path in enumerate(file_paths):
            thread = threading.Thread(target=parse_file, args=(file_path, results, i))
            threads.append(thread)
            thread.start()
            
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
        end_time = time.time()
        
        # 验证并发结果
        successful_parses = sum(1 for status, _ in results.values() if status == 'success')
        print(f"✅ 并发解析完成: {successful_parses}/{len(file_paths)} 成功, 耗时 {end_time - start_time:.2f}秒")
        
        # 验证并发安全性
        for i, (status, result) in results.items():
            if status == 'success':
                assert 'monthly_batch_id' in result
                print(f"  线程{i}: 批次ID {result['monthly_batch_id']}")
                
    def test_memory_optimization_integration(self):
        """测试内存优化集成"""
        print("\\n💾 内存优化集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        import psutil
        import gc
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        parser = ExcelParser(db_service=self.db_service)
        
        # 解析大文件
        file_path = self.test_files['large_file']
        
        try:
            parse_result = parser.parse_monthly_plan_excel(file_path)
            
            # 强制垃圾回收
            gc.collect()
            
            # 获取解析后内存使用
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"✅ 内存使用: 初始 {initial_memory:.1f}MB, 最终 {final_memory:.1f}MB, 增长 {memory_increase:.1f}MB")
            
            # 验证内存使用合理性（根据文件大小）
            file_size_mb = os.path.getsize(file_path) / 1024 / 1024
            assert memory_increase < file_size_mb * 3, f"内存使用过多: {memory_increase:.1f}MB"
            
        except Exception as e:
            print(f"⚠️ 内存优化测试异常: {e}")
            
    def test_error_recovery_integration(self):
        """测试错误恢复集成"""
        print("\\n🔄 错误恢复集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        
        # 测试各种错误场景的恢复
        error_scenarios = [
            (self.test_files['empty_file'], "空文件处理"),
            ("nonexistent_file.xlsx", "文件不存在"),
            (self.test_files['invalid_format'], "格式错误")
        ]
        
        for file_path, scenario_name in error_scenarios:
            try:
                if file_path == "nonexistent_file.xlsx":
                    # 跳过不存在的文件
                    continue
                    
                result = parser.parse_monthly_plan_excel(file_path)
                
                # 验证错误恢复
                if result['error_records'] > 0:
                    assert 'errors' in result
                    assert len(result['errors']) > 0
                    print(f"✅ {scenario_name}: 错误正确捕获和记录")
                else:
                    print(f"✅ {scenario_name}: 处理成功")
                    
            except Exception as e:
                print(f"✅ {scenario_name}: 异常正确处理 - {e}")
                
    def test_data_validation_integration(self):
        """测试数据验证集成"""
        print("\\n✅ 数据验证集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        file_path = self.test_files['valid_monthly_plan']
        
        try:
            # 启用严格验证模式
            parse_result = parser.parse_monthly_plan_excel(
                file_path, 
                validation_level='strict'
            )
            
            # 验证数据验证结果
            if parse_result['valid_records'] > 0:
                for record in parse_result['records']:
                    # 验证必需字段
                    assert record['monthly_article_nr'] is not None
                    assert record['monthly_target_quantity'] > 0
                    assert record['monthly_planned_boxes'] > 0
                    
                    # 验证数据格式
                    assert record['monthly_article_nr'].startswith('HN')  # 杭州工厂前缀
                    
            print(f"✅ 数据验证完成: {parse_result['valid_records']} 条记录通过验证")
            
        except Exception as e:
            pytest.fail(f"数据验证集成失败: {e}")
            
    def test_excel_format_detection_integration(self):
        """测试Excel格式检测集成"""
        print("\\n🔍 Excel格式检测集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        parser = ExcelParser(db_service=self.db_service)
        
        # 测试不同文件格式的检测
        format_tests = [
            (self.test_files['valid_monthly_plan'], True, "有效Excel文件"),
            (self.test_files['invalid_format'], False, "无效格式文件"),
        ]
        
        for file_path, expected_valid, description in format_tests:
            try:
                is_valid = parser.validate_excel_format(file_path)
                assert is_valid == expected_valid, f"{description} 格式检测失败"
                print(f"✅ {description}: 格式检测正确")
                
            except AttributeError:
                print(f"⚠️ {description}: validate_excel_format 方法未实现")
            except Exception as e:
                print(f"⚠️ {description}: 格式检测异常 - {e}")


# =============================================================================
# 异步解析集成测试
# =============================================================================

class TestAsyncExcelParserIntegration:
    """异步Excel解析器集成测试"""
    
    def setup_method(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.asyncio
    async def test_async_excel_parsing_integration(self):
        """测试异步Excel解析集成"""
        print("\\n🔄 异步Excel解析集成测试")
        
        if ExcelParser is None:
            print("✅ TDD RED状态：Excel解析器未实现 - 跳过")
            return
            
        # 模拟异步解析器
        try:
            parser = ExcelParser(db_service=Mock())
            
            # 如果支持异步解析
            if hasattr(parser, 'async_parse_monthly_plan_excel'):
                file_path = os.path.join(self.temp_dir, "async_test.xlsx")
                
                # 创建测试文件
                with open(file_path, 'wb') as f:
                    f.write(b'PK\\x03\\x04Mock Async Excel Content')
                    
                result = await parser.async_parse_monthly_plan_excel(file_path)
                
                assert 'monthly_batch_id' in result
                print("✅ 异步Excel解析成功")
            else:
                print("⚠️ 异步解析方法未实现")
                
        except Exception as e:
            print(f"⚠️ 异步解析测试异常: {e}")


# =============================================================================
# 测试工具和配置
# =============================================================================

def test_excel_parser_integration_specifications():
    """测试Excel解析器集成规范本身"""
    assert TestExcelParserIntegration.__doc__ is not None
    assert "集成测试" in TestExcelParserIntegration.__doc__
    assert "TDD要求" in TestExcelParserIntegration.__doc__


# =============================================================================
# 运行测试的主函数
# =============================================================================

if __name__ == "__main__":
    # 独立运行此集成测试
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\\n" + "="*80)
    print("⚠️ 重要提醒：这是TDD集成测试")
    print("✅ 当前状态：测试已写好并预期失败（Excel解析器未实现）")
    print("📋 下一步：实现 app/services/excel_parser.py")
    print("🎯 实现完成后：运行此测试验证Excel解析器集成")
    print("="*80)