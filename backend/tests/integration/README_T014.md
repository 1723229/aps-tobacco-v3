# T014 杭州厂月度Excel解析集成测试

## 测试概述

T014是专为杭州卷烟厂月度Excel格式设计的完整集成测试，验证Excel解析器在真实业务场景下的可靠性和性能。

## 测试文件结构

```
backend/tests/
├── integration/
│   ├── __init__.py
│   └── test_excel_parser_monthly.py        # 主测试文件
└── fixtures/
    ├── __init__.py
    ├── hangzhou_excel_generator.py         # Excel测试文件生成器
    └── test_helpers.py                     # 测试辅助工具
```

## 测试覆盖范围

### 1. 核心功能测试
- ✅ **T014.1**: 解析器初始化集成
- ✅ **T014.2**: 杭州厂格式识别
- ✅ **T014.3**: 月度特化字段解析
- ✅ **T014.4**: 机台代码列表解析
- ✅ **T014.5**: 完整解析工作流集成

### 2. 数据质量测试
- ✅ **T014.6**: 数据验证和完整性检查
- ✅ **T014.7**: 错误处理和异常恢复
- ✅ **T014.11**: 数据库存储集成

### 3. 性能和并发测试
- ✅ **T014.8**: 性能优化（大文件<30秒）
- ✅ **T014.9**: 并发解析安全性
- ✅ **T014.10**: 异步解析集成
- ✅ **T014.12**: 内存管理集成

## 月度特化字段

测试验证以下杭州厂专用字段：

```python
MONTHLY_FIELDS = [
    'monthly_work_order_nr',    # 月度工单号 (HZWO格式)
    'monthly_article_nr',       # 月度牌号代码 (HNZJHYLC格式)
    'monthly_article_name',     # 月度牌号名称
    'monthly_specification',    # 月度规格
    'monthly_package_type',     # 月度包装类型
    'monthly_target_quantity',  # 月度目标产量(万支)
    'monthly_planned_boxes',    # 月度计划箱数
    'monthly_feeder_codes',     # 喂丝机代码列表(逗号分隔)
    'monthly_maker_codes',      # 卷包机代码列表(逗号分隔)
    'monthly_plan_year',        # 月度计划年份
    'monthly_plan_month'        # 月度计划月份
]
```

## 机台代码格式

测试验证机台代码列表解析：

- **喂丝机**: `F001,F002,F003` → `["F001", "F002", "F003"]`
- **卷包机**: `M001,M002,M003,M004` → `["M001", "M002", "M003", "M004"]`

## 测试数据生成

### HangzhouMonthlyExcelGenerator类提供：

```python
# 标准格式Excel
generator.create_standard_excel(file_path, year=2024, month=12, record_count=10)

# 复杂格式Excel（合并单元格）
generator.create_complex_format_excel(file_path)

# 大数据量Excel（性能测试）
generator.create_large_dataset_excel(file_path, record_count=1000)

# 无效格式Excel（错误处理测试）
generator.create_invalid_format_excel(file_path)

# 边界情况Excel（边界值测试）
generator.create_edge_case_excel(file_path)
```

### 真实杭州厂产品数据：

```python
HANGZHOU_PRODUCTS = [
    {"code": "HNZJHYLC001", "name": "利群（阳光）", "spec": "硬盒"},
    {"code": "HNZJHYLC002", "name": "利群（新版）", "spec": "软盒"},
    {"code": "HNZJHYLC003", "name": "红双喜（精品）", "spec": "硬盒"},
    {"code": "HNZJHYLC004", "name": "中华（软）", "spec": "软盒"},
    # ... 更多产品
]
```

## 性能要求

- **大文件解析时间**: < 30秒
- **内存使用效率**: < 5倍文件大小
- **并发解析安全**: 支持多线程同时解析
- **批次ID唯一性**: 确保并发时无冲突

## 运行测试

### 1. 当前状态（TDD RED）
```bash
cd backend
python tests/integration/test_excel_parser_monthly.py
# 输出: TDD RED状态 - 组件未实现，符合预期
```

### 2. 组件实现完成后
```bash
cd backend
pytest tests/integration/test_excel_parser_monthly.py -v
```

### 3. 运行特定测试
```bash
pytest tests/integration/test_excel_parser_monthly.py::TestHangzhouMonthlyExcelParsingIntegration::test_hangzhou_format_recognition_integration -v
```

## 依赖组件

### 需要实现的组件：

1. **ProductionPlanExcelParser** (`app/services/excel_parser.py`)
   ```python
   class ProductionPlanExcelParser:
       def __init__(self, db_service=None):
           pass
       
       def parse_excel_file(self, file_path, **kwargs):
           pass
       
       def parse_monthly_plan_excel(self, file_path, **kwargs):
           pass
       
       def validate_hangzhou_monthly_format(self, file_path):
           pass
   ```

2. **DatabaseQueryService** (`app/services/database_query_service.py`)
   ```python
   class DatabaseQueryService:
       def save_monthly_plan_batch(self, batch_data):
           pass
       
       def validate_machine_codes(self, codes):
           pass
       
       def validate_article_codes(self, codes):
           pass
   ```

### 已存在的模型：
- ✅ `MonthlyPlan` (`app/models/monthly_plan_models.py`)
- ✅ `Machine` (`app/models/base_models.py`)
- ✅ `Material` (`app/models/base_models.py`)

## 测试辅助工具

### PerformanceMonitor
```python
monitor = PerformanceMonitor()
monitor.start_monitoring()
# ... 执行解析操作
metrics = monitor.stop_monitoring(records_processed=100)
```

### DataValidator
```python
result = DataValidator.validate_record(record_data)
batch_result = DataValidator.validate_batch(records_list)
```

### ConcurrentTestManager
```python
manager = ConcurrentTestManager(max_workers=5)
results = manager.run_concurrent_tests(test_functions, test_data)
```

## 错误模拟

测试包含各种错误场景：

- 文件不存在
- 损坏的Excel文件
- 无效数据格式
- 内存压力测试
- 权限错误模拟

## TDD工作流

1. **RED阶段** ✅ (当前状态)
   - 测试已创建
   - 运行测试显示"组件未实现"

2. **GREEN阶段** (实现阶段)
   - 实现 `ProductionPlanExcelParser`
   - 实现 `DatabaseQueryService`
   - 运行测试直到通过

3. **REFACTOR阶段** (优化阶段)
   - 代码重构优化
   - 性能调优
   - 测试保持通过

## 预期测试结果

组件实现完成后，运行测试应该看到：

```
✅ T014.1: Excel解析器初始化集成测试 - PASSED
✅ T014.2: 杭州厂格式识别集成测试 - PASSED  
✅ T014.3: 月度特化字段解析测试 - PASSED
✅ T014.4: 机台代码列表解析测试 - PASSED
✅ T014.5: 完整解析工作流集成测试 - PASSED
✅ T014.6: 数据验证和完整性检查测试 - PASSED
✅ T014.7: 错误处理和异常恢复测试 - PASSED
✅ T014.8: 性能优化集成测试 - PASSED
✅ T014.9: 并发解析安全性测试 - PASSED
✅ T014.10: 异步解析集成测试 - PASSED
✅ T014.11: 数据库存储集成测试 - PASSED
✅ T014.12: 内存管理集成测试 - PASSED

测试总结: 12/12 PASSED, 性能符合要求
```

## 注意事项

1. **Excel格式要求**: 必须符合杭州厂标准格式
2. **字段映射**: 月度字段使用`monthly_`前缀避免冲突
3. **机台代码**: 喂丝机F前缀，卷包机M前缀
4. **批次ID**: 格式`MONTHLY_YYYYMMDD_HHMMSS_XXXX`
5. **并发安全**: 测试验证线程安全和批次ID唯一性

---

*T014测试为杭州卷烟厂月度Excel解析提供全面质量保障，确保解析器在生产环境中的可靠性和性能。*