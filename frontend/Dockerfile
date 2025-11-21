# 智能装配说明书生成系统 - 前端Dockerfile
# 多阶段构建: Node.js构建 + Nginx服务

# 启用 BuildKit 语法以支持缓存挂载
# syntax=docker/dockerfile:1.4

# ============ 构建阶段 ============
FROM node:18-alpine AS builder

WORKDIR /app

# 配置国内镜像源（淘宝镜像）加速依赖下载
RUN npm config set registry https://registry.npmmirror.com

# 复制package文件（只复制依赖相关文件，利用Docker层缓存）
COPY package*.json ./

# 使用 BuildKit 缓存挂载来缓存 npm 缓存目录
# 即使层缓存失效，npm 也能复用之前下载的包，大幅提升构建速度
RUN --mount=type=cache,target=/root/.npm \
    npm install

# 复制源代码（放在 npm install 之后，避免代码修改导致重新安装依赖）
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

