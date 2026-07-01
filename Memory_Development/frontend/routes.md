# 前端路由与关键组件 (Vue 3 + Vite)

> 来源：`frontend/src/main.ts`、`frontend/src/views`、`frontend/src/components`。

## 路由表
| Path | 组件 | 功能 | 依赖 API |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页/入口展示 | 全局导航头像、favicon、Apple touch icon、PWA manifest 图标统一使用本地 `ai-robot-avatar.png`；移动端导航长品牌名缩小并两行完整显示；首页主标题采用三层排版：`工业装配工艺知识` 作为小标签，`自动解析` 作为主视觉，`数字孪生化指导系统` 作为副标题，并补齐桌面/平板/移动端字号断点；标题整体比例、手机标题比例和首页说明文字比例由 `useVisualFontSettings` 下发 CSS 变量，可在隐藏设置页调节 |
| `/generator` | Generator.vue | 上传 PDF/模型，触发生成 | `/api/upload`, `/api/generate`, `/api/status`, `/api/stream`, WebSocket `/ws/task/{id}`；读取“上一次任务”时若状态接口返回 404，会自动清理 `generator_last_task/generator_current_task` 缓存，避免残留提示 |
| `/viewer/:id?` | Viewer.vue | 3D 预览、结果查看（支持搜索栏扫一扫回填） | 读取输出目录或任务数据；扫码后自动写入 `searchQuery`；已验证 Android 系统浏览器在“自签 HTTPS + 首次信任证书”场景可正常调起摄像头并回填搜索框；桌面端管理员新增 `待调整/已完成/旧版本` 三分类和 `异常任务` 入口，并可通过 `移动到` 下拉修改项目分类；桌面项目表暴露 `window.__viewerLayoutTuner` 供控制台临时调整 `projectNameMinWidth/categoryWidth/actionWidth/actionGap`；`操作` 区点击已和行点击隔离，避免点击 `移动到` 时误打开说明书；搜索不再匹配原始 `taskId` 旧名字，列表时间列文案改为“修改时间”；移动端固定为工人查看入口，只展示 `已完成(published)` 项目，不显示管理员登录和管理按钮；删除任务成功后同步清理生成器缓存键以保持跨页面一致性 |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看与编辑、版本自增 | `/api/manual*`, `/api/manual/{task}/glb/*`, `/api/manual/{task}/pdf_images/*`；移动端返回链路收口（手动关闭弹层不再 `history.back`）+ 按 `taskId` 持久化恢复步骤索引；抽屉历史层改为“点击打开时同步 `pushState`”以规避首次返回竞态；修复手机步骤抽屉按钮错位与恢复零件后的即时状态显示；草稿弹窗改为“继续编辑 / 丢弃回线上”两动作并带二次确认；管理员状态切换时自动刷新手册并在版本变化时提醒；桌面端公共导航区与移动端底部栏统一提供 `自动翻页`，支持输入 `0.5-60` 秒后从第一步翻到最后一步，且手动切步/跳步、刷新、离开页面都会自动停止；历史版本只读页也可使用；修复长标题步骤下顶部工具栏被挤压导致高度抖动问题 |
| `/engineer` | Engineer.vue | 工程师视图：质检/分发 | 复用任务与手册数据 |
| `/settings` | Settings.vue | 配置 AI Key / 模型（隐藏入口） | `/api/settings`, `/api/settings/health`, `/api/test-model`；provider 对外统一为 `newapi`（兼容旧 `doubao`）；支持每调用点配置 `fallback_model`（主模型失败自动切换）；一键全测会分别验证主模型与兜底模型连通性；测试后端连接与一键全测具备超时提示；一键全测会返回思考参数/completion 上限的警告信息（警告但允许）；多模态调用点（`assembly/welding/bom_vision`）在 `newapi` 下不展示 `glm-5`，手填后保存会自动替换并提示；桌面端现在必须对导航头像鼠标左键长按 `5` 秒才允许进入；AI 设置会写入后端 `runtime_settings/app_settings.json`，浏览器 `localStorage.app_settings` 仅作当前浏览器回显缓存；当浏览器本地没有旧 Key 且输入框留空未改动时，保存会继续保留服务端已有 Key，若当前页尚未成功拉到一次 `/api/settings`，空值也默认走“保留”而不是“清空”；界面字号配置仍保存到 `localStorage.visual_font_settings`，可调首页标题整体/手机标题/首页说明文字/手机导航字号/手机导航宽度，并补齐设置页移动端表单换行 |
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
