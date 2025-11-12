# 🐳 Docker 快速部署指南

> 使用 Docker 一键部署智能装配说明书生成系统

## 📋 前置要求

- **Docker**: 版本 20.10 或更高
- **Docker Compose**: 版本 2.0 或更高
- **OpenRouter API Key**: 从 [OpenRouter](https://openrouter.ai/keys) 获取

### 检查 Docker 版本

```bash
docker --version
docker-compose --version
```

---

## 🚀 快速开始（3 步部署）

### 1️⃣ 克隆项目

```bash
git clone https://github.com/xiaotang-12-ops/Mecagent.git
cd Mecagent
```

### 2️⃣ 配置 API 密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 OpenRouter API Key
# Windows 用户可以用记事本打开
notepad .env

# Linux/Mac 用户可以用 nano 或 vim
nano .env
```

**在 `.env` 文件中修改**：
```bash
OPENROUTER_API_KEY=your_actual_api_key_here
```

### 3️⃣ 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

**等待 30-60 秒**，直到看到：
```
✅ 后端服务启动成功: http://0.0.0.0:8008
✅ 前端服务启动成功
```

---

## 🌐 访问系统

启动成功后，在浏览器中访问：

- **前端界面**: http://localhost:3008
- **后端 API 文档**: http://localhost:8008/api/docs
- **健康检查**: http://localhost:8008/api/health

---

## 📂 数据持久化

系统会自动在项目目录下创建以下文件夹来保存数据：

```
Mecagent/
├── uploads/          # 上传的 PDF 和 3D 模型文件
├── output/           # 生成的装配说明书
├── logs/             # 系统日志
├── pipeline_output/  # 处理流程中间结果
└── debug_output/     # 调试信息
```

**即使重启 Docker 容器，这些数据也不会丢失。**

---

## 🛠️ 常用命令

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看前端日志
docker-compose logs -f frontend
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 只重启后端
docker-compose restart backend

# 只重启前端
docker-compose restart frontend
```

### 停止服务

```bash
# 停止所有服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据）
docker-compose down

# 停止并删除容器和数据卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 更新系统

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build

# 3. 重启服务
docker-compose up -d
```

---

## 🔧 故障排除

### 问题 1: 端口被占用

**错误信息**：
```
Error: bind: address already in use
```

**解决方案**：
修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  backend:
    ports:
      - "8009:8008"  # 改为 8009
  frontend:
    ports:
      - "3009:80"    # 改为 3009
```

### 问题 2: API 密钥错误

**错误信息**：
```
❌ OpenRouter API 调用失败: 401 Unauthorized
```

**解决方案**：
1. 检查 `.env` 文件中的 `OPENROUTER_API_KEY` 是否正确
2. 确保 API Key 有足够的额度
3. 重启服务：`docker-compose restart`

### 问题 3: 容器启动失败

**解决方案**：

```bash
# 1. 查看详细日志
docker-compose logs backend

# 2. 检查容器状态
docker-compose ps

# 3. 重新构建并启动
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 问题 4: 前端无法连接后端

**解决方案**：

1. 检查后端是否正常运行：
   ```bash
   curl http://localhost:8008/api/health
   ```

2. 检查前端配置（`frontend/src/config.ts`）中的 API 地址是否正确

3. 检查 Docker 网络：
   ```bash
   docker network ls
   docker network inspect assembly-manual_assembly-network
   ```

---

## 🔒 安全建议

1. **不要将 `.env` 文件提交到 Git**
   - `.env` 文件已在 `.gitignore` 中排除
   - 只提交 `.env.example` 模板

2. **定期更新 API 密钥**
   - 定期轮换 OpenRouter API Key
   - 监控 API 使用量

3. **生产环境部署**
   - 使用反向代理（Nginx/Caddy）
   - 启用 HTTPS
   - 配置防火墙规则

---

## 📊 系统资源要求

### 最低配置
- **CPU**: 2 核
- **内存**: 4 GB
- **磁盘**: 10 GB 可用空间

### 推荐配置
- **CPU**: 4 核或更多
- **内存**: 8 GB 或更多
- **磁盘**: 50 GB 可用空间（用于存储生成的说明书）

---

## 🆘 获取帮助

如果遇到问题：

1. **查看日志**: `docker-compose logs -f`
2. **检查文档**: 阅读 [README.md](README.md)
3. **提交 Issue**: [GitHub Issues](https://github.com/xiaotang-12-ops/Mecagent/issues)

---

## 📝 下一步

部署成功后，你可以：

1. **上传文件**: 在前端界面上传 PDF 图纸和 3D 模型
2. **生成说明书**: 点击"开始生成"按钮
3. **查看结果**: 在"说明书列表"中查看和下载生成的说明书
4. **编辑内容**: 使用管理员模式编辑说明书内容

---

**祝你使用愉快！** 🎉

