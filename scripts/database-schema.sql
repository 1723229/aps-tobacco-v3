-- ========================================
-- APS智慧排产系统 数据库初始化脚本
-- 版本: v1.0.0
-- 创建日期: 2025-08-15
-- 说明: 包含表结构创建和基础数据初始化
-- ========================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 创建数据库（如果不存在）
-- CREATE DATABASE IF NOT EXISTS aps_cigarette DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE aps_cigarette;

-- ========================================
-- 1. 基础数据表
-- ========================================

-- 1.1 机台信息表
DROP TABLE IF EXISTS aps_machine;
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
) COMMENT='机台基础信息表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.2 物料信息表
DROP TABLE IF EXISTS aps_material;
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
) COMMENT='物料基础信息表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.3 机台生产速度配置表
DROP TABLE IF EXISTS aps_machine_speed;
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
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status)
) COMMENT='机台生产速度配置表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.4 机台对应关系表
DROP TABLE IF EXISTS aps_machine_relation;
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
    
    UNIQUE KEY uk_feeder_maker_date (feeder_code, maker_code, effective_from),
    INDEX idx_feeder_code (feeder_code),
    INDEX idx_maker_code (maker_code),
    INDEX idx_effective_date (effective_from, effective_to),
    INDEX idx_status (status)
) COMMENT='喂丝机与卷包机对应关系表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.5 班次配置表
DROP TABLE IF EXISTS aps_shift_config;
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
) COMMENT='班次配置表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.6 工单号序列表
DROP TABLE IF EXISTS aps_work_order_sequence;
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
) COMMENT='工单号序列表（支持MES规范：H+工单类型+9位流水号）' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 2. 业务数据表
-- ========================================

-- 2.1 导入计划表
DROP TABLE IF EXISTS aps_import_plan;
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
) COMMENT='计划导入记录表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2.2 原始旬计划表
DROP TABLE IF EXISTS aps_decade_plan;
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
    
    INDEX idx_import_batch (import_batch_id),
    INDEX idx_work_order (work_order_nr),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_validation_status (validation_status)
) COMMENT='原始卷包旬计划表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2.3 排产任务表
DROP TABLE IF EXISTS aps_scheduling_task;
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
    INDEX idx_task_status (task_status),
    INDEX idx_created_time (created_time)
) COMMENT='排产任务表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2.4 排产处理日志表
DROP TABLE IF EXISTS aps_processing_log;
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
    
    INDEX idx_task_stage (task_id, stage),
    INDEX idx_log_level (log_level),
    INDEX idx_execution_time (execution_time)
) COMMENT='排产处理日志表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 3. 结果数据表
-- ========================================

-- 3.1 卷包机工单表
DROP TABLE IF EXISTS aps_packing_order;
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
    production_speed INT COMMENT '生产速度（支/分钟）',
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
    INDEX idx_task_id (task_id),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_maker_code (maker_code),
    INDEX idx_order_status (order_status),
    INDEX idx_priority (priority)
) COMMENT='卷包机工单表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3.2 喂丝机工单表
DROP TABLE IF EXISTS aps_feeding_order;
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
    INDEX idx_task_id (task_id),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_feeder_code (feeder_code),
    INDEX idx_order_status (order_status),
    INDEX idx_priority (priority)
) COMMENT='喂丝机工单表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 4. MES集成数据表
-- ========================================

-- 4.1 工单输入批次关联表
DROP TABLE IF EXISTS aps_input_batch;
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
) COMMENT='工单输入批次关联表（支持MES InputBatch结构）' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4.2 轮保计划表
DROP TABLE IF EXISTS aps_maintenance_plan;
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
    INDEX idx_schedule_date (schedule_date),
    INDEX idx_machine_code (machine_code),
    INDEX idx_maint_time (maint_start_time, maint_end_time),
    INDEX idx_plan_status (plan_status)
) COMMENT='设备轮保计划表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4.3 MES工单下发记录表
DROP TABLE IF EXISTS aps_mes_dispatch;
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
) COMMENT='MES工单下发记录表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4.3 工单状态同步表
DROP TABLE IF EXISTS aps_order_status_sync;
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
) COMMENT='工单状态同步表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 5. 系统配置表
-- ========================================

-- 5.1 系统参数配置表
DROP TABLE IF EXISTS aps_system_config;
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
) COMMENT='系统参数配置表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5.2 业务规则配置表
DROP TABLE IF EXISTS aps_business_rule;
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
) COMMENT='业务规则配置表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 6. 操作审计表
-- ========================================

-- 6.1 系统操作日志表
DROP TABLE IF EXISTS aps_operation_log;
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
) COMMENT='系统操作日志表' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ========================================
-- 7. 基础数据初始化
-- ========================================

-- 7.1 初始化机台信息
INSERT INTO aps_machine (machine_code, machine_name, machine_type, equipment_type, production_line, status) VALUES
-- 卷包机
('A1', '卷包机A1', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A2', '卷包机A2', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A3', '卷包机A3', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A4', '卷包机A4', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A5', '卷包机A5', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A6', '卷包机A6', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A7', '卷包机A7', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A8', '卷包机A8', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('A9', '卷包机A9', 'PACKING', 'PROTOS70', 'A线', 'ACTIVE'),
('B1', '卷包机B1', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B2', '卷包机B2', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B3', '卷包机B3', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B4', '卷包机B4', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B5', '卷包机B5', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B6', '卷包机B6', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B7', '卷包机B7', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('B8', '卷包机B8', 'PACKING', 'M8', 'B线', 'ACTIVE'),
('C1', '卷包机C1', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C2', '卷包机C2', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C3', '卷包机C3', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C4', '卷包机C4', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C5', '卷包机C5', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C6', '卷包机C6', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C7', '卷包机C7', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C8', '卷包机C8', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C9', '卷包机C9', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C10', '卷包机C10', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C11', '卷包机C11', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('C12', '卷包机C12', 'PACKING', 'PROTOS70', 'C线', 'ACTIVE'),
('D1', '卷包机D1', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D2', '卷包机D2', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D3', '卷包机D3', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D4', '卷包机D4', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D5', '卷包机D5', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D6', '卷包机D6', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D7', '卷包机D7', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D8', '卷包机D8', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D9', '卷包机D9', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D10', '卷包机D10', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D11', '卷包机D11', 'PACKING', 'M8', 'D线', 'ACTIVE'),
('D12', '卷包机D12', 'PACKING', 'M8', 'D线', 'ACTIVE'),

-- 喂丝机
('1', '喂丝机1', 'FEEDING', 'YF-100', '喂丝线1', 'ACTIVE'),
('2', '喂丝机2', 'FEEDING', 'YF-100', '喂丝线2', 'ACTIVE'),
('3', '喂丝机3', 'FEEDING', 'YF-100', '喂丝线3', 'ACTIVE'),
('4', '喂丝机4', 'FEEDING', 'YF-100', '喂丝线4', 'ACTIVE'),
('5', '喂丝机5', 'FEEDING', 'YF-100', '喂丝线5', 'ACTIVE'),
('6', '喂丝机6', 'FEEDING', 'YF-100', '喂丝线6', 'ACTIVE'),
('7', '喂丝机7', 'FEEDING', 'YF-100', '喂丝线7', 'ACTIVE'),
('8', '喂丝机8', 'FEEDING', 'YF-100', '喂丝线8', 'ACTIVE'),
('9', '喂丝机9', 'FEEDING', 'YF-100', '喂丝线9', 'ACTIVE'),
('10', '喂丝机10', 'FEEDING', 'YF-100', '喂丝线10', 'ACTIVE'),
('11', '喂丝机11', 'FEEDING', 'YF-100', '喂丝线11', 'ACTIVE'),
('12', '喂丝机12', 'FEEDING', 'YF-100', '喂丝线12', 'ACTIVE'),
('13', '喂丝机13', 'FEEDING', 'YF-100', '喂丝线13', 'ACTIVE'),
('14', '喂丝机14', 'FEEDING', 'YF-100', '喂丝线14', 'ACTIVE'),
('15', '喂丝机15', 'FEEDING', 'YF-100', '喂丝线15', 'ACTIVE'),
('16', '喂丝机16', 'FEEDING', 'YF-100', '喂丝线16', 'ACTIVE'),
('17', '喂丝机17', 'FEEDING', 'YF-100', '喂丝线17', 'ACTIVE'),
('18', '喂丝机18', 'FEEDING', 'YF-100', '喂丝线18', 'ACTIVE'),
('19', '喂丝机19', 'FEEDING', 'YF-100', '喂丝线19', 'ACTIVE'),
('20', '喂丝机20', 'FEEDING', 'YF-100', '喂丝线20', 'ACTIVE'),
('21', '喂丝机21', 'FEEDING', 'YF-100', '喂丝线21', 'ACTIVE'),
('22', '喂丝机22', 'FEEDING', 'YF-100', '喂丝线22', 'ACTIVE'),
('23', '喂丝机23', 'FEEDING', 'YF-100', '喂丝线23', 'ACTIVE'),
('24', '喂丝机24', 'FEEDING', 'YF-100', '喂丝线24', 'ACTIVE'),
('25', '喂丝机25', 'FEEDING', 'YF-100', '喂丝线25', 'ACTIVE'),
('26', '喂丝机26', 'FEEDING', 'YF-100', '喂丝线26', 'ACTIVE'),
('27', '喂丝机27', 'FEEDING', 'YF-100', '喂丝线27', 'ACTIVE'),
('28', '喂丝机28', 'FEEDING', 'YF-100', '喂丝线28', 'ACTIVE'),
('29', '喂丝机29', 'FEEDING', 'YF-100', '喂丝线29', 'ACTIVE'),
('30', '喂丝机30', 'FEEDING', 'YF-100', '喂丝线30', 'ACTIVE'),
('31', '喂丝机31', 'FEEDING', 'YF-100', '喂丝线31', 'ACTIVE'),
('32', '喂丝机32', 'FEEDING', 'YF-100', '喂丝线32', 'ACTIVE');

-- 7.2 初始化物料信息
INSERT INTO aps_material (article_nr, article_name, material_type, package_type, specification, unit, conversion_rate, status) VALUES
-- 成品烟
('利群(软红长嘴)', '利群(软红长嘴)', 'FINISHED_PRODUCT', '软包', '长嘴', '箱', 1.5200, 'ACTIVE'),
('利群(软长嘴)', '利群(软长嘴)', 'FINISHED_PRODUCT', '软包', '长嘴', '箱', 1.4300, 'ACTIVE'),
('利群(软金色阳光)', '利群(软金色阳光)', 'FINISHED_PRODUCT', '软包', '长嘴', '箱', 1.4400, 'ACTIVE'),
('利群(软蓝)', '利群(软蓝)', 'FINISHED_PRODUCT', '软包', '短嘴', '箱', 1.4700, 'ACTIVE'),
('利群(新版)', '利群(新版)', 'FINISHED_PRODUCT', '硬包', '短嘴', '箱', 1.6100, 'ACTIVE'),
('利群(长嘴)', '利群(长嘴)', 'FINISHED_PRODUCT', '硬包', '长嘴', '箱', 1.5600, 'ACTIVE'),
('利群(硬)', '利群(硬)', 'FINISHED_PRODUCT', '硬包', '长嘴', '箱', 1.4900, 'ACTIVE'),
('利群(阳光)', '利群(阳光)', 'FINISHED_PRODUCT', '硬包', '超长嘴', '箱', 1.4800, 'ACTIVE'),
('利群(阳光橙中支)', '利群(阳光橙中支)', 'FINISHED_PRODUCT', '硬包', '中支', '箱', 1.7700, 'ACTIVE'),
('利群(西子阳光)', '利群(西子阳光)', 'FINISHED_PRODUCT', '硬包', '细支', '箱', 2.5200, 'ACTIVE'),
('利群(阳光尊细支)', '利群(阳光尊细支)', 'FINISHED_PRODUCT', '硬包', '细支', '箱', 2.3300, 'ACTIVE'),
('利群(休闲细支)', '利群(休闲细支)', 'FINISHED_PRODUCT', '硬包', '细支', '箱', 2.0700, 'ACTIVE'),
('利群(西湖恋)', '利群(西湖恋)', 'FINISHED_PRODUCT', '硬包', '细支', '箱', 1.8900, 'ACTIVE'),
('利群(江南韵)', '利群(江南韵)', 'FINISHED_PRODUCT', '硬包', '细支', '箱', 2.0000, 'ACTIVE');

-- 7.3 初始化机台对应关系（基于提供的对应关系表）
INSERT INTO aps_machine_relation (feeder_code, maker_code, relation_type, priority, effective_from, status) VALUES
('1', 'D3', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('2', 'D1', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('3', 'D4', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('4', 'C8', 'ONE_TO_MANY', 1, '2024-01-01', 'ACTIVE'),
('4', 'C9', 'ONE_TO_MANY', 2, '2024-01-01', 'ACTIVE'),
('5', 'B4', 'ONE_TO_MANY', 1, '2024-01-01', 'ACTIVE'),
('5', 'B5', 'ONE_TO_MANY', 2, '2024-01-01', 'ACTIVE'),
('6', 'B3', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('7', 'C10', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('8', 'B8', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('9', 'A4', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('10', 'A6', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('11', 'A5', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('12', 'B2', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('13', 'C6', 'ONE_TO_MANY', 1, '2024-01-01', 'ACTIVE'),
('13', 'C7', 'ONE_TO_MANY', 2, '2024-01-01', 'ACTIVE'),
('14', 'C2', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('15', 'A3', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('16', 'A1', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('17', 'A2', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('18', 'C1', 'ONE_TO_MANY', 1, '2024-01-01', 'ACTIVE'),
('18', 'C3', 'ONE_TO_MANY', 2, '2024-01-01', 'ACTIVE'),
('19', 'C5', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('20', 'B1', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('21', 'B7', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('22', 'A7', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('23', 'A8', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('24', 'C12', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('25', 'A9', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('26', 'D6', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('27', 'D2', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('28', 'D4', 'ONE_TO_MANY', 1, '2024-01-01', 'ACTIVE'),
('28', 'D5', 'ONE_TO_MANY', 2, '2024-01-01', 'ACTIVE'),
('29', 'C11', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('30', 'D7', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('31', 'D1', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE'),
('32', 'D12', 'ONE_TO_ONE', 1, '2024-01-01', 'ACTIVE');

-- 7.4 初始化机台生产速度配置（基于PRD 3.1，箱/小时）
INSERT INTO aps_machine_speed (machine_code, article_nr, speed, efficiency_rate, effective_from, status) VALUES
-- 通用速度（8.0箱/小时）
('*', '*', 8.0, 85.00, '2024-01-01', 'ACTIVE'),
-- A线机台速度配置（18.0箱/小时）
('A01', '*', 18.0, 85.00, '2024-01-01', 'ACTIVE'),
('A02', '*', 18.0, 85.00, '2024-01-01', 'ACTIVE'),
('A03', '*', 18.0, 85.00, '2024-01-01', 'ACTIVE'),
('A04', '*', 18.0, 85.00, '2024-01-01', 'ACTIVE'),
('A05', '*', 18.0, 85.00, '2024-01-01', 'ACTIVE'),
('A09', '*', 7.0, 85.00, '2024-01-01', 'ACTIVE'),
-- B线机台速度配置
('B01', '*', 11.0, 85.00, '2024-01-01', 'ACTIVE'),
('B02', '*', 11.0, 85.00, '2024-01-01', 'ACTIVE'),
('B03', '*', 11.0, 85.00, '2024-01-01', 'ACTIVE'),
('B04', '*', 9.0, 85.00, '2024-01-01', 'ACTIVE'),
('B05', '*', 9.0, 85.00, '2024-01-01', 'ACTIVE'),
('B06', '*', 9.0, 85.00, '2024-01-01', 'ACTIVE'),
('B07', '*', 9.0, 85.00, '2024-01-01', 'ACTIVE'),
('B08', '*', 9.0, 85.00, '2024-01-01', 'ACTIVE'),
('B12', '*', 11.0, 85.00, '2024-01-01', 'ACTIVE'),
-- C线机台速度配置
('C12', '*', 3.0, 85.00, '2024-01-01', 'ACTIVE'),
-- D线机台速度配置
('D01', '*', 7.15, 85.00, '2024-01-01', 'ACTIVE'),
('D02', '*', 6.8, 85.00, '2024-01-01', 'ACTIVE'),
('D03', '*', 6.8, 85.00, '2024-01-01', 'ACTIVE'),
('D04', '*', 7.15, 85.00, '2024-01-01', 'ACTIVE'),
('D05', '*', 7.15, 85.00, '2024-01-01', 'ACTIVE'),
('D06', '*', 6.1, 85.00, '2024-01-01', 'ACTIVE'),
('D07', '*', 7.15, 85.00, '2024-01-01', 'ACTIVE');

-- 7.5 初始化班次配置（按PRD规范）
INSERT INTO aps_shift_config (shift_name, machine_name, start_time, end_time, is_ot_needed, max_ot_duration, effective_from, status) VALUES
('早班', '*', '06:40:00', '15:40:00', FALSE, NULL, '2024-01-01', 'ACTIVE'),
('中班', '*', '15:40:00', '24:00:00', TRUE, '01:00:00', '2024-01-01', 'ACTIVE');

-- 7.6 初始化系统配置参数
INSERT INTO aps_system_config (config_key, config_value, config_type, config_group, config_description, status) VALUES
('scheduling.merge.enabled', 'true', 'BOOLEAN', 'SCHEDULING', '是否启用合并算法', 'ACTIVE'),
('scheduling.split.enabled', 'true', 'BOOLEAN', 'SCHEDULING', '是否启用拆分算法', 'ACTIVE'),
('scheduling.correction.enabled', 'true', 'BOOLEAN', 'SCHEDULING', '是否启用校正算法', 'ACTIVE'),
('scheduling.parallel.enabled', 'true', 'BOOLEAN', 'SCHEDULING', '是否启用并行算法', 'ACTIVE'),
('scheduling.timeout.seconds', '600', 'INTEGER', 'SCHEDULING', '排产算法超时时间（秒）', 'ACTIVE'),
('scheduling.batch.size', '1000', 'INTEGER', 'SCHEDULING', '批处理大小', 'ACTIVE'),
('file.upload.max.size', '10485760', 'INTEGER', 'FILE', '文件上传最大大小（字节）', 'ACTIVE'),
('file.upload.allowed.types', '.xlsx', 'STRING', 'FILE', '允许上传的文件类型', 'ACTIVE'),
('safety.stock.ratio', '0.05', 'DECIMAL', 'PRODUCTION', '安全库存比率', 'ACTIVE'),
('min.interval.minutes', '15', 'INTEGER', 'PRODUCTION', '工单间最小间隔时间（分钟）', 'ACTIVE'),
('mes.api.timeout', '30000', 'INTEGER', 'MES', 'MES接口超时时间（毫秒）', 'ACTIVE'),
('mes.retry.max.count', '3', 'INTEGER', 'MES', 'MES接口最大重试次数', 'ACTIVE'),
('cache.ttl.machine.speed', '3600', 'INTEGER', 'CACHE', '机台速度缓存TTL（秒）', 'ACTIVE'),
('cache.ttl.maintenance.plans', '7200', 'INTEGER', 'CACHE', '轮保计划缓存TTL（秒）', 'ACTIVE');

-- 7.7 初始化业务规则配置
INSERT INTO aps_business_rule (rule_code, rule_name, rule_type, rule_description, rule_parameters, priority, effective_from, status) VALUES
('MERGE_001', '旬计划合并规则', 'MERGE', '同月份、同牌号、同机台的旬计划进行合并', 
 '{"conditions": ["same_month", "same_article", "same_maker", "same_feeder"]}', 1, '2024-01-01', 'ACTIVE'),
('SPLIT_001', '工单拆分规则', 'SPLIT', '一个喂丝机对应多台卷包机时进行拆分', 
 '{"trigger": "one_to_many_relation", "allocation_method": "average"}', 1, '2024-01-01', 'ACTIVE'),
('PARALLEL_001', '并行约束规则', 'PARALLEL', '同一工单下的所有卷包机同时开始同时结束', 
 '{"constraint": "same_start_end_time", "scope": "same_original_order"}', 1, '2024-01-01', 'ACTIVE'),
('TIME_001', '时间校正规则', 'TIME_CORRECTION', '考虑轮保时间进行时间校正', 
 '{"factors": ["maintenance_plan", "shift_schedule"], "adjustment_method": "avoid_conflict"}', 1, '2024-01-01', 'ACTIVE'),
('BACKUP_001', '备用工单规则', 'BACKUP', '特殊牌号生成备用工单', 
 '{"special_articles": ["利群（新版印尼）"], "action": "create_backup"}', 1, '2024-01-01', 'ACTIVE');

-- ========================================
-- 8. 创建外键约束（在数据初始化后添加）
-- ========================================

-- 添加外键约束
ALTER TABLE aps_machine_speed ADD CONSTRAINT fk_machine_speed_machine 
    FOREIGN KEY (machine_code) REFERENCES aps_machine(machine_code) ON DELETE CASCADE;

ALTER TABLE aps_machine_speed ADD CONSTRAINT fk_machine_speed_material 
    FOREIGN KEY (article_nr) REFERENCES aps_material(article_nr) ON DELETE CASCADE;

ALTER TABLE aps_machine_relation ADD CONSTRAINT fk_feeder 
    FOREIGN KEY (feeder_code) REFERENCES aps_machine(machine_code) ON DELETE CASCADE;

ALTER TABLE aps_machine_relation ADD CONSTRAINT fk_maker 
    FOREIGN KEY (maker_code) REFERENCES aps_machine(machine_code) ON DELETE CASCADE;

ALTER TABLE aps_decade_plan ADD CONSTRAINT fk_decade_plan_import 
    FOREIGN KEY (import_batch_id) REFERENCES aps_import_plan(import_batch_id) ON DELETE CASCADE;

ALTER TABLE aps_decade_plan ADD CONSTRAINT fk_decade_plan_material 
    FOREIGN KEY (article_nr) REFERENCES aps_material(article_nr) ON DELETE RESTRICT;

ALTER TABLE aps_scheduling_task ADD CONSTRAINT fk_scheduling_import 
    FOREIGN KEY (import_batch_id) REFERENCES aps_import_plan(import_batch_id) ON DELETE CASCADE;

ALTER TABLE aps_processing_log ADD CONSTRAINT fk_log_task 
    FOREIGN KEY (task_id) REFERENCES aps_scheduling_task(task_id) ON DELETE CASCADE;

ALTER TABLE aps_packing_order ADD CONSTRAINT fk_packing_task 
    FOREIGN KEY (task_id) REFERENCES aps_scheduling_task(task_id) ON DELETE CASCADE;

ALTER TABLE aps_packing_order ADD CONSTRAINT fk_packing_material 
    FOREIGN KEY (article_nr) REFERENCES aps_material(article_nr) ON DELETE RESTRICT;

ALTER TABLE aps_packing_order ADD CONSTRAINT fk_packing_maker 
    FOREIGN KEY (maker_code) REFERENCES aps_machine(machine_code) ON DELETE RESTRICT;

ALTER TABLE aps_feeding_order ADD CONSTRAINT fk_feeding_task 
    FOREIGN KEY (task_id) REFERENCES aps_scheduling_task(task_id) ON DELETE CASCADE;

ALTER TABLE aps_feeding_order ADD CONSTRAINT fk_feeding_material 
    FOREIGN KEY (article_nr) REFERENCES aps_material(article_nr) ON DELETE RESTRICT;

ALTER TABLE aps_feeding_order ADD CONSTRAINT fk_feeding_feeder 
    FOREIGN KEY (feeder_code) REFERENCES aps_machine(machine_code) ON DELETE RESTRICT;

ALTER TABLE aps_maintenance_plan ADD CONSTRAINT fk_maint_machine 
    FOREIGN KEY (machine_code) REFERENCES aps_machine(machine_code) ON DELETE RESTRICT;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- ========================================
-- 9. 创建视图
-- ========================================

-- 9.1 机台关系视图
CREATE OR REPLACE VIEW v_machine_relation AS
SELECT 
    mr.id,
    mr.feeder_code,
    fm.machine_name AS feeder_name,
    mr.maker_code,
    mm.machine_name AS maker_name,
    mr.relation_type,
    mr.priority,
    mr.effective_from,
    mr.effective_to,
    mr.status
FROM aps_machine_relation mr
LEFT JOIN aps_machine fm ON mr.feeder_code = fm.machine_code
LEFT JOIN aps_machine mm ON mr.maker_code = mm.machine_code
WHERE mr.status = 'ACTIVE';

-- 9.2 机台速度配置视图
CREATE OR REPLACE VIEW v_machine_speed AS
SELECT 
    ms.id,
    ms.machine_code,
    m.machine_name,
    m.machine_type,
    ms.article_nr,
    mt.article_name,
    ms.speed,
    ms.efficiency_rate,
    ms.effective_from,
    ms.effective_to,
    ms.status
FROM aps_machine_speed ms
LEFT JOIN aps_machine m ON ms.machine_code = m.machine_code
LEFT JOIN aps_material mt ON ms.article_nr = mt.article_nr
WHERE ms.status = 'ACTIVE';

-- 9.3 工单汇总视图
CREATE OR REPLACE VIEW v_order_summary AS
SELECT 
    st.task_id,
    st.task_name,
    st.task_status,
    st.created_time AS task_created_time,
    COUNT(po.id) AS packing_order_count,
    COUNT(fo.id) AS feeding_order_count,
    SUM(po.quantity_total) AS total_packing_quantity,
    SUM(fo.quantity_total) AS total_feeding_quantity
FROM aps_scheduling_task st
LEFT JOIN aps_packing_order po ON st.task_id = po.task_id
LEFT JOIN aps_feeding_order fo ON st.task_id = fo.task_id
GROUP BY st.task_id, st.task_name, st.task_status, st.created_time;

-- ========================================
-- 10. 创建存储过程
-- ========================================

-- 10.1 清理过期数据存储过程
DELIMITER $$

CREATE PROCEDURE sp_cleanup_expired_data(IN days_to_keep INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- 清理过期的导入记录
    DELETE FROM aps_import_plan 
    WHERE created_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY)
    AND import_status IN ('COMPLETED', 'FAILED');

    -- 清理过期的处理日志
    DELETE FROM aps_processing_log 
    WHERE execution_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);

    -- 清理过期的操作日志
    DELETE FROM aps_operation_log 
    WHERE operation_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);

    -- 清理过期的MES下发记录
    DELETE FROM aps_mes_dispatch 
    WHERE created_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY)
    AND dispatch_status IN ('DISPATCHED', 'CONFIRMED');

    COMMIT;
    
    SELECT CONCAT('清理完成，保留近 ', days_to_keep, ' 天的数据') AS result;
END$$

DELIMITER ;

-- ========================================
-- 11. 创建定时任务（可选，需要事件调度器支持）
-- ========================================

-- 启用事件调度器（如果需要）
-- SET GLOBAL event_scheduler = ON;

-- 创建定期清理任务
-- CREATE EVENT IF NOT EXISTS e_cleanup_expired_data
-- ON SCHEDULE EVERY 1 DAY STARTS '2024-08-16 02:00:00'
-- DO
--   CALL sp_cleanup_expired_data(90);

-- ========================================
-- 12. 索引优化建议
-- ========================================

-- 为经常查询的组合字段创建复合索引
CREATE INDEX idx_decade_plan_composite ON aps_decade_plan(import_batch_id, validation_status, planned_start);
CREATE INDEX idx_packing_order_composite ON aps_packing_order(task_id, order_status, planned_start);
CREATE INDEX idx_feeding_order_composite ON aps_feeding_order(task_id, order_status, planned_start);

-- 为JSON字段中的常用查询路径创建虚拟索引（MySQL 8.0+）
-- ALTER TABLE aps_packing_order ADD processing_stage VARCHAR(50) AS (JSON_UNQUOTE(JSON_EXTRACT(processing_history, '$.current_stage'))) VIRTUAL;
-- CREATE INDEX idx_packing_processing_stage ON aps_packing_order(processing_stage);

-- ========================================
-- 初始化完成
-- ========================================

SELECT '========================================' AS '';
SELECT 'APS智慧排产系统数据库初始化完成' AS 'INITIALIZATION COMPLETED';
SELECT '========================================' AS '';
SELECT CONCAT('机台数量: ', (SELECT COUNT(*) FROM aps_machine)) AS 'Statistics';
SELECT CONCAT('物料数量: ', (SELECT COUNT(*) FROM aps_material)) AS '';
SELECT CONCAT('机台关系: ', (SELECT COUNT(*) FROM aps_machine_relation)) AS '';
SELECT CONCAT('速度配置: ', (SELECT COUNT(*) FROM aps_machine_speed)) AS '';
SELECT CONCAT('班次配置: ', (SELECT COUNT(*) FROM aps_shift_config)) AS '';
SELECT CONCAT('系统配置: ', (SELECT COUNT(*) FROM aps_system_config)) AS '';
SELECT CONCAT('业务规则: ', (SELECT COUNT(*) FROM aps_business_rule)) AS '';
SELECT '========================================' AS '';

-- 显示数据库表信息
SHOW TABLES;