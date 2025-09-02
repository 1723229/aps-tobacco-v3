# APS智慧排产系统 - 技术设计文档（实际实现状态）

## 1. 系统架构设计

### 1.1 整体架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面层     │    │    API网关层     │    │   业务服务层     │
│                 │    │                 │    │                 │
│ • Vue.js/React │◄──►│ • 请求路由       │◄──►│ • 排产算法引擎   │
│ • 甘特图组件     │    │ • 身份验证       │    │ • 工单管理服务   │
│ • 文件上传组件   │    │ • 限流控制       │    │ • 数据导入服务   │
│ • 数据展示组件   │    │ • 日志记录       │    │ • MES集成服务   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│   MES系统接口    │    │   数据持久层     │              │
│                 │    │                 │              │
│ • 轮保计划接口   │◄──►│ • MySQL数据库    │◄─────────────┘
│ • 工单下发接口   │    │ • Redis缓存      │
│ • 状态反馈接口   │    │ • 文件存储       │
└─────────────────┘    └─────────────────┘
```

### 1.2 技术栈选择（实际实现）

| 层次 | 技术选型 | 版本 | 选择理由 |
|------|----------|----------|----------|
| **前端** | Vue.js 3 + TypeScript | 3.5.18 | 组件化开发，类型安全 |
| | Element Plus | 2.8.8 | 丰富的UI组件库，中文本地化 |
| | Vue Router | 4.5.1 | 前端路由管理 |
| | Pinia | 3.0.3 | 状态管理 |
| | Axios | 1.7.7 | HTTP客户端 |
| | Vite | 7.0.6 | 前端构建工具 |
| | ECharts/G2 | - | 甘特图和数据可视化 |
| **后端** | FastAPI | 0.104.1 | 高性能异步框架，自动API文档 |
| | SQLAlchemy | 2.0.23 | Python ORM，支持异步操作 |
| | Pydantic | 2.5.0 | 数据验证和序列化 |
| | Pydantic-Settings | 2.5.2 | 配置管理 |
| **数据库** | MySQL | 8.0+ | 事务支持，成熟稳定 |
| | aiomysql | 0.2.0 | MySQL异步驱动 |
| | Redis | 7.0+ | 缓存和会话存储 |
| **文件处理** | openpyxl | 3.1.2 | Excel文件解析 |
| | pandas | 2.1.3 | 数据处理 |
| **开发工具** | pytest | 7.4.3 | 单元测试框架 |
| | black | 23.10.1 | 代码格式化 |
| | uvicorn | 0.24.0 | ASGI服务器 |

### 1.3 技术架构总览

```
aps-tobacco-v3/
├── frontend/                    # 前端模块 Vue.js应用
│   ├── src/                    # 源代码目录
│   │   ├── components/         # 业务组件
│   │   │   ├── DecadePlanUpload.vue    # 文件上传组件
│   │   │   ├── DecadePlanTable.vue     # 数据表格组件
│   │   │   ├── ParseResult.vue         # 解析结果组件
│   │   │   └── LoadingComponent.vue    # 加载组件
│   │   ├── views/              # 页面视图
│   │   │   ├── Home.vue        # 首页（统计信息、快速操作）
│   │   │   ├── DecadePlanEntry.vue     # 旬计划录入页面
│   │   │   └── DecadePlanDetail.vue    # 旬计划详情页面
│   │   ├── services/           # API服务层
│   │   │   └── api.ts          # API客户端
│   │   ├── stores/             # Pinia状态管理
│   │   │   └── decade-plan.ts  # 旬计划状态管理
│   │   ├── router/             # Vue Router配置
│   │   │   └── index.ts        # 路由定义
│   │   ├── types/              # TypeScript类型
│   │   │   └── api.ts          # API类型定义
│   │   ├── utils/              # 工具函数
│   │   │   ├── index.ts        # 通用工具函数
│   │   │   ├── http.ts         # HTTP客户端配置
│   │   │   └── error-handler.ts# 错误处理
│   │   ├── assets/             # 静态资源
│   │   ├── App.vue             # 根组件（完整导航布局）
│   │   └── main.ts             # 应用入口
│   ├── package.json            # 项目依赖配置
│   ├── vite.config.ts          # Vite构建配置
│   ├── index.html              # HTML模板
│   └── tsconfig.json           # TypeScript配置
├── backend/                     # 后端服务
│   ├── app/
│   │   ├── api/                # API路由层
│   │   │   └── v1/             # API版本1
│   │   │       ├── data.py     # 数据查询API
│   │   │       ├── plans.py    # 计划上传解析API
│   │   │       └── router.py   # 路由汇总
│   │   ├── core/               # 核心配置
│   │   │   └── config.py       # 配置管理
│   │   ├── db/                 # 数据库层
│   │   │   ├── cache.py        # Redis缓存
│   │   │   └── connection.py   # 数据库连接
│   │   ├── models/             # 数据模型
│   │   │   ├── base_models.py  # 基础模型
│   │   │   └── decade_plan.py  # 旬计划模型
│   │   ├── schemas/            # Pydantic模型
│   │   │   └── base.py         # API DTO模型
│   │   ├── services/           # 业务服务层
│   │   │   └── excel_parser.py # Excel解析服务
│   │   ├── algorithms/         # 排产算法
│   │   ├── utils/              # 工具函数
│   │   └── main.py             # 应用入口
│   ├── tests/                  # 测试代码框架
│   ├── requirements.txt        # 依赖包定义
│   └── pytest.ini             # 测试配置
├── docs/                       # 项目文档
│   ├── algorithm-design.md     # 算法设计文档
│   ├── requirements-detail.md  # 需求细化文档
│   ├── technical-design.md     # 技术设计文档
│   └── ux-design.md           # 用户体验设计
├── aps/                        # 业务样例数据
└── scripts/                    # 数据库脚本
    └── database-schema.sql     # 数据库结构
```

## 2. 数据表结构设计（实现状态）

### 2.1 基础数据表

#### 2.1.1 机台信息表 (aps_machine) ✅ 已实现

```sql
CREATE TABLE aps_machine (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    machine_code VARCHAR(20) NOT NULL COMMENT '机台代码',
    machine_name VARCHAR(100) NOT NULL COMMENT '机台名称',
    machine_type ENUM('PACKING', 'FEEDING') NOT NULL COMMENT '机台类型：卷包机/喂丝机',
    equipment_type VARCHAR(50) COMMENT '设备型号(如PROTOS70, M8)',
    production_line VARCHAR(50) COMMENT '生产线',
    status ENUM('ACTIVE', 'INACTIVE', 'MAINTENANCE') DEFAULT 'ACTIVE' COMMENT '机台状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_machine_code (machine_code),
    INDEX idx_machine_type (machine_type),
    INDEX idx_status (status)
) COMMENT='机台基础信息表';
```

#### 2.1.2 物料信息表 (aps_material) ✅ 已实现

```sql
CREATE TABLE aps_material (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    article_nr VARCHAR(100) NOT NULL COMMENT '物料编号',
    article_name VARCHAR(200) NOT NULL COMMENT '物料名称',
    material_type ENUM('FINISHED_PRODUCT', 'TOBACCO_SILK', 'RAW_MATERIAL') NOT NULL COMMENT '物料类型',
    package_type VARCHAR(50) COMMENT '包装类型（软包/硬包）',
    specification VARCHAR(50) COMMENT '规格（长嘴/短嘴/超长嘴/中支/细支）',
    unit VARCHAR(20) DEFAULT '箱' COMMENT '计量单位',
    conversion_rate DECIMAL(10,4) DEFAULT 1.0000 COMMENT '转换比率',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_article_nr (article_nr),
    INDEX idx_material_type (material_type),
    INDEX idx_status (status)
) COMMENT='物料基础信息表';
```

#### 2.1.3 机台生产速度配置表 (aps_machine_speed) ❌ 未实现

```sql
CREATE TABLE aps_machine_speed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    machine_code VARCHAR(20) NOT NULL COMMENT '机台代码',
    article_nr VARCHAR(100) NOT NULL COMMENT '物料编号',
    speed DECIMAL(10,2) NOT NULL COMMENT '生产速度（箱/小时）',
    efficiency_rate DECIMAL(5,2) DEFAULT 85.00 COMMENT '效率系数（%）',
    effective_from DATE NOT NULL COMMENT '生效日期',
    effective_to DATE COMMENT '失效日期',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_machine_article_date (machine_code, article_nr, effective_from),
    FOREIGN KEY fk_machine_speed_machine (machine_code) REFERENCES aps_machine(machine_code),
    FOREIGN KEY fk_machine_speed_material (article_nr) REFERENCES aps_material(article_nr),
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status)
) COMMENT='机台生产速度配置表';
```

#### 2.1.4 机台对应关系表 (aps_machine_relation) ❌ 未实现

```sql
CREATE TABLE aps_machine_relation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    feeder_code VARCHAR(20) NOT NULL COMMENT '喂丝机代码',
    maker_code VARCHAR(20) NOT NULL COMMENT '卷包机代码',
    relation_type ENUM('ONE_TO_ONE', 'ONE_TO_MANY') DEFAULT 'ONE_TO_ONE' COMMENT '关系类型',
    priority INT DEFAULT 1 COMMENT '优先级（1=最高）',
    effective_from DATE NOT NULL COMMENT '生效日期',
    effective_to DATE COMMENT '失效日期',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY fk_feeder (feeder_code) REFERENCES aps_machine(machine_code),
    FOREIGN KEY fk_maker (maker_code) REFERENCES aps_machine(machine_code),
    UNIQUE KEY uk_feeder_maker_date (feeder_code, maker_code, effective_from),
    INDEX idx_feeder_code (feeder_code),
    INDEX idx_maker_code (maker_code),
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status)
) COMMENT='喂丝机与卷包机对应关系表';
```

#### 2.1.5 班次配置表 (aps_shift_config) ❌ 未实现

```sql
CREATE TABLE aps_shift_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    shift_name VARCHAR(50) NOT NULL COMMENT '班次名称',
    machine_name VARCHAR(50) NOT NULL COMMENT '机台名称(*表示所有机台)',
    start_time TIME NOT NULL COMMENT '开始时间',
    end_time TIME NOT NULL COMMENT '结束时间',
    is_ot_needed BOOLEAN DEFAULT FALSE COMMENT '是否需要加班',
    max_ot_duration TIME COMMENT '最大加班时长',
    effective_from DATE NOT NULL COMMENT '生效日期',
    effective_to DATE COMMENT '失效日期',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_shift_machine_date (shift_name, machine_name, effective_from),
    INDEX idx_shift_name (shift_name),
    INDEX idx_machine_name (machine_name),
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status)
) COMMENT='班次配置表';
```

### 2.2 业务数据表

#### 2.2.1 导入计划表 (aps_import_plan) ✅ 已实现

```sql
CREATE TABLE aps_import_plan (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    import_batch_id VARCHAR(50) NOT NULL COMMENT '导入批次ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小（字节）',
    total_records INT DEFAULT 0 COMMENT '总记录数',
    valid_records INT DEFAULT 0 COMMENT '有效记录数',
    error_records INT DEFAULT 0 COMMENT '错误记录数',
    import_status ENUM('UPLOADING', 'PARSING', 'COMPLETED', 'FAILED') DEFAULT 'UPLOADING' COMMENT '导入状态',
    import_start_time DATETIME COMMENT '导入开始时间',
    import_end_time DATETIME COMMENT '导入结束时间',
    error_message TEXT COMMENT '错误信息',
    created_by VARCHAR(100) DEFAULT 'system' COMMENT '创建者',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_import_batch (import_batch_id),
    INDEX idx_import_status (import_status),
    INDEX idx_created_time (created_time)
) COMMENT='计划导入记录表';
```

#### 2.2.2 原始旬计划表 (aps_decade_plan) ✅ 已实现

```sql
CREATE TABLE aps_decade_plan (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    import_batch_id VARCHAR(50) NOT NULL COMMENT '导入批次ID',
    work_order_nr VARCHAR(50) NOT NULL COMMENT '生产订单号',
    article_nr VARCHAR(100) NOT NULL COMMENT '成品烟牌号',
    package_type VARCHAR(50) COMMENT '包装类型（软包/硬包）',
    specification VARCHAR(50) COMMENT '规格（长嘴/短嘴等）',
    quantity_total INT NOT NULL COMMENT '投料总量（箱）',
    final_quantity INT NOT NULL COMMENT '成品数量（箱）',
    production_unit VARCHAR(50) COMMENT '生产单元',
    maker_code VARCHAR(20) NOT NULL COMMENT '卷包机代码',
    feeder_code VARCHAR(20) NOT NULL COMMENT '喂丝机代码',
    planned_start DATETIME NOT NULL COMMENT '计划开始时间',
    planned_end DATETIME NOT NULL COMMENT '计划结束时间',
    production_date_range VARCHAR(100) COMMENT '成品生产日期范围',
    row_number INT COMMENT '原始行号',
    validation_status ENUM('VALID', 'WARNING', 'ERROR') DEFAULT 'VALID' COMMENT '验证状态',
    validation_message TEXT COMMENT '验证信息',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY fk_decade_plan_import (import_batch_id) REFERENCES aps_import_plan(import_batch_id),
    FOREIGN KEY fk_decade_plan_material (article_nr) REFERENCES aps_material(article_nr),
    INDEX idx_import_batch (import_batch_id),
    INDEX idx_work_order (work_order_nr),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_validation_status (validation_status)
) COMMENT='原始卷包旬计划表';
```

#### 2.2.3 排产任务表 (aps_scheduling_task) ❌ 未实现

```sql
CREATE TABLE aps_scheduling_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_id VARCHAR(50) NOT NULL COMMENT '排产任务ID',
    import_batch_id VARCHAR(50) NOT NULL COMMENT '关联导入批次ID',
    task_name VARCHAR(255) NOT NULL COMMENT '任务名称',
    task_status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED') DEFAULT 'PENDING' COMMENT '任务状态',
    current_stage VARCHAR(100) COMMENT '当前阶段',
    progress INT DEFAULT 0 COMMENT '进度百分比(0-100)',
    total_records INT DEFAULT 0 COMMENT '总记录数',
    processed_records INT DEFAULT 0 COMMENT '已处理记录数',
    
    -- 算法参数配置
    merge_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用合并',
    split_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用拆分',
    correction_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用校正',
    parallel_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用并行',
    
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    execution_duration INT COMMENT '执行耗时（秒）',
    error_message TEXT COMMENT '错误信息',
    result_summary JSON COMMENT '结果摘要（JSON格式）',
    
    created_by VARCHAR(100) DEFAULT 'system' COMMENT '创建者',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_task_id (task_id),
    FOREIGN KEY fk_scheduling_import (import_batch_id) REFERENCES aps_import_plan(import_batch_id),
    INDEX idx_task_status (task_status),
    INDEX idx_created_time (created_time)
) COMMENT='排产任务表';
```

#### 2.2.4 排产处理日志表 (aps_processing_log)

```sql
CREATE TABLE aps_processing_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_id VARCHAR(50) NOT NULL COMMENT '排产任务ID',
    stage VARCHAR(100) NOT NULL COMMENT '处理阶段',
    step_name VARCHAR(200) NOT NULL COMMENT '处理步骤名称',
    log_level ENUM('DEBUG', 'INFO', 'WARN', 'ERROR') DEFAULT 'INFO' COMMENT '日志级别',
    log_message TEXT NOT NULL COMMENT '日志消息',
    processing_data JSON COMMENT '处理数据（JSON格式）',
    execution_time DATETIME NOT NULL COMMENT '执行时间',
    duration_ms INT COMMENT '执行耗时（毫秒）',
    
    FOREIGN KEY fk_log_task (task_id) REFERENCES aps_scheduling_task(task_id),
    INDEX idx_task_stage (task_id, stage),
    INDEX idx_log_level (log_level),
    INDEX idx_execution_time (execution_time)
) COMMENT='排产处理日志表';
```

### 2.3 结果数据表

#### 2.3.1 卷包机工单表 (aps_packing_order)

```sql
CREATE TABLE aps_packing_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    work_order_nr VARCHAR(50) NOT NULL COMMENT '工单号',
    task_id VARCHAR(50) NOT NULL COMMENT '排产任务ID',
    original_order_nr VARCHAR(50) COMMENT '原始订单号',
    
    -- 产品信息
    article_nr VARCHAR(100) NOT NULL COMMENT '成品烟牌号',
    quantity_total INT NOT NULL COMMENT '投料总量（箱）',
    final_quantity INT NOT NULL COMMENT '成品数量（箱）',
    
    -- 机台信息
    maker_code VARCHAR(20) NOT NULL COMMENT '卷包机代码',
    machine_type VARCHAR(50) COMMENT '机台型号',
    
    -- 时间信息
    planned_start DATETIME NOT NULL COMMENT '计划开始时间',
    planned_end DATETIME NOT NULL COMMENT '计划结束时间',
    estimated_duration INT COMMENT '预计耗时（分钟）',
    
    -- MES接口必需字段
    sequence INT NOT NULL COMMENT '执行顺序（同一天内从1开始）',
    unit VARCHAR(20) NOT NULL DEFAULT '箱' COMMENT '基本单位',
    plan_date DATE NOT NULL COMMENT '计划日期（YYYY-MM-DD）',
    
    -- 生产参数
    production_speed DECIMAL(10,2) COMMENT '生产速度（箱/小时）',
    working_shifts JSON COMMENT '工作班次信息（JSON）',
    
    -- 关联信息
    feeder_code VARCHAR(20) NOT NULL COMMENT '对应喂丝机代码',
    related_feeder_order VARCHAR(50) COMMENT '关联喂丝机工单号',
    
    -- 状态信息
    order_status ENUM('PLANNED', 'DISPATCHED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'PLANNED' COMMENT '工单状态',
    priority INT DEFAULT 5 COMMENT '优先级（1-10，数值越小优先级越高）',
    
    -- 特殊标记
    is_split_order BOOLEAN DEFAULT FALSE COMMENT '是否为拆分工单',
    split_from VARCHAR(50) COMMENT '拆分来源工单号',
    split_index INT COMMENT '拆分序号',
    is_merged_order BOOLEAN DEFAULT FALSE COMMENT '是否为合并工单',
    merged_from JSON COMMENT '合并来源工单列表（JSON）',
    is_backup_order BOOLEAN DEFAULT FALSE COMMENT '是否为备用工单（对应MES IsBackup字段）',
    backup_reason VARCHAR(200) COMMENT '备用原因',
    
    -- 处理历史
    processing_history JSON COMMENT '处理历史记录（JSON）',
    
    -- 审计信息
    created_by VARCHAR(100) DEFAULT 'system' COMMENT '创建者',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_packing_order_nr (work_order_nr),
    FOREIGN KEY fk_packing_task (task_id) REFERENCES aps_scheduling_task(task_id),
    FOREIGN KEY fk_packing_material (article_nr) REFERENCES aps_material(article_nr),
    FOREIGN KEY fk_packing_maker (maker_code) REFERENCES aps_machine(machine_code),
    INDEX idx_task_id (task_id),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_maker_code (maker_code),
    INDEX idx_order_status (order_status),
    INDEX idx_priority (priority)
) COMMENT='卷包机工单表';
```

#### 2.3.2 喂丝机工单表 (aps_feeding_order)

```sql
CREATE TABLE aps_feeding_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    work_order_nr VARCHAR(50) NOT NULL COMMENT '工单号',
    task_id VARCHAR(50) NOT NULL COMMENT '排产任务ID',
    
    -- 产品信息
    article_nr VARCHAR(100) NOT NULL COMMENT '成品烟牌号',
    quantity_total INT NOT NULL COMMENT '总供料量（箱）',
    base_quantity INT NOT NULL COMMENT '基础需求量（箱）',
    safety_stock INT DEFAULT 0 COMMENT '安全库存（箱）',
    
    -- 机台信息
    feeder_code VARCHAR(20) NOT NULL COMMENT '喂丝机代码',
    feeder_type VARCHAR(50) COMMENT '喂丝机型号',
    production_lines TEXT COMMENT '生产线列表（支持多机台，逗号分隔）',
    
    -- 时间信息
    planned_start DATETIME NOT NULL COMMENT '计划开始时间',
    planned_end DATETIME NOT NULL COMMENT '计划结束时间',
    estimated_duration INT COMMENT '预计耗时（分钟）',
    
    -- MES接口必需字段
    sequence INT NOT NULL COMMENT '执行顺序（同一天内从1开始）',
    unit VARCHAR(20) NOT NULL DEFAULT '公斤' COMMENT '基本单位',
    plan_date DATE NOT NULL COMMENT '计划日期（YYYY-MM-DD）',
    
    -- 生产参数
    feeding_speed DECIMAL(10,2) COMMENT '喂丝速度（箱/小时）',
    material_consumption JSON COMMENT '物料消耗信息（JSON）',
    
    -- 关联信息
    related_packing_orders JSON NOT NULL COMMENT '关联卷包机工单列表（JSON）',
    packing_machines JSON NOT NULL COMMENT '对应卷包机列表（JSON）',
    
    -- 状态信息
    order_status ENUM('PLANNED', 'DISPATCHED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'PLANNED' COMMENT '工单状态',
    priority INT DEFAULT 5 COMMENT '优先级（1-10，数值越小优先级越高）',
    
    -- 审计信息
    created_by VARCHAR(100) DEFAULT 'system' COMMENT '创建者',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_feeding_order_nr (work_order_nr),
    FOREIGN KEY fk_feeding_task (task_id) REFERENCES aps_scheduling_task(task_id),
    FOREIGN KEY fk_feeding_material (article_nr) REFERENCES aps_material(article_nr),
    FOREIGN KEY fk_feeding_feeder (feeder_code) REFERENCES aps_machine(machine_code),
    INDEX idx_task_id (task_id),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_feeder_code (feeder_code),
    INDEX idx_order_status (order_status),
    INDEX idx_priority (priority)
) COMMENT='喂丝机工单表';
```

### 2.4 MES集成数据表

#### 2.4.1 工单输入批次关联表 (aps_input_batch)

```sql
CREATE TABLE aps_input_batch (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    packing_order_id BIGINT NOT NULL COMMENT '卷包工单ID',
    input_plan_id VARCHAR(50) COMMENT '前工序计划号（喂丝机工单号）',
    input_batch_code VARCHAR(50) COMMENT '前工序批次号',
    material_code VARCHAR(100) NOT NULL COMMENT '物料代码',
    bom_revision VARCHAR(50) COMMENT '版本号',
    quantity DECIMAL(10,2) COMMENT '数量',
    batch_sequence INT COMMENT '批次顺序',
    
    -- MES接口字段
    is_whole_batch BOOLEAN DEFAULT FALSE COMMENT '是否整批',
    is_main_channel BOOLEAN DEFAULT TRUE COMMENT '是否走主通道',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除（用于喂丝机工单取消追加）',
    is_last_one BOOLEAN DEFAULT FALSE COMMENT '是否最后一个批次（只有喂丝才需要）',
    is_tiled BOOLEAN DEFAULT FALSE COMMENT '是否平铺（只有回用烟丝二才会给出）',
    
    -- 备注信息
    remark1 VARCHAR(200) COMMENT '备注1',
    remark2 VARCHAR(200) COMMENT '备注2',
    
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_packing_order (packing_order_id),
    INDEX idx_input_plan (input_plan_id),
    INDEX idx_material_code (material_code),
    INDEX idx_batch_sequence (batch_sequence),
    FOREIGN KEY fk_input_batch_packing (packing_order_id) REFERENCES aps_packing_order(id) ON DELETE CASCADE
) COMMENT='工单输入批次关联表（支持MES InputBatch结构）';
```

#### 2.4.2 工单号序列表 (aps_work_order_sequence)

```sql
CREATE TABLE aps_work_order_sequence (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    order_type ENUM('HWS', 'HJB') NOT NULL COMMENT '工单类型：HWS-喂丝机,HJB-卷包机',
    sequence_date DATE NOT NULL COMMENT '序列日期',
    current_sequence INT DEFAULT 0 COMMENT '当前序列号',
    last_order_nr VARCHAR(50) COMMENT '最后生成的工单号',
    
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_order_type_date (order_type, sequence_date),
    INDEX idx_sequence_date (sequence_date),
    INDEX idx_order_type (order_type)
) COMMENT='工单号序列表（支持MES规范：H+工单类型+9位流水号）';
```

#### 2.4.3 轮保计划表 (aps_maintenance_plan)

```sql
CREATE TABLE aps_maintenance_plan (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    maint_plan_no VARCHAR(50) NOT NULL COMMENT '轮保计划编号',
    schedule_date DATE NOT NULL COMMENT '轮保日期',
    shift_code VARCHAR(20) COMMENT '班次代码',
    maint_group VARCHAR(50) COMMENT '轮保班组',
    equipment_position VARCHAR(50) NOT NULL COMMENT '设备机位',
    machine_code VARCHAR(20) NOT NULL COMMENT '机台代码',
    
    -- 时间信息
    maint_start_time DATETIME NOT NULL COMMENT '轮保开始时间',
    maint_end_time DATETIME NOT NULL COMMENT '轮保结束时间',
    estimated_duration INT COMMENT '预计耗时（分钟）',
    
    -- 轮保信息
    maint_type VARCHAR(50) COMMENT '轮保类型',
    maint_level VARCHAR(50) COMMENT '轮保级别',
    maint_description TEXT COMMENT '轮保描述',
    
    -- 状态信息
    plan_status ENUM('PLANNED', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'PLANNED' COMMENT '计划状态',
    
    -- MES同步信息
    sync_from_mes BOOLEAN DEFAULT TRUE COMMENT '是否来自MES',
    sync_time DATETIME COMMENT 'MES同步时间',
    mes_version VARCHAR(50) COMMENT 'MES版本号',
    
    planner VARCHAR(100) COMMENT '制单人',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_maint_plan_no (maint_plan_no),
    FOREIGN KEY fk_maint_machine (machine_code) REFERENCES aps_machine(machine_code),
    INDEX idx_schedule_date (schedule_date),
    INDEX idx_machine_code (machine_code),
    INDEX idx_maint_time (maint_start_time, maint_end_time),
    INDEX idx_plan_status (plan_status)
) COMMENT='设备轮保计划表';
```

#### 2.4.4 MES工单下发记录表 (aps_mes_dispatch)

```sql
CREATE TABLE aps_mes_dispatch (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    dispatch_batch_id VARCHAR(50) NOT NULL COMMENT '下发批次ID',
    work_order_nr VARCHAR(50) NOT NULL COMMENT '工单号',
    order_type ENUM('PACKING', 'FEEDING') NOT NULL COMMENT '工单类型',
    
    -- 下发信息
    dispatch_status ENUM('PENDING', 'DISPATCHED', 'CONFIRMED', 'FAILED') DEFAULT 'PENDING' COMMENT '下发状态',
    dispatch_time DATETIME COMMENT '下发时间',
    dispatch_data JSON COMMENT '下发数据（JSON）',
    
    -- MES反馈信息
    mes_response JSON COMMENT 'MES响应数据（JSON）',
    mes_confirm_time DATETIME COMMENT 'MES确认时间',
    mes_error_message TEXT COMMENT 'MES错误信息',
    
    -- 重试信息
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retry_count INT DEFAULT 3 COMMENT '最大重试次数',
    next_retry_time DATETIME COMMENT '下次重试时间',
    
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_dispatch_batch (dispatch_batch_id),
    INDEX idx_work_order (work_order_nr),
    INDEX idx_dispatch_status (dispatch_status),
    INDEX idx_order_type (order_type),
    INDEX idx_dispatch_time (dispatch_time)
) COMMENT='MES工单下发记录表';
```

#### 2.4.3 工单状态同步表 (aps_order_status_sync)

```sql
CREATE TABLE aps_order_status_sync (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    batch_code VARCHAR(50) NOT NULL COMMENT '批次号（来自MES）',
    work_order_nr VARCHAR(50) COMMENT '关联工单号',
    order_status VARCHAR(50) NOT NULL COMMENT '工单状态',
    status_change_time DATETIME NOT NULL COMMENT '状态变更时间',
    
    -- 生产信息
    actual_start_time DATETIME COMMENT '实际开始时间',
    actual_end_time DATETIME COMMENT '实际结束时间',
    actual_quantity INT COMMENT '实际产量',
    completion_rate DECIMAL(5,2) COMMENT '完成率（%）',
    
    -- MES同步信息
    sync_from_mes BOOLEAN DEFAULT TRUE COMMENT '是否来自MES',
    sync_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
    mes_data JSON COMMENT 'MES原始数据（JSON）',
    
    -- 处理状态
    processed BOOLEAN DEFAULT FALSE COMMENT '是否已处理',
    process_time DATETIME COMMENT '处理时间',
    process_result TEXT COMMENT '处理结果',
    
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_batch_code (batch_code),
    INDEX idx_work_order (work_order_nr),
    INDEX idx_status_change_time (status_change_time),
    INDEX idx_processed (processed),
    INDEX idx_sync_time (sync_time)
) COMMENT='工单状态同步表';
```

### 2.5 系统配置表

#### 2.5.1 系统参数配置表 (aps_system_config)

```sql
CREATE TABLE aps_system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    config_key VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value TEXT NOT NULL COMMENT '配置值',
    config_type ENUM('STRING', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'JSON') DEFAULT 'STRING' COMMENT '配置类型',
    config_group VARCHAR(50) COMMENT '配置分组',
    config_description VARCHAR(500) COMMENT '配置描述',
    is_encrypted BOOLEAN DEFAULT FALSE COMMENT '是否加密',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_config_key (config_key),
    INDEX idx_config_group (config_group),
    INDEX idx_status (status)
) COMMENT='系统参数配置表';
```

#### 2.5.2 业务规则配置表 (aps_business_rule)

```sql
CREATE TABLE aps_business_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    rule_code VARCHAR(100) NOT NULL COMMENT '规则代码',
    rule_name VARCHAR(200) NOT NULL COMMENT '规则名称',
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型',
    rule_description TEXT COMMENT '规则描述',
    rule_expression TEXT COMMENT '规则表达式',
    rule_parameters JSON COMMENT '规则参数（JSON）',
    priority INT DEFAULT 5 COMMENT '优先级',
    effective_from DATE NOT NULL COMMENT '生效日期',
    effective_to DATE COMMENT '失效日期',
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE' COMMENT '状态',
    created_by VARCHAR(100) DEFAULT 'system' COMMENT '创建者',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_rule_code (rule_code),
    INDEX idx_rule_type (rule_type),
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
) COMMENT='业务规则配置表';
```

### 2.6 操作审计表

#### 2.6.1 系统操作日志表 (aps_operation_log)

```sql
CREATE TABLE aps_operation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    log_id VARCHAR(50) NOT NULL COMMENT '日志ID',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型',
    operation_name VARCHAR(200) NOT NULL COMMENT '操作名称',
    operation_description TEXT COMMENT '操作描述',
    
    -- 操作主体信息
    user_id VARCHAR(100) COMMENT '用户ID',
    user_name VARCHAR(100) COMMENT '用户名称',
    client_ip VARCHAR(45) COMMENT '客户端IP',
    user_agent VARCHAR(500) COMMENT '用户代理',
    
    -- 操作对象信息
    target_type VARCHAR(100) COMMENT '目标类型',
    target_id VARCHAR(100) COMMENT '目标ID',
    target_name VARCHAR(200) COMMENT '目标名称',
    
    -- 操作详情
    request_params JSON COMMENT '请求参数（JSON）',
    response_data JSON COMMENT '响应数据（JSON）',
    operation_result ENUM('SUCCESS', 'FAILED', 'PARTIAL') NOT NULL COMMENT '操作结果',
    error_message TEXT COMMENT '错误信息',
    
    -- 时间信息
    operation_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    execution_duration INT COMMENT '执行耗时（毫秒）',
    
    UNIQUE KEY uk_log_id (log_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_user_id (user_id),
    INDEX idx_operation_time (operation_time),
    INDEX idx_operation_result (operation_result)
) COMMENT='系统操作日志表';
```

## 3. 数据库设计原则

### 3.1 命名规范

**表命名规范：**
- 统一前缀：aps_
- 使用小写字母和下划线
- 名称要体现表的业务含义
- 避免使用保留字

**字段命名规范：**
- 使用小写字母和下划线
- 主键统一使用 id
- 外键使用 表名_id 格式
- 时间字段统一后缀 _time
- 布尔字段使用 is_ 前缀

**索引命名规范：**
- 主键：PRIMARY
- 唯一索引：uk_表名_字段名
- 普通索引：idx_表名_字段名
- 外键：fk_表名_引用表名

### 3.2 数据类型选择

| 数据类型 | 使用场景 | 说明 |
|---------|----------|------|
| **BIGINT** | 主键、数量字段 | 自增主键，大数值 |
| **INT** | 一般数值字段 | 计数、数量等 |
| **VARCHAR** | 变长文本 | 根据实际长度设置合适大小 |
| **TEXT** | 长文本 | 描述、备注等 |
| **DATETIME** | 日期时间 | 精确到秒 |
| **DATE** | 日期 | 仅需要日期部分 |
| **TIME** | 时间 | 仅需要时间部分 |
| **DECIMAL** | 精确数值 | 金额、比率等 |
| **BOOLEAN** | 布尔值 | 是否标记 |
| **ENUM** | 枚举值 | 固定选项 |
| **JSON** | 复杂结构 | 动态结构数据 |

### 3.3 索引设计策略

**主键索引：**
- 所有表都有自增BIGINT主键
- 使用InnoDB引擎的聚集索引特性

**唯一索引：**
- 业务唯一字段（如工单号、任务ID）
- 复合唯一约束（如机台+日期+物料）

**普通索引：**
- 外键字段
- 查询频繁的字段
- WHERE条件经常使用的字段
- ORDER BY使用的字段

**复合索引：**
- 多字段联合查询场景
- 遵循最左前缀原则
- 选择性高的字段在前

### 3.4 约束设计

**外键约束：**
- 主要业务表使用外键约束
- 确保数据一致性
- 考虑级联更新和删除策略

**检查约束：**
- 数据范围检查
- 状态值检查
- 时间逻辑检查

**非空约束：**
- 核心业务字段不允许为空
- 提供合理的默认值

### 2.7 数据表实现状态总结

#### 已实现的数据表 ✅
1. **aps_machine** - 机台基础信息表
   - 完整的SQLAlchemy模型定义
   - 支持卷包机和喂丝机类型
   - 包含状态管理和索引优化

2. **aps_material** - 物料基础信息表
   - 完整的SQLAlchemy模型定义
   - 支持物料类型分类
   - 包含包装类型和规格信息

3. **aps_import_plan** - 导入计划表
   - 完整的SQLAlchemy模型定义
   - 支持导入状态管理
   - 文件信息和错误追踪

4. **aps_decade_plan** - 原始旬计划表
   - 完整的SQLAlchemy模型定义
   - 支持Excel解析结果存储
   - 包含机台代码和验证状态

#### 未实现的数据表 ❌
1. **业务配置表** - 速度配置、机台关系、班次配置等
2. **排产算法表** - 任务表、处理日志等
3. **工单结果表** - 卷包机工单、喂丝机工单等
4. **MES集成表** - 工单下发、状态同步等
5. **系统配置表** - 参数配置、业务规则等

#### 数据库连接状态 ✅
- **MySQL连接**: 已实现异步连接池
- **Redis连接**: 已实现缓存连接
- **连接健康检查**: 已实现监控接口
- **配置管理**: 支持环境变量配置

## 4. API接口设计（实际实现状态）

### 4.1 已实现的API接口 ✅

#### RESTful API规范（已遵循）
- **URL设计**: `/api/v1/{resource}` 格式
- **HTTP方法**: 正确使用GET/POST/PUT/DELETE
- **状态码**: 标准HTTP状态码
- **数据格式**: JSON格式，使用Pydantic验证

#### 实现的接口列表
1. **文件上传管理** (`/api/v1/plans/`)
   - `POST /upload` - Excel文件上传 ✅
   - `POST /{import_batch_id}/parse` - 文件解析 ✅
   - `GET /{import_batch_id}/status` - 解析状态查询 ✅
   - `GET /history` - 上传历史查询 ✅
   - `GET /statistics` - 上传统计信息 ✅
   - `GET /{import_batch_id}/decade-plans` - 旬计划查询 ✅

2. **数据查询服务** (`/api/v1/data/`)
   - `GET /imports` - 导入计划列表查询 ✅
   - `GET /imports/{import_batch_id}` - 导入计划详情 ✅
   - `GET /machines` - 机台信息查询 ✅
   - `GET /materials` - 物料信息查询 ✅
   - `GET /statistics` - 系统统计信息 ✅

3. **系统监控接口**
   - `GET /health` - 健康检查 ✅
   - `GET /config` - 配置信息 ✅
   - `GET /` - 系统基础信息 ✅

### 4.2 未实现的核心API接口 ❌

#### 排产算法接口（核心缺失）
- `POST /api/v1/scheduling/start` - 启动排产任务
- `GET /api/v1/scheduling/tasks/{taskId}/status` - 查询排产状态
- `GET /api/v1/scheduling/tasks/{taskId}/gantt` - 甘特图数据

#### 工单管理接口（未实现）
- `GET /api/v1/orders/packing` - 卷包机工单查询
- `GET /api/v1/orders/feeding` - 喂丝机工单查询

#### MES集成接口（未实现）
- `POST /api/v1/mes/export` - 工单导出到MES
- `GET /api/v1/mes/maintenance` - 轮保计划同步

### 4.3 API实现质量评估

#### 优势
- **代码规范**: 遵循FastAPI最佳实践
- **类型安全**: 完整的Pydantic模型验证
- **错误处理**: 详细的异常处理和中文错误信息
- **自动文档**: FastAPI自动生成API文档（/docs）
- **性能优化**: 异步处理和数据库连接池

#### 局限性
- **核心功能缺失**: 排产算法相关接口完全未实现
- **MES集成缺失**: 与外部系统的集成接口未实现
- **前端支持不足**: 缺少前端友好的数据格式

## 5. 实现状态总结

### 5.1 已完成的核心模块

#### 技术基础设施 ✅
- FastAPI框架和应用启动配置
- MySQL数据库异步连接和ORM
- Redis缓存连接和配置管理
- 完整的配置管理系统
- 健康检查和监控接口

#### 数据导入处理 ✅ (完整实现)
- Excel文件上传API
- 复杂Excel解析器（支持多工作表、合并单元格）
- 数据验证和清洗
- 导入批次管理
- 解析结果存储

#### 数据查询服务 ✅
- 分页查询API
- 多维度数据过滤
- 系统统计信息
- RESTful API设计

### 5.2 未实现的关键模块

#### 排产算法引擎 ❌ (核心缺失)
- algorithms文件夹完全为空
- 所有排产算法未实现
- 工单生成逻辑缺失

#### 前端用户界面 ✅ (完整实现)
- Vue.js 3 + TypeScript应用完全实现
- Element Plus UI组件库集成
- 完整的用户交互界面：
  - 响应式导航布局
  - 文件上传和解析流程
  - 统计信息展示
  - 历史记录查询
  - 现代化UI设计
- 状态管理（Pinia）和路由（Vue Router）
- 完善的错误处理和用户反馈
- ❌ 甘特图可视化未实现

#### MES系统集成 ❌
- 外部系统接口未实现
- 数据导出功能缺失

### 5.3 后续开发优先级

#### 高优先级（核心功能）
1. 排产算法引擎开发
2. 工单生成功能
3. ✅ 基础前端界面（已完成）

#### 中优先级（系统集成）
1. MES系统集成
2. 甘特图可视化
3. 用户权限管理

#### 低优先级（系统完善）
1. 报表导出功能
2. 业务规则配置
3. 性能监控优化

这个技术设计文档详细描述了APS智慧排产系统的实际实现状态，为后续开发提供了明确的技术方向和优先级指导。