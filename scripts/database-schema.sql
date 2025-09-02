/*
 Navicat Premium Dump SQL

 Source Server         : 10.0.0.99-aps
 Source Server Type    : MySQL
 Source Server Version : 80036 (8.0.36)
 Source Host           : 10.0.0.99:3306
 Source Schema         : aps

 Target Server Type    : MySQL
 Target Server Version : 80036 (8.0.36)
 File Encoding         : 65001

 Date: 02/09/2025 11:21:46
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for aps_business_rule
-- ----------------------------
DROP TABLE IF EXISTS `aps_business_rule`;
CREATE TABLE `aps_business_rule` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '规则代码',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '规则名称',
  `rule_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '规则类型',
  `rule_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '规则描述',
  `rule_expression` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '规则表达式',
  `rule_parameters` json DEFAULT NULL COMMENT '规则参数（JSON）',
  `priority` int DEFAULT '5' COMMENT '优先级',
  `effective_from` date NOT NULL COMMENT '生效日期',
  `effective_to` date DEFAULT NULL COMMENT '失效日期',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_by` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'system' COMMENT '创建者',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_rule_code` (`rule_code`) USING BTREE,
  KEY `idx_rule_type` (`rule_type`) USING BTREE,
  KEY `idx_effective_date` (`effective_from`,`effective_to`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `idx_priority` (`priority`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='业务规则配置表';

-- ----------------------------
-- Table structure for aps_decade_plan
-- ----------------------------
DROP TABLE IF EXISTS `aps_decade_plan`;
CREATE TABLE `aps_decade_plan` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `import_batch_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '导入批次ID',
  `work_order_nr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '生产订单号',
  `article_nr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '成品烟牌号',
  `package_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '包装类型（软包/硬包）',
  `specification` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规格（长嘴/短嘴等）',
  `quantity_total` int NOT NULL COMMENT '投料总量（箱）',
  `final_quantity` int NOT NULL COMMENT '成品数量（箱）',
  `production_unit` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生产单元',
  `maker_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '卷包机代码',
  `feeder_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '喂丝机代码',
  `planned_start` datetime NOT NULL COMMENT '计划开始时间',
  `planned_end` datetime NOT NULL COMMENT '计划结束时间',
  `production_date_range` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '成品生产日期范围',
  `row_number` int DEFAULT NULL COMMENT '原始行号',
  `validation_status` enum('VALID','WARNING','ERROR') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'VALID' COMMENT '验证状态',
  `validation_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '验证信息',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_import_batch` (`import_batch_id`) USING BTREE,
  KEY `idx_work_order` (`work_order_nr`) USING BTREE,
  KEY `idx_planned_time` (`planned_start`,`planned_end`) USING BTREE,
  KEY `idx_validation_status` (`validation_status`) USING BTREE,
  KEY `fk_decade_plan_material` (`article_nr`) USING BTREE,
  KEY `idx_decade_plan_composite` (`import_batch_id`,`validation_status`,`planned_start`) USING BTREE,
  CONSTRAINT `fk_decade_plan_import` FOREIGN KEY (`import_batch_id`) REFERENCES `aps_import_plan` (`import_batch_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_decade_plan_material` FOREIGN KEY (`article_nr`) REFERENCES `aps_material` (`article_nr`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=4706 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='原始卷包旬计划表';

-- ----------------------------
-- Table structure for aps_feeding_order
-- ----------------------------
DROP TABLE IF EXISTS `aps_feeding_order`;
CREATE TABLE `aps_feeding_order` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `plan_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '计划ID，格式:HWS+9位流水号',
  `production_line` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工序段，多个喂丝机代码逗号分隔',
  `batch_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '批次号（喂丝机通常为空）',
  `material_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '生产的物料代码',
  `bom_revision` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '版本号',
  `quantity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '计划生产量（喂丝机通常为空）',
  `plan_start_time` datetime NOT NULL COMMENT '计划开始时间',
  `plan_end_time` datetime NOT NULL COMMENT '计划结束时间',
  `sequence` int NOT NULL DEFAULT '1' COMMENT '执行顺序',
  `shift` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '班次',
  `is_vaccum` tinyint(1) DEFAULT '0' COMMENT '是否真空回潮',
  `is_sh93` tinyint(1) DEFAULT '0' COMMENT '是否走SH93',
  `is_hdt` tinyint(1) DEFAULT '0' COMMENT '是否走HDT',
  `is_flavor` tinyint(1) DEFAULT '0' COMMENT '是否补香',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '公斤' COMMENT '基本单位',
  `plan_date` date NOT NULL COMMENT '计划日期',
  `plan_output_quantity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '计划产出量',
  `is_outsourcing` tinyint(1) DEFAULT '0' COMMENT '是否委外',
  `is_backup` tinyint(1) DEFAULT '0' COMMENT '是否备用工单',
  `task_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '排产任务ID',
  `order_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PLANNED' COMMENT '工单状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `plan_id` (`plan_id`) USING BTREE,
  KEY `idx_task_id` (`task_id`) USING BTREE,
  KEY `idx_plan_date` (`plan_date`) USING BTREE,
  KEY `idx_plan_start_time` (`plan_start_time`) USING BTREE,
  KEY `idx_order_status` (`order_status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1371 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喂丝机工单表-MES规范';

-- ----------------------------
-- Table structure for aps_import_plan
-- ----------------------------
DROP TABLE IF EXISTS `aps_import_plan`;
CREATE TABLE `aps_import_plan` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `import_batch_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '导入批次ID',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件名',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '文件路径',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小（字节）',
  `total_records` int DEFAULT '0' COMMENT '总记录数',
  `valid_records` int DEFAULT '0' COMMENT '有效记录数',
  `error_records` int DEFAULT '0' COMMENT '错误记录数',
  `import_status` enum('UPLOADING','PARSING','COMPLETED','FAILED') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'UPLOADING' COMMENT '导入状态',
  `import_start_time` datetime DEFAULT NULL COMMENT '导入开始时间',
  `import_end_time` datetime DEFAULT NULL COMMENT '导入结束时间',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '错误信息',
  `created_by` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'system' COMMENT '创建者',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_import_batch` (`import_batch_id`) USING BTREE,
  KEY `idx_import_status` (`import_status`) USING BTREE,
  KEY `idx_created_time` (`created_time`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='计划导入记录表';

-- ----------------------------
-- Table structure for aps_input_batch
-- ----------------------------
DROP TABLE IF EXISTS `aps_input_batch`;
CREATE TABLE `aps_input_batch` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `packing_order_id` bigint NOT NULL COMMENT '卷包工单ID',
  `input_plan_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '前工序计划号（喂丝机工单号）',
  `input_batch_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '前工序批次号',
  `material_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物料代码',
  `bom_revision` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '版本号',
  `quantity` decimal(10,2) DEFAULT NULL COMMENT '数量',
  `batch_sequence` int DEFAULT NULL COMMENT '批次顺序',
  `is_whole_batch` tinyint(1) DEFAULT '0' COMMENT '是否整批',
  `is_main_channel` tinyint(1) DEFAULT '1' COMMENT '是否走主通道',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '是否删除（用于喂丝机工单取消追加）',
  `is_last_one` tinyint(1) DEFAULT '0' COMMENT '是否最后一个批次（只有喂丝才需要）',
  `is_tiled` tinyint(1) DEFAULT '0' COMMENT '是否平铺（只有回用烟丝二才会给出）',
  `remark1` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注1',
  `remark2` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备注2',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_packing_order` (`packing_order_id`) USING BTREE,
  KEY `idx_input_plan` (`input_plan_id`) USING BTREE,
  KEY `idx_material_code` (`material_code`) USING BTREE,
  KEY `idx_batch_sequence` (`batch_sequence`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工单输入批次关联表（支持MES InputBatch结构）';

-- ----------------------------
-- Table structure for aps_machine
-- ----------------------------
DROP TABLE IF EXISTS `aps_machine`;
CREATE TABLE `aps_machine` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `machine_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台代码',
  `machine_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台名称',
  `machine_type` enum('PACKING','FEEDING') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台类型：卷包机/喂丝机',
  `equipment_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '设备型号(如PROTOS70, M8)',
  `production_line` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '生产线',
  `status` enum('ACTIVE','INACTIVE','MAINTENANCE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '机台状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_machine_code` (`machine_code`) USING BTREE,
  KEY `idx_machine_type` (`machine_type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='机台基础信息表';

-- ----------------------------
-- Table structure for aps_machine_relation
-- ----------------------------
DROP TABLE IF EXISTS `aps_machine_relation`;
CREATE TABLE `aps_machine_relation` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `feeder_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '喂丝机代码',
  `maker_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '卷包机代码',
  `relation_type` enum('ONE_TO_ONE','ONE_TO_MANY') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ONE_TO_ONE' COMMENT '关系类型',
  `priority` int DEFAULT '1' COMMENT '优先级（1=最高）',
  `effective_from` date NOT NULL COMMENT '生效日期',
  `effective_to` date DEFAULT NULL COMMENT '失效日期',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_feeder_maker_date` (`feeder_code`,`maker_code`,`effective_from`) USING BTREE,
  KEY `idx_feeder_code` (`feeder_code`) USING BTREE,
  KEY `idx_maker_code` (`maker_code`) USING BTREE,
  KEY `idx_effective_date` (`effective_from`,`effective_to`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  CONSTRAINT `fk_feeder` FOREIGN KEY (`feeder_code`) REFERENCES `aps_machine` (`machine_code`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_maker` FOREIGN KEY (`maker_code`) REFERENCES `aps_machine` (`machine_code`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='喂丝机与卷包机对应关系表';

-- ----------------------------
-- Table structure for aps_machine_speed
-- ----------------------------
DROP TABLE IF EXISTS `aps_machine_speed`;
CREATE TABLE `aps_machine_speed` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `machine_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台代码',
  `article_nr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物料编号',
  `speed` decimal(10,2) NOT NULL COMMENT '生产速度（箱/小时）',
  `efficiency_rate` decimal(5,2) DEFAULT '85.00' COMMENT '效率系数（%）',
  `effective_from` date NOT NULL COMMENT '生效日期',
  `effective_to` date DEFAULT NULL COMMENT '失效日期',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_machine_article_date` (`machine_code`,`article_nr`,`effective_from`) USING BTREE,
  KEY `idx_effective_date` (`effective_from`,`effective_to`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE,
  KEY `fk_machine_speed_material` (`article_nr`) USING BTREE,
  CONSTRAINT `fk_machine_speed_machine` FOREIGN KEY (`machine_code`) REFERENCES `aps_machine` (`machine_code`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_machine_speed_material` FOREIGN KEY (`article_nr`) REFERENCES `aps_material` (`article_nr`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='机台生产速度配置表';

-- ----------------------------
-- Table structure for aps_maintenance_plan
-- ----------------------------
DROP TABLE IF EXISTS `aps_maintenance_plan`;
CREATE TABLE `aps_maintenance_plan` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `maint_plan_no` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '轮保计划编号',
  `schedule_date` date NOT NULL COMMENT '轮保日期',
  `shift_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '班次代码',
  `maint_group` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '轮保班组',
  `equipment_position` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '设备机位',
  `machine_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台代码',
  `maint_start_time` datetime NOT NULL COMMENT '轮保开始时间',
  `maint_end_time` datetime NOT NULL COMMENT '轮保结束时间',
  `estimated_duration` int DEFAULT NULL COMMENT '预计耗时（分钟）',
  `maint_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '轮保类型',
  `maint_level` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '轮保级别',
  `maint_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '轮保描述',
  `plan_status` enum('PLANNED','CONFIRMED','IN_PROGRESS','COMPLETED','CANCELLED') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PLANNED' COMMENT '计划状态',
  `sync_from_mes` tinyint(1) DEFAULT '1' COMMENT '是否来自MES',
  `sync_time` datetime DEFAULT NULL COMMENT 'MES同步时间',
  `mes_version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'MES版本号',
  `planner` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '制单人',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_maint_plan_no` (`maint_plan_no`) USING BTREE,
  KEY `idx_schedule_date` (`schedule_date`) USING BTREE,
  KEY `idx_machine_code` (`machine_code`) USING BTREE,
  KEY `idx_maint_time` (`maint_start_time`,`maint_end_time`) USING BTREE,
  KEY `idx_plan_status` (`plan_status`) USING BTREE,
  CONSTRAINT `fk_maint_machine` FOREIGN KEY (`machine_code`) REFERENCES `aps_machine` (`machine_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备轮保计划表';

-- ----------------------------
-- Table structure for aps_material
-- ----------------------------
DROP TABLE IF EXISTS `aps_material`;
CREATE TABLE `aps_material` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `article_nr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物料编号',
  `article_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物料名称',
  `material_type` enum('FINISHED_PRODUCT','TOBACCO_SILK','RAW_MATERIAL') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '物料类型',
  `package_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '包装类型（软包/硬包）',
  `specification` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '规格（长嘴/短嘴/超长嘴/中支/细支）',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '箱' COMMENT '计量单位',
  `conversion_rate` decimal(10,4) DEFAULT '1.0000' COMMENT '转换比率',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_article_nr` (`article_nr`) USING BTREE,
  KEY `idx_material_type` (`material_type`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='物料基础信息表';

-- ----------------------------
-- Table structure for aps_mes_dispatch
-- ----------------------------
DROP TABLE IF EXISTS `aps_mes_dispatch`;
CREATE TABLE `aps_mes_dispatch` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `dispatch_batch_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '下发批次ID',
  `work_order_nr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工单号',
  `order_type` enum('PACKING','FEEDING') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工单类型',
  `dispatch_status` enum('PENDING','DISPATCHED','CONFIRMED','FAILED') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PENDING' COMMENT '下发状态',
  `dispatch_time` datetime DEFAULT NULL COMMENT '下发时间',
  `dispatch_data` json DEFAULT NULL COMMENT '下发数据（JSON）',
  `mes_response` json DEFAULT NULL COMMENT 'MES响应数据（JSON）',
  `mes_confirm_time` datetime DEFAULT NULL COMMENT 'MES确认时间',
  `mes_error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT 'MES错误信息',
  `retry_count` int DEFAULT '0' COMMENT '重试次数',
  `max_retry_count` int DEFAULT '3' COMMENT '最大重试次数',
  `next_retry_time` datetime DEFAULT NULL COMMENT '下次重试时间',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_dispatch_batch` (`dispatch_batch_id`) USING BTREE,
  KEY `idx_work_order` (`work_order_nr`) USING BTREE,
  KEY `idx_dispatch_status` (`dispatch_status`) USING BTREE,
  KEY `idx_order_type` (`order_type`) USING BTREE,
  KEY `idx_dispatch_time` (`dispatch_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MES工单下发记录表';

-- ----------------------------
-- Table structure for aps_operation_log
-- ----------------------------
DROP TABLE IF EXISTS `aps_operation_log`;
CREATE TABLE `aps_operation_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `log_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '日志ID',
  `operation_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '操作类型',
  `operation_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '操作名称',
  `operation_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '操作描述',
  `user_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用户ID',
  `user_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用户名称',
  `client_ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '客户端IP',
  `user_agent` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '用户代理',
  `target_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '目标类型',
  `target_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '目标ID',
  `target_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '目标名称',
  `request_params` json DEFAULT NULL COMMENT '请求参数（JSON）',
  `response_data` json DEFAULT NULL COMMENT '响应数据（JSON）',
  `operation_result` enum('SUCCESS','FAILED','PARTIAL') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '操作结果',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '错误信息',
  `operation_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `execution_duration` int DEFAULT NULL COMMENT '执行耗时（毫秒）',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_log_id` (`log_id`) USING BTREE,
  KEY `idx_operation_type` (`operation_type`) USING BTREE,
  KEY `idx_user_id` (`user_id`) USING BTREE,
  KEY `idx_operation_time` (`operation_time`) USING BTREE,
  KEY `idx_operation_result` (`operation_result`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统操作日志表';

-- ----------------------------
-- Table structure for aps_order_status_sync
-- ----------------------------
DROP TABLE IF EXISTS `aps_order_status_sync`;
CREATE TABLE `aps_order_status_sync` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `batch_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '批次号（来自MES）',
  `work_order_nr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '关联工单号',
  `order_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工单状态',
  `status_change_time` datetime NOT NULL COMMENT '状态变更时间',
  `actual_start_time` datetime DEFAULT NULL COMMENT '实际开始时间',
  `actual_end_time` datetime DEFAULT NULL COMMENT '实际结束时间',
  `actual_quantity` int DEFAULT NULL COMMENT '实际产量',
  `completion_rate` decimal(5,2) DEFAULT NULL COMMENT '完成率（%）',
  `sync_from_mes` tinyint(1) DEFAULT '1' COMMENT '是否来自MES',
  `sync_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
  `mes_data` json DEFAULT NULL COMMENT 'MES原始数据（JSON）',
  `processed` tinyint(1) DEFAULT '0' COMMENT '是否已处理',
  `process_time` datetime DEFAULT NULL COMMENT '处理时间',
  `process_result` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '处理结果',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_batch_code` (`batch_code`) USING BTREE,
  KEY `idx_work_order` (`work_order_nr`) USING BTREE,
  KEY `idx_status_change_time` (`status_change_time`) USING BTREE,
  KEY `idx_processed` (`processed`) USING BTREE,
  KEY `idx_sync_time` (`sync_time`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工单状态同步表';

-- ----------------------------
-- Table structure for aps_packing_order
-- ----------------------------
DROP TABLE IF EXISTS `aps_packing_order`;
CREATE TABLE `aps_packing_order` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `plan_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '计划ID，格式:HJB+9位流水号',
  `production_line` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工序段，单个卷包机代码',
  `batch_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '批次号',
  `material_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '生产的物料代码（牌号）',
  `bom_revision` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '版本号',
  `quantity` int NOT NULL COMMENT '成品烟产量（箱）',
  `plan_start_time` datetime NOT NULL COMMENT '计划开始时间',
  `plan_end_time` datetime NOT NULL COMMENT '计划结束时间',
  `sequence` int NOT NULL DEFAULT '1' COMMENT '执行顺序',
  `shift` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '班次',
  `input_plan_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '前工序计划号（喂丝机工单号）',
  `input_batch_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '前工序批次号',
  `input_quantity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '投入数量',
  `batch_sequence` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '批次顺序',
  `is_whole_batch` tinyint(1) DEFAULT NULL COMMENT '是否整批',
  `is_main_channel` tinyint(1) DEFAULT '1' COMMENT '是否走主通道',
  `is_deleted` tinyint(1) DEFAULT '0' COMMENT '是否删除',
  `is_last_one` tinyint(1) DEFAULT NULL COMMENT '是否最后一个批次',
  `input_material_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '投入物料代码',
  `input_bom_revision` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '投入版本号',
  `tiled` tinyint(1) DEFAULT NULL COMMENT '是否平铺',
  `is_vaccum` tinyint(1) DEFAULT '0' COMMENT '是否真空回潮',
  `is_sh93` tinyint(1) DEFAULT '0' COMMENT '是否走SH93',
  `is_hdt` tinyint(1) DEFAULT '0' COMMENT '是否走HDT',
  `is_flavor` tinyint(1) DEFAULT '0' COMMENT '是否补香',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '箱' COMMENT '基本单位',
  `plan_date` date NOT NULL COMMENT '计划日期',
  `plan_output_quantity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '计划产出量',
  `is_outsourcing` tinyint(1) DEFAULT '0' COMMENT '是否委外',
  `is_backup` tinyint(1) DEFAULT '0' COMMENT '是否备用工单',
  `task_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '排产任务ID',
  `order_status` enum('PLANNED','DISPATCHED','IN_PROGRESS','COMPLETED','CANCELLED') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PLANNED' COMMENT '工单状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_plan_id` (`plan_id`) USING BTREE,
  KEY `idx_task_id` (`task_id`) USING BTREE,
  KEY `idx_material_code` (`material_code`) USING BTREE,
  KEY `idx_production_line` (`production_line`) USING BTREE,
  KEY `idx_input_plan_id` (`input_plan_id`) USING BTREE,
  KEY `idx_plan_date` (`plan_date`) USING BTREE,
  KEY `idx_order_status` (`order_status`) USING BTREE,
  CONSTRAINT `fk_packing_input` FOREIGN KEY (`input_plan_id`) REFERENCES `aps_feeding_order` (`plan_id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `fk_packing_task` FOREIGN KEY (`task_id`) REFERENCES `aps_scheduling_task` (`task_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=1727 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='卷包机工单表（完全符合MES接口规范）';

-- ----------------------------
-- Table structure for aps_processing_log
-- ----------------------------
DROP TABLE IF EXISTS `aps_processing_log`;
CREATE TABLE `aps_processing_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '排产任务ID',
  `stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '处理阶段',
  `step_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '处理步骤名称',
  `log_level` enum('DEBUG','INFO','WARN','ERROR') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'INFO' COMMENT '日志级别',
  `log_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '日志消息',
  `processing_data` json DEFAULT NULL COMMENT '处理数据（JSON格式）',
  `execution_time` datetime NOT NULL COMMENT '执行时间',
  `duration_ms` int DEFAULT NULL COMMENT '执行耗时（毫秒）',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_task_stage` (`task_id`,`stage`) USING BTREE,
  KEY `idx_log_level` (`log_level`) USING BTREE,
  KEY `idx_execution_time` (`execution_time`) USING BTREE,
  CONSTRAINT `fk_log_task` FOREIGN KEY (`task_id`) REFERENCES `aps_scheduling_task` (`task_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='排产处理日志表';

-- ----------------------------
-- Table structure for aps_scheduling_task
-- ----------------------------
DROP TABLE IF EXISTS `aps_scheduling_task`;
CREATE TABLE `aps_scheduling_task` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '排产任务ID',
  `import_batch_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '关联导入批次ID',
  `task_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '任务名称',
  `task_status` enum('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PENDING' COMMENT '任务状态',
  `current_stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '当前阶段',
  `progress` int DEFAULT '0' COMMENT '进度百分比(0-100)',
  `total_records` int DEFAULT '0' COMMENT '总记录数',
  `processed_records` int DEFAULT '0' COMMENT '已处理记录数',
  `merge_enabled` tinyint(1) DEFAULT '1' COMMENT '是否启用合并',
  `split_enabled` tinyint(1) DEFAULT '1' COMMENT '是否启用拆分',
  `correction_enabled` tinyint(1) DEFAULT '1' COMMENT '是否启用校正',
  `parallel_enabled` tinyint(1) DEFAULT '1' COMMENT '是否启用并行',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `execution_duration` int DEFAULT NULL COMMENT '执行耗时（秒）',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '错误信息',
  `result_summary` json DEFAULT NULL COMMENT '结果摘要（JSON格式）',
  `created_by` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'system' COMMENT '创建者',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_task_id` (`task_id`) USING BTREE,
  KEY `idx_task_status` (`task_status`) USING BTREE,
  KEY `idx_created_time` (`created_time`) USING BTREE,
  KEY `fk_scheduling_import` (`import_batch_id`) USING BTREE,
  CONSTRAINT `fk_scheduling_import` FOREIGN KEY (`import_batch_id`) REFERENCES `aps_import_plan` (`import_batch_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=103 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='排产任务表';

-- ----------------------------
-- Table structure for aps_shift_config
-- ----------------------------
DROP TABLE IF EXISTS `aps_shift_config`;
CREATE TABLE `aps_shift_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `shift_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '班次名称',
  `machine_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '机台名称(*表示所有机台)',
  `start_time` time NOT NULL COMMENT '开始时间',
  `end_time` time NOT NULL COMMENT '结束时间',
  `is_ot_needed` tinyint(1) DEFAULT '0' COMMENT '是否需要加班',
  `max_ot_duration` time DEFAULT NULL COMMENT '最大加班时长',
  `effective_from` date NOT NULL COMMENT '生效日期',
  `effective_to` date DEFAULT NULL COMMENT '失效日期',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_shift_machine_date` (`shift_name`,`machine_name`,`effective_from`) USING BTREE,
  KEY `idx_shift_name` (`shift_name`) USING BTREE,
  KEY `idx_machine_name` (`machine_name`) USING BTREE,
  KEY `idx_effective_date` (`effective_from`,`effective_to`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='班次配置表';

-- ----------------------------
-- Table structure for aps_system_config
-- ----------------------------
DROP TABLE IF EXISTS `aps_system_config`;
CREATE TABLE `aps_system_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '配置键',
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '配置值',
  `config_type` enum('STRING','INTEGER','DECIMAL','BOOLEAN','JSON') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'STRING' COMMENT '配置类型',
  `config_group` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '配置分组',
  `config_description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '配置描述',
  `is_encrypted` tinyint(1) DEFAULT '0' COMMENT '是否加密',
  `status` enum('ACTIVE','INACTIVE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'ACTIVE' COMMENT '状态',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_config_key` (`config_key`) USING BTREE,
  KEY `idx_config_group` (`config_group`) USING BTREE,
  KEY `idx_status` (`status`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统参数配置表';

-- ----------------------------
-- Table structure for aps_work_order_schedule
-- ----------------------------
DROP TABLE IF EXISTS `aps_work_order_schedule`;
CREATE TABLE `aps_work_order_schedule` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `work_order_nr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '生产订单号',
  `article_nr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '成品烟牌号',
  `final_quantity` int NOT NULL COMMENT '成品数量（箱）- 算法主要使用此字段',
  `quantity_total` int NOT NULL COMMENT '投料总量（箱）',
  `maker_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '卷包机代码',
  `feeder_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '喂丝机代码',
  `planned_start` datetime NOT NULL COMMENT '计划开始时间',
  `planned_end` datetime NOT NULL COMMENT '计划结束时间',
  `task_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '排产任务ID',
  `schedule_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'PENDING' COMMENT '排程状态',
  `sync_group_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '同步组ID - 同一工单的机台组',
  `is_backup` tinyint(1) DEFAULT '0' COMMENT '是否备用工单',
  `backup_reason` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '备用工单原因',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_work_order_nr` (`work_order_nr`) USING BTREE,
  KEY `idx_task_id` (`task_id`) USING BTREE,
  KEY `idx_planned_time` (`planned_start`,`planned_end`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1764 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工单机台排程表';

-- ----------------------------
-- Table structure for aps_work_order_sequence
-- ----------------------------
DROP TABLE IF EXISTS `aps_work_order_sequence`;
CREATE TABLE `aps_work_order_sequence` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `order_type` enum('HWS','HJB') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '工单类型：HWS-喂丝机,HJB-卷包机',
  `sequence_date` date NOT NULL COMMENT '序列日期',
  `current_sequence` int DEFAULT '0' COMMENT '当前序列号',
  `last_order_nr` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '最后生成的工单号',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_order_type_date` (`order_type`,`sequence_date`) USING BTREE,
  KEY `idx_sequence_date` (`sequence_date`) USING BTREE,
  KEY `idx_order_type` (`order_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工单号序列表（支持MES规范：H+工单类型+9位流水号）';

SET FOREIGN_KEY_CHECKS = 1;
