-- =============================================================================
-- APS智慧排产系统 - 月计划数据库模式
-- =============================================================================
-- 目的: 为月计划Excel直接排产功能创建完全独立的数据表结构
-- 冲突避免: 使用 aps_monthly_* 表前缀，与现有 aps_decade_* 表完全隔离
-- =============================================================================

-- 月计划基础表 - 存储从Excel解析的月度生产计划数据
CREATE TABLE IF NOT EXISTS aps_monthly_plan (
    monthly_plan_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '月计划记录唯一标识',
    monthly_batch_id VARCHAR(100) NOT NULL COMMENT '月度导入批次ID，格式: MONTHLY_YYYYMMDD_HHMMSS_XXXX',
    
    -- Excel解析相关字段
    monthly_work_order_nr VARCHAR(50) NOT NULL COMMENT '月度工单号',
    monthly_article_nr VARCHAR(100) NOT NULL COMMENT '牌号代码',
    monthly_article_name VARCHAR(200) COMMENT '牌号名称',
    monthly_specification VARCHAR(200) COMMENT '规格描述',
    monthly_package_type VARCHAR(50) COMMENT '包装类型',
    
    -- 数量字段（从Excel提取的原计划目标箱数）
    monthly_target_quantity DECIMAL(12,2) DEFAULT 0.00 COMMENT '月度目标产量（万支）',
    monthly_planned_boxes INT DEFAULT 0 COMMENT '原计划目标箱数',
    monthly_unit VARCHAR(20) DEFAULT '万支' COMMENT '产量单位',
    
    -- 机台信息（仅杭州厂数据）
    monthly_feeder_codes TEXT COMMENT '喂丝机代码列表（逗号分隔）',
    monthly_maker_codes TEXT COMMENT '卷包机代码列表（逗号分隔）',
    
    -- 时间信息
    monthly_plan_year INT NOT NULL COMMENT '计划年份（从Excel标题提取）',
    monthly_plan_month INT NOT NULL COMMENT '计划月份（从Excel标题提取）',
    monthly_planned_start DATETIME COMMENT '计划开始时间',
    monthly_planned_end DATETIME COMMENT '计划结束时间',
    
    -- Excel解析元数据
    monthly_source_file VARCHAR(500) COMMENT '源Excel文件路径',
    monthly_sheet_name VARCHAR(100) COMMENT '工作表名称',
    monthly_row_number INT COMMENT 'Excel行号',
    monthly_extraction_notes TEXT COMMENT '提取备注信息',
    
    -- 数据验证状态
    monthly_validation_status ENUM('VALID', 'WARNING', 'ERROR') DEFAULT 'VALID' COMMENT '验证状态',
    monthly_validation_message TEXT COMMENT '验证错误或警告信息',
    
    -- 审计字段
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    created_by VARCHAR(50) DEFAULT 'monthly_system' COMMENT '创建者',
    
    -- 索引和约束
    INDEX idx_monthly_batch (monthly_batch_id),
    INDEX idx_monthly_article (monthly_article_nr),
    INDEX idx_monthly_plan_time (monthly_plan_year, monthly_plan_month),
    INDEX idx_monthly_created (created_time),
    UNIQUE KEY uk_monthly_unique (monthly_batch_id, monthly_work_order_nr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='月计划基础表-存储Excel解析的月度生产计划（避免与decade_plan冲突）';

-- 工作日历表 - 月度排产专用的工作日历
CREATE TABLE IF NOT EXISTS aps_monthly_work_calendar (
    monthly_calendar_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日历记录唯一标识',
    
    -- 日期信息
    calendar_date DATE NOT NULL COMMENT '日历日期',
    calendar_year INT NOT NULL COMMENT '年份',
    calendar_month INT NOT NULL COMMENT '月份',
    calendar_day INT NOT NULL COMMENT '日期',
    calendar_week_day INT NOT NULL COMMENT '星期几(1-7, 1=星期一)',
    
    -- 工作日类型
    monthly_day_type ENUM('WORKDAY', 'WEEKEND', 'HOLIDAY', 'MAINTENANCE') DEFAULT 'WORKDAY' COMMENT '日期类型',
    monthly_is_working TINYINT(1) DEFAULT 1 COMMENT '是否工作日（1=工作，0=非工作）',
    
    -- 班次信息（支持多班次）
    monthly_shifts JSON COMMENT '班次配置JSON: [{"shift_name":"白班","start":"08:00","end":"16:00","capacity_factor":1.0}]',
    monthly_total_hours DECIMAL(4,2) DEFAULT 8.00 COMMENT '当日总工作小时数',
    
    -- 容量系数（节假日前后、维护日等的产能调整）
    monthly_capacity_factor DECIMAL(4,3) DEFAULT 1.000 COMMENT '产能系数（0.0-2.0）',
    
    -- 特殊标记
    monthly_holiday_name VARCHAR(100) COMMENT '节假日名称（如果是节假日）',
    monthly_maintenance_type VARCHAR(50) COMMENT '维护类型（如果是维护日）',
    monthly_notes TEXT COMMENT '备注信息',
    
    -- 审计字段
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引和约束
    UNIQUE KEY uk_monthly_calendar_date (calendar_date),
    INDEX idx_monthly_calendar_ym (calendar_year, calendar_month),
    INDEX idx_monthly_calendar_working (monthly_is_working),
    INDEX idx_monthly_calendar_type (monthly_day_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='月度工作日历表-专用于月计划排产的日历管理（独立于decade系统）';

-- 月度排产结果表 - 存储算法执行后的排产结果
CREATE TABLE IF NOT EXISTS aps_monthly_schedule_result (
    monthly_schedule_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '排产结果唯一标识',
    monthly_task_id VARCHAR(100) NOT NULL COMMENT '排产任务ID',
    
    -- 关联月计划记录
    monthly_plan_id BIGINT NOT NULL COMMENT '关联的月计划记录ID',
    monthly_batch_id VARCHAR(100) NOT NULL COMMENT '月度导入批次ID',
    
    -- 排产核心信息
    monthly_work_order_nr VARCHAR(50) NOT NULL COMMENT '月度工单号',
    monthly_article_nr VARCHAR(100) NOT NULL COMMENT '牌号代码',
    
    -- 分配的机台信息
    assigned_feeder_code VARCHAR(50) COMMENT '分配的喂丝机代码',
    assigned_maker_code VARCHAR(50) COMMENT '分配的卷包机代码',
    machine_group VARCHAR(50) COMMENT '机台组别',
    
    -- 时间窗口分配
    scheduled_start_time DATETIME NOT NULL COMMENT '排产开始时间',
    scheduled_end_time DATETIME NOT NULL COMMENT '排产结束时间',
    scheduled_duration_hours DECIMAL(8,2) COMMENT '排产时长（小时）',
    
    -- 产量分配
    allocated_quantity DECIMAL(12,2) NOT NULL COMMENT '分配产量（万支）',
    allocated_boxes INT COMMENT '分配箱数',
    estimated_speed DECIMAL(8,2) COMMENT '预估生产速度（万支/小时）',
    
    -- 算法决策信息
    algorithm_version VARCHAR(50) COMMENT '使用的算法版本',
    priority_score DECIMAL(8,4) COMMENT '优先级分数',
    constraint_violations TEXT COMMENT '约束违反记录',
    optimization_notes TEXT COMMENT '优化备注',
    
    -- 工作日历关联
    working_days_count INT COMMENT '占用工作日天数',
    calendar_constraints JSON COMMENT '日历约束信息JSON',
    
    -- 状态管理
    monthly_schedule_status ENUM('DRAFT', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED') DEFAULT 'DRAFT' COMMENT '排产状态',
    monthly_execution_progress DECIMAL(5,2) DEFAULT 0.00 COMMENT '执行进度（0-100）',
    
    -- 审计字段
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    created_by VARCHAR(50) DEFAULT 'monthly_algorithm' COMMENT '创建者',
    
    -- 索引和约束
    INDEX idx_monthly_task (monthly_task_id),
    INDEX idx_monthly_schedule_batch (monthly_batch_id),
    INDEX idx_monthly_schedule_plan (monthly_plan_id),
    INDEX idx_monthly_schedule_article (monthly_article_nr),
    INDEX idx_monthly_schedule_machine (assigned_feeder_code, assigned_maker_code),
    INDEX idx_monthly_schedule_time (scheduled_start_time, scheduled_end_time),
    INDEX idx_monthly_schedule_status (monthly_schedule_status),
    
    -- 外键约束
    FOREIGN KEY fk_monthly_schedule_plan (monthly_plan_id) 
        REFERENCES aps_monthly_plan(monthly_plan_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
        
    -- 确保同一时间段同一机台不重复分配
    UNIQUE KEY uk_monthly_schedule_unique (assigned_feeder_code, assigned_maker_code, scheduled_start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='月度排产结果表-存储算法执行后的机台时间分配结果（完全独立的月度系统）';

-- =============================================================================
-- 冲突避免验证规则
-- =============================================================================

-- 添加表级别注释以明确区分
ALTER TABLE aps_monthly_plan 
ADD CONSTRAINT chk_monthly_plan_batch_format 
CHECK (monthly_batch_id LIKE 'MONTHLY_%');

ALTER TABLE aps_monthly_schedule_result 
ADD CONSTRAINT chk_monthly_schedule_batch_format 
CHECK (monthly_batch_id LIKE 'MONTHLY_%');

-- 确保月度和旬度数据不会混淆
-- 月度批次ID格式: MONTHLY_YYYYMMDD_HHMMSS_XXXX
-- 旬度批次ID格式: IMPORT_YYYYMMDD_HHMMSS_XXXX (现有格式)

-- =============================================================================
-- 数据完整性和业务规则
-- =============================================================================

-- 确保月度计划的时间范围合理
ALTER TABLE aps_monthly_plan 
ADD CONSTRAINT chk_monthly_plan_time_range 
CHECK (monthly_planned_start <= monthly_planned_end OR monthly_planned_end IS NULL);

-- 确保排产结果的时间范围合理  
ALTER TABLE aps_monthly_schedule_result
ADD CONSTRAINT chk_monthly_schedule_time_range
CHECK (scheduled_start_time < scheduled_end_time);

-- 确保产量为正数
ALTER TABLE aps_monthly_plan
ADD CONSTRAINT chk_monthly_target_quantity_positive
CHECK (monthly_target_quantity >= 0);

ALTER TABLE aps_monthly_schedule_result  
ADD CONSTRAINT chk_monthly_allocated_quantity_positive
CHECK (allocated_quantity > 0);

-- 确保进度在合理范围内
ALTER TABLE aps_monthly_schedule_result
ADD CONSTRAINT chk_monthly_execution_progress_range
CHECK (monthly_execution_progress >= 0 AND monthly_execution_progress <= 100);

-- =============================================================================
-- 创建成功日志
-- =============================================================================
SELECT 'APS月计划数据库模式创建完成！' as result,
       '- aps_monthly_plan: 月计划基础表' as table1,
       '- aps_monthly_work_calendar: 工作日历表' as table2, 
       '- aps_monthly_schedule_result: 排产结果表' as table3,
       '所有表使用独立的monthly_前缀，避免与现有decade系统冲突' as conflict_avoidance;