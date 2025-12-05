# Memory Changelog (倒序)

## v2.0.20 (2025-12-05)
- 修复 ManualViewer 加载态与移动端抽屉并存导致桌面端始终停留“加载中”的问题：将主工作区+抽屉统一包裹在 `v-if="manualData"` 下，加载态单独使用 `v-else`，避免 v-else 绑定到移动端抽屉。

## v2.0.19 (2025-12-05)
- **移动端横屏适配与性能降级**：
  - 导航栏：新增汉堡按钮 + 抽屉导航，桌面保留原样。
  - ManualViewer：左右侧栏移动端改抽屉；3D 渲染降级（关闭抗锯齿、限制像素比=1.5、响应式高度），网格/控制区在移动端折叠；新增移动工具栏快速打开“图纸/步骤”抽屉。
  - ThreeViewer/AssemblyManualViewer：控制面板移动端默认折叠，画布高度 55vh，渲染像素比上限 1.5。
  - Generator/Viewer：日志面板高度在移动端收敛，项目表格增加横向滚动，主要按钮保持大触控区。
  - 桌面端保持原布局与交互不变。

## v2.0.18 (2025-12-04)
- **AI匹配增强 - NAUO排序与相邻推断**：
  - **问题根因**：大型产品总图有大量子组件零件（如85个），部分零件名称无法直接匹配BOM（如`FXB-T20×130×60-Q355B方形板`），导致匹配率下降。
  - **优化1：NAUO编号排序**：
    - 修改 `processors/file_processor.py` 的 `generate_glb_inventory()` 函数
    - `step3_glb_inventory.json` 中的 `node_to_geometry` 列表按NAUO编号从小到大排序（NAUO1, NAUO2, ..., NAUO85）
    - 便于AI观察相邻零件的关联性
  - **优化2：AI提示词增加"相邻NAUO推断"策略**：
    - 修改 `prompts/agent_2_bom_3d_matching.py`，新增策略1.6
    - 核心原理：STEP装配结构中，相邻NAUO编号通常属于同一父组件
    - 匹配逻辑：如果NAUO27无法直接匹配，查看NAUO26和NAUO28的匹配结果，若都匹配到同一BOM组件，则推断NAUO27也属于该组件
    - 置信度：0.50-0.65（推断匹配，置信度较低）
  - **影响文件**：`processors/file_processor.py`、`prompts/agent_2_bom_3d_matching.py`

## v2.0.17 (2025-12-04)
- **STEP中文编码修复**：
  - **问题根因**：STEP文件使用GB2312/GBK编码，存在两处丢失中文的问题：
    1. `step_to_glb_converter.py`：chardet检测到GB2312后直接用该编码解码，部分字符无法解码
    2. `file_processor.py`：`_decode_name()` 函数对已包含中文的字符串再次执行latin1编码，导致中文被 `errors="ignore"` 丢弃
  - **修复方案**：
    1. `step_to_glb_converter.py`：新增 `GB_ENCODING_MAP` 映射表，将GB系列编码统一映射到 **GB18030**
    2. `file_processor.py`：`_decode_name()` 函数开头增加中文检测，已有中文直接返回，避免重复编解码
  - **效果**：`E-CW3T-S40-01-01-Q355B-` → `E-CW3T-S40-01-01-Q355B方形板-机加`，中文完整保留
  - **影响文件**：`processors/step_to_glb_converter.py`、`processors/file_processor.py`

## v2.0.16 (2025-12-03)
- **AI匹配防截断**：
  - **问题根因**：一次性发送793个未匹配3D零件时，Gemini响应过长被网关/模型截断，debug输出尾部中断，JSON解析易失败。
  - **方案**：未匹配零件数量 >200 时按批次（单批100、最小拆分20）调用模型；检测 `finish_reason`/解析结果为空即拆分重试；调试输出按批写入防止丢失。
  - **影响文件**：`core/ai_matcher.py`

## v2.0.15 (2025-12-03)
- **草稿模式完善**：
  - **问题根因**：删除/插入步骤后，前端调用 `GET /api/manual/{taskId}` 只返回已发布版，而编辑操作写入的是 `draft.json`，导致界面不更新。
  - **修复方案**：
    - `refreshManualFromServer()` 和 `loadLocalJSON()`：管理员模式下优先获取草稿。
    - 新增 `isDraftMode` 状态变量，跟踪是否处于草稿模式。
  - **新增草稿提示条**：
    - 黄色横幅，显示"草稿模式 - 您有未发布的修改"。
    - 提供"丢弃修改"和"立即发布"按钮。
  - **新增丢弃草稿API**：
    - `DELETE /api/manual/{task_id}/draft`：删除草稿文件，恢复到已发布版本。
  - **UI改进**：
    - 顶部按钮改为下拉菜单分组（编辑菜单 + 版本菜单），减少按钮数量，界面更清晰。
    - 编辑菜单：编辑内容、插入步骤、删除当前步骤。
    - 版本菜单：发布新版本、历史版本。
  - **影响文件**：
    - `backend/simple_app.py`：新增 `discard_draft` API
    - `frontend/src/views/ManualViewer.vue`：草稿提示条、下拉菜单、丢弃草稿功能

- **版本历史页面优化**：
  - **时间格式**：ISO格式（`2025-12-03T11:00:37.377297+08:00`）改为友好格式（`2025-12-03 11:00:37`）
  - **来源翻译**：`publish`→发布，`rollback`→回滚，`legacy`→历史迁移
  - **版本预览改进**：点击预览按钮 → 新标签页打开完整3D手册（只读模式）
    - 路由：`/manual/{taskId}?version=v2`
    - 蓝色提示条显示"正在查看历史版本 v2（只读模式）"
    - 隐藏所有编辑功能（管理员按钮区域）
    - 可一键返回当前版本或跳转版本历史
  - **影响文件**：
    - `frontend/src/views/VersionHistory.vue`：预览改为 `window.open` 新标签页
    - `frontend/src/views/ManualViewer.vue`：新增 `historyVersion`、`isReadOnlyMode` 计算属性，支持只读模式

## v2.0.14 (2025-12-02)
- 前端 3D 展示升级：初始爆炸视图，随步骤推进累积归位；当前步骤高亮（黄色），已装配恢复正常材质，未装配半透明并保持爆炸；爆炸距离可通过滑杆调整。
- 位置控制：基于加载时记录的世界坐标和径向向量，按步骤动态计算目标位置，支持动画过渡。

## v2.0.13 (2025-12-02)
- 步骤标识升级：ManualIntegrator 生成 UUID `step_id` + `display_order` 间隔 1000，保留 `_legacy_step_id/_legacy_step_number` 方便回溯，Storage 迁移旧手册并补 `_edit_version` 默认 0。
- 后端编辑接口：新增步骤插入/删除/移动 API，`save-draft` 增加 `_edit_version` 乐观锁校验，防止并发覆盖。
- 前端适配：ManualViewer 按 `display_order` 排序并动态计算 `step_number`，管理员可在 UI 中插入/删除步骤（调用新接口），本地加载/缓存兼容 UUID 新格式。

## v2.0.12 (2025-11-28)
- 新增 `step3_glb_inventory.json`：每次转换后输出 GLB 节点/几何清单，便于调试缺件；生成逻辑插入分层匹配汇总后，文件存于任务根目录。

## v2.0.11 (2025-11-28)
- GLB 转换安全加固：geometry 解码后用 graph.update 重新绑定节点，并新增绑定完整性自检；产品总图处理增加 file_hierarchy 空值防护，避免缺失 product 字段导致流程报错。




## v2.0.10 (2025-11-28)
- **装配顺序规则重大调整**：
  - **核心原则**：严格按BOM序号装配，基准件=BOM序号1
  - **Agent3/Agent4提示词更新**：
    - 新增4大装配规则：基准件=BOM序号1、步骤数=BOM项数、每步装配1个零件、严格按BOM序号顺序
    - 明确禁止：跳过零件、合并步骤、改变顺序、添加额外步骤
    - 强调：即使BOM序号1是小零件也必须作为基准件
  - **删除step3文件保存逻辑**：
    - 原因：基准件现在固定为BOM序号1，不需要SimplePlanner来"找"基准件
    - 影响：planning_result仍在内存中传递，只是不再保存到`step3_planning_result.json`
    - 简化：减少中间文件，输出目录更清晰
  - **架构优化**：
    - SimplePlanner职责简化：只负责按BOM序号生成组件/产品规划，不再需要"智能选择"基准件
    - Agent职责明确：严格执行BOM序号顺序，不再有自主判断空间
    - 数据流简化：Step3不再保存文件，直接传递给Step4/5/6

## v2.0.9 (2025-11-28)
- 产品链路去除“产品总图”硬编码：产品STEP/BOM 按真实文件名获取（来自 file_hierarchy），不再仅匹配固定文件名或“产品总图”前缀。
- 产品规划兜底：BOM 无子装配时仍生成产品计划，避免产品装配阶段直接失败。


## v2.0.8 (2025-11-28)
- FileClassifier 支持前缀判定：01 → 组件，03/06/07/08 → 产品，去掉“产品/总图”关键词判定。
- 组件装配提示词新增前缀规则：01.03 视为焊接多零件；其他 01.* 视为单件/半成品，生成最少步骤并说明直接与上一级装配焊接/安装。


## v2.0.7 (2025-11-28)
- 模式判定改为文件名前缀：01* → 组件图；03/06/07/08* → 产品总图；未命中前缀默认组件模式。
- 取消原有“组件关键词/BOM关键词”判定，避免误判；产品模式仍跳过 Step5。
- 同步文档版本与规则说明。


## v2.0.6 (2025-11-28)
- 模式判定收敛：PDF 名含“组件”强制组件模式；否则若 BOM 含“组件”则走产品模式；其它情况组件模式。（已被验证是错误的，以v2.0.7为主）
- 产品模式下跳过 Step5 组件装配，仅执行产品总装（Step6）+焊接/安全，避免重复调用 Agent3/4。
- 文档同步更新模式规则，避免 BOM 关键词误触发与流程误判。

## v2.0.5 (2025-11-28)
- **修复 Step7 文件重复生成问题**：
  - 问题：pipeline 在 Step7 同时保存了 `step7_enhanced_result.json` 和 `assembly_manual.json`，导致数据重复且命名混淆
  - 根因：Step7 的 `save_enhanced_result()` 方法既保存了 AI 输出，又调用了 ManualIntegrator 生成前端手册
  - 解决方案：
    - Step7 只保存 AI 原始输出 → `step7_enhanced_result.json`（内容：装配步骤 + 焊接 + 安全警告）
    - Step8 负责前端适配 → `assembly_manual.json`（新增：图纸路径、step_id、3D 资源、API 路径、元数据）
  - 架构优化：明确分离 AI 增强（Step7）和前端适配（Step8）的职责
  - 数据流：Agent 3/4/5/6 → Step7（AI 视角）→ Step8（前端视角）→ 前端渲染
- **Step7 vs Step8 的区别**：
  - Step7：AI 内容增强，包含装配步骤、焊接信息、安全警告，但缺少前端资源
  - Step8：前端格式适配，添加 drawings、step_id、3D 资源路径、API 路径转换、元数据
  - 设计原则：关注点分离（AI 团队负责内容，前端团队负责格式）

## v2.0.4 (2025-11-27)
- 阶段3：移除 Agent1，接入 SimplePlanner 按 BOM 序号生成组件/产品规划。
- pipeline 使用 SimplePlanner 输出 component_assembly_plan/product_assembly_plan，避免视觉规划 AI 调用。
- 调整 Agent3/Agent4 提示词，明确 BOM 顺序和焊接/拼装规则。
- 限制单任务上传 1 个 PDF + 1 个 STEP，避免多套图纸混用。
- 单文件模式收敛：仅有产品 PDF/STEP 才进入产品模式，否则强制组件模式；BOM 关键词不再触发产品模式；组件模式下不请求产品 GLB。（此规则已被 v2.0.6 的模式判定覆盖）
- STEP→GLB 生成使用 file_hierarchy 真实路径，生成的组件 GLB 即便未匹配也写入 glb_files，手册不再硬编码 product_total.glb。

## v2.0.3 (2025-11-27)
- 阶段2：STEP→GLB 编码修复器；检测STEP编码并转换为UTF-8后再导出，导出后对GLB内名称进行二次解码（gb18030/gbk/utf-8），减少中文乱码。
- 集成 StepToGlbConverter，BOM-3D 流程默认使用新转换器。

## v2.0.2 (2025-11-27)
- 阶段1：新增草稿/发布/历史版本 API，支持版本归档与回滚，自动迁移旧任务生成 version_history。
- 后端：ManualStorage 管理 draft/versions；旧 PUT 接口兼容为直接发布；新增草稿读取接口。
- 前端：ManualViewer 增加发布/历史按钮与发布弹窗；VersionHistory 页面支持预览与回滚；草稿保存改用新接口。

## v2.0.1 (2025-11-24)
- STEP→GLB 转换：导出前对节点/几何名称执行 `latin1 -> GBK/GB18030` 解码，减少 GLB/manifest 乱码。
- 前端步骤展示：优先显示 `description`（再回退 `operation` 兼容旧数据），避免编辑描述后仍显示旧字段。
- 提示词统一：组件/产品装配 Agent 输出字段统一为 `description`，便于前端直接显示/编辑同一字段。

## v2.0.0 (2025-11-18)
- 管理员编辑：组件名称统一输入并写回 `assembly_manual.json`，前端确保同步到步骤与组件。
- 手册查看：预计时间模块隐藏（暂不展示 `estimated_time_minutes` 字段，数据仍保留）。
- UI：导航品牌图标改用 `public/image.png`，移除渐变背景；新增管理员修改流程简明文档。

## v1.1.5 (2025-11-12)
- 管理员登录与在线编辑：焊接/安全/质检可编辑，组件名可改；保存时持久化到 `assembly_manual.json` 并自增版本。
- UI/表单优化，移除调试按钮与日志框，强化验证提示。
- 修复：组件名同步、焊接单实例限制、安全警告对象化、质检只展现当前步骤。

## v1.1.4 (2025-11-10)
- 修复组件步骤过滤混乱：过滤增加 component + step_id，避免跨组件混合。
- 修正添加焊接/安全时字段取值错误，确保使用 component_name。

## v0.0.2 (2025-11-18)
- 初版生成链路完整：文件上传→分类→视觉规划→BOM/3D 匹配→组件/产品装配→焊接→安全→手册整合。
