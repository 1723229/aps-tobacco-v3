# APS智慧排产系统 - 技术设计文档

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

### 1.2 技术栈选择

| 层次 | 技术选型 | 版本要求 | 选择理由 |
|------|----------|----------|----------|
| **前端** | Vue.js 3 + TypeScript | 3.3+ | 组件化开发，类型安全 |
| | Element Plus | 2.3+ | 丰富的UI组件库 |
| | ECharts/G2 | 5.4+ | 甘特图和数据可视化 |
| **后端** | FastAPI | 0.104+ | 高性能异步框架，自动API文档 |
| | SQLAlchemy | 2.0+ | Python ORM，支持异步操作 |
| | Pydantic | 2.5+ | 数据验证和序列化 |
| **数据库** | MySQL | 8.0+ | 事务支持，成熟稳定 |
| | Redis | 7.0+ | 缓存和会话存储 |
| **中间件** | openpyxl | 3.1+ | Excel文件解析 |
| | Celery | 5.3+ | 异步任务队列 |

### 1.3 模块划分

```
aps-cigarette/
├── frontend/                    # 前端模块
│   ├── src/
│   │   ├── components/         # 通用组件
│   │   ├── views/             # 页面组件
│   │   ├── services/          # API服务
│   │   ├── utils/             # 工具类
│   │   └── types/             # TypeScript类型定义
│   └── package.json
├── backend/                # 后端服务
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   └── v1/            # API版本1
│   │   ├── core/              # 核心配置
│   │   ├── db/                # 数据库相关
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic模型
│   │   ├── services/          # 业务服务层
│   │   ├── algorithms/        # 排产算法
│   │   ├── utils/             # 工具函数
│   │   └── main.py            # 应用入口
│   ├── alembic/               # 数据库迁移
│   ├── tests/                 # 测试代码
│   ├── requirements.txt       # 依赖包
│   └── pyproject.toml         # 项目配置
└── aps-database/               # 数据库相关
    ├── seeds/                 # 初始数据
    └── docs/                  # 数据库文档
```

## 2. 数据表结构设计

### 2.1 基础数据表

#### 2.1.1 机台信息表 (aps_machine)

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

#### 2.1.2 物料信息表 (aps_material)

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

#### 2.1.3 机台生产速度配置表 (aps_machine_speed)

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

#### 2.1.4 机台对应关系表 (aps_machine_relation)

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

#### 2.1.5 班次配置表 (aps_shift_config)

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

#### 2.2.1 导入计划表 (aps_import_plan)

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

#### 2.2.2 原始旬计划表 (aps_decade_plan)

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

#### 2.2.3 排产任务表 (aps_scheduling_task)

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

## 4. API接口设计

### 4.1 RESTful API规范

**URL设计规范：**
```
/api/v1/{resource}[/{resource-id}[/{sub-resource}[/{sub-resource-id}]]]
```

**HTTP方法使用：**
- GET：查询数据
- POST：创建数据
- PUT：更新数据（全量更新）
- PATCH：更新数据（部分更新）
- DELETE：删除数据

**状态码规范：**
- 200：成功
- 201：创建成功
- 400：请求参数错误
- 401：未授权
- 403：禁止访问
- 404：资源不存在
- 500：服务器内部错误

### 4.2 核心API接口

#### 4.2.1 文件上传接口

```yaml
POST /api/v1/plans/upload
Content-Type: multipart/form-data

Request:
  file: binary           # Excel文件
  planType: string       # 计划类型：DECADE_PLAN

Response:
  code: 200
  message: "upload success"
  data:
    importBatchId: string
    fileName: string
    fileSize: number
    totalRecords: number
    uploadTime: string
```

#### 4.2.2 数据解析接口

```yaml
POST /api/v1/plans/{importBatchId}/parse

Response:
  code: 200
  message: "parse success"  
  data:
    importBatchId: string
    totalRecords: number
    validRecords: number
    errorRecords: number
    parseResult:
      - record: object
        status: "VALID|WARNING|ERROR"
        message: string
```

#### 4.2.3 排产执行接口

```yaml
POST /api/v1/scheduling/start

Request:
  importBatchId: string
  schedulingParams:
    mergeEnabled: boolean
    splitEnabled: boolean
    correctionEnabled: boolean
    parallelEnabled: boolean

Response:
  code: 200
  message: "scheduling started"
  data:
    taskId: string
    status: "RUNNING"
    progress: 0
```

#### 4.2.4 任务状态查询接口

```yaml
GET /api/v1/scheduling/tasks/{taskId}/status

Response:
  code: 200
  data:
    taskId: string
    status: "PENDING|RUNNING|COMPLETED|FAILED"
    progress: number
    currentStage: string
    startTime: string
    endTime: string
    errorMessage: string
```

#### 4.2.5 工单查询接口

```yaml
GET /api/v1/orders/packing?taskId={taskId}&page={page}&size={size}

Response:
  code: 200
  data:
    content:
      - workOrderNr: string
        articleNr: string
        makerCode: string
        quantityTotal: number
        plannedStart: string
        plannedEnd: string
        orderStatus: string
    totalElements: number
    totalPages: number
    pageable:
      pageNumber: number
      pageSize: number
```

#### 4.2.6 甘特图数据接口

```yaml
GET /api/v1/scheduling/tasks/{taskId}/gantt

Response:
  code: 200
  data:
    timeline:
      start: string        # ISO格式时间
      end: string          # ISO格式时间
    resources:
      - id: string         # 机台代码
        name: string       # 机台名称
        type: "PACKING|FEEDING"
        category: string   # 机台分类
    tasks:
      - id: string         # 工单号
        name: string       # 显示名称
        start: string      # 开始时间
        end: string        # 结束时间
        resource: string   # 关联机台
        color: string      # 显示颜色
        type: string       # 工单类型
        details:
          article: string  # 物料编号
          quantity: number # 数量
          is_split: boolean
          is_merged: boolean
    maintenances:
      - id: string         # 轮保计划号
        name: string       # 轮保名称
        start: string      # 开始时间
        end: string        # 结束时间
        resource: string   # 机台代码
        color: "#e74c3c"   # 红色
        type: "MAINTENANCE"
    relationships:
      parallel_groups:     # 并行任务组
        - feeder: string
          orders: [string]
          type: "PARALLEL"
      serial_chains:       # 串行任务链
        - machine: string
          orders: [string]
          type: "SERIAL"
```

#### 4.2.7 MES导出接口

```yaml
POST /api/v1/mes/export

Request:
  taskId: string
  exportType: "PACKING|FEEDING|ALL"
  exportFormat: "JSON|XML"

Response:
  code: 200
  message: "export success"
  data:
    dispatchBatchId: string
    exportedOrders: number
    exportTime: string
```

### 4.3 数据传输对象(DTO)

#### 4.3.1 卷包机工单DTO

```python
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class PackingOrderDTO(BaseModel):
    work_order_nr: str = Field(..., description="工单号")
    task_id: str = Field(..., description="排产任务ID")
    original_order_nr: Optional[str] = Field(None, description="原始订单号")
    
    # 产品信息
    article_nr: str = Field(..., description="成品烟牌号")
    quantity_total: int = Field(..., description="投料总量")
    final_quantity: int = Field(..., description="成品数量")
    
    # 机台信息
    maker_code: str = Field(..., description="卷包机代码")
    machine_type: Optional[str] = Field(None, description="机台型号")
    
    # 时间信息
    planned_start: datetime = Field(..., description="计划开始时间")
    planned_end: datetime = Field(..., description="计划结束时间")
    estimated_duration: Optional[int] = Field(None, description="预计耗时（分钟）")
    
    # 生产参数
    production_speed: Optional[float] = Field(None, description="生产速度（箱/小时）")
    working_shifts: Optional[Dict[str, Any]] = Field(None, description="工作班次信息")
    
    # 关联信息
    feeder_code: str = Field(..., description="对应喂丝机代码")
    related_feeder_order: Optional[str] = Field(None, description="关联喂丝机工单号")
    
    # 状态信息
    order_status: str = Field(default="PLANNED", description="工单状态")
    priority: int = Field(default=5, description="优先级")
    
    # 特殊标记
    is_split_order: bool = Field(default=False, description="是否为拆分工单")
    split_from: Optional[str] = Field(None, description="拆分来源")
    split_index: Optional[int] = Field(None, description="拆分序号")
    is_merged_order: bool = Field(default=False, description="是否为合并工单")
    merged_from: Optional[List[str]] = Field(None, description="合并来源列表")
    
    # 审计信息
    created_by: str = Field(default="system", description="创建者")
    created_time: datetime = Field(..., description="创建时间")
    updated_time: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### 4.3.2 甘特图数据DTO

```python
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TimelineDTO(BaseModel):
    start: datetime = Field(..., description="开始时间")
    end: datetime = Field(..., description="结束时间")

class ResourceDTO(BaseModel):
    id: str = Field(..., description="机台代码")
    name: str = Field(..., description="机台名称")
    type: str = Field(..., description="机台类型：PACKING|FEEDING")
    category: str = Field(..., description="机台分类")

class TaskDTO(BaseModel):
    id: str = Field(..., description="工单号")
    name: str = Field(..., description="显示名称")
    start: datetime = Field(..., description="开始时间")
    end: datetime = Field(..., description="结束时间")
    resource: str = Field(..., description="关联机台代码")
    color: str = Field(..., description="显示颜色")
    type: str = Field(..., description="工单类型")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")

class MaintenanceDTO(BaseModel):
    id: str = Field(..., description="轮保计划号")
    name: str = Field(..., description="轮保名称")
    start: datetime = Field(..., description="开始时间")
    end: datetime = Field(..., description="结束时间")
    resource: str = Field(..., description="机台代码")
    color: str = Field(default="#e74c3c", description="显示颜色")
    type: str = Field(default="MAINTENANCE", description="类型")

class ParallelGroupDTO(BaseModel):
    feeder: str = Field(..., description="喂丝机代码")
    orders: List[str] = Field(..., description="并行工单列表")
    type: str = Field(default="PARALLEL", description="关系类型")

class SerialChainDTO(BaseModel):
    machine: str = Field(..., description="机台代码")
    orders: List[str] = Field(..., description="串行工单列表")
    type: str = Field(default="SERIAL", description="关系类型")

class RelationshipsDTO(BaseModel):
    parallel_groups: List[ParallelGroupDTO] = Field(default_factory=list, description="并行任务组")
    serial_chains: List[SerialChainDTO] = Field(default_factory=list, description="串行任务链")

class GanttDataDTO(BaseModel):
    timeline: TimelineDTO = Field(..., description="时间轴配置")
    resources: List[ResourceDTO] = Field(..., description="资源列表")
    tasks: List[TaskDTO] = Field(..., description="工单任务列表")
    maintenances: List[MaintenanceDTO] = Field(default_factory=list, description="轮保计划列表")
    relationships: RelationshipsDTO = Field(default_factory=RelationshipsDTO, description="任务关系")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

## 5. 缓存设计

### 5.1 Redis缓存策略

**缓存分层：**
- L1: 应用本地缓存（Caffeine）
- L2: 分布式缓存（Redis）

**缓存键命名规范：**
```
aps:{模块}:{功能}:{标识}:{版本}
```

**示例：**
```
aps:machine:speed:JJ#01:PA:v1
aps:scheduling:task:status:task123:v1
aps:maintenance:plans:2024-08-15:v1
```

### 5.2 缓存对象设计

#### 5.2.1 机台速度缓存

```python
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
import redis
import json

class MachineSpeedCache(BaseModel):
    machine_code: str = Field(..., description="机台代码")
    article_nr: str = Field(..., description="物料编号")
    speed: float = Field(..., description="生产速度（箱/小时）")
    efficiency_rate: float = Field(..., description="效率系数（%）")
    effective_from: date = Field(..., description="生效日期")
    effective_to: Optional[date] = Field(None, description="失效日期")
    cache_time: datetime = Field(default_factory=datetime.now, description="缓存时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

    @classmethod
    def get_cache_key(cls, machine_code: str, article_nr: str) -> str:
        return f"aps:machine:speed:{machine_code}:{article_nr}:v1"

    def to_cache(self, redis_client: redis.Redis, ttl: int = 3600):
        """保存到Redis缓存"""
        key = self.get_cache_key(self.machine_code, self.article_nr)
        redis_client.setex(
            key, 
            ttl, 
            self.json(ensure_ascii=False)
        )

    @classmethod
    def from_cache(cls, redis_client: redis.Redis, machine_code: str, article_nr: str) -> Optional['MachineSpeedCache']:
        """从Redis缓存读取"""
        key = cls.get_cache_key(machine_code, article_nr)
        data = redis_client.get(key)
        if data:
            return cls.parse_raw(data)
        return None
```

#### 5.2.2 排产任务状态缓存

```python
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import redis

class SchedulingTaskStatusCache(BaseModel):
    task_id: str = Field(..., description="任务ID")
    task_status: str = Field(..., description="任务状态")
    progress: int = Field(default=0, description="进度百分比")
    current_stage: Optional[str] = Field(None, description="当前阶段")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    result_summary: Optional[Dict[str, Any]] = Field(None, description="结果摘要")
    cache_time: datetime = Field(default_factory=datetime.now, description="缓存时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def get_cache_key(cls, task_id: str) -> str:
        return f"aps:scheduling:task:{task_id}:v1"

    def to_cache(self, redis_client: redis.Redis, ttl: int = 7200):
        """保存到Redis缓存"""
        key = self.get_cache_key(self.task_id)
        redis_client.setex(
            key,
            ttl,
            self.json(ensure_ascii=False)
        )

    @classmethod
    def from_cache(cls, redis_client: redis.Redis, task_id: str) -> Optional['SchedulingTaskStatusCache']:
        """从Redis缓存读取"""
        key = cls.get_cache_key(task_id)
        data = redis_client.get(key)
        if data:
            return cls.parse_raw(data)
        return None
```

### 5.3 缓存更新策略

**更新触发时机：**
- 数据库写操作后
- 定时刷新（凌晨刷新基础数据）
- 手工刷新（管理界面触发）

**缓存失效策略：**
- TTL过期自动失效
- 数据变更主动失效
- 版本控制失效

## 6. 性能优化设计

### 6.1 数据库性能优化

**分区策略：**
```sql
-- 按月分区大表
CREATE TABLE aps_decade_plan (
    -- 字段定义...
) PARTITION BY RANGE (YEAR(planned_start) * 100 + MONTH(planned_start)) (
    PARTITION p202408 VALUES LESS THAN (202409),
    PARTITION p202409 VALUES LESS THAN (202410),
    PARTITION p202410 VALUES LESS THAN (202411),
    -- 更多分区...
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

**读写分离：**
- 主库：写操作
- 从库：读操作
- 使用@Transactional(readOnly = true)标记只读事务

**连接池优化：**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
```

### 6.2 应用性能优化

**异步处理：**
```python
from celery import Celery
import asyncio
from fastapi import BackgroundTasks

app = Celery('aps_scheduler')

@app.task
async def execute_scheduling_task(task_id: str) -> dict:
    """异步执行排产算法"""
    try:
        # 排产算法执行
        result = await scheduling_service.execute_scheduling(task_id)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# FastAPI后台任务
async def schedule_in_background(background_tasks: BackgroundTasks, task_id: str):
    background_tasks.add_task(execute_scheduling_async, task_id)
```

**批量操作：**
```python
from sqlalchemy.orm import Session
from typing import List

async def save_batch_orders(db: Session, orders: List[PackingOrder], batch_size: int = 1000):
    """批量保存工单"""
    for i in range(0, len(orders), batch_size):
        batch = orders[i:i + batch_size]
        db.add_all(batch)
        await db.commit()

async def bulk_insert_with_sqlalchemy(db: Session, orders: List[dict]):
    """使用SQLAlchemy批量插入"""
    await db.execute(
        PackingOrder.__table__.insert(),
        orders
    )
    await db.commit()
```

**分页查询优化：**
```python
from sqlalchemy import and_, desc
from typing import Optional

async def find_orders_with_cursor_pagination(
    db: Session, 
    cursor: Optional[str] = None, 
    limit: int = 20
) -> List[PackingOrder]:
    """使用游标分页替代offset分页"""
    query = db.query(PackingOrder)
    
    if cursor:
        # 解析游标获取上次查询的最后一条记录ID
        last_id = int(cursor)
        query = query.filter(PackingOrder.id > last_id)
    
    return query.order_by(PackingOrder.id).limit(limit).all()
```

## 7. 安全设计

### 7.1 数据安全

**敏感数据加密：**
```python
from cryptography.fernet import Fernet
import base64
import os

class DataEncryption:
    def __init__(self):
        # 从环境变量或配置文件获取密钥
        key = os.getenv('ENCRYPTION_KEY', self._generate_key())
        self.cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)
    
    def _generate_key(self) -> str:
        """生成加密密钥"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

# 使用示例
encryption = DataEncryption()
encrypted_password = encryption.encrypt_sensitive_data("sensitive_info")
```

**SQL注入防护：**
```python
from sqlalchemy.orm import Session
from sqlalchemy import text

# 使用参数化查询
async def safe_query_with_params(db: Session, machine_code: str):
    """安全的参数化查询"""
    result = await db.execute(
        text("SELECT * FROM aps_machine WHERE machine_code = :code"),
        {"code": machine_code}
    )
    return result.fetchall()

# 使用SQLAlchemy ORM（自动防护）
async def safe_orm_query(db: Session, machine_code: str):
    """使用ORM的安全查询"""
    return db.query(Machine).filter(Machine.machine_code == machine_code).all()

# 输入验证
from pydantic import BaseModel, validator

class MachineQueryRequest(BaseModel):
    machine_code: str
    
    @validator('machine_code')
    def validate_machine_code(cls, v):
        # 验证机台代码格式
        if not v.replace('#', '').replace('-', '').isalnum():
            raise ValueError('Invalid machine code format')
        return v
```

### 7.2 访问控制（后续扩展）

**预留接口设计：**
```python
from abc import ABC, abstractmethod
from typing import List

class SecurityService(ABC):
    """安全服务抽象类"""
    
    @abstractmethod
    async def has_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户权限"""
        pass
    
    @abstractmethod
    async def get_user_roles(self, user_id: str) -> List[str]:
        """获取用户角色列表"""
        pass
    
    @abstractmethod
    async def is_operation_allowed(self, operation: str) -> bool:
        """检查操作是否允许"""
        pass

# 实现类（后续扩展）
class DefaultSecurityService(SecurityService):
    async def has_permission(self, user_id: str, resource: str, action: str) -> bool:
        # TODO: 实现权限检查逻辑
        return True  # 暂时允许所有操作
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        # TODO: 实现角色获取逻辑
        return ["admin"]  # 暂时返回管理员角色
    
    async def is_operation_allowed(self, operation: str) -> bool:
        # TODO: 实现操作检查逻辑
        return True  # 暂时允许所有操作
```

这个技术设计文档详细描述了APS智慧排产系统的数据表结构设计、API接口规范、缓存策略、性能优化方案等技术实现细节，完全基于PRD中的业务需求和实际的数据结构进行设计，确保技术方案与业务需求完全匹配。