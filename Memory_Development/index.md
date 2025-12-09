# 📸 项目快照 - Memory Development

**创建时间**: 2025-11-18
**最后校对**: 2025-12-09
**当前版本**: v2.0.29
**项目状态**: 核心功能完成，可用

---

## 🎯 项目核心目标
智能装配说明书生成系统：解析 PDF 工程图纸与 STEP/STL 模型，经 6 个 Gemini Agent 与 3 个核心处理器生成可视化装配说明书。

---

## 🏗️ 系统架构概览
```
前端 (Vue 3 + Element Plus + Three.js)
  ↕ HTTP API + WebSocket
后端 (FastAPI + Uvicorn)
  ↕
6 个 AI Agent (Gemini 2.5 Flash)
  ↕
3 个核心处理器 (文件分类 + BOM匹配 + 手册集成)
  ↕
output/{task_id} (JSON + GLB + 图片)
```

---

## 核心文件结构
- 统一入口：`backend/simple_app.py`（FastAPI）、`frontend/src/main.ts`（Vue 入口）
- 核心流水线：`core/gemini_pipeline.py` 调度 FileClassifier、HierarchicalBOMMatcher、ManualIntegratorV2 及 6 个 Agent
- 提示词：`prompts/agent_*.py`（视觉规划、BOM-3D、组件装配、产品装配、焊接、安全FAQ）
- 前端：`frontend/src/views`（Home、Generator、Viewer、ManualViewer、Engineer、Settings 等），`frontend/src/components`（ThreeViewer、Processing*、AssemblyManualViewer 等）

---

## 后端 API（FastAPI，容器端口 8008）
| Method | Path | 功能 | 备注 |
| --- | --- | --- | --- |
| GET | `/api/health` | 健康检查 | Docker HC 使用 |
| POST | `/api/upload` | 上传 PDF/STEP/STL | 保存到 `uploads/`，每次上传前清空目录 |
| POST | `/api/generate` | 启动生成任务 | 复制上传文件到 `output/{task}/`，后台线程跑 gemini_pipeline |
| GET | `/api/status/{task_id}` | 查询任务状态 | 内存任务表 |
| GET | `/api/stream/{task_id}` | SSE 日志/进度流 | 结合 utils.logger 缓冲 |
| WS | `/ws/task/{task_id}` | WebSocket 进度流 | 周期推送进度/完成/失败 |
| GET | `/api/manuals` | 列出已生成手册 | 扫描 `output/*/assembly_manual.json` |
| GET | `/api/manual/{task_id}` | 读取手册 JSON | 直接读文件，替换 `{task_id}` 占位 |
| GET | `/api/manual/{task_id}/draft` | 读取草稿 | 无草稿返回 404 |
| DELETE | `/api/manual/{task_id}/draft` | 丢弃草稿 | 删除 `draft.json`，恢复到已发布版本 |
| POST | `/api/manual/{task_id}/save-draft` | 保存草稿 | 写入 `draft.json`，不影响已发布，支持 `_edit_version` 乐观锁 |
| POST | `/api/manual/{task_id}/publish` | 发布草稿并归档 | 生成 `assembly_manual.json` + `versions/v*.json` + `version_history.json` |
| GET | `/api/manual/{task_id}/history` | 获取版本历史 | 列出版本列表及当前版本 |
| GET | `/api/manual/{task_id}/version/{v}` | 读取指定版本 | 从 `versions/v*.json` 读取 |
| POST | `/api/manual/{task_id}/rollback/{v}` | 回滚到版本并生成新版本 | 复制目标版本为新发布 |
| DELETE | `/api/manual/{task_id}/version/{v}` | 删除指定历史版本 | 不能删除当前版本 |
| POST | `/api/manual/{task_id}/steps/insert` | 插入新步骤 | 生成 UUID step_id + display_order，可传 `_edit_version` |
| DELETE | `/api/manual/{task_id}/steps/{step_id}` | 删除步骤 | 支持 `_edit_version` 并返回被删零件 |
| POST | `/api/manual/{task_id}/steps/move` | 移动步骤 | 重算 display_order，支持 `_edit_version` |
| PUT | `/api/manual/{task_id}` | 兼容旧接口：直接发布 | 调用发布逻辑，建议改用 save-draft/publish |
| DELETE | `/api/manual/{task_id}` | 删除任务目录 | 清理内存任务 |
| HEAD | `/api/manual/{task_id}/version` | 获取手册版本 | Header `X-Manual-Version` |
| GET | `/api/manual/{task_id}/glb/{glb}` | 下载 GLB | 支持 `glb_files/` 或根目录 |
| GET | `/api/manual/{task_id}/pdf_images/{path}` | 下载 PDF 图片 | 统一 `pdf_images/{pdf_name}/page_xxx.png` |
| POST | `/api/settings` | 保存 API Key/模型 | 仅内存存储，同时写 env |
| GET | `/api/settings` | 获取已保存设置 | API Key 脱敏 |
| POST | `/api/test-model` | 连通性测试 | 调用 OpenRouter ChatCompletion |

---

## 前端路由（Vite 入口）
| Path | 组件 | 作用 | 备注 |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页展示 | |
| `/generator` | Generator.vue | 上传与任务发起 | 调 /api/upload, /api/generate |
| `/viewer/:id?` | Viewer.vue | 3D 预览与结果查看 | |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看/编辑 | 管理员支持草稿保存/发布 |
| `/version-history/:taskId` | VersionHistory.vue | 历史版本与回滚 | 调 /api/manual/* history/version/rollback |
| `/engineer` | Engineer.vue | 工程师视图（质检/分发） | |
| `/settings` | Settings.vue | API Key / 模型配置 | 调 /api/settings |
| `/glb-test` | GLBTest.vue | GLB 场景调试 | |
| `/simple-glb-test` | SimpleGLBTest.vue | 轻量 GLB 测试 | |
| `/icon-test` | IconTest.vue | 图标展示 | |

默认 API 基础地址：`VITE_API_BASE_URL`，否则 `http://localhost:8008/api`；WebSocket 使用 `ws://localhost:8008/ws/task/{id}`。

---

## 数据流与输出
- 输入：PDF 工程图、STEP/STL 模型 → `uploads/`
- 流水线：分类 → PDF 转图 + STEP 转 GLB → 装配规划（SimplePlanner，基准件=BOM序号1） → BOM/3D 匹配 → 组件/产品装配步骤（严格按BOM序号） → 焊接工艺 → 安全 FAQ → 手册整合
- 输出：`output/{task_id}/assembly_manual.json`、`draft.json`、`versions/`、`glb_files/*.glb`、`pdf_images/{pdf}/page_*.png`、各阶段 JSON。
- 核心规则：基准件=BOM序号1，装配顺序=BOM序号顺序，步骤数=BOM项数，每步装配1个零件。

---

## 运行与环境
- Docker：`docker-compose up --build`（映射 8008:8008 后端，3008:80 前端）；镜像名附版本 `assembly-manual-*-v2.0.0`。
- 本地调试：后端 `uvicorn backend.simple_app:app --host 0.0.0.0 --port 8008`；前端 `npm install && npm run dev`（默认 3000）。
- 必需环境变量：`OPENROUTER_API_KEY`；可选 `BLENDER_EXE` 指向 Blender 可执行文件。

---

## 最近 3 个版本快照
| 版本 | 日期 | 关键变更 |
| --- | --- | --- |
| v2.0.29 | 2025-12-09 | **修复草稿相关bug**：①`saveDraft()` 和 `autoSavePartStates()` 保存成功后新增 `isDraftMode.value = true`，草稿提示条立即显示；②`handleDiscardDraft()` 丢弃草稿后新增 `updateStepDisplay(false)`，3D模型状态同步恢复。 |
| v2.0.28 | 2025-12-08 | **删除零件功能（全局隐藏）**：①点击3D零件弹窗新增"删除零件"按钮（红色），删除前弹出确认框；②新增 `deletedParts: Set<string>` 存储已删除零件；③3D控制区新增"已删除零件"下拉菜单，可恢复被删除的零件；④`updateModelByStep()` 中检查 deletedParts，隐藏已删除零件；⑤自动保存 `deleted_parts` 到 manualData 并持久化；⑥加载时从 manualData.deleted_parts 恢复。 |
| v2.0.27 | 2025-12-08 | **手机端自动播放功能**：①新增"自动播放"按钮（仅手机端显示），点击后每5秒自动切换到下一步；②到达最后一步自动停止，或手动点击停止；③新增 `isAutoPlaying` 状态、`toggleAutoPlay()`/`startAutoPlay()`/`stopAutoPlay()` 方法；④组件卸载时清理定时器。 |

---

## 状态与注意事项
- 正常：上传、生成、日志流、手册读取/编辑、模型与图片下载、设置管理。
- 注意：需安装 Blender；`OPENROUTER_API_KEY` 必填；大文件性能与 Three.js 渲染待优化；前端路由默认走 8008 端口；一次任务仅支持上传 1 个 PDF + 1 个 STEP；task_id = PDF 文件名（去后缀），STEP 文件名可不同，后端生成时会按 task_id 重命名存储，同名 task_id 已存在会拒绝生成以防覆盖；模式判定：PDF 文件名前缀 01* → 组件模式；03/06/07/08* → 产品模式；未命中前缀默认组件模式；产品模式跳过 Step5，仅执行 Step6+Step7/8。

---

## 相关文档索引
- `Memory_Development/changelog.md` 完整版本历史
- `Memory_Development/backend/api.md` 后端 API 详情
- `Memory_Development/frontend/routes.md` 前端路由
- `Memory_Development/frontend/components.md` 前端组件
