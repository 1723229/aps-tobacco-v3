# APS 烟草生产计划系统 - 前端

## 项目概述

这是一个基于Vue 3 + TypeScript + Element Plus开发的烟草生产计划管理系统前端应用，主要功能是处理卷包旬计划的文件上传、解析和数据展示。

## 技术栈

- **Vue 3** - 渐进式JavaScript框架
- **TypeScript** - JavaScript超集，提供类型安全
- **Element Plus** - Vue 3 UI组件库  
- **Pinia** - Vue状态管理库
- **Vue Router** - Vue官方路由管理器
- **Axios** - HTTP客户端
- **Vite** - 前端构建工具

## 项目结构

```
src/
├── components/           # 可复用组件
│   ├── DecadePlanUpload.vue     # 文件上传组件
│   ├── ParseResult.vue          # 解析结果展示组件
│   ├── DecadePlanTable.vue      # 旬计划表格组件
│   ├── ErrorBoundary.vue        # 错误边界组件
│   └── LoadingComponent.vue     # 加载组件
├── views/               # 页面视图
│   ├── Home.vue                 # 首页
│   ├── DecadePlanEntry.vue      # 卷包旬计划录入页
│   └── DecadePlanDetail.vue     # 旬计划详情页
├── services/            # API服务
│   └── api.ts                   # 旬计划API服务
├── stores/              # 状态管理
│   └── decade-plan.ts           # 旬计划相关状态
├── types/               # TypeScript类型定义
│   ├── api.ts                   # API响应类型
│   └── index.ts                 # 通用类型
├── utils/               # 工具函数
│   ├── http.ts                  # HTTP客户端配置
│   ├── error-handler.ts         # 错误处理工具
│   └── index.ts                 # 通用工具函数
├── router/              # 路由配置
│   └── index.ts                 # 路由定义
└── main.ts              # 应用入口
```

## 核心功能

### 1. 文件上传功能
- 支持Excel文件(.xlsx/.xls)拖拽上传
- 文件大小限制(最大50MB)
- 上传进度显示
- 文件验证

### 2. 数据解析
- 异步文件解析
- 解析进度追踪
- 解析结果统计
- 错误信息收集

### 3. 数据展示
- 旬计划记录表格展示
- 数据筛选和排序
- 分页显示
- 数据导出

### 4. 用户体验
- 响应式设计
- 加载状态提示
- 错误处理和提示
- 操作历史记录

## 开发环境配置

### 环境要求
- Node.js >= 16.0.0
- npm >= 7.0.0

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

### 构建生产版本
```bash
npm run build
```

### 代码检查
```bash
npm run lint
```

### 类型检查
```bash
npm run typecheck
```

## 环境变量

创建 `.env.development` 文件配置开发环境：

```bash
# 开发环境配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_PREFIX=/api/v1
```

## API接口

### 文件上传
- `POST /api/v1/plans/upload` - 上传旬计划文件

### 文件解析  
- `POST /api/v1/plans/{import_batch_id}/parse` - 解析上传的文件

### 状态查询
- `GET /api/v1/plans/{import_batch_id}/status` - 查询解析状态

### 数据获取
- `GET /api/v1/plans/{import_batch_id}/decade-plans` - 获取旬计划记录

## 页面路由

- `/` - 系统首页
- `/decade-plan/entry` - 卷包旬计划录入页面
- `/decade-plan/detail/:batchId` - 旬计划详情页面
- `/about` - 关于页面

## 组件说明

### DecadePlanUpload
文件上传组件，支持拖拽上传、进度显示、自动解析等功能。

### ParseResult  
解析结果展示组件，显示解析统计信息、数据预览、错误详情等。

### DecadePlanTable
旬计划数据表格组件，支持筛选、排序、分页、导出等功能。

## 状态管理

使用Pinia管理应用状态：
- 上传队列管理
- 解析状态追踪
- 旬计划数据缓存
- 错误信息记录

## 错误处理

实现了统一的错误处理机制：
- 网络错误处理
- API错误处理  
- 业务逻辑错误处理
- 用户友好的错误提示

## 最佳实践

1. **类型安全** - 全面使用TypeScript提供类型安全
2. **组件化** - 合理拆分可复用组件
3. **状态管理** - 使用Pinia管理复杂状态
4. **错误处理** - 统一错误处理和用户提示
5. **代码规范** - 使用ESLint和Prettier保证代码质量

## 开发注意事项

1. 确保后端API服务正常运行
2. 上传文件需要符合预定格式
3. 注意处理网络超时和错误情况
4. 保持界面响应性和用户体验

## 部署说明

1. 构建生产版本：`npm run build`
2. 将`dist`目录部署到Web服务器
3. 配置反向代理指向后端API
4. 确保静态资源正确加载

## 联系方式

如有问题请联系开发团队或查看项目文档。