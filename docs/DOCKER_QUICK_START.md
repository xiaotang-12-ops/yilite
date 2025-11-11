# 🐳 Docker快速启动指南

## 📋 前置要求

1. **安装Docker Desktop**
   - Windows: https://www.docker.com/products/docker-desktop
   - 确保Docker Desktop正在运行

2. **配置API密钥**
   ```bash
   # 复制环境变量模板
   cp .env.example .env
   
   # 编辑.env文件，填入实际的API密钥
   # 必须配置：
   # - DASHSCOPE_API_KEY
   # - DEEPSEEK_API_KEY
   ```

## 🚀 一键启动

```bash
# 1. 停止旧容器（如果有）
docker-compose down

# 2. 构建并启动所有服务
docker-compose up -d --build

# 3. 查看日志
docker-compose logs -f
```

## ✅ 验证服务

```bash
# 等待30-60秒后，检查服务状态
docker-compose ps

# 检查后端健康状态
curl http://localhost:8008/api/health

# 应该返回：
# {"status":"healthy","service":"assembly-manual-backend","version":"1.0.0","timestamp":"..."}
```

## 🌐 访问应用

- **前端界面**: http://localhost:3008
- **后端API**: http://localhost:8008
- **API文档**: http://localhost:8008/api/docs

## 🔧 常用命令

```bash
# 查看所有服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 停止并删除所有数据
docker-compose down -v
```

## 🐛 故障排除

### 1. 前端无法连接后端

**症状**: 前端显示"连接失败"或控制台显示`ERR_CONNECTION_REFUSED`

**解决方案**:
```bash
# 检查后端是否正常运行
docker-compose logs backend

# 检查健康状态
curl http://localhost:8008/api/health

# 如果后端正常，重启前端
docker-compose restart frontend
```

### 2. PDF解析失败

**症状**: 日志显示"提取到 0 个零件"

**解决方案**:
```bash
# 重新构建后端（包含所有依赖）
docker-compose build --no-cache backend
docker-compose up -d backend
```

### 3. 端口冲突

**症状**: 启动失败，提示端口已被占用

**解决方案**:
```bash
# 修改docker-compose.yml中的端口映射
# 例如将3008改为3009
ports:
  - "3009:80"  # 前端
  - "8009:8008"  # 后端
```

### 4. 构建失败

**症状**: `docker-compose build`失败

**解决方案**:
```bash
# 清理Docker缓存
docker system prune -a

# 重新构建
docker-compose build --no-cache
```

## 📊 性能优化

### 增加资源限制

编辑`docker-compose.yml`，添加资源限制：

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

## 🔄 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 停止旧容器
docker-compose down

# 3. 重新构建并启动
docker-compose up -d --build

# 4. 清理旧镜像
docker image prune -a
```

## 📝 注意事项

1. **首次启动**可能需要1-2分钟，请耐心等待
2. **API密钥**必须正确配置，否则服务无法正常工作
3. **数据持久化**：uploads、output等目录会自动挂载到主机
4. **日志文件**：可在`logs`目录查看详细日志

## 🆘 获取帮助

如遇到问题，请：
1. 查看日志：`docker-compose logs -f`
2. 检查服务状态：`docker-compose ps`
3. 查看详细文档：[README_DOCKER.md](README_DOCKER.md)

