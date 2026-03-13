# 前端路由与关键组件 (Vue 3 + Vite)

> 来源：`frontend/src/main.ts`、`frontend/src/views`、`frontend/src/components`。

## 路由表
| Path | 组件 | 功能 | 依赖 API |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页/入口展示 | - |
| `/generator` | Generator.vue | 上传 PDF/模型，触发生成 | `/api/upload`, `/api/generate`, `/api/status`, `/api/stream`, WebSocket `/ws/task/{id}`；读取“上一次任务”时若状态接口返回 404，会自动清理 `generator_last_task/generator_current_task` 缓存，避免残留提示 |
| `/viewer/:id?` | Viewer.vue | 3D 预览、结果查看（支持搜索栏扫一扫回填） | 读取输出目录或任务数据；扫码后自动写入 `searchQuery`；已验证 Android 系统浏览器在“自签 HTTPS + 首次信任证书”场景可正常调起摄像头并回填搜索框；移动端采用卡片布局（白色背景、圆角阴影、信息层级清晰），桌面端保持表格布局；删除任务成功后同步清理生成器缓存键以保持跨页面一致性 |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看与编辑、版本自增 | `/api/manual*`, `/api/manual/{task}/glb/*`, `/api/manual/{task}/pdf_images/*`；移动端返回链路收口（手动关闭弹层不再 `history.back`）+ 按 `taskId` 持久化恢复步骤索引；抽屉历史层改为“点击打开时同步 `pushState`”以规避首次返回竞态；修复手机步骤抽屉按钮错位与恢复零件后的即时状态显示；草稿弹窗改为“继续编辑 / 丢弃回线上”两动作并带二次确认；管理员状态切换时自动刷新手册并在版本变化时提醒；修复长标题步骤下顶部工具栏被挤压导致高度抖动问题 |
| `/engineer` | Engineer.vue | 工程师视图：质检/分发 | 复用任务与手册数据 |
| `/settings` | Settings.vue | 配置 AI Key / 模型（隐藏入口） | `/api/settings`, `/api/test-model`；provider 对外统一为 `newapi`（兼容旧 `doubao`）；支持每调用点配置 `fallback_model`（主模型失败自动切换）；一键全测会分别验证主模型与兜底模型连通性；测试后端连接与一键全测具备超时提示；一键全测会返回思考参数/completion 上限的警告信息（警告但允许）；多模态调用点（`assembly/welding/bom_vision`）在 `newapi` 下不展示 `glm-5`，手填后保存会自动替换并提示 |
| `/glb-test` | GLBTest.vue | GLB 场景调试 | 本地 mock 资源 |
| `/simple-glb-test` | SimpleGLBTest.vue | 轻量 GLB 测试 | 本地 mock 资源 |
| `/icon-test` | IconTest.vue | 图标样例 | - |

默认 API 基础地址：`VITE_API_BASE_URL`（未配置时同源 `/api`）；WebSocket：默认跟随当前页面协议/主机拼接 `/ws/task/{id}`（`TaskWebSocket`）；SSE：同源 `/api/stream/{id}`。
移动端扫码注意：浏览器摄像头通常要求安全上下文（`https://` 或 `localhost`）；当前已验证内网自签 `HTTPS` 方案可用，但推荐使用系统浏览器/Chrome/Safari，第三方浏览器兼容性不稳定；客户若使用固定内网 `IP` 部署，证书需按该 `IP` 重签。

## 主要组件
- `ProcessingSteps.vue` / `ProcessingVisualization*.vue`：展示任务进度与阶段。
- `AssemblyManualViewer.vue`：渲染与交互编辑手册数据。
- `ThreeViewer.vue`、`WorkerThreeViewer.vue`：Three.js 模型展示。
- 工程师面板：`components/engineer/*`（上传、AI 处理、人工审核、质检、分发）。
- 工人面板：`components/worker/*`（求助、问题上报、三维视图）。
