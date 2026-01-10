# Memory Changelog

## v2.0.77 (2026-01-10)
- **生成/查看器卡死兜底入口**：
  - 生成页（`Generator.vue`）新增“强制中断/清理”按钮：有 taskId 或处理中时可见，确认后关闭 SSE、调用删除接口并重置状态，便于清理卡任务后重传。
  - 查看器列表（`Viewer.vue`）对 `processing` 状态新增“中断/删除”按钮，直接调用 `DELETE /api/manual/{taskId}` 清理卡住任务。
- **问题记录**：在 `.cursor/step_hang_findings.md` 记录 STEP 文件过大（30MB、30万+实体）导致 cascadio/trimesh 在 Step4 卡死的原因与防护建议。
- 影响文件：`frontend/src/views/Generator.vue`、`frontend/src/views/Viewer.vue`、`.cursor/step_hang_findings.md`

## v2.0.76 (2026-01-09)
- **任务状态持久化 + 刷新恢复 + 失败任务可视化**：
  - `/api/manuals` 新增 `include_failed`，无手册但有残留目录时可作为失败/处理中任务返回，便于前端显示并删除。
  - 生成任务状态落盘 `task_status.json`，`/api/status/{task_id}` 可在内存缺失时从文件恢复，生成页刷新可自动重连或提示完成/失败。
  - 查看器添加失败任务的删除按钮；生成页开始生成时记录 taskId，完成/失败后清理。
  - 影响文件：`backend/simple_app.py`、`frontend/src/views/Viewer.vue`、`frontend/src/views/Generator.vue`

## v2.0.75 (2026-01-09)
- **生成前自动清理半途失败的残留任务目录**：/api/generate 遇到同名 `output/{task_id}` 但缺少 `assembly_manual.json` 时，会自动清空该目录并移除内存任务记录后再启动新任务，避免“任务已存在”挡住重跑。
  - **安全约束**：若目录内已有手册仍会拒绝覆盖；清理失败会返回 500。
  - 影响文件：`backend/simple_app.py`

## v2.0.74 (2025-12-27)
- **手册页侧栏可拖拽伸缩 + 悬浮折叠**：ManualViewer 桌面端左右侧栏支持拖拽调整宽度；折叠按钮默认隐藏，仅悬浮侧栏边缘/拖拽线时显示（折叠保留 16px 轨道），避免按钮压到 3D 模型区域。
  - **细节修复**：侧栏收起时隐藏内容，避免出现“残字/露字”；侧栏宽度变化时主动触发 3D 画布尺寸重算，避免渲染比例异常。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.73 (2025-12-26)
- **首页标题行高修正**：主页主标题行高从 0.9 提升至 1.05，子行设置 1.08 行高与 4px 间距，并取消 `content-overlay` 溢出裁剪，避免大字号被截断。
  - 影响文件：`frontend/src/views/HomeNew.vue`
- **导航 Logo 放大 + 路径统一**：导航品牌图标切换到 `public/logo.png` 并将尺寸放大到 56px（圆角 12px），确保新版资源生效。
  - 影响文件：`frontend/src/App.vue`

## v2.0.72 (2025-12-25)
- **移动端首页隐藏“开始工作”按钮**：仅在手机端隐藏首页“开始工作”入口，避免移动端显示该按钮。
  - **核心改动**：在移动端样式中隐藏 `.action-buttons` 区域。
  - **行为变化**：移动端首页不再显示“开始工作”；桌面端不受影响。
  - 影响文件：`frontend/src/views/HomeNew.vue`

## v2.0.71 (2025-12-25)
- **发布弹窗版本号纠偏（历史预览→编辑场景）**：管理员加载草稿时补拉线上最新版本号，避免“当前线上/即将发布”被草稿版本覆盖。
  - **核心改动**：在管理员草稿加载流程中新增 `fetchLatestVersion()`（草稿存在时也会拉 HEAD 版本）。
  - **行为变化**：从历史预览编辑 v3 再发布时，显示“当前线上 v10 / 草稿 v3 / 即将发布 v11”而非 v3/v4。
  - **风险与兜底**：若 HEAD 请求失败，则沿用草稿版本显示并打印 warning。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.70 (2025-12-25)
- **历史版本入口按来源控制（仅查看器入口可见）**：手册页“历史版本”入口仅在从查看器进入时显示；从历史预览进入编辑或其他入口（如生成器）进入时默认隐藏，避免误用历史入口。
  - **核心改动**：查看器跳转手册新增 `?source=viewer`；手册页读取 `route.query.source` 判断是否展示历史入口；保留 `editingFromHistory` 兜底以避免编辑历史时误显示。
  - **行为变化**：查看器进入手册仍可打开历史版本；历史预览点击“修改当前版本”后，历史入口不再出现。
  - 影响文件：`frontend/src/views/Viewer.vue`、`frontend/src/views/ManualViewer.vue`

## v2.0.69 (2025-12-25)
- **历史预览转草稿弹窗抑制（跨路由）**：从历史预览点击“修改当前版本”并创建草稿后，进入编辑页不会再误弹“发现草稿”，只抑制一次提示，避免打断用户编辑流程。
  - **核心改动**：新增 `draft_prompt_suppress_once_<taskId>` 单次抑制标记；创建草稿成功后写入标记；进入编辑加载草稿时先消费标记再决定是否弹窗，确保不会长期抑制真实旧草稿提示。
  - **行为变化**：点击“修改当前版本”直接进入编辑，不弹“已有草稿”；如果确实存在旧草稿，仍会按原逻辑提示。
- **草稿创建时间记录与展示**：后端保存草稿时新增 `draftCreatedAt` 字段（首次创建写入，后续保存保留）；弹窗展示创建时间，旧草稿缺失时回退显示 `lastUpdated` 并标注“使用最后保存时间”。
  - **核心改动**：`save_draft()` 写入/保留 `draftCreatedAt`；前端 `draftPromptContext` 增加 `draftCreatedAt/createdAtFallback` 并在弹窗中显示格式化时间。
  - **兼容说明**：历史草稿无法追溯真实创建时间，会显示“最后保存时间”作为兜底。
  - 影响文件：`frontend/src/views/ManualViewer.vue`、`core/storage.py`

## v2.0.68 (2025-12-24)
- **移动端大图/抽屉分层返回**：大图与抽屉各自维护历史栈，轻点大图只关闭大图、保留抽屉；返回键按栈逐层关闭（先大图后抽屉），避免直接退出到查看器。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.67 (2025-12-24)
- **路由渲染兜底**：移除 App 层页面切换过渡动画并为 `router-view` 添加 fallback，占位避免渲染异常导致全屏空白；新增全局错误/路由错误打印，渲染失败会直接暴露日志，不再静默。
  - 影响文件：`frontend/src/App.vue`、`frontend/src/main.ts`
- **移动端预览交互优化**：手机端大图/抽屉打开时，物理返回键或导航优先关闭预览/抽屉并阻止本次跳转，避免直接跳出页面；轻点大图即可关闭预览（捏合/拖拽时不误触），提升可用性。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.66 (2025-12-24)
- **移动端图纸/抽屉历史副作用移除**：不再向浏览器历史栈插入 `pushState/back`，抽屉与大图全由本地状态控制；组件卸载时兜底恢复 `html/body.touchAction`，修复点击图纸后切换首页/查看器/生成器出现空白或无响应的问题。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.65 (2025-12-24)
- **网格遮挡优化（黄色/蓝色状态）**：网格材质开启深度测试，避免高亮/已装状态下仍显示网格线覆盖模型。
  - **改动字段/状态**：`refreshGridHelper()` 中 `gridHelper.material.depthTest` 由 `false` 改为 `true`，保持 `depthWrite = false` 与透明度不变。
  - **行为变化**：网格会被模型遮挡（正常遮挡），模型本身显示不受影响。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.64 (2025-12-24)
- **草稿弹窗抑制（删除/插入步骤）**：删除或插入步骤生成草稿后，在刷新草稿的流程中抑制一次“发现草稿”弹窗，使行为与“编辑标题/调整顺序”等同一类编辑操作一致。
  - **改动字段/状态**：在插入/删除成功后设置 `suppressDraftPromptOnce = true`，只影响一次 `refreshManualFromServer()` 的弹窗逻辑，不改变草稿生成本身。 
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.63 (2025-12-24)
- **手册编辑稳定性修复**：历史预览改为显式进入编辑（移除自动草稿创建），步骤标题显示兼容 `title/action`；插入步骤标题必填与“开头插入”显示修复；丢弃草稿后恢复零件可见性。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.62 (2025-12-24)
- **产品级日志对齐 Step2 语义**：产品级纠正日志改为 `product_code_correction_log.json`，字段/决策含义与 Step2 保持一致（keep/correct_to_text_pc/correct_to_name_pc/no_safe_pc），并补充 code_hits/name_hits 含义说明。
  - 影响文件：`core/hierarchical_bom_matcher_v2.py`

## v2.0.61 (2025-12-23)
- **产品级层级匹配防串件 + 调试日志**：在 `_build_assembly_mesh_mapping` 增加 product_code+名称双重校验，遇到代码命中但名称不符时改用唯一名称匹配，否则跳过以避免 -02/-03 误配；匹配决策输出到 `debug_output/<任务目录>/product_code_validation.json`，便于人工复核。
  - 影响文件：`core/hierarchical_bom_matcher_v2.py`


## v2.0.60 (2025-12-23)
- **调试输出目录归档修复（避免按Agent拆分）**：同一次任务运行中固定 `debug_output/<时间戳_任务名>` 目录，Agent4/5/6/FAQ 的调试输出统一落在任务目录下。
  - 影响文件：`utils/time_utils.py`、`core/gemini_pipeline.py`

## v2.0.59 (2025-12-23)
- **步骤拖拽可滚动（65+ 步场景）**：步骤顺序弹窗的拖拽改为 `forceFallback` 并开启自动滚动参数（scrollSensitivity/scrollSpeed），拖拽过程中可自动滚动列表，支持将第1步拖到第65步。
  - 影响文件：`frontend/src/views/ManualViewer.vue`
- **“已装”禁用态更明显**：按钮增加固定可见的“（禁用）”标识，并调整状态点样式，避免仅悬停时才看得出不可用。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.58 (2025-12-23)
- **ManualViewer 步骤拖拽排序（方案A）**：在“编辑”菜单新增“调整步骤顺序”弹窗，按 `step_id` 全局重排 `display_order`（1000 步进）并一次性保存到草稿；保存后按原 `step_id` 重新定位当前步骤并刷新3D显示。
  - 影响文件：`frontend/src/views/ManualViewer.vue`
- **暂时禁用“已装”手动标记**：前端按钮不可点击，并在 `setPartStatus` 增加兜底拦截，便于阶段性验证“未装/正在装”链路。
  - 影响文件：`frontend/src/views/ManualViewer.vue`
- **前端依赖**：引入 `vuedraggable` 作为拖拽库。
  - 影响文件：`frontend/package.json`、`frontend/package-lock.json`

## v2.0.57 (2025-12-22)
- **ManualViewer 固定小网格**：网格固定尺寸 150、分隔 40，固定高度 -5，并添加边界线，避免随模型/爆炸高度变化导致“无限”或漂浮感。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.56 (2025-12-22)
- **有限网格（终版）**：网格固定 1600 尺寸、160 分隔（单格约 10），范围不再随模型扩大，转动时避免“无边界”眩晕；网格临时/重建逻辑保持一致。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.55 (2025-12-22)
- **网格再收缩 + 调试可用**：固定网格 1000 尺寸、100 分隔（单格约 10），并将 `THREE` 暴露到 `__three_debug__`，便于在浏览器控制台直接创建/调整网格。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.52 (2025-12-22)
- **网格可见性修复**：网格尺寸随模型包围盒自适应生成，颜色加深并关闭深度遮挡，位置略低于模型底部，避免 z-fighting 与“网格消失”。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.51 (2025-12-22)
- **装配状态继承补全 + 只读保护**：`updateStepDisplay` 向前继承 `not_installed`，未装状态在后续步骤保持爆炸视图直到显式改为正在装/已装；历史版本预览/非管理员禁止调用 `setPartStatus` 修改零件状态。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.50 (2025-12-22)
- **ManualViewer 相机自适应与缩放收敛**：加载/切换 GLB 时基于包围盒自动框选相机，动态设置 near/far，并将模型放大上限收敛到 1e4，避免深度闪烁和“缩小后看不到模型”的问题；重置相机复用同一逻辑。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.49 (2025-12-22)
- **调试输出按任务分目录（中文日期+时间+任务名）**：新增统一目录生成工具 `build_debug_output_dir`，AI匹配、Gemini Agent、视觉模型、双通道解析等调试文件全部落在 `debug_output/<yyyy年MM月dd日_HHmmss_任务名>/`，便于按任务归档；时间统一用北京时间。
  - 影响文件：`utils/time_utils.py`、`core/ai_matcher.py`、`agents/base_gemini_agent.py`、`models/vision_model.py`、`models/gemini_model.py`、`core/dual_channel_parser.py`


## v2.0.48 (2025-12-18)
- **落地PDF文本层BOM补全（替代/回退Vision）**：Step2 提取BOM时优先从 PDF 文本层确定性解析 7 列（`seq/code/product_code/name/quantity/unit_weight/total_weight`），文本层结果可信时直接使用并跳过 Vision；文本层不可信则回退 Vision，并用文本层结果补齐缺失字段与漏行，解决 `product_code` 等字段丢失导致的后续流程不稳定。
  - 影响文件：`core/pdf_text_bom_extractor.py`、`core/gemini_pipeline.py`

## v2.0.47 (2025-12-18)
- **修复step4层级匹配丢件/串件（同名重复件）**：层级匹配不再依赖“几何名全局匹配”，改为优先使用STEP解析出的 NAUO 父子边（带父级上下文）来生成 `assembly_to_mesh`/`bom_to_mesh`，并用 GLB `parts_info.node_name` 将同一 NAUO 展开到 `NAUOxxx_1/_2...` 等重复实例，解决组件内同名件（如防滑条/下齿板）导致的高亮丢失与串件。
  - 根本原因：旧逻辑在 `_build_assembly_mesh_mapping` 中用 `geom_to_node.setdefault(...)` 把“同名多实例”压成一对一；且一旦命中“无后缀”的同名件会跳过实例收集，导致重复件只取到 1 个，并可能拿到其他装配体的同名件（跨父级串件）。
  - 影响文件：`core/step_hierarchy_parser.py`、`core/hierarchical_bom_matcher_v2.py`

## v2.0.46 (2025-12-18)
- **修复3D高亮丢失**：ManualIntegratorV2新增`_inject_node_names_to_steps`方法，在整合步骤数据时利用`bom_to_mesh`映射把`node_name`注入到步骤的`components`/`fasteners`/`parts_used`里，修复前端3D高亮和三色状态功能。
  - 根本原因：AI Agent生成的步骤数据只有`bom_seq`/`bom_name`/`quantity`，缺少`node_name`；而`bom_to_mesh`映射是正确的但未被注入到步骤中。
  - 影响文件：`core/manual_integrator_v2.py`

## v2.0.45 (2025-12-17)
- **历史预览一键转草稿**：预览历史版本后点击“修改当前版本”会先基于预览版拉取数据并创建草稿，再跳转到编辑页，避免回落到最新发布版导致编辑/发布基线错位。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.44 (2025-12-16)
- **查看器列表移除删除按钮**：列表只保留“查看说明书”，删除入口统一在手册内的编辑菜单，避免误删。
  - 影响文件：`frontend/src/views/Viewer.vue`

## v2.0.43 (2025-12-16)
- **删除图纸入口收敛到编辑菜单**：管理员在编辑下拉中新增“删除当前图纸”选项，操作前弹确认，调用删除接口后清理缓存并返回首页，避免无权限用户误删。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.42 (2025-12-16)
- **草稿提示显示版本**：草稿模式提示条直接显示当前修改基于的版本号，便于确认正在编辑哪一版的未发布修改。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.41 (2025-12-16)
- **版本选择弹窗文案与选项收敛**：历史预览返回时的提示改为“两选项”（继续修改上一次未发布版本 / 丢弃并改当前预览版），移除“当前线上”概念，文案更直白。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.40 (2025-12-16)
- **历史预览创建草稿对齐**：历史预览跳转编辑时记住预览版本，在草稿提示中提供基于预览版创建新草稿的选项，避免默认落到最新草稿版本。
  - 影响文件：`frontend/src/views/ManualViewer.vue`


## v2.0.39 (2025-12-16)
- **历史预览返回交互卡死修复**：3D查看器重复初始化前先清理旧 renderer/controls/canvas 和监听，避免叠加遮挡导致模型无法旋转/选中。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.38 (2025-12-16)
- **草稿来源提示与选择**：检测到旧草稿时弹窗提示基线版本，可选择继续旧草稿、丢弃草稿回到线上、或基于当前预览版本创建新草稿，避免旧草稿悄悄抢优先级。
- **草稿文案精简**：发布弹窗/提示仅显示草稿基线版本，不再展示“草稿#次数”。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.37 (2025-12-16)
- **版本号显示防回退**：历史预览/草稿不会把最新发布版本号覆盖成旧号，发布弹窗的“当前线上版本/即将发布”始终基于最新版本。
- **历史返回自动刷新**：从历史预览跳回当前版本时强制重新加载数据，避免停留在旧版本内容。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.36 (2025-12-15)
- **发布说明字数限制**：发布弹窗的版本说明 textarea 增加 `maxlength=500` + 字数统计，避免过长输入。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.35 (2025-12-15)
- **步骤标题可编辑**：管理员在内容编辑弹窗中可直接修改步骤标题（同步到 title/action 字段），支持草稿保存与发布。
- **步骤标题对齐优化**：步骤卡片头部左对齐，减少标题与步骤号之间的空白距离。
  - 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.34 (2025-12-15)
- **发布弹窗与版本号显示修复**：
  - **问题现象**：历史版本预览时，发布弹窗的"当前版本/即将发布"基于预览的旧版本（如预览 v4 时显示将发布 v5），实际发布成功版本为最新（如 v10），显示与真实版本不一致。
  - **修复方案**：发布弹窗优先使用后端 `HEAD /api/manual/{task}/version` 返回的最新版本号，回退到当前加载数据的 `version`，`nextVersionPreview` 基于最新版本递增。
  - **影响文件**：`frontend/src/views/ManualViewer.vue`（`latestVersion` 状态、`fetchLatestVersion`、`currentVersionDisplay/nextVersionPreview` 计算）
- **发布失败提示本地化**：
  - **问题现象**：未修改内容直接发布时，后端返回英文"no changes"文案，弹窗提示为英文。
  - **修复方案**：前端拦截包含"no changes/nothing to publish"的错误信息，提示为中文"未进行修改，无法生成新版本"。
  - **影响文件**：`frontend/src/views/ManualViewer.vue`（`translatePublishError`）
- **全屏看图隐藏导航栏**：放大图纸时为 `body` 添加 `manual-viewer-zoomed` 样式，隐藏顶部导航栏，避免遮挡图纸视图。
  - **影响文件**：`frontend/src/views/ManualViewer.vue`（全局样式与卸载清理）

## v2.0.33 (2025-12-15)
- **匹配流程优化：层级匹配优先**：
  - **问题现象**：
    1. 当前流程：代码匹配 → AI匹配 → 层级匹配，层级匹配执行太晚
    2. 层级匹配基于STEP文件的真实父子关系，100%准确，却在AI匹配之后才执行
    3. AI匹配会处理本应由层级匹配覆盖的零件，浪费token且可能出错
  - **优化方案**（小糖提出）：
    1. **层级匹配优先执行**：基于STEP文件真实父子关系，100%准确
    2. **代码匹配处理剩余**：排除已被层级匹配覆盖的零件和BOM
    3. **AI匹配兜底**：只处理仍未匹配的零件和BOM，减少token消耗
  - **代码修改**（`core/hierarchical_bom_matcher_v2.py` 第393-536行）：
    1. 步骤1：层级匹配 `_build_assembly_mesh_mapping()`，收集 `hierarchy_matched_nodes` 和 `hierarchy_matched_bom_codes`
    2. 步骤2：代码匹配，输入 `remaining_parts` 和 `remaining_bom`（排除层级已覆盖的）
    3. 步骤3：AI匹配，只处理未被层级和代码匹配覆盖的
    4. 步骤4：合并结果 `{**assembly_to_mesh, **code_bom_to_mesh, **ai_bom_to_mesh}`
  - **新增统计字段**：`product_level_mapping` 新增 `hierarchy_matched` 字段，记录层级匹配的装配体数量
  - **优势**：
    - 层级匹配100%准确，优先使用
    - 减少AI调用次数和token消耗
    - 匹配逻辑更合理：确定性 → 概率性

## v2.0.32 (2025-12-09)
- **子装配体层级匹配修复**：
  - **问题现象**：
    1. `step4_matching_result.json` 中 `assembly_to_mesh: {}` 为空，层级文件完全没起作用
    2. "挂架组件" 本应匹配 25 个叶子零件，但 AI 匹配到了错误的 5 个零件（S-LP1730 系列）
    3. 匹配率显示 100% 但实际子装配体高亮不正确
  - **问题根因**：
    1. `_build_assembly_mesh_mapping` 使用精确匹配，但 BOM product_code 和层级 key 格式不一致
       - BOM: `S-AB1830(72IN)-MP1140-01`
       - 层级: `S-AB1830(72IN)-MP1140-01挂架组件`
    2. 返回值使用 `mesh_id`，但 `bom_to_mesh` 期望 `node_name`
    3. 输出 key 使用 `candidate_key`，但应该使用 `bom_code`
  - **修复方案**：
    1. 改用 **包含匹配**：如果 `normalize(product_code)` 在 `normalize(层级key)` 中就匹配成功
    2. 建立 `geometry_name -> node_name` 索引（而非 mesh_id）
    3. 增加前缀匹配处理 `_1`, `_2` 等后缀（同一零件多实例）
    4. 使用 `bom_code` 作为输出 key
  - **验证结果**：
    - 挂架组件：25 个 node_name ✅
    - 主框架组件：16 个 node_name ✅
    - 毛刷套组件：6 个 node_name ✅
  - **影响文件**：`core/hierarchical_bom_matcher_v2.py`（`_build_assembly_mesh_mapping` 函数）

## v2.0.31 (2025-12-09)
- **STEP 层级解析编码修复 + 输出简化**：
  - **问题现象**：`step_assembly_hierarchy.json` 中的中文显示为乱码（如 `S-AB1830(72IN)-MP1140ɨбͣ`）
  - **问题根因**：STEP 文件通常使用 GBK/GB2312 编码，但解析器使用 UTF-8 导致乱码
  - **修复方案**：
    1. 修改 `core/step_hierarchy_parser.py` 第 40-51 行，自动检测编码：优先尝试 GBK → GB18030 → GB2312 → UTF-8
    2. 如果所有编码都失败，使用 GBK + replace 模式兜底
  - **输出简化**：
    - 修改返回值，只保留 `hierarchy` 和 `stats`，去掉冗余的 `products`、`pd_to_name`、`nauos`
    - 文件从 2614 行精简到约 300 行，更易阅读
  - **影响文件**：`core/step_hierarchy_parser.py`

## v2.0.30 (2025-12-09)
- **STEP 装配层级解析 + 子装配体高亮**：
  - 新增 `core/step_hierarchy_parser.py`，正则解析 PRODUCT / PRODUCT_DEFINITION / NAUO，输出 `step_assembly_hierarchy.json`
  - 产品总图转换时自动生成层级 JSON（存于任务根目录），失败时打印警告不阻断流程
  - 产品级 BOM 匹配新增子装配体→叶子零件的 mesh 映射，`assembly_to_mesh` 合并进 `bom_to_mesh`，前端可据此高亮组件
  - 影响文件：`core/step_hierarchy_parser.py`、`core/hierarchical_bom_matcher_v2.py`

## v2.0.29 (2025-12-09)
- **修复草稿提示条不即时显示的bug**：
  - **问题现象**：编辑内容或修改零件状态后，草稿提示条没有立即显示，需要切换页面或刷新才能看到
  - **问题根因**：
    - `saveDraft()` 保存成功后没有设置 `isDraftMode.value = true`
    - `autoSavePartStates()` 保存成功后没有设置 `isDraftMode.value = true`
  - **修复方案**：
    1. `saveDraft()` 保存成功后新增 `isDraftMode.value = true`
    2. `autoSavePartStates()` 保存成功后新增 `isDraftMode.value = true`
- **修复丢弃草稿后3D模型状态不更新的bug**：
  - **问题现象**：丢弃修改后，零件颜色状态没有恢复，需要刷新页面才能看到正确状态
  - **问题根因**：`handleDiscardDraft()` 只更新了 manualData 数据，没有调用 `updateStepDisplay()` 刷新3D显示
  - **修复方案**：丢弃草稿成功后新增 `updateStepDisplay(false)` 刷新3D模型显示
  - **注意**：不能用 `init3DViewerAndModel()`，因为它会重复创建 canvas 导致3D交互失效
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.28 (2025-12-08)
- **删除零件功能（全局隐藏）**：
  - **需求**：用户点击3D零件后，可以选择删除它（从视图中隐藏）
  - **设计决策**：
    - 删除是**全局**的，不是按步骤删除（所有步骤都不显示该零件）
    - 删除本质是隐藏（`mesh.visible = false`），不修改 GLB 文件
    - 支持恢复功能
  - **实现**：
    1. 新增 `deletedParts: ref<Set<string>>` 存储已删除零件的 meshKey
    2. 弹窗添加"删除零件"按钮（红色危险按钮），带 `ElMessageBox.confirm()` 确认
    3. 3D控制区新增"已删除零件"下拉菜单（仅管理员可见），点击可恢复
    4. `deletePart()` - 删除零件（添加到 deletedParts，隐藏 mesh）
    5. `restorePart(meshKey)` - 恢复零件（从 deletedParts 移除，显示 mesh）
    6. `getDeletedPartDisplayName(meshKey)` - 获取已删除零件的显示名称
    7. 修改 `updateModelByStep()` - 在遍历 mesh 时检查 deletedParts，隐藏已删除零件
    8. 修改 `autoSavePartStates()` - 保存时将 deletedParts Set 转为数组存入 `manualData.deleted_parts`
    9. 修改 `restorePartAssemblyStates()` - 加载时从 `manualData.deleted_parts` 恢复到 Set
  - **样式**：
    - `.popup-footer` - 弹窗底部删除按钮区域
    - `.deleted-parts-dropdown` - 已删除零件下拉菜单样式
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.27 (2025-12-08)
- **手机端自动播放功能**：
  - **需求**：用户希望在手机页面添加自动播放按钮，点击后每5秒自动切换到下一步，直到最后一步停止
  - **实现**：
    1. 在 `.mobile-action-bar` 区域新增"自动播放"按钮（绿色），播放中变为"停止播放"（红色）
    2. 新增图标导入：`VideoPlay`、`VideoPause`
    3. 新增状态变量：`isAutoPlaying` ref、`autoPlayTimer` 定时器
    4. 新增方法：
       - `toggleAutoPlay()` - 切换播放/停止状态
       - `startAutoPlay()` - 启动定时器，每5秒调用 `currentStepIndex++`
       - `stopAutoPlay()` - 清除定时器，重置状态
    5. 边界处理：已是最后一步时提示"已经是最后一步了"；到达最后一步时自动停止并提示"播放完成"
    6. 组件卸载时清理定时器（`onUnmounted`）
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.26 (2025-12-08)
- **历史版本页面优化+删除版本功能+UI重构**：
  - **修改1 - VersionHistory.vue 标题**：
    - el-page-header 组件的 title 属性从默认 "Back" 改为 "回退"
  - **修改2 - ManualViewer.vue 历史版本提示条**：
    - "返回当前版本" 按钮改名为 "修改当前版本"
    - 新增 "退出" 按钮，调用 `window.close()` 关闭当前标签页
    - 新增 `exitHistoryPreview()` 方法
  - **修改3 - 3D零件弹窗显示优化**：
    - 同时显示零件名称和 NAUO 序号（两行布局）
    - 新增 `getPartNauoName()` 函数获取原始 mesh.name
    - 取消 `max-width` 和 `text-overflow: ellipsis` 限制，使用 `word-break: break-all` 自动换行
    - 弹窗宽度：`min-width: 320px`，`max-width: 500px`
  - **修改4 - 删除历史版本功能**：
    - 后端 `core/storage.py` 新增 `delete_version()` 方法
    - 后端 `simple_app.py` 新增 `DELETE /api/manual/{task_id}/version/{version}` API
    - 前端 `VersionHistory.vue` 新增删除按钮（当前版本禁用）+ `ElMessageBox.confirm()` 确认弹框
  - **修改5 - 按钮栏 UI 重构（方案A简约分组风格）**：
    - 按钮分为三组：导航组（上一步/步骤指示器/下一步）、功能组（编辑/版本下拉菜单）、状态组（管理员徽章/退出）
    - 组之间用分隔线 `.action-divider` 分隔
    - 统一配色：白底按钮、蓝色主按钮、绿色管理员徽章
    - 移除原有的 `el-button-group`、`type="warning/success"` 等混乱配色
  - **影响文件**：`frontend/src/views/ManualViewer.vue`、`frontend/src/views/VersionHistory.vue`、`backend/simple_app.py`、`core/storage.py`

## v2.0.25 (2025-12-08)
- **修复3D零件名称显示+删除冗余按钮**：
  - **问题1 - 零件名称还是显示NAUO序号**：
    - **问题根因**：v2.0.24 前端调用的 API 路径 `/api/manual/${taskId}/file/step3_glb_inventory.json` 在后端不存在，请求失败导致数据未加载。
    - **修复方案**：
      1. 后端 `simple_app.py` 新增 API：`GET /api/manual/{task_id}/glb-inventory`，返回 `step3_glb_inventory.json` 内容
      2. 前端 `loadGlbInventory()` 使用正确的 API 路径 `/api/manual/${taskId}/glb-inventory`
  - **问题2 - 删除冗余按钮**：
    - 删除右侧步骤详情区的"在当前后插入"和"删除当前"按钮（dropdown 菜单中已有相同功能）
  - **影响文件**：`frontend/src/views/ManualViewer.vue`、`backend/simple_app.py`

## v2.0.24 (2025-12-08)
- **3D零件名称显示改用geometry字段**：
  - **问题根因**：v2.0.23 使用 BOM 映射表获取零件名称，但用户希望显示的是3D零件的实际名称（来自 STEP 文件），而非 BOM 表中的名称。
  - **数据来源**：`step3_glb_inventory.json` 的 `node_to_geometry` 字段包含了准确的3D零件名称，如 `"NAUO7" → "GB╱T 5782-2016[六角头螺栓M20×90]_M20×90"`。
  - **修复方案**：
    1. 新增 `glbNodeToGeometry` ref 存储 `node_to_geometry` 数据
    2. 新增 `loadGlbInventory()` 函数，在页面加载时请求 `step3_glb_inventory.json`
    3. 修改 `nodeNameToPartName` computed，优先使用 `glbNodeToGeometry` 数据，回退到 BOM 映射表
  - **实现原理**：页面加载时一次性请求 `step3_glb_inventory.json`，数据存在内存中，点击零件时直接从内存查表，不需要额外网络请求。
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.23 (2025-12-08)
- **状态继承+零件名称显示优化**：
  - **问题1 - 状态继承**：
    - **问题根因**：`partAssemblyStates` 按步骤独立存储（`stepId → meshKey → status`），当第3步设为"正在装"后切换到第4步，因第4步没有手动状态，系统使用自动逻辑判定，导致零件变成灰色+爆炸。
    - **用户期望**：第N步设为"正在装"的零件，在第N+1步及之后应自动变成"已装"（蓝色+归位）。
    - **修复方案**：在 `updateStepDisplay` 中添加状态继承逻辑。如果当前步骤没有手动状态，向前查找之前步骤的状态：
      1. 之前有 `installing` 或 `installed` → 当前视为 `installed`（蓝色+归位）
      2. 之前没有手动状态 → 使用自动逻辑
  - **问题2 - 零件名称显示**：
    - **问题根因**：点击零件时显示的是 NAUO 序号（如 "NAUO123"），用户希望显示实际零件名称。
    - **修复方案**：
      1. 新增 `nodeNameToPartName` computed 属性，从 BOM 映射表构建 node_name → 零件名称 的映射
      2. 修改 `getPartDisplayName` 函数，优先从映射中获取实际零件名称（如 "T-SPV250-Z602-02-01-Q355B 方形板-机加"）
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.22 (2025-12-08)
- **装配逻辑一致性修复**：
  - **问题根因**：`updateStepDisplay` 函数中颜色判断和位置判断逻辑不一致。颜色判断会检查管理员的手动标记状态（`manualStatus`），但位置判断只使用自动逻辑（根据步骤数据中的 `node_name`），不考虑手动状态。
  - **问题场景**：如果一个零件不在任何步骤的 `node_name` 中，但管理员手动标记为"已装"，设置时位置正确归位，但切换步骤后重新计算时位置会错误地变成爆炸位置，而颜色仍然是蓝色。
  - **修复方案**：
    1. 将手动状态获取移到位置计算之前
    2. 位置判断：先检查 `manualStatus`，再用自动逻辑
    3. `manualStatus === 'installed'` 或 `'installing'` → 归位
    4. `manualStatus === 'not_installed'` → 始终爆炸位置（与 `applyPartPosition` 一致）
    5. 无手动状态 → 使用原有自动逻辑
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

## v2.0.21 (2025-12-06)
- **零件装配状态按步骤存储**：
  - **问题根因**：`partAssemblyStates` 使用全局 `Map<meshKey, status>` 存储，当用户在第三步设置零件为"正在装"（黄色），再到第四步设为"已装"（蓝色），回到第三步时读取到的仍是"已装"（蓝色），而非预期的黄色。
  - **修复方案**：
    1. 数据结构从 `Map<string, AssemblyStatus>` 改为 `Map<string, Map<string, AssemblyStatus>>`，即 `stepId → (meshKey → status)`，每个步骤独立存储。
    2. `setPartStatus()` 按当前步骤的 `step_id` 存储状态。
    3. `getPartStatus()` 按当前步骤的 `step_id` 获取状态。
    4. `updateStepDisplay()` 按当前步骤获取手动标记的状态。
  - **新增字段**：`manualData.part_assembly_states` 存储格式 `{ "step_xxx": { "NAUO123": "installing", ... }, ... }`
  - **自动保存**：每次修改状态后自动保存草稿（防抖500ms），调用 `/api/manual/{taskId}/save-draft`。
  - **数据恢复**：加载数据时从 `part_assembly_states` 恢复 Map 结构。
  - **影响文件**：`frontend/src/views/ManualViewer.vue`

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
