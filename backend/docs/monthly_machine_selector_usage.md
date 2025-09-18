# 月度机台选择算法模块 T022 - 使用示例

## 模块概述

`MonthlyMachineSelector` 是一个基于月度容量的智能机台选择算法模块，专门设计用于杭州卷烟厂的生产排产系统。该模块支持卷包机和喂丝机的联合选择优化，考虑机台维护计划、产能限制、产品适配性等多种约束条件。

## 主要特性

- ✅ **多策略选择算法**: 支持产能最优、效率最优、平衡最优、维护感知等策略
- ✅ **智能产能计算**: 基于工作日历和维护计划的动态产能评估
- ✅ **机台关系优化**: 智能匹配卷包机和喂丝机的最优组合
- ✅ **约束条件处理**: 支持效率要求、换产时间、机台偏好等约束
- ✅ **风险评估**: 提供容量风险、维护风险等多维度评估
- ✅ **CLI支持**: 完整的命令行接口，支持多种输出格式
- ✅ **异步高性能**: 基于异步数据库查询，支持高并发处理

## 快速开始

### 1. 基础用法

```python
import asyncio
from datetime import datetime
from decimal import Decimal
from app.algorithms.monthly_scheduling.monthly_machine_selector import (
    MonthlyMachineSelector,
    MachineSelectionCriteria,
    MachineSelectionStrategy,
    SelectionObjective,
    MachineType,
    Priority,
    create_machine_selector
)

async def basic_machine_selection():
    """基础机台选择示例"""
    
    # 创建机台选择器
    selector = await create_machine_selector()
    
    # 定义选择标准
    criteria = MachineSelectionCriteria(
        article_nr="123456",                              # 物料编号
        target_quantity=Decimal("1000"),                 # 目标产量（万支）
        planned_start=datetime(2025, 2, 1),             # 计划开始时间
        planned_end=datetime(2025, 2, 28),              # 计划结束时间
        priority=Priority.HIGH,                          # 任务优先级
        required_machine_types=[MachineType.FEEDER, MachineType.MAKER],  # 需要的机台类型
        preferred_machines=["M001", "F002"],             # 偏好机台
        excluded_machines=["M999"],                      # 排除机台
        max_setup_time=Decimal("2.0"),                  # 最大换产时间（小时）
        min_efficiency=Decimal("0.8"),                  # 最小效率要求
        selection_strategy=MachineSelectionStrategy.BALANCE_OPTIMAL,    # 选择策略
        objective=SelectionObjective.MAXIMIZE_THROUGHPUT # 优化目标
    )
    
    # 执行机台选择
    result = await selector.select_optimal_machines(criteria)
    
    print(f"选择结果:")
    print(f"主选机台: 喂丝机={result.selected_feeder}, 卷包机={result.selected_maker}")
    print(f"总产能: {result.total_capacity}")
    print(f"效率分数: {result.efficiency_score:.2%}")
    print(f"约束满足: {'是' if result.constraints_satisfied else '否'}")
    
    return result

# 运行示例
asyncio.run(basic_machine_selection())
```

### 2. 机台产能计算

```python
async def calculate_capacity_example():
    """机台产能计算示例"""
    
    selector = await create_machine_selector()
    
    # 计算指定机台的月度产能
    capacity_info = await selector.calculate_machine_capacity(
        machine_code="M001",     # 机台代码
        year=2025,               # 年份
        month=2,                 # 月份
        article_nr="123456"      # 可选：特定物料编号
    )
    
    print("机台产能分析:")
    print(f"机台代码: {capacity_info['machine_code']}")
    print(f"计算期间: {capacity_info['period']}")
    print(f"工作日数: {capacity_info['working_days']}")
    print(f"有效月产能: {capacity_info['effective_monthly_capacity']:.2f} 万支")
    print(f"可用产能: {capacity_info['available_capacity']:.2f} 万支")
    print(f"当前利用率: {capacity_info['current_utilization']:.2%}")
    print(f"维护影响: {capacity_info['maintenance_impact']:.2%}")

asyncio.run(calculate_capacity_example())
```

### 3. 查询可用机台

```python
async def query_available_machines():
    """查询可用机台示例"""
    
    selector = await create_machine_selector()
    
    # 查询所有可用的喂丝机
    feeder_machines = await selector.get_available_machines(
        machine_type=MachineType.FEEDER,
        article_nr="123456",  # 检查对特定物料的适配性
        time_range=(datetime(2025, 2, 1), datetime(2025, 2, 28))  # 时间范围
    )
    
    print(f"可用喂丝机数量: {len(feeder_machines)}")
    for machine in feeder_machines[:5]:  # 显示前5个
        print(f"  {machine['machine_code']} - {machine['machine_name']}")
        print(f"    产能: {machine['capability']['base_capacity']:.2f} 箱/h")
        print(f"    效率: {machine['capability']['efficiency_factor']:.2%}")
        print(f"    利用率: {machine['capability']['current_utilization']:.2%}")

asyncio.run(query_available_machines())
```

## 高级用法

### 1. 多策略对比选择

```python
async def strategy_comparison():
    """不同策略对比示例"""
    
    selector = await create_machine_selector()
    
    base_criteria = MachineSelectionCriteria(
        article_nr="123456",
        target_quantity=Decimal("1000"),
        planned_start=datetime(2025, 2, 1),
        priority=Priority.HIGH,
        required_machine_types=[MachineType.FEEDER, MachineType.MAKER],
        preferred_machines=[],
        excluded_machines=[],
        max_setup_time=None,
        min_efficiency=None,
        selection_strategy=MachineSelectionStrategy.CAPACITY_OPTIMAL,  # 将被覆盖
        objective=SelectionObjective.MAXIMIZE_THROUGHPUT
    )
    
    strategies = [
        MachineSelectionStrategy.CAPACITY_OPTIMAL,
        MachineSelectionStrategy.EFFICIENCY_OPTIMAL,
        MachineSelectionStrategy.BALANCE_OPTIMAL,
        MachineSelectionStrategy.MAINTENANCE_AWARE
    ]
    
    results = {}
    for strategy in strategies:
        criteria = base_criteria.copy()  # Create a copy to avoid mutation.copy()  # Create a copy to avoid mutation
        criteria.selection_strategy = strategytry:
            result = await selector.select_optimal_machines(criteria)
            results[strategy.value] = {
                "feeder": result.selected_feeder,
                "maker": result.selected_maker,
                "capacity": float(result.total_capacity),
                "efficiency": float(result.efficiency_score)
            }
        except Exception as e:
            print(f"策略 {strategy.value} 执行失败: {e}")
    
    print("策略对比结果:")
    for strategy, result in results.items():
        print(f"{strategy}:")
        print(f"  机台组合: {result['feeder']}/{result['maker']}")
        print(f"  总产能: {result['capacity']:.2f}")
        print(f"  效率分数: {result['efficiency']:.2%}")

asyncio.run(strategy_comparison())
```

### 2. 使用 AlgorithmBase 接口

```python
async def algorithm_base_usage():
    """使用AlgorithmBase接口示例"""
    
    selector = await create_machine_selector()
    
    # 构建算法输入数据
    input_data = [{
        "article_nr": "123456",
        "target_quantity": 1000,
        "priority": "HIGH",
        "required_machine_types": ["FEEDER", "MAKER"],
        "preferred_machines": ["M001", "F002"],
        "selection_strategy": "balance_optimal",
        "objective": "maximize_throughput"
    }]
    
    # 使用process方法执行算法
    algorithm_result = await selector.process(input_data)
    
    print(f"算法执行结果:")
    print(f"成功: {algorithm_result.success}")
    print(f"处理记录数: {algorithm_result.metrics.processed_records}")
    print(f"执行时间: {algorithm_result.metrics.execution_time:.2f}秒")
    
    if algorithm_result.success and algorithm_result.output_data:
        selection_data = algorithm_result.output_data[0]
        print(f"选择的机台: {selection_data['selected_machines']}")

asyncio.run(algorithm_base_usage())
```

## CLI 使用示例

### 1. 机台选择

```bash
# 基础机台选择
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --select 123456 1000 \
    --strategy balance_optimal \
    --objective maximize_throughput

# JSON格式输出
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --select 123456 1000 \
    --strategy capacity_optimal \
    --format json
```

### 2. 产能计算

```bash
# 计算机台月度产能
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --capacity M001 2025 2

# 计算特定物料的产能
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --capacity M001 2025 2 \
    --article 123456 \
    --json
```

### 3. 查询可用机台

```bash
# 查询所有可用喂丝机
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --available feeder

# 查询对特定物料兼容的机台
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --available all \
    --article 123456 \
    --format csv

# 列出所有机台信息
python -m app.algorithms.monthly_scheduling.monthly_machine_selector \
    --machines \
    --format json
```

## 配置选项

### 选择器配置

```python
from app.algorithms.monthly_scheduling.monthly_machine_selector import MonthlyMachineSelectorConfig

# 自定义配置
config = MonthlyMachineSelectorConfig(
    default_working_hours_per_day=Decimal("16"),      # 每日工作小时数
    overtime_factor=Decimal("1.2"),                   # 加班产能因子
    efficiency_threshold=Decimal("0.75"),             # 效率阈值
    utilization_threshold=Decimal("0.85"),            # 利用率阈值
    capacity_weight=Decimal("0.4"),                   # 产能权重
    efficiency_weight=Decimal("0.3"),                 # 效率权重
    availability_weight=Decimal("0.2"),               # 可用性权重
    relationship_weight=Decimal("0.1"),               # 关系权重
    max_selection_candidates=50,                      # 最大候选机台数
    backup_machines_count=2,                          # 备选机台数量
    setup_time_penalty=Decimal("0.1"),                # 换产时间惩罚
    maintenance_buffer_hours=4,                       # 维护缓冲时间（小时）
    risk_tolerance=Decimal("0.2"),                    # 风险容忍度
    contingency_capacity=Decimal("0.15")              # 应急容量
)

# 使用自定义配置创建选择器
selector = MonthlyMachineSelector(session, calendar_service, config)
```

## 错误处理

```python
async def error_handling_example():
    """错误处理示例"""
    
    selector = await create_machine_selector()
    
    try:
        criteria = MachineSelectionCriteria(
            article_nr="INVALID_ARTICLE",
            target_quantity=Decimal("0"),  # 无效数量
            priority=Priority.HIGH,
            required_machine_types=[],     # 空的机台类型
            preferred_machines=[],
            excluded_machines=[],
            max_setup_time=None,
            min_efficiency=None,
            selection_strategy=MachineSelectionStrategy.BALANCE_OPTIMAL,
            objective=SelectionObjective.MAXIMIZE_THROUGHPUT
        )
        
        result = await selector.select_optimal_machines(criteria)
        
    except ValueError as e:
        print(f"输入参数错误: {e}")
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
```

## 性能优化建议

1. **缓存利用**: 选择器会自动缓存机台能力信息，避免重复查询
2. **批量查询**: 对于多个选择任务，重用同一个选择器实例
3. **索引优化**: 确保数据库表有适当的索引（machine_code, article_nr等）
4. **连接池**: 使用数据库连接池以提高并发性能

```python
# 性能优化示例
async def optimized_batch_selection():
    """批量选择优化示例"""
    
    # 创建一个选择器实例，重复使用
    selector = await create_machine_selector()
    
    # 批量处理多个选择任务
    tasks = [
        {"article_nr": "123456", "quantity": 1000},
        {"article_nr": "789012", "quantity": 800},
        {"article_nr": "345678", "quantity": 1200}
    ]
    
    results = []
    for task in tasks:
        criteria = MachineSelectionCriteria(
            article_nr=task["article_nr"],
            target_quantity=Decimal(str(task["quantity"])),
            priority=Priority.MEDIUM,
            required_machine_types=[MachineType.FEEDER, MachineType.MAKER],
            preferred_machines=[],
            excluded_machines=[],
            max_setup_time=None,
            min_efficiency=None,
            selection_strategy=MachineSelectionStrategy.BALANCE_OPTIMAL,
            objective=SelectionObjective.MAXIMIZE_THROUGHPUT
        )
        
        try:
            result = await selector.select_optimal_machines(criteria)
            results.append(result)
        except Exception as e:
            print(f"处理任务 {task['article_nr']} 失败: {e}")
    
    return results
```

## 总结

月度机台选择算法模块 T022 提供了完整的智能机台选择解决方案，支持多种选择策略和优化目标，能够有效处理复杂的生产排产需求。通过灵活的配置选项和完善的错误处理机制，该模块能够适应不同的业务场景和性能要求。