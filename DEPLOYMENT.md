# 🚀 部署指南

本文档说明如何从 GitHub 克隆项目并使用 Docker 部署智能装配说明书生成系统。

**当前版本**: v2.1.48 | [查看所有版本](https://github.com/xiaotang-12-ops/yilite/releases)

---

## 📋 前置要求

在开始之前，请确保你的系统已安装以下软件：

### 必需软件
- **Docker**: 版本 20.10 或更高
- **Docker Compose**: 版本 2.0 或更高
- **Git**: 用于克隆代码

### 检查安装
```bash
# 检查 Docker 版本
docker --version
# 输出示例: Docker version 24.0.0, build ...

# 检查 Docker Compose 版本
docker-compose --version
# 输出示例: Docker Compose version v2.20.0

# 检查 Git 版本
git --version
# 输出示例: git version 2.40.0
```

---

## 🔧 部署步骤

### 步骤1: 克隆项目

#### 部署最新版本（推荐）

```bash
# 克隆项目到本地
git clone https://github.com/xiaotang-12-ops/yilite.git

# 进入项目目录
cd yilite
```

#### 部署特定版本

如果你想部署特定版本（例如 `v2.1.48`），可以使用以下命令：

```bash
# 克隆项目
git clone https://github.com/xiaotang-12-ops/yilite.git
cd yilite

# 查看所有可用版本
git tag

# 切换到特定版本
git checkout v2.1.48

# 进入项目目录
cd yilite
```

**查看所有版本**: https://github.com/xiaotang-12-ops/yilite/releases

### 步骤2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
# Windows 用户可以使用记事本打开
notepad .env

# Linux/Mac 用户可以使用 vim 或 nano
vim .env
```

**重要**: 必须填写 `OPENROUTER_API_KEY`，否则系统无法正常工作！

`.env` 文件示例：
```env
# OpenRouter API密钥 (必需)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx

# 可选配置
DEBUG=false
VERBOSE=false
```

### 步骤3: 准备 HTTPS 证书目录

前端容器默认同时提供 `HTTP(3008)` 和 `HTTPS(3443)`，因此宿主机本地必须准备证书目录：

```text
frontend/ssl/
├── server.crt
├── server.key
├── rootCA.crt   # 可选，用于给客户端安装信任链
└── rootCA.cer   # 可选，Windows 安装时常用
```

说明：
- `frontend/ssl/` 是本地部署目录，不随仓库分发
- `server.crt` / `server.key` 会在运行时只读挂载到容器 `/etc/nginx/ssl`
- 建议每个客户环境使用独立证书，避免多个现场共用同一把私钥

### 步骤4: 启动服务

```bash
# 构建并启动所有服务（首次启动需要下载镜像和构建，可能需要5-10分钟）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志（可选）
docker-compose logs -f
```

### 步骤5: 验证部署

等待服务启动完成（约30-60秒），然后访问：

- **前端页面（HTTP）**: http://localhost:3008
- **前端页面（HTTPS，自签证书）**: https://localhost:3443
- **后端API**: http://localhost:8008/api/docs

如果能正常访问，说明部署成功！🎉

---

## 📊 服务说明

### 服务列表

| 服务名称 | 容器名称 | 端口 | 说明 |
|---------|---------|------|------|
| backend | assembly-backend-v2.1.48 | 8008 | FastAPI 后端服务 |
| frontend | assembly-frontend-v2.1.48 | 3008 / 3443 (映射到容器的 80 / 443 端口) | Vue 3 前端服务，支持 HTTP/HTTPS，证书来自宿主机挂载 |

### 数据持久化

以下目录会被挂载到宿主机，数据不会因为容器重启而丢失：

- `./uploads` - 用户上传的文件
- `./output` - 生成的装配说明书
- `./static` - 静态资源文件
- `./pipeline_output` - Pipeline 输出数据
- `./debug_output` - 调试输出
- `./logs` - 日志文件
- `./temp` - 临时文件

---

## 🛠️ 常用命令

### 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 只启动后端
docker-compose up -d backend

# 只启动前端
docker-compose up -d frontend
```

### 停止服务
```bash
# 停止所有服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 查看最近100行日志
docker-compose logs --tail=100
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启后端
docker-compose restart backend

# 重启前端
docker-compose restart frontend
```

### 重新构建
```bash
# 重新构建所有服务（代码更新后需要执行）
docker-compose build

# 重新构建并启动
docker-compose up -d --build

# 只重新构建后端
docker-compose build backend
```

### 进入容器
```bash
# 进入后端容器
docker exec -it assembly-backend-v2.1.48 bash

# 进入前端容器
docker exec -it assembly-frontend-v2.1.48 sh

# 在后端容器中执行Python命令
docker exec -it assembly-backend-v2.1.48 python -c "print('Hello')"
```

---

## 🔍 故障排除

### 问题1: 端口被占用

**错误信息**:
```
Error: bind: address already in use
```

**解决方案**:
1. 检查端口占用情况：
   ```bash
   # Windows
   netstat -ano | findstr :3008
   netstat -ano | findstr :8008
   
   # Linux/Mac
   lsof -i :3008
   lsof -i :8008
   ```

2. 修改 `docker-compose.yml` 中的端口映射：
   ```yaml
   ports:
     - "3009:80"  # 将3008改为3009
   ```

### 问题2: 服务启动失败

**检查步骤**:
1. 查看服务状态：
   ```bash
   docker-compose ps
   ```

2. 查看详细日志：
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

3. 检查健康状态：
   ```bash
   docker inspect assembly-backend-v2.1.48 | grep -A 10 Health
   docker inspect assembly-frontend-v2.1.48 | grep -A 10 Health
   ```

### 问题3: API密钥错误

**错误信息**:
```
Error: OPENROUTER_API_KEY not set
```

**解决方案**:
1. 确认 `.env` 文件存在且包含正确的API密钥
2. 重启服务：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 问题4: 前端无法连接后端

**检查步骤**:
1. 确认后端服务正常运行：
   ```bash
   curl http://localhost:8008/api/health
   ```

2. 检查网络连接：
   ```bash
   docker network ls
   docker network inspect assembly-network
   ```

3. 检查前端配置（`frontend/src/` 中的API地址）

### 问题5: 构建失败

**常见原因**:
- 网络问题（无法下载依赖）
- 磁盘空间不足
- Docker 版本过低

**解决方案**:
1. 清理 Docker 缓存：
   ```bash
   docker system prune -a
   ```

2. 检查磁盘空间：
   ```bash
   df -h
   ```

3. 使用国内镜像源（已在 Dockerfile 中配置）

---

## 🔄 更新代码

当 GitHub 仓库有新代码时，按以下步骤更新：

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 停止服务
docker-compose down

# 3. 重新构建并启动
docker-compose up -d --build

# 4. 查看日志确认启动成功
docker-compose logs -f
```

---

## 📝 生产环境建议

### 安全配置
1. **修改默认端口**: 不要使用默认的 3008 和 8008 端口
2. **使用 HTTPS**: 为每个客户环境准备独立 SSL 证书，并通过 `frontend/ssl/` 本地挂载
3. **限制访问**: 使用防火墙限制访问来源
4. **定期备份**: 备份 `output/` 和 `uploads/` 目录

### 性能优化
1. **增加资源限制**: 在 `docker-compose.yml` 中配置 CPU 和内存限制
2. **使用 Redis**: 添加缓存层提升性能
3. **负载均衡**: 使用 Nginx 进行负载均衡

### 监控和日志
1. **日志收集**: 使用 ELK 或 Loki 收集日志
2. **监控告警**: 使用 Prometheus + Grafana 监控服务状态
3. **健康检查**: 定期检查服务健康状态

---

## 📞 获取帮助

如果遇到问题：

1. **查看文档**: 阅读 `README.md` 和 `docs/` 目录下的文档
2. **查看日志**: 使用 `docker-compose logs` 查看详细日志
3. **提交 Issue**: 在 GitHub 上提交 Issue 描述问题
4. **联系维护者**: 通过 GitHub 联系项目维护者

---

## ✅ 部署检查清单

部署完成后，请检查以下项目：

- [ ] Docker 和 Docker Compose 已安装
- [ ] 代码已从 GitHub 克隆
- [ ] `.env` 文件已配置（包含 API 密钥）
- [ ] `frontend/ssl/server.crt` 与 `frontend/ssl/server.key` 已放到宿主机本地
- [ ] 服务已启动（`docker-compose ps` 显示所有服务为 `Up`）
- [ ] 前端页面可以访问（http://localhost:3008）
- [ ] HTTPS 页面可以访问（https://localhost:3443）
- [ ] 后端 API 可以访问（http://localhost:8008/api/docs）
- [ ] 健康检查通过（`docker inspect` 显示 `healthy`）
- [ ] 可以上传文件并生成装配说明书

---

**部署成功！** 🎉

现在你可以开始使用智能装配说明书生成系统了！

