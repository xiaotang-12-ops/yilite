# 📸 项目快照 - Memory Development

**创建时间**: 2025-11-18
**最后校对**: 2026-04-14
**当前版本**: v2.1.57
**项目状态**: 核心功能完成，可用

---

## 🎯 项目核心目标
智能装配说明书生成系统：解析 PDF 工程图纸与 STEP/STL 模型，经 6 个 Gemini Agent 与 3 个核心处理器生成可视化装配说明书。

---

## 🏗️ 系统架构概览
```
前端 (Vue 3 + Element Plus + Three.js)
  ↕ 同源 HTTP(S) API + WebSocket/SSE
后端 (FastAPI + Uvicorn)
  ↕
6 个 AI Agent（OpenRouter/DeepSeek/NewAPI 可配置）
  ↕
3 个核心处理器 (文件分类 + BOM匹配 + 手册集成)
  ↕
output/{task_id} (JSON + GLB + 图片)
```

---

## 核心文件结构
- 统一入口：`backend/simple_app.py`（FastAPI）、`frontend/src/main.ts`（Vue 入口）
- 核心流水线：`core/gemini_pipeline.py` 调度 FileClassifier、HierarchicalBOMMatcher、ManualIntegratorV2 及 6 个 Agent；`core/pdf_text_bom_extractor.py` 负责 PDF 文本层 BOM 固定 6 列提取（`seq/code/product_code/name/material/quantity`）与纠偏补充，当前支持 `01.01.01.4422` 和 `01.01.01.10852` 这类 `4-5` 位尾号 BOM 代码；`HierarchicalBOMMatcher` 现采用层级结果锁定 + 最终 AI 补漏；`agents/product_assembly_agent.py` 现在会按 BOM 宽表强制收口产品步骤归属，确保“1 步 = 1 个 BOM 序号”；`ManualIntegratorV2` 会对未绑定 3D 节点的步骤显式打标
- 提示词：`prompts/agent_*.py`（视觉规划、BOM-3D、组件装配、产品装配、焊接、安全FAQ）
- 前端：`frontend/src/views`（Home、Generator、Viewer、ManualViewer、Engineer、Settings 等），`frontend/src/components`（ThreeViewer、Processing*、AssemblyManualViewer 等）

---

## 后端 API（FastAPI，容器端口 8008）
| Method | Path | 功能 | 备注 |
| --- | --- | --- | --- |
| GET | `/api/health` | 健康检查 | Docker HC 使用 |
| POST | `/api/upload` | 上传 PDF/STEP/STL | 保存到 `uploads/`，每次上传前清空目录 |
| POST | `/api/generate` | 启动生成任务 | JSON：`config.projectName`、`pdf_files[]`(1)、`model_files[]`(1)、`conflict_strategy`（prompt/overwrite/duplicate）；复制上传文件到 `output/{task}/`，后台线程跑 gemini_pipeline；同名返回 409（含 `manual_valid/manual_error/failure_hint` 等），成功任务覆盖前归档到 `output_archive/`，失败/损坏任务覆盖前直接删除 |
| GET | `/api/status/{task_id}` | 查询任务状态 | 内存任务表优先；若内存不存在则回退 `output/{task_id}/task_status.json` |
| POST | `/api/task/{task_id}/cancel` | 停止任务但保留结果 | 标记任务 `cancelled`，保留中间输出（可继续） |
| POST | `/api/task/{task_id}/resume` | 继续失败/中断任务 | 基于 `output/{task_id}` 继续跑，若已完成或运行中返回 409 冲突 |
| GET | `/api/stream/{task_id}` | SSE 日志/进度流 | 结合 utils.logger 缓冲 |
| WS | `/ws/task/{task_id}` | WebSocket 进度流 | 周期推送进度/完成/失败 |
| GET | `/api/manuals` | 列出已生成手册 | 扫描 `output/*/assembly_manual.json`；返回 `projectCategory`（`pending/published/archived`） |
| GET | `/api/manual/{task_id}` | 读取手册 JSON | 直接读文件，替换 `{task_id}` 占位 |
| PUT | `/api/manual/{task_id}/rename` | 重命名项目显示名 | 同步更新 `assembly_manual.json`/`draft.json`/`task_status.json`/内存任务 |
| PUT | `/api/manual/{task_id}/category` | 更新项目业务分类 | 同步更新 `assembly_manual.json`/`draft.json`/`task_status.json`/内存任务中的 `project_category` |
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
| POST | `/api/settings` | 保存 AI 设置 | OpenRouter/DeepSeek/NewAPI Key + 调用点模型配置（含可选 `fallback_model/custom_key`），内存存储并写入 env；多模态调用点若配置 `newapi + glm-5`（主模型或兜底模型）会返回 400 |
| GET | `/api/settings` | 获取 AI 设置 | 返回脱敏 key、调用点配置（含可选提供方） |
| POST | `/api/test-model` | 连通性测试 | 支持 OpenRouter/DeepSeek/NewAPI；可传 `fallback_model` 自动切换并返回 `used_fallback`；返回能力警告 |

---

## 前端路由（Vite 入口）
| Path | 组件 | 作用 | 备注 |
| --- | --- | --- | --- |
| `/` | HomeNew.vue | 首页展示 | 全局导航头像改为本地 `ai-robot-avatar.png`；移动端导航长品牌名缩小并两行完整显示；首页主标题采用 `title-kicker/title-primary/title-secondary` 三层排版，突出“自动解析”，避免长中文标题被动挤成孤行；标题整体比例、手机标题比例和首页说明文字比例改由 `visual_font_settings` 本地字号配置驱动 |
| `/generator` | Generator.vue | 上传与任务发起 | 调 /api/upload, /api/generate |
| `/viewer/:id?` | Viewer.vue | 3D 预览与结果查看 | 搜索栏支持“扫一扫”回填；扫码成功后会直接写入 `searchQuery`；已验证 Android 系统浏览器在“自签 HTTPS + 首次信任证书”场景可调起摄像头；移动端固定为工人查看入口，仅展示 `已完成(published)` 项目且不提供管理员登录；桌面端管理员新增 `待调整/已完成/旧版本/异常任务` 视图和项目 `移动到` 分类能力；搜索不再匹配原始 `taskId` 旧名字，时间列文案改为“修改时间” |
| `/manual/:taskId` | ManualViewer.vue | 装配手册查看/编辑 | 管理员支持草稿保存/发布；桌面端公共导航区与移动端底部栏都支持 `自动翻页`，统一输入 `0.5-60` 秒间隔后从第一步翻到最后一步；历史版本只读页也可使用；修复顶部工具栏在长标题步骤下的高度抖动 |
| `/version-history/:taskId` | VersionHistory.vue | 历史版本与回滚 | 调 /api/manual/* history/version/rollback |
| `/engineer` | Engineer.vue | 工程师视图（质检/分发） | |
| `/settings` | Settings.vue | AI 设置（隐藏入口） | Logo 10 秒内连点 10 次解锁；调 /api/settings；支持每调用点 `兜底模型`；一键全测会分别测试主模型与兜底模型；测试后端/全测具备超时提示；`newapi` 下多模态调用点不展示 `glm-5`，手填会自动替换并提示；新增“界面字号调节”，可保存首页标题/说明文字与手机导航标题字号，配置写入 `localStorage.visual_font_settings` 并实时预览 |
| `/glb-test` | GLBTest.vue | GLB 场景调试 | |
| `/simple-glb-test` | SimpleGLBTest.vue | 轻量 GLB 测试 | |
| `/icon-test` | IconTest.vue | 图标展示 | |

默认 API 基础地址：`VITE_API_BASE_URL`，否则同源 `/api`；WebSocket 默认跟随当前页面协议/主机拼接 `/ws/task/{id}`；SSE 默认走同源 `/api/stream/{id}`。

---

## 数据流与输出
- 输入：PDF 工程图、STEP/STL 模型 → `uploads/`
- 流水线：分类 → PDF 转图 + STEP 转 GLB → 装配规划（SimplePlanner，基准件=BOM序号1） → BOM/3D 匹配 → 组件/产品装配步骤（严格按BOM序号） → 组件模式执行焊接+安全 / 产品模式默认跳过焊接仅执行安全 → 手册整合
- 输出：`output/{task_id}/assembly_manual.json`、`task_status.json`、`draft.json`、`versions/`、`glb_files/*.glb`、`pdf_images/{pdf}/page_*.png`、各阶段 JSON。
- 核心规则：基准件=BOM序号1，装配顺序=BOM序号顺序，步骤数=BOM项数，每步装配1个零件。

---

## 运行与环境
- Docker：`docker-compose up --build`（映射 `8008:8008` 后端、`3008:80` 前端 HTTP、`3443:443` 前端 HTTPS）；前端 `HTTPS` 证书目录统一为宿主机本地 `./ssl` 只读挂载到容器 `/etc/nginx/ssl`，不再打包进镜像；根目录 `.gitignore` 与 `.dockerignore` 都会排除 `ssl/`；镜像名附版本 `assembly-manual-*-v2.1.49`。
- 本地调试：后端 `uvicorn backend.simple_app:app --host 0.0.0.0 --port 8008`；前端 `npm install && npm run dev`（默认 3000）。
- 必需环境变量：按调用点配置需要 `OPENROUTER_API_KEY` / `DEEPSEEK_API_KEY` / `NEWAPI_API_KEY`（兼容 `ARK_API_KEY`）；可选 `BLENDER_EXE` 指向 Blender 可执行文件。

---

## 最近 3 个版本快照
| 版本 | 日期 | 关键变更 |
| --- | --- | --- |
| v2.1.57 | 2026-04-14 | **首页 AI 机器人头像与标题排版优化**：<br/>- 新增本地 `frontend/public/ai-robot-avatar.png`，全局导航头像、favicon、Apple touch icon 与 PWA manifest 图标统一使用机器人头像<br/>- `HomeNew.vue` 首页标题改为“小标签 + 主标题 + 副标题”三层排版：`工业装配工艺知识 / 自动解析 / 数字孪生化指导系统`<br/>- 补齐桌面、平板、移动端标题字号断点，并压缩移动端导航品牌长标题，避免文字截断或挤占导航按钮<br/>- 新增 `useVisualFontSettings` 和隐藏设置页“界面字号调节”，后续可在头像 10 连点入口内直接调首页标题、说明文字和手机导航字号 |
| v2.1.56 | 2026-03-23 | **ManualViewer 自动翻页公共化**：<br/>- `ManualViewer.vue` 把桌面管理员录制和手机自动播放收口成一套公共 `自动翻页` 状态与定时器<br/>- 桌面入口移到顶部公共导航区，手机端改为同一套“输入秒数后开始”，历史版本只读页也允许使用<br/>- 用户文案统一为 `自动翻页 / 停止翻页 / 开始`，并移除“播放完成”提示 |
| v2.1.55 | 2026-03-18 | **PDF 文本层 BOM 提取支持 5 位尾号代码**：<br/>- `pdf_text_bom_extractor.py` 的记录头识别从固定 `4` 位尾号放宽到 `4-5` 位，`01.01.01.10852/10853` 这类真实 BOM 代码不再被漏掉<br/>- 新增回归测试覆盖 `5` 位尾号 BOM 文本层提取，防止再次只识别到后半段 BOM<br/>- 本地复跑 `组件图1.pdf` 文本层提取后，BOM 数量从 `2` 条恢复为 `4` 条 |

---

## 🔥 重要未发布变更（v2.0.81 记录）
- **STEP→GLB 自动简化（仅超大模型触发）**：在导出 GLB 前自动识别“毛刷/刷丝”这类高重复特征层父节点并合并子 mesh，降低 nodes 数与 draw calls，解决连接器类模型渲染/交互卡顿问题。
  - 默认触发：`nodes_geometry >= 5000` 且折叠规模满足阈值；可用 `AUTO_SIMPLIFY_GLB=false` 关闭。
  - 典型效果（AS3000 连接器）：`nodes_geometry 35900 -> 16738`（合并 67 个盘级节点、移除 19229 个刷丝节点）。
  - 代价：可能增大 GLB 体积（合并会破坏实例化复用），但前端性能显著改善。
- **STEP→GLB OCP 兜底转换（解决卡死/超时）**：当 `trimesh.load(..., force='scene')` 在加载/三角化阶段超时或失败时，自动改用 OpenCASCADE（`cadquery-ocp`）读取并三角化导出 GLB；对“超长参数行 STEP”会预检后优先走 OCP，避免先等 120s 超时。
  - 主要开关：`OCP_STEP_FALLBACK`（默认 true）、`OCP_STEP_FALLBACK_TIMEOUT_SECONDS`、`OCP_MESH_LINEAR_DEFLECTION`、`OCP_MESH_ANGULAR_DEFLECTION`、`OCP_MAX_MESHES`、`OCP_COLLAPSE_LEAF_THRESHOLD`。
  - 预检开关：`STEP_TO_GLB_PREFER_OCP` 强制优先 OCP；或通过 `STEP_LONG_LINE_THRESHOLD/STEP_LONG_LINE_HIT_COUNT` 自动命中后优先 OCP。

---

## 状态与注意事项
- 正常：上传、生成、日志流、手册读取/编辑、模型与图片下载、设置管理。
- 注意：需安装 Blender；`OPENROUTER_API_KEY`/`DEEPSEEK_API_KEY`/`NEWAPI_API_KEY`（兼容 `ARK_API_KEY`）按调用点配置；设置页默认隐藏，Logo 10 秒内连点 10 次可进入；大文件性能与 Three.js 渲染待优化；前端路由默认走 8008 端口；一次任务仅支持上传 1 个 PDF + 1 个 STEP；运行中全局仅允许 1 个任务，上传/生成会返回 409 `TASK_BUSY` 提示等待；task_id = PDF 文件名（去后缀），STEP 文件名可不同，后端生成时会按 task_id 重命名存储；同名生成返回 409，可在前端选择覆盖（成功任务归档到 `output_archive/`，失败/损坏任务直接删除）或生成第二套 `_v_n`；任务状态持久化到 `output/{task_id}/task_status.json`，支持 `/api/task/{task_id}/cancel` 停止保留结果与 `/api/task/{task_id}/resume` 继续生成；生成任务可被中断（删除/覆盖/残留清理时会中断后台线程并写入 `cancelled`）；模式判定：PDF 文件名前缀 01* → 组件模式；03/06/07/08* → 产品模式；未命中前缀默认组件模式；产品模式跳过 Step5，且 Step7 默认跳过焊接仅执行安全。
- PDF 文本层 BOM：当前文本提取优先保证 `seq/code/product_code/name/quantity` 5 列稳定；`unit_weight/total_weight` 仅做可选补充，不再因为重量列漂移就丢整行；`gemini_pipeline.py` 会优先采用文本层 `quantity` 纠正 Vision 冲突值。
- PDF 文本层 BOM：当前主目标已升级为固定 6 列：`seq/code/product_code/name/material/quantity`；数量识别改为前向扫描，不再主要依赖尾部关键词截断；`gemini_pipeline.py` 会同步用文本层 `material` / `quantity` 纠正 Vision 结果；记录头中的 BOM 代码当前支持 `4-5` 位尾号，避免 `01.01.01.10852` 这类真实物料代码被误丢。
- 产品级 BOM/3D 匹配：层级匹配结果现在作为底座锁定，后续代码/AI 只能补节点不能覆盖；装配体名称匹配支持短中文锚点（如 `油缸`）；最后一层补漏改为复用同一 BOM-3D 匹配模型的“最终 AI 补漏”，不再扩张规则兜底，但 `M10*75` ↔ `M10×80` 这类硬规格冲突仍保持拦截。
- 产品总装步骤归属：`product_assembly_agent.py` 会在 AI 生成后按 `bom_mapping_table` 收口每一步的 BOM 归属，当前步骤只能保留自己的 `bom_seq`；历史任务若仍有重复节点，`ManualViewer.vue` 也只会把“首次在当前步骤出现”的节点刷成黄色，已经在前序步骤出现过的节点保持蓝色。
- 手册节点绑定告警：步骤会输出 `has_3d_binding`、`missing_node_binding_codes`、`binding_warning`，显式提示“当前步骤有文字但未绑定 3D 节点”。
- Viewer 扫码：`/viewer` 搜索栏支持扫码填充物料代码；前端已切到同源 API/WS/SSE，支持内网自签 `HTTPS` 入口；已验证 Android 系统浏览器在“首次信任证书”后可直接扫码回填搜索框。第三方浏览器（如百度）兼容性不稳定，不建议作为交付验收标准；若客户固定内网 `IP` 变更，需在宿主机本地重签 `ssl/server.crt` / `server.key`；该目录不再纳入 Git 或镜像。
- Viewer 项目管理：项目列表新增业务分类 `pending/published/archived`；桌面端管理员可在 `待调整/已完成/旧版本` 与 `异常任务` 间切换，并通过 `移动到` 下拉修改分类；桌面表格支持通过 `window.__viewerLayoutTuner` 临时调 `项目名称/分类/操作` 列宽与按钮间距；移动端固定为工人查看入口，不显示管理员登录且只展示 `published` 项目。
- Viewer 搜索与时间文案：搜索不再匹配原始 `taskId`，避免重命名后旧名字继续命中；列表时间列文案改为“修改时间”，与后端返回的发布文件修改时间口径一致。
- Viewer 项目管理容错：`PUT /api/manual/{task_id}/category` 与 `PUT /api/manual/{task_id}/rename` 遇到历史损坏的 `task_status.json` 会按发布版手册和任务目录自动重建最小合法状态，不再因为半截 `"thread":` 旧数据卡住分类/改名。
- Viewer 移动端布局：项目选择弹窗改为近全宽显示，列表采用单列信息与整行操作按钮，减少文字挤压和无效留白。
- Generator/Viewer 任务缓存一致性：查看器删除任务后会同步清理 `generator_last_task` 与 `generator_current_task`；生成器读取上一次任务时若状态接口返回 404，会自动清理残留提示。
- NewAPI 兼容：provider 对外统一 `newapi`（兼容旧 `doubao`）；默认关闭 `thinking/reasoning_effort`，若模型返回 `Unknown parameter` 或参数不识别会自动降级；若返回 completion 上限（`at most N`）会自动降级到 `N` 后重试；多模态调用点（`assembly/welding/bom_vision`）不允许 `glm-5`，设置页会自动替换并警告，后端也会拒绝非法组合。
- 模型兜底与测试超时：设置页每个调用点可配置 `fallback_model`（主模型失败自动切换）；`/api/test-model` 返回 `used_model/used_fallback` 便于确认是否触发兜底；测试后端连接与一键全测加入超时提示，避免无限转圈。
- 一键全测兜底覆盖：配置 `fallback_model` 后，前端会追加“兜底模型独立连通测试”，结果中以 `（兜底）` 前缀展示，避免主模型成功时遗漏兜底验证。
- 焊接智能体请求策略：`WeldingAgent` 单独使用 `timeout=1800s` + `max_retries=0`，降低超长任务下同模型自动重试导致的重复计费风险；主模型失败后仍可切换兜底模型。
- 焊接/安全智能体瘦身：两者仅接收精简步骤字段（`step_id/step_number/title/description/quality_check` 等），模型只返回增量标注（`welding_annotations/safety_annotations`）再由后端本地合并，显著减少 token 与长 JSON 往返。
- 任务状态序列化：`_json_safe` 仅对容器做循环检测，避免普通值误写为 `"[circular]"`；恢复任务与手册读取/列表会对历史脏标题自动回退到 `task_id`。
- ManualViewer 返回键：移动端弹层手动关闭不再触发 `history.back`，并新增 `currentStepIndex`（按 `taskId`）持久化恢复；抽屉历史层改为“点击打开时同步入栈”，降低首次返回竞态导致的“像刷新并回第一页”风险；历史版本 `query.version/source` 逻辑保持不变。
- ManualViewer 细节修复：手机“选择步骤”抽屉按钮列表统一左对齐；恢复已删除零件时立即重算材质/位置，避免瞬时显示为“已装”。
- ManualViewer 草稿弹窗：改为两动作（继续编辑 / 丢弃回线上）+ 丢弃二次确认；弹窗显示 `draftCreatedAt` 与 `lastUpdated`，旧草稿无创建字段时给出兜底说明。
- ManualViewer 管理员登录态：监听 `isAdmin` 切换并自动刷新；若登录切管理员后发现版本/更新时间变化，会提示“数据已更新，已自动刷新”。
- ManualViewer 自动翻页：桌面端公共导航区与移动端底部栏都可输入 `0.5-60` 秒间隔后开始，从第一步自动翻到最后一步；自动翻页中手动切步、步骤跳转、刷新手册、退出管理员或离开页面会自动停止，结束时无弹窗提示；历史版本只读页同样可用。
- ManualViewer 顶部工具栏：长步骤标题会在进度区内截断，右侧操作区与管理员徽标保持单行，步骤切换不再出现高度忽高忽低。
- ManualViewer 相机：加载/切换 GLB 时基于包围盒自动框选，动态设置 near/far，并收敛模型放大上限（≤1e4）以避免深度闪烁和“需大幅放大才能看到”问题；移动端图纸/抽屉会写入一层同页历史用于“返回键先关弹层”，并通过弹层关闭链路收口减少返回竞态；移动端预览支持“返回键先关预览/抽屉”“轻点图片关闭”。
- STEP→GLB：`trimesh` 子进程 120s 硬超时（超时强制终止），不再启用 ocp_tessellate 兜底；并新增“自动简化”兜底（仅超大 nodes 模型触发，合并刷丝/毛刷等特征层为盘级 mesh），需要时可在上传前提示大文件转 STL。
  - 现已新增 OCP(cadquery-ocp) 兜底：trimesh/cascadio 超时/失败或预检命中超长行时，会自动回退/优先走 OCP 导出可用 GLB（粒度可能更粗，以保证能生成与可渲染）。

---

## 相关文档索引
- `Memory_Development/changelog.md` 完整版本历史
- `Memory_Development/backend/api.md` 后端 API 详情
- `Memory_Development/frontend/routes.md` 前端路由
