# APS Tobacco v3 快速入门指南

**功能特性**: 月计划Excel直接排产功能  
**版本**: 3.0.0  
**创建时间**: 2025-01-16  
**基于**: 浙江中烟2019年7月份生产计划安排表数据格式

## 🚀 快速开始

### 系统架构概览
- **前端**: Vue.js 3 + Element Plus (localhost:5173)
- **后端**: FastAPI + SQLAlchemy (localhost:8000)
- **数据库**: MySQL 8.0+ + Redis 7.0+
- **核心功能**: Excel解析 → 智能排产 → 甘特图展示 → 工单生成

### 环境要求
- Node.js 20.19.0+
- Python 3.11+
- MySQL 8.0+
- Redis 7.0+

---

## 📋 用户场景指南

### 场景1: 月计划Excel上传与解析

**用户故事**: 生产计划员需要上传月度生产计划Excel文件，系统自动解析杭州卷烟厂数据并验证。

#### API调用流程
```bash
# 1. 上传Excel文件
curl -X POST "http://localhost:8000/api/v1/plans/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/浙江中烟2019年7月份生产计划安排表.xlsx" \
  -F "allow_overwrite=true"

# 响应示例
{
  "code": 200,
  "message": "文件上传成功",
  "timestamp": "2024-10-16T15:30:00Z",
  "status": "success",
  "data": {
    "import_batch_id": "IMPORT_20241016_153000_a1b2c3d4",
    "file_name": "浙江中烟2019年7月份生产计划安排表.xlsx",
    "file_size": 2048576,
    "upload_time": "2024-10-16T15:30:00Z"
  }
}
```

```bash
# 2. 触发Excel文件解析
curl -X POST "http://localhost:8000/api/v1/plans/IMPORT_20241016_153000_a1b2c3d4/parse"

# 响应示例
{
  "code": 200,
  "message": "文件解析成功",
  "data": {
    "import_batch_id": "IMPORT_20241016_153000_a1b2c3d4",
    "total_records": 120,
    "valid_records": 115,
    "error_records": 5,
    "records": [
      {
        "row_number": 5,
        "article_name": "利群（休闲）",
        "article_nr": "PA001",
        "material_input": 1000,
        "final_quantity": 980,
        "validation_status": "VALID"
      }
    ]
  }
}
```

**验收检查点**:
- ✅ 文件上传成功，获得唯一`import_batch_id`
- ✅ 解析仅提取杭州厂相关产品数据
- ✅ 过滤掉原计划为空或0的条目
- ✅ 支持合并单元格的复杂Excel格式

### 场景2: 智能排产算法执行

**用户故事**: 基于解析的杭州厂生产需求，执行智能排产算法，自动分配机台和时间段。

#### API调用流程
```bash
# 1. 查询可排产的批次
curl "http://localhost:8000/api/v1/plans/available-for-scheduling"

# 响应示例
{
  "code": 200,
  "data": {
    "available_batches": [
      {
        "batch_id": "IMPORT_20241016_153000_a1b2c3d4",
        "file_name": "浙江中烟2019年7月份生产计划安排表.xlsx",
        "total_records": 120,
        "valid_records": 115,
        "can_schedule": true
      }
    ]
  }
}
```

```bash
# 2. 执行排产算法
curl -X POST "http://localhost:8000/api/v1/scheduling/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "import_batch_id": "IMPORT_20241016_153000_a1b2c3d4",
    "algorithm_config": {
      "merge_enabled": true,
      "split_enabled": true,
      "correction_enabled": true,
      "parallel_enabled": true,
      "efficiency_rate": 0.85,
      "maintenance_buffer_minutes": 30
    }
  }'

# 响应示例
{
  "code": 200,
  "message": "排产任务创建成功",
  "data": {
    "task_id": "SCHEDULE_20241016_160000_x9y8z7w6",
    "import_batch_id": "IMPORT_20241016_153000_a1b2c3d4",
    "status": "PENDING",
    "message": "任务已创建，正在后台执行排产算法"
  }
}
```

```bash
# 3. 监控排产任务状态
curl "http://localhost:8000/api/v1/scheduling/tasks/SCHEDULE_20241016_160000_x9y8z7w6/status"

# 响应示例
{
  "code": 200,
  "data": {
    "task_id": "SCHEDULE_20241016_160000_x9y8z7w6",
    "status": "COMPLETED",
    "current_stage": "工单生成完成",
    "progress": 100,
    "total_records": 115,
    "processed_records": 115,
    "execution_duration": 45.2,
    "result_summary": {
      "work_orders_generated": 25,
      "machines_allocated": 8,
      "time_span_days": 15
    }
  }
}
```

**算法验证场景**:
- **场景A**: 利群(休闲)1000箱 → 找到J01机台(100箱/小时) → 分配10小时 → 安排7月1日08:00-18:00
- **场景B**: J01已排满 → 自动选择J02机台(90箱/小时) → 重新计算12小时
- **场景C**: 5000箱需求 → 单台月产能4000箱 → 拆分为两台各2500箱

### 场景3: 甘特图可视化展示

**用户故事**: 查看排产方案的甘特图展示，了解机台利用率和时间分配。

#### API调用流程
```bash
# 1. 获取工单排程数据（甘特图专用）
curl "http://localhost:8000/api/v1/work-orders/schedule?task_id=SCHEDULE_20241016_160000_x9y8z7w6"

# 响应示例
{
  "code": 200,
  "data": {
    "schedules": [
      {
        "work_order_nr": "W0001",
        "article_nr": "PA001",
        "final_quantity": 1000,
        "maker_code": "C1",
        "feeder_code": "15",
        "planned_start": "2024-07-01T08:00:00Z",
        "planned_end": "2024-07-01T18:00:00Z",
        "schedule_status": "PLANNED",
        "sync_group_id": "SYNC_001"
      },
      {
        "work_order_nr": "W0002",
        "article_nr": "PA001",
        "final_quantity": 1000,
        "maker_code": "C1",
        "feeder_code": "16",
        "planned_start": "2024-07-01T08:00:00Z",
        "planned_end": "2024-07-01T18:00:00Z",
        "schedule_status": "PLANNED",
        "sync_group_id": "SYNC_001"
      }
    ],
    "total_count": 25,
    "page": 1,
    "page_size": 100
  }
}
```

**甘特图展示特性**:
- 时间轴：planned_start ~ planned_end
- 机台分组：按maker_code + feeder_code
- 同步标识：sync_group_id标识协调工单
- 状态颜色：PLANNED/RUNNING/COMPLETED状态可视化

### 场景4: 工单生成与管理

**用户故事**: 生成详细工单，包含机台代码、产品规格、数量、时间段等信息。

#### API调用流程
```bash
# 1. 查询生成的工单列表
curl "http://localhost:8000/api/v1/scheduling/work-orders?task_id=SCHEDULE_20241016_160000_x9y8z7w6"

# 响应示例
{
  "code": 200,
  "message": "查询到 25 条工单数据（排程数据源）",
  "data": {
    "work_orders": [
      {
        "work_order_nr": "W0001",
        "work_order_type": "HJB",
        "machine_type": "合并计划",
        "machine_code": "C1+15",
        "maker_code": "C1",
        "feeder_code": "15",
        "product_code": "PA001",
        "plan_quantity": 1000,
        "work_order_status": "PLANNED",
        "planned_start_time": "2024-07-01T08:00:00Z",
        "planned_end_time": "2024-07-01T18:00:00Z",
        "task_id": "SCHEDULE_20241016_160000_x9y8z7w6"
      }
    ],
    "total_count": 25,
    "data_source": "work_order_schedule"
  }
}
```

```bash
# 2. 查询单个工单详情
curl "http://localhost:8000/api/v1/work-orders/W0001"

# 响应示例
{
  "code": 200,
  "data": {
    "work_order_nr": "W0001",
    "work_order_type": "HJB",
    "machine_code": "C1+15",
    "product_code": "PA001",
    "plan_quantity": 1000,
    "work_order_status": "PLANNED",
    "planned_start_time": "2024-07-01T08:00:00Z",
    "planned_end_time": "2024-07-01T18:00:00Z",
    "safety_stock": 50,
    "sync_group_id": "SYNC_001"
  }
}
```

**工单特性**:
- **工单类型**: HJB(卷包机)、HWS(喂丝机)
- **机台关联**: maker_code + feeder_code组合
- **同步协调**: sync_group_id确保卷包机与喂丝机协调
- **状态管理**: PLANNED → RUNNING → COMPLETED

## 🧪 端到端集成测试

### 测试场景1: 完整业务流程
```bash
#!/bin/bash
# 完整业务流程测试脚本

set -e
BASE_URL="http://localhost:8000/api/v1"

echo "=== 步骤1: 上传Excel文件 ==="
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/plans/upload" \
  -F "file=@aps_v2/浙江中烟2019年7月份生产计划安排表（6.20）.xlsx")

BATCH_ID=$(echo $UPLOAD_RESPONSE | jq -r '.data.import_batch_id')
echo "导入批次ID: $BATCH_ID"

echo "=== 步骤2: 解析Excel文件 ==="
curl -s -X POST "$BASE_URL/plans/$BATCH_ID/parse" | jq '.'

echo "=== 步骤3: 等待解析完成 ==="
while true; do
  STATUS_RESPONSE=$(curl -s "$BASE_URL/plans/$BATCH_ID/status")
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.data.import_status')
  echo "解析状态: $STATUS"
  
  if [ "$STATUS" = "COMPLETED" ]; then
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "解析失败!"
    exit 1
  fi
  
  sleep 2
done

echo "=== 步骤4: 执行排产算法 ==="
SCHEDULE_RESPONSE=$(curl -s -X POST "$BASE_URL/scheduling/execute" \
  -H "Content-Type: application/json" \
  -d "{\"import_batch_id\":\"$BATCH_ID\",\"algorithm_config\":{\"merge_enabled\":true,\"split_enabled\":true}}")

TASK_ID=$(echo $SCHEDULE_RESPONSE | jq -r '.data.task_id')
echo "排产任务ID: $TASK_ID"

echo "=== 步骤5: 等待排产完成 ==="
while true; do
  TASK_STATUS_RESPONSE=$(curl -s "$BASE_URL/scheduling/tasks/$TASK_ID/status")
  TASK_STATUS=$(echo $TASK_STATUS_RESPONSE | jq -r '.data.status')
  PROGRESS=$(echo $TASK_STATUS_RESPONSE | jq -r '.data.progress')
  echo "排产状态: $TASK_STATUS ($PROGRESS%)"
  
  if [ "$TASK_STATUS" = "COMPLETED" ]; then
    break
  elif [ "$TASK_STATUS" = "FAILED" ]; then
    echo "排产失败!"
    exit 1
  fi
  
  sleep 5
done

echo "=== 步骤6: 验证工单生成 ==="
WORK_ORDERS_RESPONSE=$(curl -s "$BASE_URL/scheduling/work-orders?task_id=$TASK_ID")
WORK_ORDERS_COUNT=$(echo $WORK_ORDERS_RESPONSE | jq '.data.total_count')
echo "生成工单数量: $WORK_ORDERS_COUNT"

echo "=== 步骤7: 获取甘特图数据 ==="
curl -s "$BASE_URL/work-orders/schedule?task_id=$TASK_ID" | jq '.data.schedules[0:3]'

echo "=== 测试完成 ==="
echo "✅ Excel上传与解析: 成功"
echo "✅ 智能排产算法: 成功"
echo "✅ 工单生成: $WORK_ORDERS_COUNT 条"
echo "✅ 甘特图数据: 可用"
```

### 测试场景2: 性能基准测试
```bash
#!/bin/bash
# 性能基准测试

echo "=== 性能基准测试 ==="

# 文件上传性能
echo "1. 文件上传性能测试"
time curl -X POST "http://localhost:8000/api/v1/plans/upload" \
  -F "file=@aps_v2/浙江中烟2019年7月份生产计划安排表（6.20）.xlsx"

# Excel解析性能
echo "2. Excel解析性能测试 (目标: <30秒)"
start_time=$(date +%s)
# ... 执行解析逻辑 ...
end_time=$(date +%s)
parse_duration=$((end_time - start_time))
echo "解析耗时: ${parse_duration}秒"

if [ $parse_duration -lt 30 ]; then
  echo "✅ 解析性能达标"
else
  echo "❌ 解析性能未达标 (超过30秒)"
fi

# 排产算法性能
echo "3. 排产算法性能测试 (目标: <2分钟)"
start_time=$(date +%s)
# ... 执行排产逻辑 ...
end_time=$(date +%s)
schedule_duration=$((end_time - start_time))
echo "排产耗时: ${schedule_duration}秒"

if [ $schedule_duration -lt 120 ]; then
  echo "✅ 排产性能达标"
else
  echo "❌ 排产性能未达标 (超过2分钟)"
fi
```

## 🔍 故障排除指南

### 常见问题与解决方案

#### 问题1: Excel文件解析失败
```bash
# 检查文件格式
curl "http://localhost:8000/api/v1/plans/BATCH_ID/status"

# 常见原因
# - 文件格式不是.xlsx/.xls
# - 杭州厂数据列缺失
# - 合并单元格格式异常

# 解决方案
# 1. 验证Excel文件是否包含杭州厂数据列
# 2. 检查是否有原计划数量为空的行
# 3. 使用force_reparse重新解析
curl -X POST "http://localhost:8000/api/v1/plans/BATCH_ID/parse?force_reparse=true"
```

#### 问题2: 排产算法执行失败
```bash
# 查看详细错误日志
curl "http://localhost:8000/api/v1/scheduling/tasks/TASK_ID"

# 常见原因
# - 机台速度配置缺失
# - 工作日历数据不完整
# - 产能超出可用机台限制

# 解决方案
# 1. 检查机台速度配置
curl "http://localhost:8000/api/v1/machines/machine-speeds"

# 2. 验证工作日历
curl "http://localhost:8000/api/v1/data/statistics"

# 3. 重试失败的任务
curl -X POST "http://localhost:8000/api/v1/scheduling/tasks/TASK_ID/retry"
```

#### 问题3: 甘特图数据为空
```bash
# 检查工单生成状态
curl "http://localhost:8000/api/v1/scheduling/work-orders?task_id=TASK_ID"

# 常见原因
# - 排产任务未完成
# - 工单数据源配置错误
# - 时间范围过滤条件错误

# 解决方案
# 1. 确认排产任务已完成
curl "http://localhost:8000/api/v1/scheduling/tasks/TASK_ID/status"

# 2. 检查数据源优先级 (work_order_schedule > mes_work_orders)
# 3. 调整查询参数
curl "http://localhost:8000/api/v1/work-orders/schedule?task_id=TASK_ID&page_size=100"
```

### 系统健康检查
```bash
# 检查系统各组件状态
curl "http://localhost:8000/api/v1/health"

# 预期响应
{
  "status": "healthy",
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 15.5},
    "redis": {"status": "healthy", "response_time_ms": 2.1},
    "filesystem": {"status": "healthy", "disk_usage_percent": 45.2}
  }
}

# 获取系统配置信息
curl "http://localhost:8000/api/v1/config"
```

## 📊 性能基准

### 处理能力基准
- **Excel文件大小**: 最大50MB
- **记录处理能力**: 单次处理500+条记录
- **解析时间**: <30秒 (标准2MB文件)
- **排产算法执行**: <2分钟 (100条记录)
- **甘特图渲染**: <5秒 (25个工单)

### 并发基准
- **文件上传**: 支持5个并发上传
- **排产任务**: 支持3个并发排产任务
- **API查询**: 支持50个并发查询请求

### 数据规模基准
- **月计划记录**: 500条记录/文件
- **工单生成**: 50个工单/排产任务
- **机台支持**: 20台机台同时调度
- **时间跨度**: 支持31天排产周期

## 🎯 验证清单

### Excel处理验证
- [ ] 文件上传成功，获得import_batch_id
- [ ] Excel解析仅提取杭州厂数据
- [ ] 过滤原计划为空/0的记录
- [ ] 处理合并单元格格式
- [ ] 验证数据完整性(品牌规格+数量)

### 排产算法验证
- [ ] 机台选择基于aps_machine_speed表
- [ ] 时间计算考虑效率系数
- [ ] 工作日历约束生效
- [ ] 维修计划避让正确
- [ ] 产能超出时正确拆分
- [ ] 负载均衡算法工作

### 甘特图验证
- [ ] 时间轴显示正确
- [ ] 机台分组清晰
- [ ] 同步组标识准确
- [ ] 状态颜色区分
- [ ] 交互操作响应

### 工单生成验证
- [ ] HJB/HWS工单类型正确
- [ ] 机台代码匹配
- [ ] 数量计算准确
- [ ] 时间段无重叠
- [ ] MES集成格式兼容

## 📚 相关文档

- [API规范文档](contracts/api-spec.yaml)
- [功能规格说明](spec.md)
- [数据模型设计](data-model.md)
- [技术设计方案](../docs/technical-design.md)
- [测试用例集](../backend/tests/)

## 🤝 支持

如遇到问题，请参考：
1. 本文档的故障排除指南
2. 系统健康检查接口
3. API错误响应信息
4. 后端日志文件(`/app/logs/`)

---

**最后更新**: 2025-01-16  
**版本**: 1.0.0  
**维护者**: APS开发团队