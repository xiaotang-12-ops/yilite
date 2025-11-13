# Mecagent 项目快照

**项目类型**: 小型项目
**当前版本**: v1.1.6
**最后更新**: 2025-11-13
**GitHub**: https://github.com/xiaotang-12-ops/yilite

---

## 📁 项目结构

```
Mecagent/
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   │   └── ManualViewer.vue  # 装配说明书查看器（核心页面）
│   │   └── components/   # 通用组件
│   └── public/           # 静态资源
├── backend/              # 后端服务
├── agents/               # AI Agent 模块
│   ├── vision_planning_agent.py      # Agent 1: 视觉规划
│   ├── component_assembly_agent.py   # Agent 3: 组件装配
│   ├── product_assembly_agent.py     # Agent 4: 产品装配
│   ├── welding_agent.py              # Agent 5: 焊接工艺
│   └── safety_faq_agent.py           # Agent 6: 安全FAQ
├── core/                 # 核心处理模块
│   ├── gemini_pipeline.py           # Gemini 处理流水线
│   ├── ai_matcher.py                # AI 匹配器
│   └── manual_integrator_v2.py      # 说明书集成器
├── api.py                # FastAPI 主入口
├── output/               # 生成的装配说明书输出
└── docs/                 # 文档
```

---

## 🔌 API 清单

| 端点 | 方法 | 功能 | 参数 |
|------|------|------|------|
| `/api/upload` | POST | 上传文件（PDF/STEP） | `files: List[UploadFile]` |
| `/api/generate` | POST | 生成装配说明书 | `task_id: str` |
| `/output/{path}` | GET | 获取输出文件 | `path: str` |
| `/api/health` | GET | 健康检查 | 无 |

---

## 🎯 功能概览

### 核心功能
1. **文件上传**: 支持 PDF（图纸）和 STEP（3D模型）文件上传
2. **AI 处理流水线**: 
   - Agent 1: 视觉分析（Qwen-VL）
   - Agent 2: BOM-3D 匹配（DeepSeek）
   - Agent 3: 组件装配规划（Gemini）
   - Agent 4: 产品装配规划（Gemini）
   - Agent 5: 焊接工艺分析（Gemini）
   - Agent 6: 安全警告和FAQ（Gemini）
3. **装配说明书生成**: 生成 JSON 格式的装配说明书
4. **前端查看器**: 
   - 3D 模型展示（Three.js）
   - 步骤导航
   - 焊接要求、安全警告、质检、FAQ 展示
   - **管理员编辑功能**（v1.1.5+）

### 管理员编辑功能（重要）
- 登录验证（用户名/密码）
- 编辑当前步骤的：
  - 焊接要求
  - 安全警告
  - 质检要求
  - FAQ
  - **组件名称**（v1.1.6+）
- 实时保存到 JSON 文件
- 自动版本号递增

---

## 📝 最近3个版本

### v1.1.6 (2025-11-13) - 修复焊接模块组件名称同步问题

**问题**:
- 修改焊接模块的组件名称无法同步到 `component_name`
- 安全警告模块可以同步，但焊接模块不行

**根本原因**:
- 保存时，焊接模块先更新 `component_name`（新值）
- 安全警告模块后更新 `component_name`（旧值）
- 导致安全警告模块覆盖了焊接模块的更新

**修复方案**:
1. 添加 `watch` 监听焊接模块的组件名称变化
2. 自动同步到安全警告模块的所有警告
3. 安全警告模块的组件名称设为只读（灰色背景）
4. 焊接模块增加醒目的警告提示（橙色 + 图标）

**修改文件**:
- `frontend/src/views/ManualViewer.vue`
  - 第383-392行: 焊接模块组件名称提示增强
  - 第484-494行: 安全警告模块组件名称设为只读
  - 第587-592行: 导入 Warning 图标
  - 第1206-1220行: 添加 watch 监听逻辑

**技术细节**:
```javascript
// 监听焊接模块的组件名称变化
watch(
  () => editData.value.welding_requirements.length > 0
    ? editData.value.welding_requirements[0].component
    : null,
  (newComponentName) => {
    if (newComponentName && editData.value.safety_warnings.length > 0) {
      // 同步到所有安全警告
      editData.value.safety_warnings.forEach(warning => {
        warning.component = newComponentName
      })
      console.log('🔄 [组件名称同步] 焊接模块 → 安全警告模块:', newComponentName)
    }
  }
)
```

---

### v1.1.5 (2025-11-10) - 支持组件名称修改

**新功能**:
1. 支持修改组件名称
2. 使用唯一 `step_id` 精确匹配，避免误更新
3. 修改后实时同步到前端显示
4. 自动保存到后端 JSON 文件

**Bug 修复**:
1. **组件名称更新问题**
   - 问题: 修改组件名称后，前端显示没有更新
   - 原因: 前端显示的是 `component.component_name`（组件级别），但代码只更新了 `step.component_name`（步骤级别）
   - 修复: 同时更新组件级别和步骤级别的 `component_name`

2. **焊接要求添加问题**
   - 问题: 添加第二个焊接要求后无法保存
   - 原因: 后端数据结构 `step.welding` 是单个对象，不支持数组
   - 修复: 限制每个步骤只能添加一个焊接要求

3. **质检显示问题**
   - 问题: 质检标签页显示了所有步骤的质检要求
   - 修复: 新增 `currentStepQualityCheck` 计算属性，只返回当前步骤的质检

**修改文件**:
- `frontend/src/views/ManualViewer.vue`
  - 第1277-1340行: 焊接模块保存逻辑（更新组件名称）
  - 第1342-1382行: 安全警告模块保存逻辑（更新组件名称）

---

### v1.1.4 (2025-11-10) - 修复组件步骤过滤BUG

**严重BUG修复**:
- 问题: 不同组件的相同步骤号数据混在一起显示
- 原因: 过滤逻辑只按步骤号过滤，没有同时匹配组件名称
- 修复: 恢复双重过滤逻辑（`step_number` + `component`）

**修改**:
1. 恢复焊接数据双重过滤逻辑
2. 恢复安全警告双重过滤逻辑
3. 编辑对话框中组件名称设为只读（当时的方案，v1.1.5 改为可编辑）
4. 添加数据时自动填充正确的组件名称
5. 保存时强制使用当前步骤的组件名称

**修改文件**:
- `frontend/src/views/ManualViewer.vue`
  - 第957-996行: 恢复焊接数据双重过滤逻辑
  - 第400-422行: 焊接数据编辑表单 - 组件名称设为只读
  - 第501-524行: 安全警告编辑表单 - 组件名称设为只读
  - 第1183-1220行: 修复添加函数使用正确的字段
  - 第1252-1287行: 保存焊接数据时强制使用正确的值

---

## 🔍 关键技术点

### 前端技术栈
- Vue 3 + TypeScript
- Element Plus UI 组件库
- Three.js（3D 模型渲染）
- Axios（HTTP 请求）

### 后端技术栈
- FastAPI（Python Web 框架）
- Gemini API（Google AI）
- Qwen-VL（视觉分析）
- DeepSeek（BOM 匹配）

### 数据结构
- 装配说明书: JSON 格式
- 步骤数据: 包含 `step_id`（唯一标识）、`step_number`、`component_name`
- 焊接数据: 步骤内嵌字段 `step.welding`（单个对象）
- 安全警告: 步骤内嵌字段 `step.safety_warnings`（字符串数组）

---

## ⚠️ 重要注意事项

1. **组件名称同步**: 
   - v1.1.6 开始，焊接模块的组件名称会自动同步到安全警告模块
   - 安全警告模块的组件名称是只读的，只能通过焊接模块修改

2. **步骤唯一标识**: 
   - 使用 `step_id` 作为唯一标识，避免步骤号重复导致的数据混乱
   - 不同组件可以有相同的步骤号，但 `step_id` 必须唯一

3. **焊接要求限制**: 
   - 每个步骤只能添加一个焊接要求（后端数据结构限制）

4. **Docker 部署**: 
   - 前后端都基于 Docker 运行
   - 不要直接用 `npm run dev` 启动，应该使用 Docker 命令

---

## 📚 相关文档

- 详细 API 文档: 见 `Memory_Development/api.md`
- 完整版本历史: 见 `Memory_Development/changelog.md`

