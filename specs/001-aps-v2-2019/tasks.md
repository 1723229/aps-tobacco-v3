# Tasks: 月计划Excel直接排产功能（冲突避免版本）

**Input**: 冲突避免设计文档来自 `/Users/spuerman/work/self_code/aps-tobacco-v3/specs/001-aps-v2-2019/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/api-spec.yaml
**重要**: 本版本任务列表基于冲突避免设计，确保与现有旬计划系统零冲突

## 🔥 冲突避免设计要点

**核心原则**: 月计划功能与现有旬计划系统**完全独立**，零干扰现有业务

### 关键隔离措施
1. **API路由隔离**: 使用`/monthly-*`前缀，避免与现有`/plans`路由冲突
2. **数据表隔离**: 所有新表使用`aps_monthly_*`前缀
3. **字段命名隔离**: 关键字段使用`monthly_`前缀
4. **枚举值隔离**: 所有枚举值使用`MONTHLY_`前缀
5. **批次ID隔离**: 使用`MONTHLY_`前缀，区别于现有`IMPORT_`前缀
6. **工单号隔离**: 使用`MW_`前缀，区别于现有`WO_`前缀

## 执行流程 (main)
```
1. 从功能目录加载 plan.md ✅
   → 技术栈：Python 3.11 (后端), Vue.js 3.5.18 + TypeScript (前端)
   → 库：FastAPI 0.104.1, SQLAlchemy 2.0.23, openpyxl 3.1.2, Element Plus 2.8.8
   → 结构：Web应用程序（backend/frontend 目录）
2. 加载冲突避免设计文档 ✅:
   → data-model-revised.md: 3个独立实体 (MonthlyPlan, MonthlyWorkCalendar, MonthlyScheduleResult)
   → contracts/api-spec-revised.yaml: 独立的API路由前缀设计
   → research.md: 算法架构，包含9个月度特化模块
3. 按类别生成冲突避免任务 ✅:
   → 设置：数据库迁移，月度算法模块结构
   → 测试：独立的月度API端点合约测试，集成测试
   → 核心：3个月度模型，9个月度算法模块，独立的API端点组
   → 集成：前端组件，月度Excel解析器
   → 完善：性能测试，文档
4. 应用任务规则 ✅:
   → 不同文件 = 标记 [P] 用于并行执行
   → 同文件 = 顺序（无 [P]）
   → 测试优先于实现（TDD严格顺序）
5. 任务编号 T001-T055 ✅
6. 依赖关系验证 ✅
7. 并行执行示例提供 ✅
```

## 格式: `[ID] [P?] 描述`
- **[P]**: 可并行运行（不同文件，无依赖关系）
- 描述中包含确切的文件路径
- 所有新文件使用月度特化命名，避免与现有文件冲突

## 路径约定
- **后端**: `backend/app/` 用于源代码
- **前端**: `frontend/src/` 用于Vue组件
- **测试**: `backend/tests/` 用于Python测试
- **月度特化**: 所有新组件使用`Monthly`或`monthly`前缀

## 阶段3.1: 设置和数据库基础（冲突避免）

- [ ] **T001** 创建月度计划表的独立数据库模式在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/monthly_plan_schema.sql`
- [ ] **T002** 创建月度特化数据库索引优化脚本在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/monthly_plan_indexes.sql`  
- [ ] **T003** 创建月度工作日历数据SQL脚本在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/init_monthly_work_calendar.sql`
- [ ] **T004** 初始化月度工作日历数据（2024-2026中国节假日）在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/init_monthly_calendar.py`
- [ ] **T005** 创建月度排产算法模块结构在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/`
- [ ] **T006** [P] 创建月度系统配置表在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/monthly_system_config.sql`

## 阶段3.2: 测试优先（TDD）⚠️ 必须在3.3前完成
**关键：这些测试必须写出并且必须失败，然后才能实现任何功能**

### 月度合约测试（API端点）- 使用独立路由
- [ ] **T007** [P] 合约测试 POST /api/v1/monthly-plans/upload 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_plans_upload_contract.py`
- [ ] **T008** [P] 合约测试 POST /api/v1/monthly-plans/{import_batch_id}/parse 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_plans_parse_contract.py`
- [ ] **T009** [P] 合约测试 POST /api/v1/monthly-scheduling/execute 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_scheduling_execute_contract.py`
- [ ] **T010** [P] 合约测试 GET /api/v1/monthly-scheduling/tasks 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_scheduling_tasks_contract.py`
- [ ] **T011** [P] 合约测试 GET /api/v1/monthly-work-orders/schedule 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_work_orders_schedule_contract.py`
- [ ] **T012** [P] 合约测试 GET /api/v1/work-calendar 在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_work_calendar_contract.py`

### 月度集成测试
- [ ] **T013** [P] 集成测试完整月计划工作流（上传→解析→排产→结果）在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/integration/test_monthly_plan_workflow.py`
- [ ] **T014** [P] 集成测试Excel解析杭州厂月度格式在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/integration/test_excel_parser_monthly.py`
- [ ] **T015** [P] 集成测试月度算法管道执行在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/integration/test_monthly_algorithm_pipeline.py`
- [ ] **T016** [P] 集成测试月度排产中的工作日历约束在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/integration/test_monthly_calendar_constraints.py`

## 阶段3.3: 核心实现（仅在测试失败后）- 月度特化

### 月度数据库模型（独立命名）
- [ ] **T017** [P] MonthlyWorkCalendar模型在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/models/monthly_work_calendar_models.py`
- [ ] **T018** [P] MonthlyPlan模型在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/models/monthly_plan_models.py`
- [ ] **T019** [P] MonthlyScheduleResult模型在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/models/monthly_schedule_result_models.py`
- [ ] **T020** [P] MonthlyImportPlan模型在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/models/monthly_import_plan_models.py`

### 月度算法核心模块（独立实现）
- [ ] **T021** [P] 月度日历服务模块在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_calendar_service.py`
- [ ] **T022** [P] 月度机台选择算法在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_machine_selector.py`
- [ ] **T023** [P] 月度容量计算模块在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_capacity_calculator.py`
- [ ] **T024** [P] 月度时间分配算法在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_time_allocator.py`
- [ ] **T025** [P] 月度约束求解模块在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_constraint_solver.py`
- [ ] **T026** [P] 月度负载均衡算法在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_load_balancer.py`
- [ ] **T027** 月度引擎编排在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/monthly_engine.py`（依赖T021-T026）

### 月度Excel解析器（独立于现有解析器）
- [ ] **T028** 创建月度计划Excel解析器在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/services/monthly_plan_parser.py`
- [ ] **T029** 月度Excel格式检测器在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/services/monthly_excel_detector.py`

### 月度API端点（独立路由）
- [ ] **T030** [P] 月度计划上传端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_plans.py`
- [ ] **T031** 月度计划解析端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_plans.py`（扩展T030文件）
- [ ] **T032** [P] 月度排产执行端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_scheduling.py`
- [ ] **T033** 月度排产任务查询端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_scheduling.py`（扩展T032文件）
- [ ] **T034** [P] 月度工单排程端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_work_orders.py`
- [ ] **T035** [P] 月度数据查询端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/monthly_data.py`
- [ ] **T036** [P] 工作日历管理端点在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/work_calendar.py`

### 月度Pydantic模式（独立命名）
- [ ] **T037** [P] 月度计划模式在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/schemas/monthly_schemas.py`
- [ ] **T038** [P] 月度工作日历模式在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/schemas/monthly_calendar_schemas.py`
- [ ] **T039** [P] 月度排产模式在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/schemas/monthly_scheduling_schemas.py`

## 阶段3.4: 前端集成（月度特化组件）

### Vue组件（月度特化）
- [ ] **T040** [P] MonthlyPlanUpload.vue组件在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/MonthlyPlanUpload.vue`
- [ ] **T041** [P] MonthlyPlanTable.vue组件在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/MonthlyPlanTable.vue`
- [ ] **T042** [P] MonthlyGanttChart.vue组件（Vue Ganttastic）在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/MonthlyGanttChart.vue`
- [ ] **T043** [P] MonthlyPlanEntry.vue页面在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/views/MonthlyPlanEntry.vue`
- [ ] **T044** [P] MonthlyScheduling.vue页面在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/views/MonthlyScheduling.vue`
- [ ] **T045** [P] MonthlyWorkOrderView.vue页面在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/views/MonthlyWorkOrderView.vue`

### 前端服务（月度特化）
- [ ] **T046** [P] 月度计划API客户端在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/services/monthly-api.ts`
- [ ] **T047** [P] 月度计划Pinia存储在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/stores/monthly-plan.ts`

### TypeScript类型（月度特化）
- [ ] **T048** [P] 月度计划TypeScript定义在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/types/monthly-types.ts`

## 阶段3.5: 系统集成（独立路由集成）

### 路由集成（避免冲突）
- [ ] **T049** 将月度计划路由集成到主路由器在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/api/v1/router.py`
- [ ] **T050** 添加月度计划导航到前端路由器在 `/Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/router/index.ts`

### 性能与文档
- [ ] **T051** [P] 月度算法执行性能测试（<5分钟目标）在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/performance/test_monthly_algorithm_performance.py`
- [ ] **T052** [P] 使用quickstart工作流场景的端到端测试在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/e2e/test_monthly_plan_e2e.py`

### 部署和配置（独立配置）
- [ ] **T053** [P] 月度计划功能环境变量配置在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/core/config.py`
- [ ] **T054** [P] 更新API文档和swagger配置在 `/Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/main.py`

### 数据库管理（独立维护）
- [ ] **T055** [P] 月度计划数据清理和维护脚本在 `/Users/spuerman/work/self_code/aps-tobacco-v3/scripts/monthly_plan_maintenance.py`

## 依赖关系（冲突避免版本）

### 关键依赖关系
- **月度数据库基础**: T001-T006必须在模型任务T017-T020前完成
- **月度算法依赖**: T021-T026必须在T027（月度引擎）前完成
- **TDD顺序**: 所有测试任务（T007-T016）必须完成并失败，然后才能进行实现（T017-T055）
- **月度API依赖**: T030基础文件在T031扩展前
- **前端依赖**: T046-T048在T043-T045页面组件前

### 顺序执行链
```
月度数据库: T001→T002→T003→T004→T005→T006→T017,T018,T019,T020
月度算法: T021-T026 [并行] → T027
月度API: T030 → T031; T032 → T033（同文件）
前端: T046,T047,T048 [并行] → T043,T044,T045 [并行]
```

## 并行执行示例（冲突避免版本）

### 阶段3.2 月度合约测试（同时启动）
```bash
Task(subagent_type="task-executor", description="月度上传端点合约测试", 
     prompt="根据API规格在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_plans_upload_contract.py 写失败的POST /api/v1/monthly-plans/upload合约测试")

Task(subagent_type="task-executor", description="月度解析端点合约测试",
     prompt="根据API规格在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_plans_parse_contract.py 写失败的POST /api/v1/monthly-plans/{import_batch_id}/parse合约测试")

Task(subagent_type="task-executor", description="月度排产端点合约测试",
     prompt="根据API规格在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/tests/test_monthly_scheduling_execute_contract.py 写失败的POST /api/v1/monthly-scheduling/execute合约测试")
```

### 阶段3.3 月度算法模块（同时启动）
```bash
Task(subagent_type="task-executor", description="月度日历服务实现",
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/ 实现monthly_calendar_service.py，支持月度工作日历集成和CLI")

Task(subagent_type="task-executor", description="月度机台选择器实现",
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/ 实现monthly_machine_selector.py，基于月度容量选择和CLI支持")

Task(subagent_type="task-executor", description="月度容量计算器实现", 
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/backend/app/algorithms/monthly_scheduling/ 实现monthly_capacity_calculator.py，月度容量算法和CLI支持")
```

### 阶段3.4 月度前端组件（同时启动）
```bash
Task(subagent_type="task-executor", description="月度上传组件实现",
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/ 实现MonthlyPlanUpload.vue，专门处理月度Excel上传和Element Plus集成")

Task(subagent_type="task-executor", description="月度表格组件实现", 
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/ 实现MonthlyPlanTable.vue，月度数据展示和Element Plus表格")

Task(subagent_type="task-executor", description="月度甘特图组件实现",
     prompt="在 /Users/spuerman/work/self_code/aps-tobacco-v3/frontend/src/components/ 实现MonthlyGanttChart.vue，Vue Ganttastic集成月度时间线")
```

## 冲突避免检查清单 ✅

### API路由隔离检查
- [x] 所有月度API使用`/monthly-*`前缀，与现有`/plans`完全隔离
- [x] 月度排产使用`/monthly-scheduling`，避免与现有`/scheduling`冲突  
- [x] 月度工单使用`/monthly-work-orders`，独立于现有工单接口

### 数据模型隔离检查
- [x] 所有新表使用`aps_monthly_*`前缀
- [x] 关键字段使用`monthly_`前缀避免混淆
- [x] 枚举值使用`MONTHLY_`前缀完全隔离
- [x] 外键仅引用基础表，不引用decade plan表

### 代码组件隔离检查
- [x] 前端组件使用`Monthly`前缀命名
- [x] 算法模块使用`monthly_`前缀命名
- [x] API模块使用独立的文件名
- [x] 测试文件使用`monthly`前缀避免混淆

### 业务逻辑隔离检查
- [x] 批次ID使用`MONTHLY_`前缀
- [x] 工单号使用`MW_`前缀
- [x] 状态转换系统完全独立
- [x] 配置系统使用独立表和前缀

## 备注
- **冲突零容忍**: 所有新组件必须确保与现有系统零冲突
- **[P] 任务** = 不同文件，无依赖关系，安全并行执行
- **TDD强制执行**: 所有合约和集成测试（T007-T016）必须写出并失败，然后才能进行实现任务
- **文件路径要求**: 每个任务指定确切的绝对文件路径用于实现
- **月度算法CLI**: 每个算法模块必须支持--help, --version, --json, --format标志，符合宪法要求
- **性能目标**: Excel解析<30秒，算法执行<5分钟，API响应<200ms
- **Vue Ganttastic**: 在MonthlyGanttChart组件中使用Vue Ganttastic 2.3.2进行专业甘特图实现
- **独立部署**: 月度功能可以独立部署和维护，不影响现有旬计划系统

## 任务生成规则应用（冲突避免版本）

1. **来自冲突避免合约（api-spec-revised.yaml）**:
   - 5个资源组 → 6个合约测试任务（T007-T012）[P]
   - 按资源组 → 7个实现任务（T030-T036，其中T030-T031、T032-T033共享文件）
   
2. **来自冲突避免数据模型**:
   - 4个独立实体 → 4个模型创建任务（T017-T020）[P]
   - 关系 → 服务层和算法任务
   
3. **来自研究决策**:
   - 7个月度算法模块 → 7个实现任务（T021-T027）
   - 前端架构 → 6个组件任务（T040-T045）

4. **应用的排序**:
   - 设置（T001-T006）→ 测试（T007-T016）→ 模型（T017-T020）→ 服务/算法（T021-T039）→ 前端（T040-T048）→ 集成（T049-T050）→ 完善（T051-T055）

## 验证检查清单 ✅

- [x] 所有6个合约组有对应的测试（T007-T012）
- [x] 所有4个实体有模型任务（T017-T020）
- [x] 所有测试（T007-T016）在实现（T017+）前
- [x] 并行任务[P]真正独立（不同文件）
- [x] 每个任务指定确切文件路径
- [x] 没有[P]任务修改与另一个[P]任务相同的文件
- [x] 强制执行TDD顺序（测试必须在实现前失败）
- [x] 算法模块遵循库优先架构和CLI支持
- [x] 前端使用既定的Vue.js 3.5.18 + Element Plus模式
- [x] 与现有代码库完全隔离（独立router.py集成）
- [x] 所有命名使用月度特化前缀避免冲突