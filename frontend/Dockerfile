# 智能装配说明书生成系统 - 前端Dockerfile
# 多阶段构建: Node.js构建 + Nginx服务

# ============ 构建阶段 ============
FROM node:18-alpine AS builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖（包括可选依赖以支持alpine）
RUN npm install

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ============ 生产阶段 ============
FROM nginx:alpine

# 复制自定义nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]

