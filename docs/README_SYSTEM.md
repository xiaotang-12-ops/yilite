# 🏭 智能装配说明书生成系统

> **双通道架构版本** - 让普通工人看完AI生成的装配说明书也能进行加工

## 📋 项目概述

本系统采用创新的双通道架构，通过PyPDF文本解析 + Qwen3-VL视觉解析，结合DeepSeek融合推理，自动生成工人友好的装配说明书。

### 🏗️ 系统架构

```
PDF工程图纸 + 3D模型 
    ↓
双通道解析（文本通道 + 视觉通道）
    ↓
候选事实JSON（统一数据契约）
    ↓
DeepSeek融合推理专家
    ↓
装配规范JSON
    ↓
工程师人工复核
    ↓
HTML装配说明书生成
    ↓
分发给工人（专用界面）
```

## 🚀 快速开始

### 方式1：一键启动（推荐）
```bash
python start.py
```

### 方式2：分别启动
```bash
# 启动后端
python app.py

# 启动前端（新终端）
cd frontend
npm run dev
```

### 方式3：系统检查
```bash
python system_check.py
```

## 📍 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000  
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

## 🎯 核心功能

### 👨‍💼 工程师界面
- **文件上传**: 支持PDF工程图纸和3D模型文件
- **AI处理监控**: 实时查看双通道解析进度
- **人工复核**: 检查和修正AI解析结果
- **质量检查**: 多维度质量评估和报告
- **工人分发**: 选择工人并分发装配任务

### 👷‍♂️ 工人界面  
- **3D模型查看**: 交互式3D模型显示和操作
- **装配指导**: 分步骤装配说明和注意事项
- **问题反馈**: 快速报告问题和获取帮助
- **进度跟踪**: 实时更新装配进度

## 🔧 技术栈

### 后端
- **FastAPI**: 现代化API框架
- **PyPDF2 + Camelot**: PDF文本和表格解析
- **Qwen3-VL**: 阿里云视觉大模型
- **DeepSeek**: 融合推理大模型
- **Uvicorn**: ASGI服务器

### 前端
- **Vue 3**: 渐进式JavaScript框架
- **Element Plus**: Vue 3 UI组件库
- **Three.js**: 3D图形渲染库
- **Vite**: 现代化构建工具

## 📦 安装依赖

### Python依赖
```bash
pip install -r requirements.txt
```

### 前端依赖
```bash
cd frontend
npm install
```

## ⚙️ 环境配置

### API密钥设置
```bash
# DeepSeek API密钥
export DEEPSEEK_API_KEY="your_deepseek_api_key"

# 阿里云DashScope API密钥  
export DASHSCOPE_API_KEY="your_dashscope_api_key"
```

### 目录结构
```
智能装配说明书项目/
├── app.py                 # 统一后端入口
├── start.py              # 一键启动脚本
├── system_check.py       # 系统状态检查
├── frontend/             # 前端项目
├── core/                 # 核心解析组件
├── models/               # AI模型组件
├── processors/           # 文件处理器
├── generators/           # HTML生成器
├── static/               # 静态文件
├── output/               # 输出文件
├── uploads/              # 上传文件
└── temp/                 # 临时文件
```

## 🎨 前端组件

### 工程师界面组件
- `FileUploadSection.vue` - 文件上传
- `AIProcessingSection.vue` - AI处理进度
- `HumanReviewSection.vue` - 人工复核
- `QualityCheckSection.vue` - 质量检查
- `WorkerDistributionSection.vue` - 工人分发

### 工人界面组件
- `WorkerThreeViewer.vue` - 3D模型查看器
- `IssueReportDialog.vue` - 问题反馈对话框
- `HelpRequestDialog.vue` - 帮助请求对话框

## 🔍 API接口

### 基础接口
- `GET /` - 系统首页
- `GET /api/health` - 健康检查
- `GET /docs` - API文档

### 文件管理
- `POST /api/upload` - 文件上传
- `GET /api/files/{file_id}` - 获取文件信息

### 任务管理
- `POST /api/tasks` - 创建处理任务
- `POST /api/tasks/{task_id}/process` - 开始处理
- `GET /api/tasks/{task_id}/status` - 获取任务状态
- `POST /api/tasks/{task_id}/cancel` - 取消任务

### 工人管理
- `GET /api/workers` - 获取工人列表
- `POST /api/distribute` - 分发装配说明书
- `POST /api/issues` - 问题反馈
- `POST /api/help` - 请求帮助

## 🐛 已知问题

### 🔧 需要修复的问题
- [ ] **3D模型渲染问题**: WorkerThreeViewer组件中Three.js模型无法正常渲染
- [ ] **依赖包缺失**: dashscope, PyPDF2, camelot-py, Pillow等包需要安装
- [ ] **API密钥配置**: 需要正确设置DEEPSEEK_API_KEY和DASHSCOPE_API_KEY

### ✅ 已完成的功能
- [x] 双通道架构核心流程
- [x] 完整的前端组件系统
- [x] 统一的后端API服务
- [x] 前后端集成和通信
- [x] 文件上传和处理
- [x] 任务管理和状态跟踪

## 📊 系统状态

当前系统完成度：**85%**

```
✅ P0 - 核心流程测试 (100%)
✅ P1 - 前端组件开发 (100%) 
✅ P2 - 用户体验优化 (100%)
🔄 P3 - 问题修复和完善 (进行中)
```

## 🎯 下一步计划

1. **修复3D模型渲染问题**
   - 调试Three.js集成
   - 检查WebGL兼容性
   - 优化模型加载逻辑

2. **完善依赖管理**
   - 更新requirements.txt
   - 添加依赖检查脚本
   - 优化安装流程

3. **增强错误处理**
   - 添加更多错误提示
   - 改进用户体验
   - 增加日志记录

## 📞 技术支持

如果遇到问题，请：

1. 运行系统检查：`python system_check.py`
2. 查看生成的系统报告
3. 检查API密钥配置
4. 确认依赖包安装

## 📄 许可证

本项目采用MIT许可证。

---

**开发团队**: 架构设计Agent → 测试调优Agent  
**项目版本**: 2.0.0  
**最后更新**: 2024-01-16
