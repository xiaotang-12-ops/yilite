# 🐳 Docker部署指南

智能装配说明书生成系统的Docker容器化部署文档。

## 📋 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [常用命令](#常用命令)
- [故障排除](#故障排除)
- [生产环境部署](#生产环境部署)

---

## 🔧 系统要求

### 必需软件
- **Docker**: >= 20.10
- **Docker Compose**: >= 2.0

### 硬件要求
- **CPU**: 2核心以上
- **内存**: 4GB以上（推荐8GB）
- **磁盘**: 10GB可用空间

### API密钥
- **阿里云DashScope API密钥** (必需)
- **DeepSeek API密钥** (必需)
- **OpenRouter API密钥** (可选，用于Gemini模型)

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd 装修说明书项目
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入实际的API密钥
nano .env  # 或使用其他编辑器
```

**必须配置的环境变量：**
```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 3. 构建并启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 验证服务

```bash
# 等待服务启动（约30-60秒）
# 检查后端健康状态
curl http://localhost:8008/api/health

# 应该返回：
# {"status":"healthy","service":"assembly-manual-backend","version":"1.0.0","timestamp":"..."}

# 检查前端是否可访问
curl -I http://localhost:3008

# 应该返回：HTTP/1.1 200 OK
```

### 5. 访问应用

- **前端界面**: http://localhost:3008
- **后端API**: http://localhost:8008
- **API文档**: http://localhost:8008/api/docs
- **健康检查**: http://localhost:8008/api/health

**首次启动可能需要1-2分钟，请耐心等待服务完全就绪。**

---

## ⚙️ 详细配置

### 服务架构

```
┌─────────────────┐
│   浏览器        │
└────────┬────────┘
         │ :80
         ▼
┌─────────────────┐
│  Frontend       │
│  (Nginx)        │
└────────┬────────┘
         │ API代理
         ▼
┌─────────────────┐
│  Backend        │
│  (FastAPI)      │ :8000
└─────────────────┘
```

### 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|---------|---------|------|
| Frontend | 80 | 3008 | Web界面 |
| Backend | 8008 | 8008 | API服务 |

### 数据持久化

以下目录会被挂载到主机，确保数据持久化：

```yaml
volumes:
  - ./uploads:/app/uploads              # 上传的文件
  - ./output:/app/output                # 生成的说明书
  - ./static:/app/static                # 静态资源
  - ./pipeline_output:/app/pipeline_output  # 处理流程输出
  - ./debug_output:/app/debug_output    # 调试输出
  - ./logs:/app/logs                    # 日志文件
  - ./temp:/app/temp                    # 临时文件
```

---

## 📝 常用命令

### 启动和停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 停止并删除所有容器、网络、卷
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看最近100行日志
docker-compose logs --tail=100 backend
```

### 重新构建

```bash
# 重新构建所有服务
docker-compose build

# 重新构建特定服务
docker-compose build backend
docker-compose build frontend

# 强制重新构建（不使用缓存）
docker-compose build --no-cache
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 以root用户进入
docker-compose exec -u root backend bash
```

### 健康检查

```bash
# 检查服务健康状态
docker-compose ps

# 查看后端健康检查
curl http://localhost:8008/api/health

# 查看前端健康检查
curl http://localhost:3008/
```

---

## 🔍 故障排除

### 1. 服务无法启动

**问题**: 容器启动失败

**解决方案**:
```bash
# 查看详细日志
docker-compose logs backend

# 检查环境变量是否正确配置
docker-compose config

# 重新构建
docker-compose down
docker-compose up -d --build
```

### 2. API密钥错误

**问题**: 后端日志显示API密钥未设置

**解决方案**:
```bash
# 检查.env文件是否存在
ls -la .env

# 验证环境变量
docker-compose exec backend env | grep API_KEY

# 重新配置.env后重启
docker-compose restart backend
```

### 3. 前端无法访问后端

**问题**: 前端页面显示API连接失败

**解决方案**:
```bash
# 检查网络连接
docker-compose exec frontend ping backend

# 检查nginx配置
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# 重启前端服务
docker-compose restart frontend
```

### 4. 端口冲突

**问题**: 端口已被占用

**解决方案**:
```bash
# 修改docker-compose.yml中的端口映射
# 例如将80改为8080
ports:
  - "8080:80"

# 重新启动
docker-compose up -d
```

### 5. 磁盘空间不足

**问题**: 构建失败或运行缓慢

**解决方案**:
```bash
# 清理未使用的Docker资源
docker system prune -a

# 清理未使用的卷
docker volume prune

# 查看磁盘使用情况
docker system df
```

---

## 🏭 生产环境部署

### 1. 安全配置

**修改docker-compose.yml**:
```yaml
services:
  backend:
    # 不暴露后端端口到主机
    # ports:
    #   - "8000:8000"
    expose:
      - "8000"
```

**使用secrets管理敏感信息**:
```yaml
secrets:
  dashscope_key:
    file: ./secrets/dashscope_key.txt
  deepseek_key:
    file: ./secrets/deepseek_key.txt

services:
  backend:
    secrets:
      - dashscope_key
      - deepseek_key
```

### 2. 性能优化

**增加资源限制**:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 3. 日志管理

**配置日志驱动**:
```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 使用反向代理

推荐在生产环境使用Nginx或Traefik作为反向代理，配置HTTPS：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. 备份策略

```bash
# 备份数据卷
docker run --rm \
  -v assembly-backend_uploads:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/uploads-$(date +%Y%m%d).tar.gz /data

# 定期备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
tar czf $BACKUP_DIR/uploads.tar.gz ./uploads
tar czf $BACKUP_DIR/output.tar.gz ./output
tar czf $BACKUP_DIR/pipeline_output.tar.gz ./pipeline_output
EOF

chmod +x backup.sh
```

---

## 📊 监控和维护

### 查看资源使用

```bash
# 查看容器资源使用情况
docker stats

# 查看特定容器
docker stats assembly-backend assembly-frontend
```

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -a
```

---

## 📞 支持

如有问题，请查看：
- [主README](README.md)
- [系统文档](README_SYSTEM.md)
- [API文档](http://localhost:8000/api/docs)

或提交Issue到项目仓库。

