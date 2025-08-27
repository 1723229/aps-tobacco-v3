# 开发指南

## 快速开始

### 1. 环境准备
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问应用
http://localhost:5173
```

### 2. 目录结构
```
frontend/
├── src/
│   ├── components/      # 可复用组件
│   ├── views/          # 页面组件
│   ├── services/       # API服务
│   ├── stores/         # 状态管理
│   ├── types/          # 类型定义
│   ├── utils/          # 工具函数
│   └── router/         # 路由配置
├── docs/               # 项目文档
└── public/             # 静态资源
```

## 开发规范

### 组件开发
1. 使用Vue 3 Composition API
2. 使用`<script setup>`语法
3. 组件名使用PascalCase
4. Props和Emits使用TypeScript类型定义

### 代码风格
1. 使用2空格缩进
2. 字符串使用单引号
3. 语句末尾加分号
4. 使用驼峰命名法

### 类型定义
1. 所有API接口都要有类型定义
2. 组件Props使用interface定义
3. 复杂对象使用type或interface

## 功能模块

### 文件上传
- 支持拖拽上传
- 文件大小和格式验证
- 上传进度显示
- 错误处理

### 数据展示
- 表格分页和排序
- 筛选功能
- 数据导出
- 状态显示

### 状态管理
- 使用Pinia管理状态
- 按功能模块拆分store
- 提供计算属性和方法

## API集成

### 请求配置
```typescript
// 基础配置
const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000
})
```

### 错误处理
```typescript
// 统一错误处理
import { handleError } from '@/utils/error-handler'

try {
  const response = await api.upload(file)
} catch (error) {
  handleError(error, '文件上传')
}
```

## 常用命令

```bash
# 开发
npm run dev

# 构建
npm run build

# 预览
npm run preview

# 类型检查
npm run typecheck

# 代码检查
npm run lint

# 代码格式化
npm run format
```

## 调试技巧

### Vue DevTools
安装Vue DevTools浏览器扩展进行调试

### 网络请求
使用浏览器开发者工具查看API请求

### 状态管理
使用Pinia DevTools查看状态变化

## 常见问题

### 1. 安装依赖失败
```bash
# 清除缓存
npm cache clean --force

# 删除node_modules重新安装
rm -rf node_modules package-lock.json
npm install
```

### 2. 开发服务器启动失败
检查端口占用情况，修改vite.config.ts中的端口配置

### 3. API请求失败
检查后端服务是否启动，确认API基础URL配置

## 部署配置

### 环境变量
```bash
# 生产环境
VITE_API_BASE_URL=https://api.example.com
VITE_API_PREFIX=/api/v1
```

### 构建配置
```typescript
// vite.config.ts
export default defineConfig({
  base: '/aps/', // 子路径部署
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

## 性能优化

### 代码分割
使用动态导入进行路由级代码分割

### 组件懒加载
对大型组件使用懒加载

### 图片优化
使用WebP格式，设置适当的图片大小

## 安全考虑

### XSS防护
- 不使用v-html渲染用户输入
- 对用户输入进行转义

### CSRF防护
- API请求包含CSRF令牌
- 使用SameSite Cookie

### 敏感信息
- 不在前端存储敏感信息
- 使用HTTPS传输

## 测试指南

### 单元测试
```bash
# 运行测试
npm run test

# 测试覆盖率
npm run test:coverage
```

### E2E测试
```bash
# 运行E2E测试
npm run test:e2e
```

## 版本控制

### Git工作流
1. 从main分支创建功能分支
2. 开发完成后提交PR
3. 代码审查后合并

### 提交信息
```
feat: 添加文件上传功能
fix: 修复表格排序问题
docs: 更新API文档
style: 调整组件样式
refactor: 重构错误处理逻辑
test: 添加单元测试
```

## 贡献指南

1. Fork项目到个人仓库
2. 创建功能分支进行开发
3. 遵循代码规范和测试要求
4. 提交Pull Request
5. 等待代码审查和合并

## 联系方式

如有问题请联系：
- 技术负责人：xxx@example.com
- 项目经理：xxx@example.com