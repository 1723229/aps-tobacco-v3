# Implementation Plan: 月计划Excel直接排产功能

**Branch**: `001-aps-v2-2019` | **Date**: 2025-01-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/spuerman/work/self_code/aps-tobacco-v3/specs/001-aps-v2-2019/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✅
   → 已加载月计划Excel直接排产功能规格
2. Fill Technical Context (scan for NEEDS CLARIFICATION) ✅
   → 基于现有APS Tobacco v3项目技术栈
   → 项目类型：Web应用程序（前端+后端）
3. Evaluate Constitution Check section below ✅
   → 冲突避免设计确保零干扰现有旬计划系统
   → 更新Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md ✅
   → 所有NEEDS CLARIFICATION已解决
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md ✅
6. Re-evaluate Constitution Check section ✅
   → 设计符合宪法要求，无新违规
   → 更新Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md) ✅
8. STOP - Ready for /tasks command ✅
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
基于现有APS智慧排产系统v3，新增月计划Excel直接排产功能。系统支持浙江中烟月度计划Excel格式(.xlsx)自动解析，提取杭州卷烟厂生产需求，通过9个专门算法自动分配机台和时间，生成详细工单和甘特图排程。**关键设计原则：与现有旬计划系统完全独立，零冲突保证**。

技术方案采用独立的数据表(`aps_monthly_*`)、API路由(`/monthly-*`)、前端组件和算法模块，确保新功能不影响现有业务。支持工作日历约束、机台产能优化、维修计划处理和MES系统集成。

## Technical Context
**Language/Version**: Python 3.11 (Backend), TypeScript 5.8 (Frontend)
**Primary Dependencies**: FastAPI 0.104.1, SQLAlchemy 2.0.23, Vue.js 3.5.18, Element Plus 2.8.8
**Storage**: MySQL 8.0+ (主数据), Redis 7.0+ (缓存), openpyxl 3.1.2 (Excel处理)
**Testing**: pytest 7.4.3 (后端), Vue Test Utils (前端待配置)
**Target Platform**: Linux server + 现代浏览器 (Chrome/Firefox/Safari)
**Project Type**: web - 确定源代码结构为backend/frontend分离
**Performance Goals**: Excel解析<30秒, API响应<200ms, 支持100+并发排产请求
**Constraints**: 与现有旬计划系统零冲突, 支持大型Excel文件(>10MB), 机台排程实时优化
**Scale/Scope**: 支持月度1000+产品规格, 100+机台, 10000+工单, 3年历史数据查询

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 3 (backend-api, frontend-ui, database-schema) - 符合最大3个项目限制
- Using framework directly? ✅ (FastAPI直接使用，Vue.js直接使用，无包装类)
- Single data model? ✅ (3个核心实体：MonthlyPlan, WorkCalendar, ScheduleResult，无冗余DTO)
- Avoiding patterns? ✅ (避免Repository/UoW模式，直接使用SQLAlchemy查询)

**Architecture**:
- EVERY feature as library? ✅ (月度排产算法作为独立库)
- Libraries listed: 
  * monthly-scheduling-engine (9个排产算法模块)
  * monthly-excel-parser (Excel解析和数据验证)
  * monthly-calendar-service (工作日历计算)
- CLI per library: 
  * `monthly-scheduler --help/--version/--format`
  * `excel-parser --help/--version/--format`
  * `calendar-service --help/--version/--format`
- Library docs: ✅ 计划生成llms.txt格式文档

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? ✅ (已创建11个合约测试，全部处于RED状态)
- Git commits show tests before implementation? ✅ (TDD严格执行)
- Order: Contract→Integration→E2E→Unit strictly followed? ✅ (T006-T013已完成合约和集成测试)
- Real dependencies used? ✅ (真实MySQL数据库，真实Redis缓存)
- Integration tests for: ✅ 新月度算法库、月度API合约、共享数据库模式
- FORBIDDEN: ✅ 严禁实现前测试，严禁跳过RED阶段

**Observability**:
- Structured logging included? ✅ (Python logging配置，JSON格式输出)
- Frontend logs → backend? ✅ (Vue前端日志通过API发送到后端统一流)
- Error context sufficient? ✅ (算法错误追踪，Excel解析错误详情，排产失败原因)

**Versioning**:
- Version number assigned? ✅ (v3.1.0 - 月计划功能为minor版本)
- BUILD increments on every change? ✅ (每次提交自动增加BUILD号)
- Breaking changes handled? ✅ (与现有API完全独立，无破坏性变更)

## Project Structure

### Documentation (this feature)
```
specs/001-aps-v2-2019/
├── plan.md              # This file (/plan command output) ✅
├── research.md          # Phase 0 output (/plan command) ✅ 
├── data-model.md        # Phase 1 output (/plan command) ✅
├── quickstart.md        # Phase 1 output (/plan command) ✅
├── api-spec.yaml        # Phase 1 output (/plan command) ✅
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan) ⏳
```

### Source Code (repository root) - 现有结构
```
# Option 2: Web application (when "frontend" + "backend" detected) ✅ CURRENT
backend/
├── app/
│   ├── models/                # ✅ 现有SQLAlchemy模型
│   │   ├── base_models.py     # Machine, Material基础模型
│   │   ├── decade_plan.py     # 现有旬计划模型
│   │   └── monthly_plan_models.py  # 🆕 待创建月计划模型
│   ├── services/              # ✅ 现有业务服务
│   │   ├── excel_parser.py    # 现有Excel解析器
│   │   └── monthly_plan_parser.py  # 🆕 待创建月计划解析器
│   ├── algorithms/            # ✅ 现有算法模块
│   │   ├── base.py, merge_algorithm.py, split_algorithm.py...
│   │   └── monthly_scheduling/  # 🆕 已创建月度算法目录
│   │       ├── __init__.py, base.py  # ✅ 已完成
│   │       └── 7个算法模块 (待实现)
│   └── api/v1/                # ✅ 现有API路由
│       ├── plans.py           # 现有旬计划API (不可修改)
│       ├── monthly_plans.py   # 🆕 待创建月计划API
│       ├── monthly_scheduling.py  # 🆕 待创建月度排产API
│       └── monthly_work_orders.py # 🆕 待创建月度工单API
├── tests/                     # ✅ 现有测试结构
│   ├── test_*_contract.py     # ✅ 已完成11个合约测试
│   ├── test_*_integration.py  # ✅ 已完成2个集成测试
│   └── test_monthly_*.py      # 🆕 待创建更多月度测试
└── requirements.txt           # ✅ 现有依赖列表

frontend/
├── src/
│   ├── components/            # ✅ 现有Vue组件
│   │   ├── DecadePlanUpload.vue    # 现有旬计划组件
│   │   ├── MonthlyPlanUpload.vue   # 🆕 待创建月计划组件
│   │   └── MonthlyGanttChart.vue   # 🆕 待创建月度甘特图
│   ├── views/                 # ✅ 现有页面组件
│   │   ├── DecadePlanEntry.vue     # 现有旬计划页面
│   │   ├── MonthlyPlanEntry.vue    # 🆕 待创建月计划页面
│   │   └── MonthlyScheduling.vue   # 🆕 待创建月度排产页面
│   └── services/api.ts        # ✅ 现有API客户端
└── package.json               # ✅ 现有依赖列表

scripts/                       # ✅ 现有数据库脚本
├── database-schema.sql        # 现有数据库架构
├── monthly_plan_schema.sql    # ✅ 已完成月计划表结构
└── init_work_calendar.sql     # ✅ 已完成工作日历初始化
```

**Structure Decision**: Option 2 (Web application) - 基于现有backend/frontend分离架构

## Phase 0: Outline & Research ✅
*Prerequisites: Technical Context填写完成*

### 研究发现总结

1. **现有系统分析**:
   - APS智慧排产系统v3已实现完整的旬计划功能
   - 使用FastAPI + SQLAlchemy + Vue.js技术栈成熟稳定
   - 现有21个测试文件覆盖算法、API、集成场景
   - 支持复杂Excel解析、机台排产、甘特图可视化

2. **冲突避免方案**:
   - 数据表：`aps_monthly_*` vs 现有`aps_decade_*`
   - API路由：`/monthly-*` vs 现有`/plans`
   - 批次ID：`MONTHLY_` vs 现有`IMPORT_`
   - 组件名：`Monthly*` vs 现有`Decade*`

3. **技术选型决策**:
   - **数据库**: 继续使用MySQL 8.0+，利用现有连接池和缓存
   - **Excel处理**: 继续使用openpyxl 3.1.2，扩展支持月计划格式
   - **算法架构**: 基于现有算法基类，创建9个月度特化模块
   - **前端UI**: 继续使用Element Plus，复用现有甘特图组件

4. **性能优化策略**:
   - 异步Excel解析避免阻塞请求
   - Redis缓存排产中间结果
   - 数据库索引优化月度查询
   - 前端虚拟滚动处理大量工单

**Output**: ✅ research.md with all technical decisions documented

## Phase 1: Design & Contracts ✅
*Prerequisites: research.md complete*

### 已完成设计文档

1. **数据模型设计** (`data-model.md`) ✅:
   - 3个核心实体：MonthlyPlan, MonthlyWorkCalendar, MonthlyScheduleResult
   - 完整的字段定义、约束关系、索引策略
   - 与现有数据库模式的集成点
   - 冲突避免命名约定

2. **API合约设计** (`api-spec.yaml`) ✅:
   - 5个资源组：monthly-plans, monthly-scheduling, monthly-work-orders, monthly-data, monthly-calendar
   - 15个API端点的完整OpenAPI 3.0规范
   - 请求/响应模式、错误处理、认证授权
   - 与现有API完全隔离的路由设计

3. **合约测试生成** ✅:
   - 11个合约测试文件已创建并验证RED状态
   - 2个集成测试覆盖完整工作流和Excel解析
   - 所有测试正确地预期404错误（端点未实现）

4. **快速启动文档** (`quickstart.md`) ✅:
   - 开发环境搭建步骤
   - 月计划Excel文件格式说明
   - API使用示例和测试场景
   - 与现有旬计划功能的对比

5. **Agent上下文更新** (`CLAUDE.md`) ✅:
   - 月计划功能的技术栈信息
   - 冲突避免设计原则
   - 开发命令和测试策略
   - 文件组织和命名约定

**Output**: ✅ data-model.md, api-spec.yaml, failing contract tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

### Task Generation Strategy

**基于现有实现状态的任务生成**:

1. **设置任务** (T001-T005) ✅ 已完成:
   - 数据库架构、索引、工作日历初始化
   - 月度算法模块基础结构

2. **测试任务** (T006-T013) ✅ 已完成:
   - 11个合约测试 (T006-T011)
   - 2个集成测试 (T012-T013)
   - 所有测试处于正确的TDD RED状态

3. **核心实现任务** (T014-T040) 📋 待生成:
   - 从Phase 1设计文档生成具体实现任务
   - 3个数据模型创建任务 [P]
   - 9个算法模块实现任务 [P]
   - 5个API端点实现任务
   - Excel解析器扩展任务

4. **前端任务** (T041-T050) 📋 待生成:
   - 基于现有Vue组件模式生成
   - 月计划上传组件 [P]
   - 排产管理页面 [P]
   - 甘特图组件集成 [P]

5. **集成任务** (T051-T055) 📋 待生成:
   - 端到端测试场景
   - 性能测试和优化
   - 文档完善和部署准备

**Ordering Strategy**:
- **TDD严格顺序**: Tests before implementation (T001-T013 ✅ 已完成测试阶段)
- **依赖顺序**: Models → Services → APIs → Frontend
- **并行标记[P]**: 独立文件可并行开发
- **冲突避免**: 确保所有新任务不影响现有代码

**Estimated Output**: 55个编号任务，其中13个已完成，42个待生成

### 基于现有assets的任务优化

**利用已完成工作**:
- T001-T005: 数据库和基础设施 ✅
- T006-T013: 完整的测试覆盖 ✅
- 现有算法基类和工具函数可复用
- 现有Vue组件可作为模板

**下一阶段重点**:
- T014-T025: 核心业务逻辑实现
- T026-T035: API端点开发
- T036-T045: 前端界面开发
- T046-T055: 系统集成和优化

**IMPORTANT**: 此阶段由/tasks命令执行，不在/plan范围内

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*本项目无宪法违规，无需填写*

所有设计决策都符合Constitution要求：
- 项目数量：3个 (符合≤3限制)
- 架构简洁：直接使用框架，无包装层
- 测试优先：TDD严格执行
- 结构清晰：现有成熟架构基础上扩展

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅
- [x] Phase 1: Design complete (/plan command) ✅ 
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [ ] Phase 3: Tasks generated (/tasks command) 📋 下一步
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅
- [x] Complexity deviations documented ✅ (无违规)

**Implementation Progress** (基于现有工作):
- [x] Database Schema: 100% ✅ (T001-T005)
- [x] Contract Tests: 100% ✅ (T006-T013) 
- [ ] Core Models: 0% (待T014-T016)
- [ ] Algorithm Modules: 11% (基础结构已建立)
- [ ] API Endpoints: 0% (待T017-T025)
- [ ] Frontend Components: 0% (待T026-T035)
- [ ] Integration: 0% (待T036-T040)

---
*Based on Constitution v2.1.1 and existing APS Tobacco v3 system architecture*
*Generated on 2025-01-16 for branch 001-aps-v2-2019*