# APS智慧排产系统 (APS Tobacco v3)

## 项目概述

APS智慧排产系统是专为烟草生产企业设计的智能排产调度系统，基于先进的排产算法和现代化技术架构，实现卷包旬计划的自动化处理、优化排产和可视化管理。

## 🚀 项目状态

### ✅ 已完成模块

#### 数据导入管理（完整实现）
- Excel文件上传（支持拖拽上传、进度显示）
- 复杂Excel解析器（支持多工作表、合并单元格）
- 数据验证和清洗
- 导入批次管理和状态追踪

#### 前端用户界面（完整实现）
- Vue.js 3 + TypeScript + Element Plus现代化Web应用
- 响应式导航布局和用户友好界面
- 完整的文件上传和解析流程
- 统计信息展示和历史记录查询
- Pinia状态管理和Vue Router路由
- 完善的错误处理和用户反馈机制

#### 后端API服务（基础完成）
- FastAPI高性能异步框架
- MySQL数据库异步连接和ORM模型
- Redis缓存和配置管理
- 完整的API接口（文件上传、解析、查询）
- 健康检查和系统监控接口

#### 数据存储（部分完成）
- 机台信息表 (aps_machine)
- 物料信息表 (aps_material)
- 导入计划表 (aps_import_plan)
- 旬计划表 (aps_decade_plan)

### ❌ 待实现模块

#### 排产算法引擎（核心缺失）
- 规则合并处理算法
- 规则拆分处理算法
- 时间校正算法（轮保、班次考虑）
- 并行切分算法

#### 工单生成功能
- 卷包机工单生成
- 喂丝机工单生成
- 工单数据模型完善

#### MES系统集成
- 轮保计划接口对接
- 工单下发接口
- 状态同步机制

#### 甘特图可视化
- 排产结果可视化展示
- 时间轴和资源分配图表

## 🛠 技术架构

### 前端技术栈
- **Vue.js 3.5.18** - 现代化前端框架
- **TypeScript** - 类型安全
- **Element Plus 2.8.8** - UI组件库（中文本地化）
- **Pinia 3.0.3** - 状态管理
- **Vue Router 4.5.1** - 路由管理
- **Axios 1.7.7** - HTTP客户端
- **Vite 7.0.6** - 前端构建工具

### 后端技术栈
- **FastAPI 0.104.1** - 高性能异步Web框架
- **SQLAlchemy 2.0.23** - Python ORM，支持异步操作
- **Pydantic 2.5.0** - 数据验证和序列化
- **aiomysql 0.2.0** - MySQL异步驱动
- **Redis** - 缓存和会话存储
- **openpyxl 3.1.2** - Excel文件解析

### 数据库
- **MySQL 8.0+** - 主数据库
- **Redis 7.0+** - 缓存数据库

## 📁 项目结构

```
aps-tobacco-v3/
├── frontend/                    # ✅ 完整Vue.js应用
│   ├── src/
│   │   ├── components/         # 业务组件
│   │   ├── views/             # 页面视图
│   │   ├── services/          # API服务层
│   │   ├── stores/            # Pinia状态管理
│   │   ├── router/            # Vue Router配置
│   │   ├── types/             # TypeScript类型定义
│   │   └── utils/             # 工具函数
│   └── package.json
├── backend/                     # ✅ 核心API服务
│   ├── app/
│   │   ├── api/               # API路由层
│   │   ├── core/              # 核心配置
│   │   ├── db/                # 数据库层
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic模型
│   │   ├── services/          # 业务服务层
│   │   ├── algorithms/        # ❌ 排产算法（待实现）
│   │   └── utils/             # 工具函数
│   └── requirements.txt
├── docs/                       # ✅ 项目文档
│   ├── requirements-detail.md  # 需求细化文档
│   ├── technical-design.md     # 技术设计文档
│   ├── algorithm-design.md     # 算法设计文档
│   └── ux-design.md           # 用户体验设计
└── scripts/                    # ✅ 数据库脚本
    └── database-schema.sql
```

## 🚀 快速开始

### 环境要求

- Node.js 20.19.0+ (前端)
- Python 3.11+ (后端)
- MySQL 8.0+
- Redis 7.0+

### 前端开发

```bash
cd frontend/
npm install
npm run dev
```

访问: `http://localhost:5173`

### 后端开发

```bash
cd backend/
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问: `http://localhost:8000`
API文档: `http://localhost:8000/docs`

## 📋 功能特性

### ✅ 已实现功能

1. **文件上传管理**
   - 拖拽上传Excel文件(.xlsx, .xls)
   - 实时上传进度显示
   - 文件大小和格式验证
   - 上传历史记录

2. **Excel数据解析**
   - 复杂Excel结构解析（多工作表、合并单元格）
   - 机台代码列表解析
   - 日期范围解析
   - 数据验证和清洗

3. **Web用户界面**
   - 现代化响应式设计
   - 统计信息仪表板
   - 文件上传和解析流程
   - 历史记录查询和管理

4. **API服务**
   - RESTful API设计
   - 异步文件处理
   - 数据查询和分页
   - 系统健康检查

### ❌ 待实现功能

1. **排产算法引擎** - 系统核心功能
2. **工单生成和管理**
3. **MES系统集成**
4. **甘特图可视化**
5. **用户权限管理**

## 📊 开发进度

- 🟢 **前端界面**: 90% 完成
- 🟢 **数据导入**: 95% 完成
- 🟡 **后端API**: 70% 完成
- 🟡 **数据模型**: 60% 完成
- 🔴 **排产算法**: 0% 完成
- 🔴 **MES集成**: 0% 完成
- 🔴 **可视化**: 10% 完成

## 🎯 下一步开发计划

### 阶段1：核心功能补全（高优先级）
1. **排产算法引擎开发**
   - 实现规则合并处理
   - 实现规则拆分处理
   - 实现时间校正算法
   - 实现并行切分算法

2. **工单生成功能**
   - 卷包机工单生成
   - 喂丝机工单生成
   - 工单数据模型完善

### 阶段2：系统集成（中优先级）
1. **MES系统集成**
   - 轮保计划接口对接
   - 工单下发接口实现
   - 状态同步机制

2. **甘特图可视化**
   - 甘特图数据接口
   - 前端甘特图组件

### 阶段3：系统完善（低优先级）
1. **用户权限系统**
2. **业务规则配置界面**
3. **报表导出功能**
4. **系统监控增强**

## 📖 文档

- [需求细化文档](docs/requirements-detail.md) - 详细功能需求和验收标准
- [技术设计文档](docs/technical-design.md) - 技术架构和实现细节
- [算法设计文档](docs/algorithm-design.md) - 排产算法设计方案
- [用户体验设计](docs/ux-design.md) - UI/UX设计规范

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

该项目遵循 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 开发团队

- **项目负责人**: [项目经理]
- **前端开发**: Vue.js + TypeScript
- **后端开发**: FastAPI + Python
- **算法设计**: 排产优化算法

---

**注意**: 本项目目前处于开发阶段，排产算法引擎为核心待实现功能。前端界面和数据导入功能已基本完成，可用于演示和测试。
