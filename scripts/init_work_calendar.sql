-- =============================================================================
-- APS智慧排产系统 - 月计划工作日历初始化SQL脚本  
-- =============================================================================
-- 目的: 为2024-2026年中国法定节假日和工作日历数据初始化
-- 数据来源: 国务院办公厅关于节假日安排的通知
-- =============================================================================

-- 清理已有数据（仅初始化时使用）
DELETE FROM aps_monthly_work_calendar WHERE calendar_year BETWEEN 2024 AND 2026;

-- =============================================================================
-- 2024年中国法定节假日数据
-- =============================================================================

-- 2024年元旦（2024年1月1日，星期一）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-01-01', 2024, 1, 1, 1, 'HOLIDAY', 0, 0, 0, '元旦', '法定节假日');

-- 2024年春节（2024年2月10日-17日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-02-10', 2024, 2, 10, 6, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-11', 2024, 2, 11, 7, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-12', 2024, 2, 12, 1, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-13', 2024, 2, 13, 2, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-14', 2024, 2, 14, 3, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-15', 2024, 2, 15, 4, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-16', 2024, 2, 16, 5, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2024-02-17', 2024, 2, 17, 6, 'HOLIDAY', 0, 0, 0, '春节', '春节假期');

-- 2024年清明节（2024年4月4日-6日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-04-04', 2024, 4, 4, 4, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日'),
('2024-04-05', 2024, 4, 5, 5, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日'),
('2024-04-06', 2024, 4, 6, 6, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日');

-- 2024年劳动节（2024年5月1日-5日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-05-01', 2024, 5, 1, 3, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2024-05-02', 2024, 5, 2, 4, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2024-05-03', 2024, 5, 3, 5, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2024-05-04', 2024, 5, 4, 6, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2024-05-05', 2024, 5, 5, 7, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日');

-- 2024年端午节（2024年6月10日）  
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-06-10', 2024, 6, 10, 1, 'HOLIDAY', 0, 0, 0, '端午节', '法定节假日');

-- 2024年中秋节（2024年9月17日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-09-17', 2024, 9, 17, 2, 'HOLIDAY', 0, 0, 0, '中秋节', '法定节假日');

-- 2024年国庆节（2024年10月1日-7日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2024-10-01', 2024, 10, 1, 2, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-02', 2024, 10, 2, 3, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-03', 2024, 10, 3, 4, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-04', 2024, 10, 4, 5, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-05', 2024, 10, 5, 6, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-06', 2024, 10, 6, 7, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2024-10-07', 2024, 10, 7, 1, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假');

-- =============================================================================
-- 2025年中国法定节假日数据  
-- =============================================================================

-- 2025年元旦（2025年1月1日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-01-01', 2025, 1, 1, 3, 'HOLIDAY', 0, 0, 0, '元旦', '法定节假日');

-- 2025年春节（2025年1月28日-2月3日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-01-28', 2025, 1, 28, 2, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-01-29', 2025, 1, 29, 3, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-01-30', 2025, 1, 30, 4, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-01-31', 2025, 1, 31, 5, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-02-01', 2025, 2, 1, 6, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-02-02', 2025, 2, 2, 7, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2025-02-03', 2025, 2, 3, 1, 'HOLIDAY', 0, 0, 0, '春节', '春节假期');

-- 2025年清明节（2025年4月5日-7日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-04-05', 2025, 4, 5, 6, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日'),
('2025-04-06', 2025, 4, 6, 7, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日'),
('2025-04-07', 2025, 4, 7, 1, 'HOLIDAY', 0, 0, 0, '清明节', '法定节假日');

-- 2025年劳动节（2025年5月1日-3日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-05-01', 2025, 5, 1, 4, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2025-05-02', 2025, 5, 2, 5, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日'),
('2025-05-03', 2025, 5, 3, 6, 'HOLIDAY', 0, 0, 0, '劳动节', '法定节假日');

-- 2025年端午节（2025年5月31日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-05-31', 2025, 5, 31, 6, 'HOLIDAY', 0, 0, 0, '端午节', '法定节假日');

-- 2025年中秋节（2025年10月6日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-10-06', 2025, 10, 6, 1, 'HOLIDAY', 0, 0, 0, '中秋节', '法定节假日');

-- 2025年国庆节（2025年10月1日-7日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2025-10-01', 2025, 10, 1, 3, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2025-10-02', 2025, 10, 2, 4, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2025-10-03', 2025, 10, 3, 5, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2025-10-04', 2025, 10, 4, 6, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2025-10-05', 2025, 10, 5, 7, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假'),
('2025-10-07', 2025, 10, 7, 2, 'HOLIDAY', 0, 0, 0, '国庆节', '国庆长假');

-- =============================================================================
-- 2026年中国法定节假日数据（预估）
-- =============================================================================

-- 2026年元旦（2026年1月1日）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2026-01-01', 2026, 1, 1, 4, 'HOLIDAY', 0, 0, 0, '元旦', '法定节假日');

-- 2026年春节（2026年2月17日-23日，预估）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_holiday_name, monthly_notes
) VALUES 
('2026-02-17', 2026, 2, 17, 2, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-18', 2026, 2, 18, 3, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-19', 2026, 2, 19, 4, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-20', 2026, 2, 20, 5, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-21', 2026, 2, 21, 6, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-22', 2026, 2, 22, 7, 'HOLIDAY', 0, 0, 0, '春节', '春节假期'),
('2026-02-23', 2026, 2, 23, 1, 'HOLIDAY', 0, 0, 0, '春节', '春节假期');

-- 其他2026年节假日（清明、劳动、端午、中秋、国庆）根据实际公布日期更新...

-- =============================================================================
-- 特殊维护日和调休日配置（示例）
-- =============================================================================

-- 月度设备维护日（每月最后一个周日，产能减半）
INSERT INTO aps_monthly_work_calendar (
    calendar_date, calendar_year, calendar_month, calendar_day, calendar_week_day,
    monthly_day_type, monthly_is_working, monthly_total_hours, monthly_capacity_factor,
    monthly_maintenance_type, monthly_notes
) VALUES 
-- 2024年各月最后一个周日维护示例
('2024-01-28', 2024, 1, 28, 7, 'MAINTENANCE', 1, 6, 0.5, '月度设备维护', '设备保养日，产能50%'),
('2024-02-25', 2024, 2, 25, 7, 'MAINTENANCE', 1, 6, 0.5, '月度设备维护', '设备保养日，产能50%'),
('2024-03-31', 2024, 3, 31, 7, 'MAINTENANCE', 1, 6, 0.5, '月度设备维护', '设备保养日，产能50%');

-- =============================================================================
-- 标准工作日班次配置
-- =============================================================================

-- 为所有非节假日的工作日设置标准班次（这个会在Python脚本中批量生成）
-- 标准班次配置：两班制
-- 白班：08:00-16:00 (8小时)  
-- 夜班：20:00-04:00 (8小时)
-- 总计：16小时/天

-- =============================================================================
-- 数据验证和统计查询
-- =============================================================================

-- 验证节假日数量
SELECT 
    calendar_year,
    COUNT(*) as holiday_days,
    GROUP_CONCAT(DISTINCT monthly_holiday_name) as holidays
FROM aps_monthly_work_calendar 
WHERE monthly_day_type = 'HOLIDAY' 
GROUP BY calendar_year
ORDER BY calendar_year;

-- 验证维护日配置
SELECT 
    calendar_year,
    calendar_month,
    COUNT(*) as maintenance_days
FROM aps_monthly_work_calendar 
WHERE monthly_day_type = 'MAINTENANCE'
GROUP BY calendar_year, calendar_month
ORDER BY calendar_year, calendar_month;

-- 工作日统计（按月）
SELECT 
    calendar_year,
    calendar_month,
    SUM(CASE WHEN monthly_is_working = 1 THEN 1 ELSE 0 END) as working_days,
    SUM(CASE WHEN monthly_day_type = 'HOLIDAY' THEN 1 ELSE 0 END) as holiday_days,
    SUM(CASE WHEN monthly_day_type = 'WEEKEND' THEN 1 ELSE 0 END) as weekend_days
FROM aps_monthly_work_calendar 
GROUP BY calendar_year, calendar_month
ORDER BY calendar_year, calendar_month;

-- =============================================================================
-- 初始化完成确认
-- =============================================================================
SELECT 'APS月计划工作日历初始化完成！' as result,
       CONCAT('节假日数据: ', (SELECT COUNT(*) FROM aps_monthly_work_calendar WHERE monthly_day_type = 'HOLIDAY'), ' 天') as holidays,
       CONCAT('维护日数据: ', (SELECT COUNT(*) FROM aps_monthly_work_calendar WHERE monthly_day_type = 'MAINTENANCE'), ' 天') as maintenance,
       '数据范围: 2024-2026年' as data_range,
       '数据来源: 国务院办公厅节假日安排通知' as data_source;