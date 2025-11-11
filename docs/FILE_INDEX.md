# 文件索引 - 快速定位关键代码

---

## 🔴 需要立即修复的文件

### 1. `core/dual_channel_parser.py`
**问题**: Qwen-VL JSON解析失败，需要添加重试机制

**关键方法**:
- `_call_assembly_expert_model()` - 第300-464行
  - **需要修改**: 添加重试循环（max_retries=3）
  - **需要修改**: 添加max_tokens=4000限制
  - **需要修改**: 失败时抛出异常而不是返回空数据

**修复优先级**: 🔴 最高

---

### 2. `core/parallel_pipeline.py`
**问题1**: DeepSeek匹配结果显示0  
**问题2**: 错误时不停止流程

**关键方法**:
- `_generate_assembly_specification()` - 第403-475行
  - **需要添加**: 调试日志，打印DeepSeek完整返回
  - **需要修改**: 根据实际结构调整字段提取逻辑
  
- `process()` - 第162-169行
  - **需要修改**: 视觉分析失败时抛出异常（不返回空数据）

**修复优先级**: 🔴 最高

---

### 3. `frontend/src/views/Generator.vue`
**问题**: 错误时不停止流程

**关键方法**:
- `updateStepByLog()` - 第637-726行
  - **需要添加**: 错误级别日志的处理逻辑
  - **需要添加**: 停止进度条并显示错误对话框

**修复优先级**: 🔴 高

---

## 📁 后端文件结构

```
backend/
├── app.py                          # FastAPI主应用
│   ├── /api/generate               # 启动生成任务
│   ├── /ws/{task_id}               # WebSocket连接
│   └── /api/settings               # API密钥配置
│
├── websocket_manager.py            # WebSocket管理
│   ├── ConnectionManager           # 连接管理器
│   └── ProgressReporter            # 进度报告器
│
├── core/
│   ├── parallel_pipeline.py        # 🔴 并行处理流水线（核心）
│   │   ├── process()               # 主流程入口
│   │   ├── _process_models_with_progress()  # STEP→GLB转换
│   │   └── _generate_assembly_specification()  # 🔴 DeepSeek匹配
│   │
│   └── dual_channel_parser.py      # 🔴 双通道PDF解析
│       ├── parse()                 # 主入口
│       ├── _text_channel_parse()   # 文本通道（pypdf）
│       ├── _vision_channel_parse() # 视觉通道（Qwen-VL）
│       └── _call_assembly_expert_model()  # 🔴 调用Qwen-VL
│
├── models/
│   ├── vision_model.py             # Qwen-VL模型封装
│   │   └── analyze_with_context()  # 视觉分析
│   │
│   └── assembly_expert.py          # DeepSeek模型封装
│       └── generate_assembly_specification()  # 生成装配规范
│
├── processors/
│   └── file_processor.py           # 文件处理
│       ├── PDFProcessor            # PDF处理
│       │   └── extract_text()      # 提取文本
│       │
│       └── ModelProcessor          # 3D模型处理
│           ├── step_to_glb()       # STEP→GLB转换
│           └── generate_explosion_data()  # 生成爆炸动画
│
└── generators/
    └── html_generator.py           # HTML说明书生成
        └── generate()              # 生成HTML
```

---

## 📁 前端文件结构

```
frontend/src/
├── views/
│   ├── Generator.vue               # 🔴 主生成界面
│   │   ├── startGeneration()       # 启动生成
│   │   ├── connectWebSocket()      # 建立WebSocket
│   │   ├── handleWebSocketMessage()  # 处理WebSocket消息
│   │   └── updateStepByLog()       # 🔴 根据日志更新步骤
│   │
│   ├── Settings.vue                # API密钥配置
│   └── Home.vue                    # 首页
│
└── components/
    └── ProcessingSteps.vue         # 步骤进度展示
        ├── addLog()                # 添加日志
        └── updateStep()            # 更新步骤状态
```

---

## 🔍 快速查找代码

### 查找Qwen-VL调用
```bash
# 文件: core/dual_channel_parser.py
# 方法: _call_assembly_expert_model()
# 行数: 约300-464行
```

### 查找DeepSeek调用
```bash
# 文件: core/parallel_pipeline.py
# 方法: _generate_assembly_specification()
# 行数: 约403-475行
```

### 查找STEP→GLB转换
```bash
# 文件: processors/file_processor.py
# 方法: ModelProcessor.step_to_glb()
# 行数: 约122-221行
```

### 查找WebSocket消息处理
```bash
# 文件: frontend/src/views/Generator.vue
# 方法: handleWebSocketMessage()
# 行数: 约480-565行
```

### 查找步骤状态更新
```bash
# 文件: frontend/src/views/Generator.vue
# 方法: updateStepByLog()
# 行数: 约637-726行
```

---

## 📊 数据流转图

```
用户上传文件
    ↓
app.py: /api/generate
    ↓
parallel_pipeline.py: process()
    ↓
┌─────────────────────────────────────────────────────┐
│  并行处理（ThreadPoolExecutor, 3个线程）              │
├─────────────────┬─────────────────┬─────────────────┤
│  通道1          │  通道2          │  通道3          │
│  PDF解析        │  STEP→GLB       │  视觉分析       │
│                 │                 │                 │
│  dual_channel_  │  file_processor │  dual_channel_  │
│  parser.py      │  .py            │  parser.py      │
│  ↓              │  ↓              │  ↓              │
│  pypdf提取文本  │  trimesh转换    │  Qwen-VL分析    │
│  ↓              │  ↓              │  ↓              │
│  53个BOM项      │  414个零件      │  11个装配关系   │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
parallel_pipeline.py: _generate_assembly_specification()
    ↓
assembly_expert.py: generate_assembly_specification()
    ↓
DeepSeek API调用
    ↓
装配规范JSON
    ↓
html_generator.py: generate()
    ↓
HTML说明书
    ↓
WebSocket推送结果
    ↓
Generator.vue: handleWebSocketMessage()
    ↓
ProcessingSteps.vue: 显示进度
```

---

## 🐛 调试文件位置

### 后端日志
- **控制台输出**: 运行 `python backend/app.py` 的终端
- **调试文件**: `debug_output/assembly_expert_output_*.json`

### 前端日志
- **浏览器控制台**: F12 → Console
- **WebSocket消息**: F12 → Network → WS → Messages

### 生成结果
- **输出目录**: `output/{task_id}/`
- **处理结果**: `output/{task_id}/processing_result.json`
- **HTML说明书**: `output/{task_id}/index.html`

---

## 📝 配置文件

### API密钥配置
- **前端**: localStorage (`dashscope_api_key`, `deepseek_api_key`)
- **后端**: 环境变量或 `app.py` 中的 `api_keys` 字典

### 模型配置
- **Qwen-VL**: `models/vision_model.py` - `model_name = "qwen-vl-max"`
- **DeepSeek**: `models/assembly_expert.py` - `model_name = "deepseek-chat"`

---

## 🔧 常用命令

### 启动后端
```bash
cd e:\装修说明书项目
python backend/app.py
```

### 启动前端（如果需要）
```bash
cd frontend
npm run dev
```

### 查看日志
```bash
# 后端日志
tail -f backend.log

# 查看debug输出
ls -lt debug_output/
cat debug_output/assembly_expert_output_*.json
```

### 清理输出
```bash
# 清理所有输出
rm -rf output/*
rm -rf debug_output/*
```

---

## 📚 相关文档

- `docs/HANDOVER.md` - 完整交接文档
- `docs/QUICK_FIX_GUIDE.md` - 快速修复指南
- `docs/workflow_summary.md` - 流程梳理
- `docs/api_key_setup.md` - API密钥配置
- `docs/websocket_fix.md` - WebSocket修复说明

---

**快速定位，高效修复！** 🎯

