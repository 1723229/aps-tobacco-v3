# APS智慧排产系统v3 - 月计划Excel直接排产功能技术方案研究

## 研究概述

基于现有APS智慧排产系统(v3)的技术栈，设计集成浙江中烟月计划Excel格式处理功能的技术方案。系统需要在现有旬计划(decade plan)处理能力基础上，并行支持月度生产排产能力，保持架构一致性和代码复用性。

## 现有技术栈分析

**后端技术栈:**
- FastAPI 0.104.1 (异步Python框架)
- SQLAlchemy 2.0.23 (异步ORM)
- aiomysql 0.2.0 (异步MySQL驱动)
- openpyxl 3.1.2 (Excel处理)
- MySQL 8.0+ (主数据库)
- Redis 7.0+ (缓存层)

**前端技术栈:**
- Vue.js 3.5.18 + TypeScript
- Element Plus 2.8.8 (中文UI组件库)
- Pinia 3.0.3 (状态管理)
- Vite 7.0.6 (构建工具)
- Vue Ganttastic 2.3.2 (甘特图组件)

**现有架构优势:**
- ✅ 完整的Excel解析管道 (`ProductionPlanExcelParser`)
- ✅ 成熟的排产算法引擎 (`AlgorithmPipeline`, `SchedulingEngine`)
- ✅ 21个测试文件覆盖核心功能
- ✅ 异步数据库连接和事务管理
- ✅ Vue 3组合式API和TypeScript支持

## 关键技术决策

### 1. Excel处理策略

**决策**: 创建可插拔的Excel格式处理器架构

**选择了什么**: 设计抽象的`PlanExcelParser`基类，配合具体的格式处理器(`DecadeFormatProcessor`, `MonthlyFormatProcessor`)

**理由**:
- **可扩展性**: 遵循开放/封闭原则，未来可轻松添加新的计划类型
- **代码复用**: 共享Excel基础解析逻辑，避免重复开发
- **风险隔离**: 新功能不影响现有旬计划解析功能
- **维护性**: 每种格式有独立的处理器，便于维护和调试

**考虑的替代方案**:
- 直接扩展现有`ProductionPlanExcelParser`: 风险高，可能破坏现有功能
- 创建完全独立的`MonthlyPlanExcelParser`: 代码重复，维护成本高

**技术实现**:
```python
# 抽象基类
class AbstractPlanExcelParser:
    def __init__(self, format_processor: FormatProcessor):
        self.format_processor = format_processor
    
    async def parse_excel_file(self, file_path: str) -> Dict[str, Any]:
        # 通用解析逻辑
        pass

# 格式处理器
class DecadeFormatProcessor(FormatProcessor):
    """现有旬计划格式处理器"""
    pass

class MonthlyFormatProcessor(FormatProcessor): 
    """新的月计划格式处理器"""
    pass
```

### 2. 数据库集成策略

**决策**: 创建独立的`aps_monthly_plan`表，与现有`aps_decade_plan`表并行

**选择了什么**: SQLAlchemy 2.0.23异步模式下新增专用的月计划数据表

**理由**:
- **业务语义清晰**: 月计划和旬计划有不同的业务语义和字段要求
- **性能优化**: 独立表可针对月计划数据特点设置专门的索引和约束
- **风险隔离**: 不影响现有旬计划表的数据完整性和性能
- **扩展空间**: 月计划可能需要特有字段(如月度汇总统计等)

**考虑的替代方案**:
- 在`aps_decade_plan`表添加`plan_type`列: 混合语义，潜在字段冲突
- 创建`aps_plan_base`父表: 过度设计，查询复杂度高

**表结构设计**:
```sql
CREATE TABLE `aps_monthly_plan` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `import_batch_id` varchar(50) NOT NULL COMMENT '导入批次ID',
  `work_order_nr` varchar(50) NOT NULL COMMENT '生产订单号',
  `article_nr` varchar(100) NOT NULL COMMENT '成品烟牌号',
  `package_type` varchar(50) COMMENT '包装类型',
  `specification` varchar(50) COMMENT '规格',
  `quantity_total` int NOT NULL COMMENT '月度投料总量（箱）',
  `final_quantity` int NOT NULL COMMENT '月度成品数量（箱）',
  `production_unit` varchar(50) COMMENT '生产单元',
  `maker_code` varchar(50) NOT NULL COMMENT '卷包机代码',
  `feeder_code` varchar(50) NOT NULL COMMENT '喂丝机代码',
  `planned_month` date NOT NULL COMMENT '计划月份',
  `planned_start` datetime COMMENT '月度计划开始时间',
  `planned_end` datetime COMMENT '月度计划结束时间',
  -- 月计划特有字段
  `monthly_target` int COMMENT '月度生产目标',
  `weekly_distribution` json COMMENT '按周分配比例',
  `validation_status` enum('VALID','WARNING','ERROR') DEFAULT 'VALID',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_monthly_plan_batch` (`import_batch_id`),
  KEY `idx_monthly_plan_month` (`planned_month`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度生产计划表';
```

### 3. 算法架构设计

**决策**: 基于现有算法引擎创建可插拔的计划类型处理器模式

**选择了什么**: `PlanTypeProcessor`抽象模式，配合`DecadePlanProcessor`和`MonthlyPlanProcessor`具体实现

**理由**:
- **架构一致性**: 复用现有`SchedulingEngine`架构，保持系统一致性
- **算法复用**: 部分算法(如时间校正、并行处理)可在不同计划类型间共享
- **独立性**: 月计划处理逻辑独立，不影响现有旬计划算法
- **可测试性**: 每个处理器可独立测试，便于质量保证

**考虑的替代方案**:
- 修改现有`AlgorithmPipeline`添加计划类型判断: 增加复杂度，违反单一职责
- 创建完全独立的`MonthlyAlgorithmPipeline`: 代码重复，难以共享通用算法

**架构设计**:
```python
class AbstractPlanProcessor:
    """计划处理器抽象基类"""
    
    @abstractmethod
    async def validate_input_data(self, plan_data: List[Dict]) -> bool:
        pass
    
    @abstractmethod 
    async def execute_scheduling_pipeline(self, plan_data: List[Dict]) -> AlgorithmResult:
        pass

class DecadePlanProcessor(AbstractPlanProcessor):
    """旬计划处理器 - 重构现有逻辑"""
    def __init__(self):
        self.pipeline = AlgorithmPipeline()  # 复用现有管道
    
    async def execute_scheduling_pipeline(self, plan_data: List[Dict]) -> AlgorithmResult:
        # 重构现有旬计划算法逻辑
        return await self.pipeline.execute_full_pipeline(plan_data)

class MonthlyPlanProcessor(AbstractPlanProcessor):
    """月计划处理器 - 新实现"""
    def __init__(self):
        self.monthly_pipeline = MonthlyAlgorithmPipeline()
    
    async def execute_scheduling_pipeline(self, plan_data: List[Dict]) -> AlgorithmResult:
        # 月计划特有的算法逻辑
        # 1. 月度数据分解为周计划
        # 2. 应用月度约束规则
        # 3. 生成月度工单
        pass

class PlanTypeRegistry:
    """计划类型注册器"""
    processors = {
        'decade': DecadePlanProcessor,
        'monthly': MonthlyPlanProcessor
    }
    
    @classmethod
    def get_processor(cls, plan_type: str) -> AbstractPlanProcessor:
        return cls.processors[plan_type]()
```

### 4. Vue.js 3.5.18 + Element Plus前端集成

**决策**: 创建专门的月计划视图组件，配合共享的通用计划组件

**选择了什么**: 新增`MonthlyPlanEntry.vue`、`MonthlyPlanDetail.vue`等专门视图，同时抽取共享组件

**理由**:
- **用户体验**: 针对月计划的特定UI需求优化用户界面
- **代码复用**: 抽取共享组件避免重复开发(如文件上传、数据表格等)
- **风险控制**: 不修改现有旬计划视图，避免影响现有功能
- **类型安全**: TypeScript支持确保组件props和数据类型安全

**考虑的替代方案**:
- 在现有视图中添加计划类型选择: UI复杂度高，用户体验差
- 完全独立的月计划页面: 代码重复，维护成本高
- 共享组件模式: 复杂度高，prop传递层级深

**前端架构设计**:
```typescript
// 路由配置扩展
const monthlyPlanRoutes = [
  {
    path: "/monthly-plan/entry",
    name: "monthly-plan-entry", 
    component: () => import("../views/MonthlyPlanEntry.vue"),
    meta: { title: "月计划录入" }
  },
  {
    path: "/monthly-plan/detail/:batchId",
    name: "monthly-plan-detail",
    component: () => import("../views/MonthlyPlanDetail.vue"), 
    meta: { title: "月计划详情" },
    props: true
  }
];

// 共享组件设计
// components/shared/PlanUpload.vue
interface PlanUploadProps {
  planType: 'decade' | 'monthly';
  acceptedFormats?: string[];
  maxFileSize?: number;
}

// components/shared/PlanTable.vue  
interface PlanTableProps {
  planType: 'decade' | 'monthly';
  data: DecadePlan[] | MonthlyPlan[];
  columns: TableColumn[];
}
```

**Element Plus 2.8.8 组件利用**:
- `el-upload`: 文件上传功能复用
- `el-table`: 数据展示表格复用
- `el-form`: 表单验证逻辑复用
- `el-date-picker`: 月份选择器扩展
- `el-tabs`: 计划类型切换

## 实施优先级和风险评估

### 高优先级实施项
1. **Excel格式处理器架构** - 核心功能基础
2. **MonthlyPlan数据模型** - 数据层支撑
3. **MonthlyPlanProcessor算法** - 业务逻辑核心
4. **基础API endpoints** - 前后端接口

### 中优先级实施项
1. **MonthlyPlanEntry.vue视图** - 用户入口界面
2. **共享组件抽取** - 代码复用优化
3. **单元测试覆盖** - 质量保证

### 低优先级实施项
1. **MonthlyPlanDetail.vue详情页** - 详细数据展示
2. **甘特图月计划支持** - 可视化增强
3. **月计划特有的业务规则** - 业务逻辑细化

### 技术风险
- **Excel格式兼容性**: 浙江中烟月计划Excel格式可能与旬计划差异较大
- **性能考虑**: 月计划数据量可能比旬计划大，需要优化查询和算法性能
- **业务规则复杂度**: 月计划的业务约束可能比旬计划复杂
- **数据一致性**: 需要保证月计划和旬计划数据的一致性检查

### 缓解措施
- **渐进式开发**: 先实现基础功能，再逐步添加复杂业务规则
- **充分测试**: 针对每个组件编写单元测试和集成测试
- **性能监控**: 在开发过程中持续监控数据库查询和算法性能
- **向后兼容**: 确保新功能不影响现有旬计划功能

## 总结

该技术方案基于现有APS智慧排产系统v3的成熟技术栈，通过可插拔的架构模式实现月计划Excel处理功能。方案重点关注：

1. **架构可扩展性**: 通过抽象模式为未来更多计划类型奠定基础
2. **代码复用性**: 最大化利用现有组件和算法
3. **风险控制**: 独立实现避免影响现有功能
4. **用户体验**: 针对月计划特点优化界面设计

该方案充分利用了FastAPI + SQLAlchemy 2.0.23 + Vue.js 3.5.18的技术优势，为浙江中烟月计划Excel直接排产提供了可靠的技术基础。