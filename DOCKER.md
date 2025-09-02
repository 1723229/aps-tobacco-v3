# APS智慧排产系统 - Docker 部署指南

本文档介绍如何使用 Docker 容器化部署 APS 智慧排产系统。

## 🏗️ 架构概览

系统采用微服务架构，包含以下组件：

- **Frontend**: Vue 3 + TypeScript + Nginx (端口: 80)
- **Backend**: Python FastAPI (端口: 8000)
- **MySQL**: 数据库 (端口: 3306)
- **Redis**: 缓存 (端口: 6379)

## 📋 前置要求

- Docker 20.0+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd aps-tobacco-v3
```

### 2. 使用 Docker Compose 启动（推荐）
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 访问应用
- **前端界面**: http://localhost
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 🔧 单独构建

### 后端 Dockerfile
```bash
cd backend
docker build -t aps-backend .
docker run -d -p 8000:8000 \
  -e MYSQL_URL="mysql+aiomysql://user:pass@host:3306/aps" \
  -e REDIS_URL="redis://:pass@host:6379/0" \
  aps-backend
```

### 前端 Dockerfile
```bash
cd frontend
docker build -t aps-frontend .
docker run -d -p 80:80 aps-frontend
```

## ⚙️ 环境配置

### 环境变量

#### 后端环境变量
```bash
# 数据库配置
MYSQL_URL=mysql+aiomysql://user:password@host:3306/database
MYSQL_ECHO=false
MYSQL_POOL_SIZE=20

# Redis 配置
REDIS_URL=redis://:password@host:6379/0
REDIS_MAX_CONNECTIONS=50

# 应用配置
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=4

# 日志配置
LOG_LEVEL=info
```

#### MySQL 环境变量
```bash
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_DATABASE=aps
MYSQL_USER=aps_user
MYSQL_PASSWORD=your_password
```

#### Redis 环境变量
```bash
# Redis 使用命令行参数配置密码
# --requirepass your_password
```

## 🛠️ 开发环境

### 开发模式启动
```bash
# 仅启动基础设施（数据库、缓存）
docker-compose up -d mysql redis

# 本地运行后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 本地运行前端
cd frontend
npm install
npm run dev
```

### 实时代码挂载
```bash
# 修改 docker-compose.yml，添加代码挂载
volumes:
  - ./backend/app:/app/app
  - ./frontend/src:/app/src
```

## 📊 监控和健康检查

### 健康检查端点
- 后端健康检查: `GET /health`
- 前端健康检查: `GET /` (200 状态码)

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mysql
docker-compose logs redis

# 实时跟踪日志
docker-compose logs -f backend
```

## 🔐 生产环境配置

### 安全配置
1. **修改默认密码**: 更改所有默认密码
2. **网络隔离**: 使用内部网络，不暴露数据库端口
3. **HTTPS**: 配置 SSL 证书
4. **防火墙**: 限制访问端口

### 性能优化
1. **资源限制**: 设置容器内存和 CPU 限制
2. **数据持久化**: 使用外部存储卷
3. **负载均衡**: 配置多实例和负载均衡器

### 生产环境 docker-compose 示例
```yaml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    restart: always
    
  frontend:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    restart: always
```

## 🚨 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查 MySQL 服务状态
docker-compose logs mysql

# 检查网络连接
docker-compose exec backend ping mysql
```

#### 2. Redis 连接失败
```bash
# 检查 Redis 服务状态
docker-compose logs redis

# 测试 Redis 连接
docker-compose exec backend redis-cli -h redis ping
```

#### 3. 前端访问 API 失败
```bash
# 检查后端服务状态
curl http://localhost:8000/health

# 检查 Nginx 配置
docker-compose exec frontend nginx -t
```

#### 4. 容器启动失败
```bash
# 查看容器详细信息
docker inspect <container_name>

# 检查资源使用情况
docker stats
```

### 清理和重置
```bash
# 停止所有服务
docker-compose down

# 删除所有数据卷（注意：会丢失数据）
docker-compose down -v

# 重新构建镜像
docker-compose build --no-cache

# 清理未使用的镜像
docker system prune -a
```

## 📝 维护建议

1. **定期备份**: 备份 MySQL 数据和 Redis 数据
2. **更新镜像**: 定期更新基础镜像和依赖
3. **监控资源**: 监控 CPU、内存、磁盘使用情况
4. **日志轮转**: 配置日志轮转防止磁盘满载
5. **安全扫描**: 定期扫描镜像安全漏洞

## 🔗 相关链接

- [项目文档](./README.md)
- [API 文档](http://localhost:8000/docs)
- [技术设计文档](./docs/technical-design.md)
- [算法设计文档](./docs/algorithm-design.md)
