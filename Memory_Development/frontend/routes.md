# 前端路由与关键组件 (Vue 3 + Vite)

> 来源：`frontend/src/main.ts`、`frontend/src/views`、`frontend/src/components`。

## 路由表
| Path | 组件 | 功能 | 依赖 API |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页/入口展示 | - |
| `/generator` | Generator.vue | 上传 PDF/模型，触发生成 | `/api/upload`, `/api/generate`, `/api/status`, `/api/stream`, WebSocket `/ws/task/{id}`；读取“上一次任务”时若状态接口返回 404，会自动清理 `generator_last_task/generator_current_task` 缓存，避免残留提示 |
| `/viewer/:id?` | Viewer.vue | 3D 预览、结果查看（支持搜索栏扫一扫回填） | 读取输出目录或任务数据；扫码后自动写入 `searchQuery`；已验证 Android 系统浏览器在“自签 HTTPS + 首次信任证书”场景可正常调起摄像头并回填搜索框；桌面端管理员新增 `待调整/已完成/旧版本` 三分类和 `异常任务` 入口，并可通过 `移动到` 下拉修改项目分类；桌面项目表暴露 `window.__viewerLayoutTuner` 供控制台临时调整 `projectNameMinWidth/categoryWidth/actionWidth/actionGap`；`操作` 区点击已和行点击隔离，避免点击 `移动到` 时误打开说明书；搜索不再匹配原始 `taskId` 旧名字，列表时间列文案改为“修改时间”；移动端固定为工人查看入口，只展示 `已完成(published)` 项目，不显示管理员登录和管理按钮；删除任务成功后同步清理生成器缓存键以保持跨页面一致性 |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看与编辑、草稿/发布 | `/api/manual*`, `/api/manual/{task}/glb/*`, `/api/manual/{task}/pdf_images/*`；桌面端管理员可从 3D 控制区打开“调整位置”，组件挂在默认宽 `400px` 的右侧说明栏内，以无蒙层定位层覆盖说明内容而不重排或覆盖中间 3D 画布；滑杆实时调整网格上下、模型左右和模型上下位置，取消回退、恢复默认，确认时一次调用 `save-draft`。底层仍以归位模型底部计算网格基线，只移动 Grid/Boundary Group，并同步平移相机与 `OrbitControls.target`；配置继续写入 `metadata.viewer_settings.scene_calibration_by_glb[glb_file]`，发布后普通查看者读取；旧手册无字段自动默认，历史版本和移动端不显示入口。源码已完成生产构建、`9/9` 场景回归与静态契约检查，小糖已完成最新容器页面验收；既有移动端返回链路、按 `taskId` 恢复步骤索引、草稿继续/丢弃、管理员自动刷新、桌面自动播放和长标题工具栏修复保持不变 |
| `/engineer` | Engineer.vue | 工程师视图：质检/分发 | 复用任务与手册数据 |
| `/settings` | Settings.vue | 配置 AI Key / 模型（隐藏入口） | `/api/settings`, `/api/settings/health`, `/api/test-model`；品牌区鼠标左键长按 5 秒进入；provider 对外统一为 `newapi`（兼容旧 `doubao`）；支持每调用点配置 `fallback_model`（主模型失败自动切换）；一键全测会分别验证主模型与兜底模型连通性；测试后端连接与一键全测具备超时提示；一键全测会返回思考参数/completion 上限的警告信息（警告但允许）；多模态调用点（`assembly/welding/bom_vision`）在 `newapi` 下不展示 `glm-5`，手填后保存会自动替换并提示；本地缓存缺失时留空保存默认保留服务端已有 Key |
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
