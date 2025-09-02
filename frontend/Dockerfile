# APS智慧排产系统 - 前端 Dockerfile
# 多阶段构建：Node.js 构建 + Nginx 服务

# 第一阶段：构建阶段
FROM node:22-alpine AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production

# 复制 package 文件
COPY package*.json ./

# 安装依赖（使用 npm ci 确保一致性）
RUN npm ci --only=production --no-audit --no-fund

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 第二阶段：生产阶段
FROM nginx:1.25-alpine

# 安装 curl 用于健康检查
RUN apk add --no-cache curl

# 创建非特权用户
RUN addgroup -g 1001 -S aps && \
    adduser -S aps -u 1001

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 设置正确的权限
RUN chown -R aps:aps /usr/share/nginx/html && \
    chown -R aps:aps /var/cache/nginx && \
    chown -R aps:aps /var/log/nginx && \
    chown -R aps:aps /etc/nginx/conf.d

# 修改 nginx.conf 以支持非特权用户
RUN touch /var/run/nginx.pid && \
    chown -R aps:aps /var/run/nginx.pid

# 切换到非特权用户
USER aps

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
