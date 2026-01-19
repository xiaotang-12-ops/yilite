# 前端路由与关键组件 (Vue 3 + Vite)

> 来源：`frontend/src/main.ts`、`frontend/src/views`、`frontend/src/components`。

## 路由表
| Path | 组件 | 功能 | 依赖 API |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页/入口展示 | - |
| `/generator` | Generator.vue | 上传 PDF/模型，触发生成 | `/api/upload`, `/api/generate`, `/api/status`, `/api/stream`, WebSocket `/ws/task/{id}` |
| `/viewer/:id?` | Viewer.vue | 3D 预览、结果查看 | 读取输出目录或任务数据 |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看与编辑、版本自增 | `/api/manual*`, `/api/manual/{task}/glb/*`, `/api/manual/{task}/pdf_images/*` |
| `/engineer` | Engineer.vue | 工程师视图：质检/分发 | 复用任务与手册数据 |
| `/settings` | Settings.vue | 配置 AI Key / 模型（隐藏入口） | `/api/settings`, `/api/test-model` |
| `/glb-test` | GLBTest.vue | GLB 场景调试 | 本地 mock 资源 |
| `/simple-glb-test` | SimpleGLBTest.vue | 轻量 GLB 测试 | 本地 mock 资源 |
| `/icon-test` | IconTest.vue | 图标样例 | - |

默认 API 基础地址：`VITE_API_BASE_URL`（未配置时 `http://localhost:8008/api`）；WebSocket：`ws://localhost:8008/ws/task/{id}`（`TaskWebSocket`）。

## 主要组件
- `ProcessingSteps.vue` / `ProcessingVisualization*.vue`：展示任务进度与阶段。
- `AssemblyManualViewer.vue`：渲染与交互编辑手册数据。
- `ThreeViewer.vue`、`WorkerThreeViewer.vue`：Three.js 模型展示。
- 工程师面板：`components/engineer/*`（上传、AI 处理、人工审核、质检、分发）。
- 工人面板：`components/worker/*`（求助、问题上报、三维视图）。
\n🙂
