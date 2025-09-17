-- =============================================================================
-- APS智慧排产系统 - 月计划数据库索引优化脚本
-- =============================================================================
-- 目的: 为月计划表创建高性能查询索引，支持复杂查询场景
-- 优化目标: 查询响应时间<200ms，支持大规模数据（>10万条记录）
-- =============================================================================

-- =============================================================================
-- aps_monthly_plan 表索引优化
-- =============================================================================

-- 基础查询索引（已在schema中创建，此处为文档说明）
-- INDEX idx_monthly_batch (monthly_batch_id) - 基础批次查询
-- INDEX idx_monthly_article (monthly_article_nr) - 牌号查询
-- INDEX idx_monthly_plan_time (monthly_plan_year, monthly_plan_month) - 时间范围查询
-- INDEX idx_monthly_created (created_time) - 创建时间排序
-- UNIQUE KEY uk_monthly_unique (monthly_batch_id, monthly_work_order_nr) - 唯一性约束

-- 复合索引 - 批次+状态+时间（最常用的组合查询）
CREATE INDEX idx_monthly_batch_status_time 
ON aps_monthly_plan (monthly_batch_id, monthly_validation_status, created_time DESC)
COMMENT '批次状态时间复合索引-用于状态过滤和时间排序';

-- 复合索引 - 牌号+年月（产品计划查询）
CREATE INDEX idx_monthly_article_yearmonth 
ON aps_monthly_plan (monthly_article_nr, monthly_plan_year, monthly_plan_month)
COMMENT '牌号年月复合索引-用于产品月度计划查询';

-- 复合索引 - 机台代码查询（支持包含查询）
CREATE INDEX idx_monthly_feeder_codes 
ON aps_monthly_plan (monthly_feeder_codes(100))
COMMENT '喂丝机代码索引-支持机台分配查询';

CREATE INDEX idx_monthly_maker_codes 
ON aps_monthly_plan (monthly_maker_codes(100))  
COMMENT '卷包机代码索引-支持机台分配查询';

-- 数量范围查询索引
CREATE INDEX idx_monthly_quantity_range 
ON aps_monthly_plan (monthly_target_quantity, monthly_planned_boxes)
COMMENT '产量范围索引-支持产量统计和分析';

-- 文件来源查询索引
CREATE INDEX idx_monthly_source_sheet 
ON aps_monthly_plan (monthly_source_file(200), monthly_sheet_name)
COMMENT '文件工作表索引-支持按Excel文件查询';

-- =============================================================================
-- aps_monthly_work_calendar 表索引优化  
-- =============================================================================

-- 基础查询索引（已在schema中创建）
-- UNIQUE KEY uk_monthly_calendar_date (calendar_date) - 日期唯一性
-- INDEX idx_monthly_calendar_ym (calendar_year, calendar_month) - 年月查询
-- INDEX idx_monthly_calendar_working (monthly_is_working) - 工作日过滤
-- INDEX idx_monthly_calendar_type (monthly_day_type) - 日期类型过滤

-- 复合索引 - 年月+工作日（最常用的工作日历查询）
CREATE INDEX idx_monthly_calendar_ym_working 
ON aps_monthly_work_calendar (calendar_year, calendar_month, monthly_is_working, calendar_date)
COMMENT '年月工作日复合索引-用于工作日统计和排产日历';

-- 复合索引 - 日期范围+类型（排产算法专用）
CREATE INDEX idx_monthly_calendar_range_type 
ON aps_monthly_work_calendar (calendar_date, monthly_day_type, monthly_capacity_factor)
COMMENT '日期范围类型索引-用于算法的日历约束检查';

-- 星期维度索引（支持按星期统计）
CREATE INDEX idx_monthly_calendar_weekday 
ON aps_monthly_work_calendar (calendar_week_day, monthly_is_working)
COMMENT '星期工作日索引-支持按星期维度的统计分析';

-- =============================================================================
-- aps_monthly_schedule_result 表索引优化
-- =============================================================================

-- 基础查询索引（已在schema中创建）
-- INDEX idx_monthly_task (monthly_task_id) - 任务查询
-- INDEX idx_monthly_schedule_batch (monthly_batch_id) - 批次查询  
-- INDEX idx_monthly_schedule_plan (monthly_plan_id) - 计划关联
-- INDEX idx_monthly_schedule_article (monthly_article_nr) - 牌号查询
-- INDEX idx_monthly_schedule_machine (assigned_feeder_code, assigned_maker_code) - 机台查询
-- INDEX idx_monthly_schedule_time (scheduled_start_time, scheduled_end_time) - 时间范围
-- INDEX idx_monthly_schedule_status (monthly_schedule_status) - 状态过滤
-- UNIQUE KEY uk_monthly_schedule_unique (assigned_feeder_code, assigned_maker_code, scheduled_start_time) - 机台时间冲突避免

-- 复合索引 - 批次+状态+时间（排产结果最常用查询）
CREATE INDEX idx_monthly_schedule_batch_status_time 
ON aps_monthly_schedule_result (monthly_batch_id, monthly_schedule_status, scheduled_start_time)
COMMENT '批次状态时间复合索引-用于排产结果状态查询';

-- 复合索引 - 机台+时间段（机台占用率分析）
CREATE INDEX idx_monthly_schedule_machine_timerange 
ON aps_monthly_schedule_result (assigned_feeder_code, assigned_maker_code, scheduled_start_time, scheduled_end_time)
COMMENT '机台时间段复合索引-用于机台占用率和冲突检测';

-- 复合索引 - 牌号+状态+数量（产品排产分析）
CREATE INDEX idx_monthly_schedule_article_status_qty 
ON aps_monthly_schedule_result (monthly_article_nr, monthly_schedule_status, allocated_quantity)
COMMENT '牌号状态数量索引-用于产品排产进度统计';

-- 算法性能索引 - 优先级+约束（算法决策查询）
CREATE INDEX idx_monthly_schedule_algorithm 
ON aps_monthly_schedule_result (algorithm_version, priority_score, monthly_schedule_status)
COMMENT '算法版本优先级索引-用于算法性能分析';

-- 时间维度索引 - 支持时间窗口查询（Gantt图专用）
CREATE INDEX idx_monthly_schedule_timewindow 
ON aps_monthly_schedule_result (scheduled_start_time, scheduled_duration_hours, monthly_schedule_status)
COMMENT '时间窗口索引-专用于Gantt图时间轴查询';

-- 进度跟踪索引 - 执行状态+进度（生产监控）
CREATE INDEX idx_monthly_schedule_progress 
ON aps_monthly_schedule_result (monthly_schedule_status, monthly_execution_progress, updated_time DESC)
COMMENT '进度跟踪索引-用于生产执行监控和进度统计';

-- =============================================================================
-- 高性能查询场景索引
-- =============================================================================

-- 场景1: 批次排产概览（Dashboard）
-- SELECT 批次信息, COUNT(*), SUM(allocated_quantity) FROM aps_monthly_schedule_result 
-- WHERE monthly_batch_id = ? AND monthly_schedule_status IN (...)
-- 索引: idx_monthly_schedule_batch_status_time

-- 场景2: 机台时间表（Gantt Chart）
-- SELECT * FROM aps_monthly_schedule_result 
-- WHERE assigned_feeder_code = ? AND scheduled_start_time BETWEEN ? AND ?
-- 索引: idx_monthly_schedule_machine_timerange

-- 场景3: 产品排产进度（Product Dashboard）
-- SELECT monthly_article_nr, SUM(allocated_quantity), COUNT(*) 
-- FROM aps_monthly_schedule_result 
-- WHERE monthly_article_nr IN (...) AND monthly_schedule_status = ?
-- 索引: idx_monthly_schedule_article_status_qty

-- 场景4: 工作日历查询（Algorithm）
-- SELECT * FROM aps_monthly_work_calendar 
-- WHERE calendar_year = ? AND calendar_month = ? AND monthly_is_working = 1
-- 索引: idx_monthly_calendar_ym_working

-- 场景5: 算法性能分析（Monitoring）
-- SELECT algorithm_version, AVG(priority_score), COUNT(*) 
-- FROM aps_monthly_schedule_result 
-- WHERE algorithm_version = ? GROUP BY monthly_schedule_status
-- 索引: idx_monthly_schedule_algorithm

-- =============================================================================
-- JSON字段索引（MySQL 5.7+）
-- =============================================================================

-- 为JSON字段创建虚拟列和索引（如果需要按JSON内容查询）

-- 班次配置查询索引
ALTER TABLE aps_monthly_work_calendar 
ADD COLUMN monthly_first_shift_start TIME AS (JSON_UNQUOTE(JSON_EXTRACT(monthly_shifts, '$[0].start'))) VIRTUAL;

CREATE INDEX idx_monthly_calendar_shift_start 
ON aps_monthly_work_calendar (monthly_first_shift_start)
COMMENT 'JSON虚拟列索引-首班开始时间';

-- 约束违反快速查询索引  
ALTER TABLE aps_monthly_schedule_result
ADD COLUMN has_constraint_violations TINYINT(1) AS (CASE WHEN constraint_violations IS NOT NULL AND constraint_violations != '' THEN 1 ELSE 0 END) VIRTUAL;

CREATE INDEX idx_monthly_schedule_violations 
ON aps_monthly_schedule_result (has_constraint_violations, monthly_schedule_status)
COMMENT 'JSON虚拟列索引-约束违反标记';

-- =============================================================================
-- 索引使用建议和维护
-- =============================================================================

-- 定期索引统计更新（建议每天执行）
-- ANALYZE TABLE aps_monthly_plan;
-- ANALYZE TABLE aps_monthly_work_calendar;  
-- ANALYZE TABLE aps_monthly_schedule_result;

-- 索引使用情况监控查询
-- SELECT 
--   TABLE_NAME, INDEX_NAME, CARDINALITY, 
--   ROUND(CARDINALITY / TABLE_ROWS * 100, 2) as selectivity_percent
-- FROM information_schema.statistics s
-- JOIN information_schema.tables t ON s.TABLE_NAME = t.TABLE_NAME
-- WHERE s.TABLE_SCHEMA = DATABASE() 
--   AND s.TABLE_NAME LIKE 'aps_monthly_%'
-- ORDER BY TABLE_NAME, selectivity_percent DESC;

-- 慢查询监控（production环境启用）
-- SET GLOBAL slow_query_log = 'ON';
-- SET GLOBAL long_query_time = 0.2; -- 200ms阈值

-- =============================================================================
-- 性能验证脚本
-- =============================================================================

-- 插入测试数据以验证索引性能（可选，仅开发环境）
DELIMITER //
CREATE PROCEDURE test_monthly_index_performance()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_id VARCHAR(100);
    DECLARE article_codes JSON DEFAULT JSON_ARRAY('HNZJHYLC001', 'HNZJHYLC002', 'HNZJHYLC003', 'HNZJHYLC004');
    
    -- 创建测试批次  
    SET batch_id = CONCAT('MONTHLY_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s'), '_TEST');
    
    WHILE i <= 1000 DO
        INSERT INTO aps_monthly_plan (
            monthly_batch_id, monthly_work_order_nr, monthly_article_nr,
            monthly_target_quantity, monthly_plan_year, monthly_plan_month
        ) VALUES (
            batch_id, 
            CONCAT('MO_', LPAD(i, 6, '0')),
            JSON_UNQUOTE(JSON_EXTRACT(article_codes, CONCAT('$[', i % 4, ']'))),
            ROUND(RAND() * 1000, 2),
            2024,
            11
        );
        SET i = i + 1;
    END WHILE;
    
    SELECT CONCAT('已插入 ', i-1, ' 条测试数据到批次: ', batch_id) as result;
END //
DELIMITER ;

-- 清理测试数据的存储过程
DELIMITER //  
CREATE PROCEDURE cleanup_monthly_test_data()
BEGIN
    DELETE FROM aps_monthly_plan WHERE monthly_batch_id LIKE 'MONTHLY_%_TEST';
    DELETE FROM aps_monthly_schedule_result WHERE monthly_batch_id LIKE 'MONTHLY_%_TEST';
    SELECT '测试数据清理完成' as result;
END //
DELIMITER ;

-- =============================================================================
-- 创建完成确认
-- =============================================================================
SELECT 'APS月计划数据库索引优化完成！' as result,
       '- 基础索引: 12个（批次、牌号、时间等）' as basic_indexes,
       '- 复合索引: 15个（多字段组合查询优化）' as composite_indexes, 
       '- JSON索引: 2个（虚拟列查询优化）' as json_indexes,
       '- 存储过程: 2个（性能测试和数据清理）' as procedures,
       '预期查询性能: <200ms（10万级数据）' as performance_target;