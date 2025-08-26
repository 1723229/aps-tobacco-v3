# APS智慧排产系统 - 技术架构设计文档

## 1. 概述

本文档基于APS智慧排产思路PRD的技术要求和业务逻辑，设计了完整的技术架构方案，包括系统架构、技术栈选型、数据库设计、API接口设计和部署方案。

## 2. 系统整体架构

### 2.1 架构设计原则

- **前后端分离**：React前端 + Python后端，支持独立部署和扩展
- **微服务化**：核心业务模块独立，便于维护和升级
- **数据驱动**：基于PRD中的数据表结构，确保业务逻辑准确性
- **高可用性**：支持集群部署，提供故障恢复能力
- **易扩展性**：模块化设计，支持业务功能的快速扩展

### 2.2 系统架构图

```mermaid
graph TB
    subgraph "前端层"
        WEB[Web前端<br/>React + Ant Design]
        MOBILE[移动端<br/>React Native可选]
    end
    
    subgraph "接入层"
        NGINX[Nginx负载均衡<br/>SSL终结]
        GATEWAY[API网关<br/>认证/限流]
    end
    
    subgraph "应用层"
        subgraph "核心服务"
            API[API服务<br/>FastAPI]
            ALGO[排产算法服务<br/>独立进程]
            SCHEDULER[任务调度<br/>Celery]
        end
        
        subgraph "业务服务" 
            DATA[数据处理服务<br/>Excel解析]
            MES[MES集成服务<br/>SOAP接口]
            EXPORT[导出服务<br/>报表生成]
        end
    end
    
    subgraph "数据层"
        MYSQL[(MySQL主库<br/>业务数据)]
        REDIS[(Redis缓存<br/>会话/队列)]
        FILES[(文件存储<br/>Excel/导出)]
    end
    
    subgraph "外部系统"
        MES_SYS[MES系统<br/>工单接口]
        MAINT[轮保系统<br/>维护计划]
    end
    
    WEB --> NGINX
    MOBILE --> NGINX
    NGINX --> GATEWAY
    GATEWAY --> API
    
    API --> DATA
    API --> SCHEDULER
    API --> EXPORT
    
    SCHEDULER --> ALGO
    DATA --> MES
    
    API --> MYSQL
    API --> REDIS
    API --> FILES
    
    MES --> MES_SYS
    MES --> MAINT
```

## 3. 技术栈选型

### 3.1 前端技术栈

| 技术 | 版本 | 选择理由 | 应用场景 |
|------|------|---------|---------|
| React | 18.x | 生态成熟，组件化开发 | 主框架 |
| TypeScript | 5.x | 类型安全，开发效率 | 语言 |
| Ant Design | 5.x | 企业级UI组件，表格组件强大 | UI组件库 |
| React Query | 4.x | 数据请求和缓存管理 | 状态管理 |
| Vite | 4.x | 快速构建，开发体验好 | 构建工具 |
| Axios | 1.x | HTTP客户端 | 网络请求 |

### 3.2 后端技术栈

| 技术 | 版本 | 选择理由 | 应用场景 |
|------|------|---------|---------|
| Python | 3.11+ | 科学计算生态丰富 | 主语言 |
| FastAPI | 0.104+ | 高性能，自动文档生成 | Web框架 |
| SQLAlchemy | 2.0+ | ORM功能强大，支持异步 | 数据库ORM |
| Alembic | 1.12+ | 数据库迁移 | 数据库版本管理 |
| Celery | 5.3+ | 异步任务处理 | 任务队列 |
| Pandas | 2.1+ | Excel处理，数据分析 | 数据处理 |
| NumPy | 1.25+ | 数值计算 | 科学计算 |
| Pydantic | 2.4+ | 数据验证 | 数据模型 |

### 3.3 基础设施技术栈

| 技术 | 版本 | 选择理由 | 应用场景 |
|------|------|---------|---------|
| MySQL | 8.0+ | 事务支持，性能稳定 | 主数据库 |
| Redis | 7.0+ | 高性能缓存，支持多数据结构 | 缓存/消息队列 |
| Nginx | 1.24+ | 高性能反向代理 | 负载均衡 |
| Docker | 24.0+ | 容器化部署 | 部署 |
| Docker Compose | 2.20+ | 本地开发环境 | 开发环境 |

## 4. 数据库设计

### 4.1 基础数据表设计

基于PRD中的已有表结构，保持原有设计不变：

#### 4.1.1 FinishingSpeed表（生产速度配置）

```sql
-- 基于PRD知识表1的设计
CREATE TABLE finishing_speed (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_nr VARCHAR(10) NOT NULL COMMENT '设备编号，*表示通用',
    article_nr VARCHAR(20) NOT NULL COMMENT '产品编号，*表示通用',
    speed DECIMAL(8,2) NOT NULL COMMENT '生产速度(箱/小时)',
    effective_date DATE NOT NULL COMMENT '生效日期',
    expiry_date DATE COMMENT '失效日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_equipment_article (equipment_nr, article_nr),
    INDEX idx_effective_date (effective_date)
) COMMENT '卷包机台加工速度配置表';

-- 初始化数据（基于PRD表格）
INSERT INTO finishing_speed (equipment_nr, article_nr, speed, effective_date) VALUES
('*', '*', 8.0, '2024-01-01'),
('A01', '*', 18.0, '2024-01-01'),
('A02', '*', 18.0, '2024-01-01'),
('A03', '*', 18.0, '2024-01-01'),
('A04', '*', 18.0, '2024-01-01'),
('A05', '*', 18.0, '2024-01-01'),
('B02', '*', 11.0, '2024-01-01'),
('B07', '*', 9.0, '2024-01-01'),
('B08', '*', 9.0, '2024-01-01'),
('B03', '*', 11.0, '2024-01-01'),
('C12', '*', 3.0, '2024-01-01'),
('D02', '*', 6.8, '2024-01-01'),
('D03', '*', 6.8, '2024-01-01'),
('B12', '*', 11.0, '2024-01-01'),
('A09', '*', 7.0, '2024-01-01'),
('B04', '*', 9.0, '2024-01-01'),
('B05', '*', 9.0, '2024-01-01'),
('B06', '*', 9.0, '2024-01-01'),
('D01', '*', 7.15, '2024-01-01'),
('D04', '*', 7.15, '2024-01-01'),
('D05', '*', 7.15, '2024-01-01'),
('D06', '*', 6.1, '2024-01-01'),
('B01', '*', 11.0, '2024-01-01'),
('D07', '*', 7.15, '2024-01-01');
```

#### 4.1.2 ShiftName表（班次定义）

```sql
-- 基于PRD知识表2的设计
CREATE TABLE shift_definition (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shift_name VARCHAR(10) NOT NULL COMMENT '班次名称',
    machine_name VARCHAR(10) DEFAULT '*' COMMENT '机台名称，*表示通用',
    start_time TIME NOT NULL COMMENT '开始时间',
    end_time TIME NOT NULL COMMENT '结束时间',
    is_ot_needed BOOLEAN DEFAULT FALSE COMMENT '是否需要加班',
    max_ot_duration INT COMMENT '最大加班时间(分钟)',
    effective_date DATE NOT NULL COMMENT '生效日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_shift_machine (shift_name, machine_name),
    INDEX idx_effective_date (effective_date)
) COMMENT '班次定义表';

-- 初始化数据（基于PRD示例数据）
INSERT INTO shift_definition (shift_name, machine_name, start_time, end_time, is_ot_needed, max_ot_duration, effective_date) VALUES
('早班', '*', '06:40:00', '15:40:00', FALSE, NULL, '2024-01-01'),
('中班', '*', '15:40:00', '24:00:00', TRUE, 60, '2024-01-01'),
('晚班', '*', '00:00:00', '06:40:00', FALSE, NULL, '2024-01-01');
```

### 4.2 业务数据表设计

#### 4.2.1 卷包旬计划导入表

```sql
-- 卷包旬计划原始数据表
CREATE TABLE jb_plan_import (
    id INT AUTO_INCREMENT PRIMARY KEY,
    import_batch_id VARCHAR(50) NOT NULL COMMENT '导入批次ID',
    production_unit INT NOT NULL COMMENT '生产单元',
    package_type VARCHAR(10) COMMENT '包装类型(软包/硬包)',
    specification VARCHAR(10) COMMENT '规格(长嘴/短嘴等)',
    feeder_machine_nr VARCHAR(50) COMMENT '喂丝机号(可多个)',
    maker_machine_nr VARCHAR(50) COMMENT '卷包机号(可多个)',
    article_nr VARCHAR(50) NOT NULL COMMENT '牌号',
    input_quantity INT COMMENT '本次投料',
    output_quantity INT COMMENT '本次成品',
    production_date_range VARCHAR(50) COMMENT '成品生产日期',
    planned_start DATE COMMENT '计划开始日期',
    planned_end DATE COMMENT '计划结束日期',
    import_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '导入时间',
    status VARCHAR(20) DEFAULT 'IMPORTED' COMMENT '状态',
    INDEX idx_import_batch (import_batch_id),
    INDEX idx_production_unit (production_unit)
) COMMENT '卷包旬计划导入表';
```

#### 4.2.2 卷包工单表

```sql
-- 基于PRD表2卷包机工单的设计
CREATE TABLE jb_work_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_nr VARCHAR(50) NOT NULL UNIQUE COMMENT '生产订单号',
    article_nr VARCHAR(50) NOT NULL COMMENT '成品烟牌号',
    quantity_total INT NOT NULL COMMENT '总量',
    final_quantity INT NOT NULL COMMENT '成品数量',
    maker_code VARCHAR(20) NOT NULL COMMENT '卷包机代码',
    feeder_code VARCHAR(20) COMMENT '关联喂丝机代码',
    planned_start DATETIME NOT NULL COMMENT '计划开始时间',
    planned_end DATETIME NOT NULL COMMENT '计划结束时间',
    actual_start DATETIME COMMENT '实际开始时间',
    actual_end DATETIME COMMENT '实际结束时间',
    sequence_no INT DEFAULT 1 COMMENT '执行序号',
    is_backup BOOLEAN DEFAULT FALSE COMMENT '是否备用工单',
    is_merged BOOLEAN DEFAULT FALSE COMMENT '是否合并生成',
    merge_source TEXT COMMENT '合并源工单信息',
    import_batch_id VARCHAR(50) COMMENT '来源导入批次',
    status VARCHAR(20) DEFAULT 'CREATED' COMMENT '工单状态',
    mes_sent_time DATETIME COMMENT 'MES发送时间',
    mes_status VARCHAR(20) COMMENT 'MES状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_work_order_nr (work_order_nr),
    INDEX idx_maker_code (maker_code),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_import_batch (import_batch_id)
) COMMENT '卷包工单表';
```

#### 4.2.3 喂丝机工单表

```sql
-- 喂丝机工单表
CREATE TABLE ws_work_order (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_nr VARCHAR(50) NOT NULL UNIQUE COMMENT '喂丝机工单号',
    feeder_codes TEXT NOT NULL COMMENT '喂丝机代码(多个用逗号分隔)',
    material_code VARCHAR(50) COMMENT '物料代码',
    bom_revision VARCHAR(20) COMMENT 'BOM版本号',
    planned_start DATETIME NOT NULL COMMENT '计划开始时间',
    planned_end DATETIME NOT NULL COMMENT '计划结束时间',
    sequence_no INT DEFAULT 1 COMMENT '执行序号',
    related_jb_orders TEXT COMMENT '关联卷包工单号(多个用逗号分隔)',
    import_batch_id VARCHAR(50) COMMENT '来源导入批次',
    status VARCHAR(20) DEFAULT 'CREATED' COMMENT '工单状态',
    mes_sent_time DATETIME COMMENT 'MES发送时间',
    mes_status VARCHAR(20) COMMENT 'MES状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_work_order_nr (work_order_nr),
    INDEX idx_planned_time (planned_start, planned_end),
    INDEX idx_import_batch (import_batch_id)
) COMMENT '喂丝机工单表';
```

#### 4.2.4 轮保计划表

```sql
-- 基于PRD 5.1.2.2轮保接口设计
CREATE TABLE maintenance_plan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    maint_plan_no VARCHAR(50) NOT NULL COMMENT '计划编号',
    schedule_date DATE NOT NULL COMMENT '计划日期',
    shift VARCHAR(10) COMMENT '班次(1.早班 2.中班 3.晚班)',
    maint_group VARCHAR(10) COMMENT '班别(1.甲班 2.乙班 3.丙班)',
    planner VARCHAR(50) COMMENT '制单人',
    equipment_position VARCHAR(20) NOT NULL COMMENT '机组位置',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    status VARCHAR(20) DEFAULT 'PLANNED' COMMENT '状态',
    from_mes BOOLEAN DEFAULT TRUE COMMENT '是否来自MES',
    sync_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
    INDEX idx_equipment_date (equipment_position, schedule_date),
    INDEX idx_plan_no (maint_plan_no)
) COMMENT '轮保计划表';
```

### 4.3 系统辅助表

#### 4.3.1 排产任务表

```sql
-- 排产任务执行记录表
CREATE TABLE scheduling_task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL UNIQUE COMMENT '任务ID',
    import_batch_id VARCHAR(50) NOT NULL COMMENT '导入批次ID',
    task_type VARCHAR(20) DEFAULT 'FULL_SCHEDULING' COMMENT '任务类型',
    parameters JSON COMMENT '排产参数',
    status VARCHAR(20) DEFAULT 'PENDING' COMMENT '任务状态',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    progress INT DEFAULT 0 COMMENT '进度百分比',
    current_stage VARCHAR(50) COMMENT '当前阶段',
    result_summary JSON COMMENT '结果摘要',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_import_batch (import_batch_id),
    INDEX idx_status (status)
) COMMENT '排产任务表';
```

#### 4.3.2 设备对应关系表

```sql
-- 喂丝机与卷包机对应关系表
CREATE TABLE feeder_maker_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    feeder_code VARCHAR(20) NOT NULL COMMENT '喂丝机代码',
    maker_code VARCHAR(20) NOT NULL COMMENT '卷包机代码',
    is_primary BOOLEAN DEFAULT TRUE COMMENT '是否主要对应关系',
    effective_date DATE NOT NULL COMMENT '生效日期',
    expiry_date DATE COMMENT '失效日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_feeder (feeder_code),
    INDEX idx_maker (maker_code),
    UNIQUE KEY uk_feeder_maker (feeder_code, maker_code, effective_date)
) COMMENT '喂丝机与卷包机对应关系表';

-- 初始化对应关系数据（基于提供的对应关系）
INSERT INTO feeder_maker_mapping (feeder_code, maker_code, effective_date) VALUES
('1', 'D3', '2024-01-01'),
('2', 'D1', '2024-01-01'),
('3', 'D4', '2024-01-01'),
('4', 'C8', '2024-01-01'),
('4', 'C9', '2024-01-01'),
('5', 'B4', '2024-01-01'),
('5', 'B5', '2024-01-01'),
('6', 'B3', '2024-01-01'),
('7', 'C10', '2024-01-01'),
('8', 'B8', '2024-01-01'),
('9', 'A4', '2024-01-01'),
('10', 'A6', '2024-01-01'),
('11', 'A5', '2024-01-01'),
('12', 'B2', '2024-01-01'),
('13', 'C6', '2024-01-01'),
('13', 'C7', '2024-01-01'),
('14', 'C2', '2024-01-01'),
('15', 'A3', '2024-01-01'),
('16', 'A1', '2024-01-01'),
('17', 'A2', '2024-01-01'),
('18', 'C1', '2024-01-01'),
('18', 'C3', '2024-01-01'),
('19', 'C5', '2024-01-01'),
('20', 'B1', '2024-01-01'),
('21', 'B7', '2024-01-01'),
('22', 'A7', '2024-01-01'),
('23', 'A8', '2024-01-01'),
('24', 'C12', '2024-01-01'),
('25', 'A9', '2024-01-01'),
('26', 'D6', '2024-01-01'),
('27', 'D2', '2024-01-01'),
('28', 'D4', '2024-01-01'),
('28', 'D5', '2024-01-01'),
('29', 'C11', '2024-01-01');
```

## 5. API接口设计

### 5.1 API架构设计

```python
# app/api/v1/router.py
from fastapi import APIRouter
from .endpoints import (
    data_import,
    scheduling, 
    work_orders,
    maintenance,
    export,
    monitoring
)

api_router = APIRouter()

# 数据导入接口
api_router.include_router(
    data_import.router, 
    prefix="/data-import", 
    tags=["数据导入"]
)

# 排产管理接口
api_router.include_router(
    scheduling.router, 
    prefix="/scheduling", 
    tags=["排产管理"]
)

# 工单管理接口
api_router.include_router(
    work_orders.router, 
    prefix="/work-orders", 
    tags=["工单管理"]
)

# 轮保管理接口
api_router.include_router(
    maintenance.router, 
    prefix="/maintenance", 
    tags=["轮保管理"]
)

# 导出服务接口
api_router.include_router(
    export.router, 
    prefix="/export", 
    tags=["导出服务"]
)

# 监控接口
api_router.include_router(
    monitoring.router, 
    prefix="/monitoring", 
    tags=["系统监控"]
)
```

### 5.2 核心接口定义

#### 5.2.1 数据导入接口

```python
# app/api/v1/endpoints/data_import.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import pandas as pd
from app.schemas import ImportResponse, ValidationResult
from app.services.data_import_service import DataImportService

router = APIRouter()

@router.post("/upload-excel", response_model=ImportResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    validate_only: bool = False
):
    """
    上传Excel卷包旬计划文件
    
    Args:
        file: Excel文件
        validate_only: 是否仅验证不导入
    
    Returns:
        ImportResponse: 导入结果
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="文件格式不支持，请上传.xlsx或.xls文件"
        )
    
    service = DataImportService()
    result = await service.process_excel_import(file, validate_only)
    return result

@router.get("/import-status/{import_batch_id}")
async def get_import_status(import_batch_id: str):
    """获取导入状态"""
    service = DataImportService()
    status = await service.get_import_status(import_batch_id)
    return status

@router.get("/preview-data/{import_batch_id}")
async def preview_import_data(
    import_batch_id: str,
    page: int = 1,
    size: int = 20
):
    """预览导入数据"""
    service = DataImportService()
    data = await service.get_preview_data(import_batch_id, page, size)
    return data
```

#### 5.2.2 排产管理接口

```python
# app/api/v1/endpoints/scheduling.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas import SchedulingRequest, SchedulingResponse, TaskStatus
from app.services.scheduling_service import SchedulingService
from app.tasks.scheduling_tasks import execute_scheduling_task

router = APIRouter()

@router.post("/execute", response_model=SchedulingResponse)
async def execute_scheduling(
    request: SchedulingRequest,
    background_tasks: BackgroundTasks
):
    """
    执行排产
    
    Args:
        request: 排产请求参数
        background_tasks: 后台任务
    
    Returns:
        SchedulingResponse: 排产任务信息
    """
    service = SchedulingService()
    
    # 创建排产任务
    task = await service.create_scheduling_task(request)
    
    # 异步执行排产算法
    background_tasks.add_task(
        execute_scheduling_task.delay,
        task.task_id,
        request.dict()
    )
    
    return SchedulingResponse(
        task_id=task.task_id,
        status="STARTED",
        message="排产任务已启动"
    )

@router.get("/task-status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """获取排产任务状态"""
    service = SchedulingService()
    status = await service.get_task_status(task_id)
    return status

@router.get("/task-result/{task_id}")
async def get_task_result(task_id: str):
    """获取排产结果"""
    service = SchedulingService()
    result = await service.get_task_result(task_id)
    return result

@router.post("/cancel-task/{task_id}")
async def cancel_task(task_id: str):
    """取消排产任务"""
    service = SchedulingService()
    result = await service.cancel_task(task_id)
    return result
```

#### 5.2.3 工单管理接口

```python
# app/api/v1/endpoints/work_orders.py
from fastapi import APIRouter, Query
from typing import List, Optional
from app.schemas import WorkOrderResponse, WorkOrderFilter
from app.services.work_order_service import WorkOrderService

router = APIRouter()

@router.get("/jb-orders", response_model=List[WorkOrderResponse])
async def get_jb_work_orders(
    import_batch_id: Optional[str] = None,
    maker_code: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """获取卷包工单列表"""
    service = WorkOrderService()
    filter_params = WorkOrderFilter(
        import_batch_id=import_batch_id,
        maker_code=maker_code,
        status=status
    )
    orders = await service.get_jb_work_orders(filter_params, page, size)
    return orders

@router.get("/ws-orders", response_model=List[WorkOrderResponse])
async def get_ws_work_orders(
    import_batch_id: Optional[str] = None,
    feeder_code: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """获取喂丝机工单列表"""
    service = WorkOrderService()
    filter_params = WorkOrderFilter(
        import_batch_id=import_batch_id,
        feeder_code=feeder_code,
        status=status
    )
    orders = await service.get_ws_work_orders(filter_params, page, size)
    return orders

@router.get("/statistics/{import_batch_id}")
async def get_work_order_statistics(import_batch_id: str):
    """获取工单统计信息"""
    service = WorkOrderService()
    stats = await service.get_statistics(import_batch_id)
    return stats
```

### 5.3 数据模型定义

```python
# app/schemas/scheduling.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ImportResponse(BaseModel):
    """导入响应模型"""
    import_batch_id: str
    status: str
    total_records: int
    valid_records: int
    error_records: int
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

class SchedulingRequest(BaseModel):
    """排产请求模型"""
    import_batch_id: str
    optimization_target: str = Field(default="on_time_completion", description="优化目标")
    enable_merge: bool = Field(default=True, description="启用合并")
    enable_split: bool = Field(default=True, description="启用拆分")
    strict_parallel: bool = Field(default=True, description="严格并行模式")
    ignore_maintenance: bool = Field(default=False, description="忽略轮保")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="额外参数")

class SchedulingResponse(BaseModel):
    """排产响应模型"""
    task_id: str
    status: str
    message: str
    estimated_duration: Optional[int] = None

class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    progress: int = Field(ge=0, le=100)
    current_stage: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

class WorkOrderResponse(BaseModel):
    """工单响应模型"""
    work_order_nr: str
    article_nr: str
    quantity_total: int
    final_quantity: int
    maker_code: Optional[str] = None
    feeder_code: Optional[str] = None
    planned_start: datetime
    planned_end: datetime
    status: str
    is_backup: bool = False
    is_merged: bool = False
    created_at: datetime
```

## 6. 核心服务设计

### 6.1 排产算法服务

```python
# app/services/scheduling_service.py
from typing import List, Dict, Any
from app.models import JBPlanImport, JBWorkOrder, WSWorkOrder
from app.algorithms import (
    MergeAlgorithm,
    SplitAlgorithm, 
    ParallelAlgorithm,
    TimeAdjustmentAlgorithm
)

class SchedulingService:
    """排产服务类"""
    
    def __init__(self):
        self.merge_algo = MergeAlgorithm()
        self.split_algo = SplitAlgorithm()
        self.parallel_algo = ParallelAlgorithm()
        self.time_algo = TimeAdjustmentAlgorithm()
    
    async def execute_full_scheduling(self, import_batch_id: str, parameters: Dict[str, Any]):
        """执行完整排产流程"""
        # 1. 加载导入数据
        import_data = await self.load_import_data(import_batch_id)
        
        # 2. 数据预处理
        work_orders = await self.preprocess_data(import_data)
        
        # 3. 执行合并算法
        if parameters.get('enable_merge', True):
            work_orders = await self.merge_algo.execute(work_orders)
        
        # 4. 执行拆分算法
        if parameters.get('enable_split', True):
            work_orders = await self.split_algo.execute(work_orders)
        
        # 5. 执行并行处理算法
        work_orders = await self.parallel_algo.execute(work_orders)
        
        # 6. 时间校正
        work_orders = await self.time_algo.execute(work_orders)
        
        # 7. 生成工单
        jb_orders = await self.generate_jb_orders(work_orders)
        ws_orders = await self.generate_ws_orders(work_orders)
        
        # 8. 保存结果
        await self.save_results(jb_orders, ws_orders, import_batch_id)
        
        return {
            'jb_orders_count': len(jb_orders),
            'ws_orders_count': len(ws_orders),
            'on_time_rate': await self.calculate_on_time_rate(jb_orders),
            'load_balance_score': await self.calculate_load_balance(jb_orders)
        }
```

### 6.2 MES集成服务

```python
# app/services/mes_integration_service.py
from typing import List, Dict, Any
from app.models import JBWorkOrder, WSWorkOrder
import xml.etree.ElementTree as ET
from zeep import Client
import logging

class MESIntegrationService:
    """MES集成服务"""
    
    def __init__(self):
        self.mes_client = None
        self.logger = logging.getLogger(__name__)
    
    async def export_to_mes(self, import_batch_id: str) -> Dict[str, Any]:
        """导出工单到MES系统"""
        try:
            # 1. 获取工单数据
            jb_orders = await self.get_jb_orders(import_batch_id)
            ws_orders = await self.get_ws_orders(import_batch_id)
            
            # 2. 生成XML数据
            xml_data = self.build_mes_xml(jb_orders, ws_orders)
            
            # 3. 调用MES接口
            response = await self.call_mes_api(xml_data)
            
            # 4. 处理响应
            if response.get('success'):
                await self.update_order_status(jb_orders + ws_orders, 'MES_SENT')
                self.logger.info(f"成功导出{len(jb_orders + ws_orders)}个工单到MES")
            
            return {
                'success': response.get('success', False),
                'message': response.get('message', ''),
                'exported_count': len(jb_orders + ws_orders)
            }
            
        except Exception as e:
            self.logger.error(f"MES导出失败: {str(e)}")
            return {
                'success': False,
                'message': f'导出失败: {str(e)}',
                'exported_count': 0
            }
    
    def build_mes_xml(self, jb_orders: List[JBWorkOrder], ws_orders: List[WSWorkOrder]) -> str:
        """构建MES XML数据"""
        root = ET.Element('WorkOrders')
        
        # 卷包工单
        for order in jb_orders:
            order_elem = ET.SubElement(root, 'JBWorkOrder')
            ET.SubElement(order_elem, 'WorkOrderNr').text = order.work_order_nr
            ET.SubElement(order_elem, 'ArticleNr').text = order.article_nr
            ET.SubElement(order_elem, 'QuantityTotal').text = str(order.quantity_total)
            ET.SubElement(order_elem, 'FinalQuantity').text = str(order.final_quantity)
            ET.SubElement(order_elem, 'MakerCode').text = order.maker_code
            ET.SubElement(order_elem, 'PlannedStart').text = order.planned_start.strftime('%Y-%m-%d %H:%M:%S')
            ET.SubElement(order_elem, 'PlannedEnd').text = order.planned_end.strftime('%Y-%m-%d %H:%M:%S')
        
        # 喂丝机工单  
        for order in ws_orders:
            order_elem = ET.SubElement(root, 'WSWorkOrder')
            ET.SubElement(order_elem, 'WorkOrderNr').text = order.work_order_nr
            ET.SubElement(order_elem, 'FeederCodes').text = order.feeder_codes
            ET.SubElement(order_elem, 'MaterialCode').text = order.material_code or ''
            ET.SubElement(order_elem, 'PlannedStart').text = order.planned_start.strftime('%Y-%m-%d %H:%M:%S')
            ET.SubElement(order_elem, 'PlannedEnd').text = order.planned_end.strftime('%Y-%m-%d %H:%M:%S')
        
        return ET.tostring(root, encoding='unicode')
```

## 7. 部署架构

### 7.1 Docker部署配置

```dockerfile
# Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 创建非root用户
RUN groupadd -r aps && useradd -r -g aps aps
RUN chown -R aps:aps /app
USER aps

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Dockerfile.frontend  
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY src/ ./src/
COPY public/ ./public/
COPY tsconfig.json .
COPY vite.config.ts .

RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 7.2 Docker Compose配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # MySQL数据库
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: aps_db
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    command: --default-authentication-plugin=mysql_native_password
    restart: unless-stopped

  # Redis缓存
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    restart: unless-stopped

  # 后端API服务
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      DATABASE_URL: mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/aps_db
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - mysql
      - redis
    restart: unless-stopped

  # Celery Worker
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/aps_db
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    depends_on:
      - mysql
      - redis
    restart: unless-stopped

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  # Nginx负载均衡
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:
```

### 7.3 Kubernetes部署配置

```yaml
# k8s/aps-backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aps-backend
  labels:
    app: aps-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aps-backend
  template:
    metadata:
      labels:
        app: aps-backend
    spec:
      containers:
      - name: backend
        image: aps/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aps-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://aps-redis:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: aps-backend-service
spec:
  selector:
    app: aps-backend
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

## 8. 监控与运维

### 8.1 健康检查

```python
# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
import redis
import logging

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """系统健康检查"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {}
    }
    
    # 检查数据库连接
    try:
        await db.execute("SELECT 1")
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 检查Redis连接
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 检查Celery
    try:
        from app.celery_app import celery_app
        i = celery_app.control.inspect()
        stats = i.stats()
        if stats:
            health_status["components"]["celery"] = "healthy"
        else:
            health_status["components"]["celery"] = "no workers"
    except Exception as e:
        health_status["components"]["celery"] = f"unhealthy: {str(e)}"
    
    return health_status

@router.get("/metrics")
async def system_metrics():
    """系统监控指标"""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
    }
```

### 8.2 日志配置

```python
# app/core/logging.py
import logging
import logging.handlers
from pythonjsonlogger import jsonlogger
from app.core.config import settings

def setup_logging():
    """配置日志系统"""
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # JSON格式化器
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if settings.LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=100*1024*1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
```

### 8.3 性能监控

```python
# app/middleware/monitoring.py
from fastapi import Request, Response
import time
import logging

logger = logging.getLogger(__name__)

async def monitoring_middleware(request: Request, call_next):
    """性能监控中间件"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        "Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host
        }
    )
    
    # 执行请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录响应信息
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
```

## 9. 安全考虑

### 9.1 数据安全

```python
# app/core/security.py
from cryptography.fernet import Fernet
from passlib.context import CryptContext
import os

class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.encryption_key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
```

### 9.2 API安全

```python
# app/core/auth.py
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """验证访问令牌"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## 10. 总结

本技术架构文档基于APS智慧排产思路PRD的业务需求，设计了完整的技术实现方案：

### 10.1 架构特点

- **技术先进**：采用FastAPI + React的现代技术栈
- **性能优异**：异步处理 + 缓存机制 + 分布式部署
- **扩展性强**：微服务架构 + 容器化部署
- **业务准确**：严格遵循PRD的数据结构和业务逻辑
- **运维友好**：完善的监控、日志和健康检查

### 10.2 核心优势

- **数据库设计**：基于PRD表结构，保持业务一致性
- **算法引擎**：独立的排产算法服务，便于优化升级
- **MES集成**：标准化接口，支持多种MES系统
- **高可用性**：支持集群部署和故障恢复
- **安全可靠**：多层安全防护和数据保护

该架构设计为APS智慧排产系统提供了坚实的技术基础，确保系统的稳定性、可扩展性和可维护性。

---

*本文档版本：v1.0*  
*最后更新：2024-08-26*  
*上一个文档：APS-Business-Requirements.md*