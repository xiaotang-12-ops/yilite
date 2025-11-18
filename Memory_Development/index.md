# 📸 项目快照 - Memory Development

**创建时间**: 2025-11-18  
**最后校对**: 2025-11-18  
**当前版本**: v1.1.5  
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
| PUT | `/api/manual/{task_id}` | 更新手册并自增版本 | 写回 `assembly_manual.json`，更新 `lastUpdated` |
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
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看/编辑 | 使用 /api/manual*, 版本自增 |
| `/engineer` | Engineer.vue | 工程师视图（质检/分发） | |
| `/settings` | Settings.vue | API Key / 模型配置 | 调 /api/settings |
| `/glb-test` | GLBTest.vue | GLB 场景调试 | |
| `/simple-glb-test` | SimpleGLBTest.vue | 轻量 GLB 测试 | |
| `/icon-test` | IconTest.vue | 图标展示 | |

默认 API 基础地址：`VITE_API_BASE_URL`，否则 `http://localhost:8008/api`；WebSocket 使用 `ws://localhost:8008/ws/task/{id}`。

---

## 数据流与输出
- 输入：PDF 工程图、STEP/STL 模型 → `uploads/`
- 流水线：分类 → PDF 转图 + STEP 转 GLB → 视觉规划 → BOM/3D 匹配 → 组件/产品装配步骤 → 焊接工艺 → 安全 FAQ → 手册整合
- 输出：`output/{task_id}/assembly_manual.json`、`glb_files/*.glb`、`pdf_images/{pdf}/page_*.png`、各阶段 JSON。

---

## 运行与环境
- Docker：`docker-compose up --build`（映射 8008:8008 后端，3008:80 前端）；镜像名附版本 `assembly-manual-*-v2.0.0`。
- 本地调试：后端 `uvicorn backend.simple_app:app --host 0.0.0.0 --port 8008`；前端 `npm install && npm run dev`（默认 3000）。
- 必需环境变量：`OPENROUTER_API_KEY`；可选 `BLENDER_EXE` 指向 Blender 可执行文件。

---

## 最近 3 个版本快照
| 版本 | 日期 | 关键变更 |
| --- | --- | --- |
| v1.1.5 | 2025-11-12 | 管理员登录与在线编辑：焊接/安全/质检可编辑，组件名修改，持久化自增版本，UI 优化。 |
| v1.1.4 | 2025-11-10 | 修复组件步骤过滤混乱：按 component + step_id 精确匹配，修正焊接/安全添加字段。 |
| v0.0.2 | 2025-11-18 | 初版快照与工作流描述；基础生成链路可用。 |

---

## 状态与注意事项
- 正常：上传、生成、日志流、手册读取/编辑、模型与图片下载、设置管理。
- 注意：需安装 Blender；`OPENROUTER_API_KEY` 必填；大文件性能与 Three.js 渲染待优化；前端路由默认走 8008 端口。

---

## 相关文档索引
- `docs/WORKFLOW_ANALYSIS.md` 全流程
- `docs/AGENT_ARCHITECTURE.md` Agent 架构
- `docs/API_INTEGRATION_GUIDE.md` API 对接
- `docs/FILE_INDEX.md` 文件索引
- `docs/CHANGELOG.md` 历史版本

---

**维护者**: Memory Development Team
