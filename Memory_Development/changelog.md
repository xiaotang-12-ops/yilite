# Memory Changelog

## v2.1.18 (2026-02-05)
- **历史版本预览禁止删除零件**：
  - **用户提问**：查看历史版本的时候，预览某个版本，我发现还是可以删除零件，应该要禁止才行，和修改已经那些一样，这个时候只是查看，禁止删除。
  - **问题根因**：
    - 删除零件按钮（Line 307-314）没有 `v-if` 条件，历史版本模式下仍然显示
    - `deletePart` 函数（Line 4990）没有只读模式检查，而其他修改函数（如修改零件状态 Line 4879、调整步骤顺序 Line 3311）都有检查
  - **问题场景**：用户在历史版本预览页面点击零件，弹出状态弹窗，可以看到并点击"删除零件"按钮，导致历史版本被修改
  - **修复方案**：
    1. **隐藏删除按钮**（Line 306）：添加 `v-if="isAdmin && !isReadOnlyMode"` 条件，历史版本模式下不显示删除按钮
    2. **添加只读检查**（Line 4990）：在 `deletePart` 函数开头添加只读模式检查，提示"历史版本为只读，无法删除零件"（防御性编程）
  - **影响文件**：`frontend/src/views/ManualViewer.vue`
  - **记录人**：小雅

## v2.1.17 (2026-02-05)
- **手机端图纸抽屉返回刷新问题彻底修复（二次修复）**：
  - **用户提问**：手机端查看图纸到任意第二步以上，第一次打开图纸抽屉，点击返回，整个页面会刷新并跳到第一步。
  - **问题根因**：
    - **第一层问题**：抽屉打开时没有向浏览器历史栈添加记录（`pushState`），导致点击返回键时触发真实的路由返回。虽然 `onBeforeRouteLeave` 守卫会拦截并阻止跳转，但路由触发过程已经开始，可能导致状态重置或页面刷新。
    - **第二层问题（致命漏洞）**：`popstate` 监听器中直接赋值关闭抽屉（`showDrawingsDrawer.value = false`），没有调用 `closeMobileDrawers()` 函数，导致历史回退逻辑完全没有执行。
    - **第三层问题**：watch 监听器没有检查 `closingOverlayFromPopstate` 标记，导致 popstate 触发时 watch 重复处理，可能引发逻辑混乱。
  - **问题场景**：
    - 用户在步骤2打开图纸抽屉
    - 点击返回键 → 触发路由返回
    - 路由守卫拦截并关闭抽屉，但页面已经出现刷新或跳转到第一步
  - **第一次修复（不彻底）**：
    1. 添加 `watch` 监听三个抽屉的打开/关闭状态
    2. 抽屉打开时添加历史记录（`pushState` + `overlayStack.push`）
    3. 修改 `closeMobileDrawers()` 添加 `skipHistory` 参数
    4. ❌ **遗漏**：`popstate` 监听器仍然直接赋值，没有调用 `closeMobileDrawers()`
    5. ❌ **遗漏**：watch 监听器没有检查 `closingOverlayFromPopstate`
  - **第二次修复（彻底）**：
    1. **修复 `popstate` 监听器**（Line 5236-5239）：调用 `closeMobileDrawers(true)` 而不是直接赋值，确保关闭逻辑统一
    2. **修复 watch 监听器**（Line 4668）：添加 `closingOverlayFromPopstate` 检查，避免在 popstate 触发时重复处理
  - **技术细节**：
    - 抽屉的历史记录管理逻辑与图片预览保持一致
    - 使用 `closingOverlayFromManual` 标记避免手动关闭时重复处理 `popstate`
    - 使用 `closingOverlayFromPopstate` 标记避免 popstate 触发时 watch 重复处理
    - `closeMobileOverlays()` 调用时传入 `skipHistory=true`，避免重复 `back()`
    - `popstate` 监听器调用 `closeMobileDrawers(true)`，统一关闭逻辑
  - **反思与教训**：
    - ⚠️ **修复不彻底的原因**：只关注了"添加历史记录"，忽略了"消费历史记录"的逻辑是否正确执行
    - ⚠️ **应该做的**：修复后应该完整追踪整个逻辑链（打开 → 添加历史 → 返回 → 消费历史 → 关闭），而不是只看部分环节
    - ⚠️ **标记的重要性**：多个异步事件（popstate、watch、手动关闭）需要用标记（flag）避免重复处理
  - **验证要点**：手机端进入步骤2 → 打开图纸抽屉 → 点击返回键 → 只关闭抽屉，不刷新页面，不跳转步骤
- **爆炸视图累积放大问题修复**：
  - **用户提问**：查看器图纸的爆炸视图，放大到一定程度后，点击"默认"/"分散"来回切换，爆炸视图会越来越大。
  - **问题根因**：`updateStepDisplay()` 函数每次都实时计算模型的包围盒（`Box3().setFromObject(model)`），而包围盒会包含当前爆炸状态下的零件位置，导致 `maxDim` 越来越大，形成正反馈循环（爆炸 → 包围盒变大 → 下次爆炸更大）。
  - **问题场景**：
    - 用户来回点击"默认"/"分散"切换爆炸模式
    - 控制台显示 `explodeBase` 从 5.657 涨到 26.839（涨了4.7倍）
    - 零件飞得越来越远
  - **修复方案**：
    1. 添加全局变量 `cachedModelMaxDim` 缓存原始包围盒的 `maxDim`
    2. 在 `loadModel()` 和 `switchGLBModel()` 中，模型居中后立即计算并缓存原始包围盒（零件归位状态）
    3. 修改 `updateStepDisplay()` 使用缓存的 `cachedModelMaxDim` 替代实时计算
    4. 在 `clearModelData()` 中清理缓存
  - **次要优化**：
    - 添加动画取消机制：存储每个 mesh 的 `requestAnimationFrame` ID，新动画开始前取消旧动画，避免多个动画同时运行导致位置混乱
    - 添加防抖处理：使用 `useDebounceFn` 对滑块拖动添加 100ms 防抖，优化拖动体验
  - **验证要点**：来回点击"默认"/"分散" 10次，控制台的 `explodeBase` 值应该稳定不变
- **手机端隐藏管理员登录按钮**：
  - **用户提问**：手机端不要显示管理员登录按钮。
  - **修复方案**：在 `App.vue` 的管理员登录/退出按钮外层添加 `v-if="!isMobile"` 判断，手机端完全隐藏管理员相关UI。
  - **验证要点**：手机端导航栏不显示管理员登录按钮和管理员状态
- 影响文件：`frontend/src/views/ManualViewer.vue`、`frontend/src/App.vue`、`Memory_Development/changelog.md`、`VERSION`

## v2.1.16 (2026-02-03)
- **新增文件上传时的2D/3D图纸匹配验证**：
  - **问题根因**：上传接口没有验证PDF和STEP文件名是否匹配，导致用户上传错误图纸也能通过，后续生成时才发现问题。
  - **问题场景**：
    - 用户上传了不同项目的PDF和STEP文件
    - 系统直接保存，没有任何提示
    - 生成时才发现图纸不匹配，浪费时间
  - **修复方案**：
    1. 新增`extract_core_name_from_pdf()`函数：去掉PDF文件名的前缀编号（格式：`数字.数字.数字.数字字母-`）和扩展名，提取核心名称
    2. 新增`extract_core_name_from_step()`函数：去掉STEP文件名的前缀字母（格式：`字母-`）、后缀版本号（格式：`-数字`）和扩展名，提取核心名称
    3. 在`/api/upload`接口中添加验证逻辑：
       - 检查PDF和STEP文件数量是否一致
       - 提取每个文件的核心名称
       - 验证每个PDF都有对应的STEP文件（核心名称完全匹配）
       - 不匹配时返回400错误："当前2D与3D图纸不匹配，请更换后再试"
  - **匹配规则示例**：
    - PDF: `06.84.01.0001T-HSB1220(48IN)-NL-Z吹雪机无连接器.pdf` → 核心名称: `HSB1220(48IN)-NL-Z吹雪机无连接器`
    - STEP: `T-HSB1220(48IN)-NL-Z吹雪机无连接器-203.STEP` → 核心名称: `HSB1220(48IN)-NL-Z吹雪机无连接器`
    - ✅ 匹配成功
  - **影响范围**：文件上传验证
- 影响文件：`api.py`、`Memory_Development/changelog.md`

## v2.1.15 (2026-02-03)
- **增强任务恢复前的完整性检查**：
  - **问题根因**：镜像重启后，中间JSON文件可能损坏（截断、格式错误），但系统只检查最终的`assembly_manual.json`，不检查中间文件，导致用户点击"继续生成"后才发现任务损坏，浪费时间。
  - **问题场景**：
    - Agent4成功生成58个步骤，但Agent5和Agent6的输出被截断（JSON解析失败）
    - 镜像重启后，用户尝试恢复任务
    - 系统认为任务可以恢复（因为`assembly_manual.json`不存在，但中间文件存在）
    - 运行时才抛出`ResumeDataError`，提示"step4_assembly_steps.json损坏"
  - **修复方案**：
    1. 修改`_validate_manual_json()`函数，增加关键中间文件检查
    2. 检查3个关键文件：`step1_bom.json`（BOM提取）、`step2_bom_matched.json`（BOM匹配）、`step4_assembly_steps.json`（装配步骤）
    3. 如果中间文件存在但无法解析或为空，返回`{"valid": False, "error": "resume_corrupt"}`
    4. 前端在恢复任务前提示用户："旧任务数据损坏，请删除后重试"
  - **验证要点**：
    - 镜像重启后，损坏任务在恢复前被检测到
    - 提示用户"旧任务数据损坏，请删除后重试"
    - 正常任务的恢复不受影响
  - **影响范围**：任务恢复逻辑、任务状态检查
- 影响文件：`backend/simple_app.py`、`Memory_Development/changelog.md`、`VERSION`

## v2.1.14 (2026-02-03)
- **彻底修复调用点独立Key丢失问题**：
  - **问题根因**：v2.1.13的修复不完整，`_resolve_call_point`方法在返回调用点配置时，只返回了`{"provider": provider, "model": model}`，**丢弃了`custom_key`字段**，导致`_get_api_key`方法无法获取到独立Key。
  - **问题场景**：
    - v2.1.13修改了`_get_api_key`方法，使其能够接收并使用`custom_key`
    - 但`_resolve_call_point`方法返回的字典中没有包含`custom_key`
    - 导致测试成功（测试API直接使用`custom_key`），但实际运行失败（`_get_api_key`拿到的字典没有`custom_key`）
    - 继续出现403错误："该令牌无权访问模型 google/gemini-3-flash-preview"
  - **修复方案**：
    1. 修改`_resolve_call_point`方法，在返回字典时保留`custom_key`字段
    2. 增强`_get_api_key`方法的日志，打印Key来源（独立Key/全局Key）和脱敏后的Key值
    3. 确保配置传递链路完整：`call_point_settings` → `_resolve_call_point` → `_get_api_key`
  - **验证要点**：
    - 查看Docker日志，确认显示"🔑 使用独立Key: sk-xxx...xxx"
    - 不再出现403错误
    - AI匹配、Agent4等调用点正常工作
  - **影响范围**：所有调用点（AI匹配、组件装配、产品总装、焊接增强、安全FAQ、BOM视觉）
- 影响文件：`core/gemini_pipeline.py`、`Memory_Development/changelog.md`、`VERSION`

## v2.1.13 (2026-02-03)
- **修复调用点独立Key未生效的严重BUG**：
  - **问题根因**：Pipeline的`_get_api_key`方法只接收`provider`参数，完全忽略了调用点配置中的`custom_key`字段，导致测试成功但实际运行失败。
  - **问题场景**：
    - 用户在设置页面为"AI匹配"配置了独立Key（有Gemini权限）
    - 测试模型时成功（因为测试API优先使用`custom_key`）
    - 实际运行时失败（因为Pipeline只使用全局OpenRouter Key，该Key无Gemini权限）
    - 导致403错误："该令牌无权访问模型 google/gemini-3-flash-preview"
  - **修复方案**：
    1. 修改`_get_api_key`方法签名：从`_get_api_key(provider: str)`改为`_get_api_key(call_point: Dict[str, str])`
    2. 方法内部优先使用`call_point.get("custom_key")`，如果没有则根据`provider`返回全局Key
    3. 修改所有调用`_get_api_key`的地方（6处），传入完整的`call_point`对象而不是`provider`字符串
    4. 确保测试和实际运行使用相同的Key选择逻辑
  - **验证要点**：
    - 调用点配置了独立Key时，实际运行使用独立Key
    - 调用点没有配置独立Key时，使用全局Key
    - 测试模型和实际运行使用相同的Key
  - **影响范围**：所有调用点（AI匹配、组件装配、产品总装、焊接增强、安全FAQ、BOM视觉）
- **AI匹配失败时立即终止流程**：
  - **问题根因**：AI匹配失败后，代码只记录错误但没有抛出异常，导致后续所有Agent继续执行，浪费大量费用。
  - **问题场景**：
    - AI匹配失败（403错误）
    - 但Agent4、Agent5、Agent6继续执行
    - 总计浪费$0.738（约5.3元）
    - 最后validation检查时才发现失败
  - **修复方案**：
    1. AI匹配失败时，打印详细错误信息（错误原因、检查建议）
    2. 立即抛出异常`ValueError(f"ai_matching_failed: {error_msg}")`
    3. 终止整个流程，不再执行后续Agent
  - **验证要点**：AI匹配失败后立即终止，不再浪费费用
- 影响文件：`core/gemini_pipeline.py`、`Memory_Development/changelog.md`、`Memory_Development/index.md`、`VERSION`

## v2.1.12 (2026-02-02)
- **调用点独立API Key配置**：
  - **问题根因**：用户使用NewAPI中转服务，不同模型需要不同的渠道Key，但原有设计所有调用点共用一个Key，导致403错误。
  - **问题场景**：用户"匹配"调用点使用 `google/gemini-3-flash-preview` 模型（需要Key A），其他调用点使用 `doubao-seed-1-8-251228` 模型（需要Key B），但所有调用点都通过同一个NewAPI地址调用，只是Key不同。
  - **修复方案**：
    1. 前端：每个调用点增加"独立Key"输入框（可选，留空则使用默认Key）
    2. 数据结构：`CallPointConfig` 增加 `customKey` 字段
    3. 后端：保存和读取 `custom_key` 字段
    4. Pipeline：`_get_api_key` 方法优先使用调用点的独立Key，没有则使用默认Key
    5. 测试接口：支持 `custom_key` 参数
  - **验证要点**：每个调用点可以配置不同的Key；留空则使用对应提供方的默认Key；测试模型时使用正确的Key。
  - **UI改进**：每个调用点配置区域增加独立Key输入框，提示"如果某个调用点需要不同的Key（如NewAPI中不同渠道的Key），请填写'独立Key'"。
- 影响文件：`frontend/src/views/Settings.vue`、`backend/simple_app.py`、`core/gemini_pipeline.py`、`Memory_Development/changelog.md`、`Memory_Development/index.md`、`VERSION`

## v2.1.11 (2026-02-02)
- **Step2 BOM文本层优先纠正机制**：
  - **问题根因**：Vision API识别BOM代号时可能出错（如将 `01.03.5275` 误识别为 `01.03.5276`），导致重复代号和3D高亮错误。
  - **问题场景**：PDF文本层能提取到正确的BOM代号，但原有逻辑只"补全空字段"，不"纠正错误字段"，导致Vision的错误值被保留。
  - **修复方案**：
    1. 修改 `_merge_vision_with_text_layer` 函数，增加"文本层优先纠正"策略：
       - 对 `code` 字段：如果文本层有值且与Vision不同，用文本层覆盖（无论Vision是否有值）
       - 对 `product_code`、`name` 字段：如果文本层有值且与Vision不同，用文本层覆盖
       - 保留原有的补全逻辑（`quantity`、`weight` 等字段）
    2. 生成 `step2_bom_correction_log.json`，记录所有纠正和补全操作（包含 seq、source_pdf、field、vision_value、text_value、decision）
    3. 函数返回值改为 `(merged_items, correction_log)` 元组
  - **验证要点**：文本层提取到的正确值会覆盖Vision的错误值；生成纠正日志便于追溯；解决BOM代号重复问题。
  - **实际效果**：文本层能提取约64%的BOM项（37/58），这些项的准确性高于Vision，成功纠正Vision的识别错误。
- 影响文件：`core/gemini_pipeline.py`、`Memory_Development/changelog.md`、`VERSION`

## v2.1.10 (2026-01-30)
- **失败即失败 + 断点校验强化**：
  - **问题场景**：模型调用失败后仍写出空手册并标记成功；断点续跑可能复用无效结果，导致“中途有问题却可进入查看器”。
  - **修复方案**：
    1. Pipeline 增加步骤有效性校验：Step1~Step7 结果无效则重跑；仍无效直接失败。
    2. 手册整合前强制校验步骤数，`steps=0` 直接判失败，不写空手册。
    3. 后端对 `assembly_manual.json` 做内容校验（空手册视为失败），`/api/status` 自动修正 completed→failed。
    4. 前端失败态只允许“余额不足/取消”继续，未知错误提示“文件错误”仅删除。
  - **验证要点**：模型权限失败时不再出现空白成功；失败任务不显示查看入口；续跑仅复用有效产物。
- 影响文件：`core/gemini_pipeline.py`、`backend/simple_app.py`、`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`VERSION`

## v2.1.09 (2026-01-29)
- **模型快捷选择**：
  - **问题场景**：每个调用点都需要手动输入模型 ID，容易拼写错误，操作繁琐。
  - **修复方案**：
    1. 设置页“调用点模型配置”新增“快捷模型”下拉。
    2. 选择 `gemini3-flash` 自动填充 `google/gemini-3-flash-preview`。
    3. 仅在提供方为 豆包（NewAPI）时展示，避免误选到其他平台。
  - **验证要点**：切到 豆包 后出现下拉；选择后模型输入框自动更新。
- 影响文件：`frontend/src/views/Settings.vue`、`Memory_Development/index.md`、`VERSION`

## v2.1.08 (2026-01-29)
- **镜像体积减负（白名单COPY）**：
  - **问题场景**：后端镜像体积过大，`COPY . .` 构建层达到 1.63GB。
  - **修复方案**：
    1. 后端 `Dockerfile` 将 `COPY . .` 改为白名单复制核心源码目录与必要文件（`backend/core/agents/processors/utils/models/prompts` + `config.py`/`api.py`）。
  - **验证要点**：重新构建后 `docker history` 中 `COPY` 层显著缩小，镜像体积下降约 1.6GB。
- 影响文件：`Dockerfile`、`Memory_Development/index.md`、`VERSION`

## v2.1.07 (2026-01-29)
- **镜像体积减负（构建上下文）**：
  - **问题场景**：镜像体积变大，怀疑历史产物被打入构建上下文。
  - **修复方案**：
    1. `.dockerignore` 增加 `output_archive/`，防止历史归档产物进入后端镜像构建。
  - **验证要点**：重新 `docker build` 后镜像体积下降；`docker save` 生成的 tar 体积同步下降。
- 影响文件：`.dockerignore`、`Memory_Development/index.md`、`VERSION`

## v2.1.06 (2026-01-29)
- **管理员入口与生成器门禁**：
  - **问题场景**：管理员登录只在 ManualViewer 内，生成器入口对所有人可见，容易误触或绕过。
  - **修复方案**：
    1. 顶部导航将“帮助”替换为管理员登录入口，显示管理员状态与退出。
    2. 生成器入口仅管理员可见：首页/查看器内按钮同步隐藏。
    3. 路由守卫拦截未登录访问 `/generator`。
    4. 管理员状态统一 Pinia + `sessionStorage`，ManualViewer 登录/退出与全局同步。
  - **验证要点**：未登录看不到生成器按钮；直输 `/generator` 跳回首页；登录后入口恢复。
- 影响文件：`frontend/src/App.vue`、`frontend/src/views/HomeNew.vue`、`frontend/src/views/Viewer.vue`、`frontend/src/views/ManualViewer.vue`、`frontend/src/main.ts`、`frontend/src/stores/admin.ts`、`Memory_Development/index.md`、`VERSION`

## v2.1.05 (2026-01-29)
- **后端立即失败修复**：
  - **问题场景**：删除任务后重新上传，任务一开始就失败；后端日志显示 `IndentationError`，并被二次异常掩盖。
  - **修复方案**：
    1. 修复 `product_assembly_agent` 覆盖率分支缩进错误，避免 `IndentationError`。
    2. 在 `run_pipeline` 中为 `ResumeDataError` 提前占位，导入失败时不再触发 `UnboundLocalError`。
  - **结果**：流水线可正常启动，真实失败原因不会被二次异常遮挡。
- 影响文件：`agents/product_assembly_agent.py`、`backend/simple_app.py`、`Memory_Development/index.md`、`VERSION`

## v2.1.04 (2026-01-29)
- **上次任务信息提示补齐**：
  - **问题场景**：上传页只知道“有上次任务”，但不知道具体任务名/状态/更新时间，删除确认也缺少上下文，容易误删。
  - **修复方案**：
    1. 监听 `last_task_id` 后调用 `/api/status/{task_id}` 获取 `projectName/status/updated_at`。
    2. 上传页展示“上一次任务：名称 + 状态 + 更新时间”，提高可辨识度。
    3. 删除确认弹窗拼接任务名，避免删错。
  - **影响行为**：只增强信息提示与确认文案，不改变任务判断逻辑。
- 影响文件：`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`VERSION`

## v2.1.03 (2026-01-28)
- **失败任务手动删除入口**：
  - **问题场景**：继续失败的自动提示未必触发，用户缺少“主动清理旧任务”的入口，导致卡住无法重新生成。
  - **修复方案**：
    1. `last_task_id` 存在且未生成中时显示“删除上一次任务”按钮。
    2. 点击后二次确认，调用 `DELETE /api/manual/{task_id}` 清理旧任务。
    3. 成功后清空 `last_task_id`，回到上传页，允许重新上传。
  - **验证要点**：失败任务出现按钮可见；删除成功后提示“已删除任务，请重新上传”。
- 影响文件：`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`VERSION`

## v2.1.02 (2026-01-28)
- **继续失败自动删除提示强化**：
  - **问题场景**：点击“继续上一次任务”后如果源文件缺失/损坏，会反复失败且停留在生成页，无法回到上传。
  - **修复方案**：
    1. 继续任务失败时（HTTP 400 或错误文本包含“缺少源文件/损坏/resume_corrupt”）触发删除确认提示。
    2. 用户确认后调用 `DELETE /api/manual/{task_id}`，关闭 SSE 并停止轮询，重置到上传页。
  - **结果**：避免“继续→失败→卡住”的死循环，用户可直接重新上传。
- 影响文件：`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`VERSION`

## v2.1.01 (2026-01-28)
- **生成器继续入口**：
  - 上传页新增“继续上一次任务”按钮，停止/失败后可直接调用 `/api/task/{task_id}/resume`。
  - 停止/失败自动记录 `last_task_id`，成功完成会清理该记录。
- **恢复日志页 + 覆盖率重试修复**：
  - 生成中从查看器返回生成器时，恢复连接会自动切回日志页。
  - 修复 Agent3/Agent4 重试提示引用未定义 `coverage_rate` 的崩溃。
- **继续失败删除提示**：
  - 继续任务失败（缺少源文件/数据损坏）时弹出删除提示，并调用 `/api/manual/{task_id}` 清理旧任务。
- 影响文件：`frontend/src/views/Generator.vue`、`agents/component_assembly_agent.py`、`agents/product_assembly_agent.py`、`Memory_Development/index.md`、`VERSION`
- 平台名字修改：AI智能装配平台改为AI智能装配指导

## v2.1.00 (2026-01-28)
- **断点续跑与失败任务识别**：
  - 新增 `/api/task/{task_id}/resume` 与 `/api/task/{task_id}/cancel`，任务状态持久化到 `task_status.json`（安全序列化，避免 thread/circular）。
  - 同名冲突支持失败态识别：`assembly_manual.json` 缺失/损坏视为失败，成功任务覆盖前归档，失败任务直接删除。
  - 失败原因分类（余额不足/无权限/AI-Key 缺失）写入 `failure_hint`，供前端提示。
- **流水线断点续跑**：
  - `GeminiAssemblyPipeline` 支持基于 step1-7 JSON 复用继续，并上报进度文案。
- **前端生成器进度条**：
  - 日志黑框下方新增进度条，轮询 `/api/status` 展示 `progress_message`。
  - 冲突弹窗支持“继续上一次任务/删除失败任务”，中断按钮改为保留结果。
- 影响文件：`backend/simple_app.py`、`core/gemini_pipeline.py`、`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`Memory_Development/backend/api.md`、`VERSION`

## v2.0.99 (2026-01-28)
- **安全输出结构兼容**：
  - Agent6 支持模型直接返回数组（顶层为 list）或对象（包含 `enhanced_steps/faq_items`），避免 `.get` 导致任务失败。
  - 输出结构异常时返回失败并保留原步骤，避免流水线中断。
- **重试逻辑健壮性**：
  - 重试检查兼容非 dict 的有效 JSON 结果，避免在重试阶段再次触发 `.get` 崩溃。
- 影响文件：`agents/safety_faq_agent.py`、`agents/base_gemini_agent.py`

## v2.0.98 (2026-01-20)
- **焊接输出结构兼容**：
  - Agent5 支持模型直接返回数组，避免 `.get` 导致任务失败。
  - 输出结构异常时返回失败并保留原步骤，防止装配步骤被清空。
- 影响文件：`agents/welding_agent.py`、`Memory_Development/index.md`、`VERSION`

## v2.0.97 (2026-01-20)
- **豆包参数冲突修复**：
  - 全部豆包调用点改用 `max_completion_tokens`，避免与 `max_tokens` 同时出现导致 400。
  - BOM 视觉与模型测试对豆包不再发送 `max_tokens`。
- 影响文件：`agents/base_gemini_agent.py`、`models/gemini_model.py`、`core/ai_matcher.py`、`core/gemini_pipeline.py`、`backend/simple_app.py`、`Memory_Development/index.md`、`VERSION`

## v2.0.96 (2026-01-20)
- **NewAPI 基址切换 + 豆包 64k 输出上限**：
  - 豆包调用点默认 Base URL 切到 NewAPI（支持 `DOUBAO_BASE_URL` / `ARK_BASE_URL` 覆盖）。
  - 豆包调用点统一设置 `max_tokens=64000`，避免长输出被截断。
- 影响文件：`agents/base_gemini_agent.py`、`models/gemini_model.py`、`core/ai_matcher.py`、`core/gemini_pipeline.py`、`backend/simple_app.py`、`Memory_Development/index.md`、`VERSION`

## v2.0.95 (2026-01-16)
- **AI匹配输出长度与思考模式调整**：
  - 豆包调用点启用深度思考（`reasoning_effort=medium`），并将输出上限设置为 `max_completion_tokens=64000`。
  - 豆包调用点超时提升到 1800 秒，避免深度思考导致超时。
- **冲突弹窗文案优化**：
  - 隐藏任务ID显示，避免无关信息干扰。
  - 文案改为“下一套”，避免多套场景误导。
- **AI匹配日志显示实际模型**：
  - 匹配阶段日志输出 `provider/model`，避免固定写死模型名。
- 影响文件：`core/ai_matcher.py`、`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.94 (2026-01-16)
- **豆包调用点接入 + 默认模型自动填充**：
  - 新增豆包(ARK)提供方与 `ARK_API_KEY` 支持，视觉调用点支持 OpenRouter/豆包，文本调用点支持 OpenRouter/DeepSeek/豆包。
  - 设置页切换提供方后自动填入默认模型ID，减少手动输入。
  - 模型测试与流水线调用按提供方选择 Base URL 与 API Key。
- 影响文件：`backend/simple_app.py`、`core/gemini_pipeline.py`、`core/ai_matcher.py`、`agents/base_gemini_agent.py`、`models/gemini_model.py`、`core/hierarchical_bom_matcher_v2.py`、`frontend/src/views/Settings.vue`、`.env.example`、`Memory_Development/index.md`、`Memory_Development/backend/api.md`、`VERSION`

## v2.0.93 (2026-01-16)
- **全局单任务运行锁 + 上传冲突提示**：
  - 上传/生成时检测全局运行中任务，返回 `TASK_BUSY` 提示并阻止并发启动。
  - 前端冲突弹窗增加运行中任务信息（名称/时间）并提供清晰提示。
- 影响文件：`backend/simple_app.py`、`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`Memory_Development/backend/api.md`、`VERSION`

## v2.0.92 (2026-01-16)
- **设置页一键全测模型连接**：
  - 测试按钮改为依次测试所有调用点模型，结果展示成功/失败明细。
  - 状态提示支持多行，便于定位失败调用点。
- 影响文件：`frontend/src/views/Settings.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.91 (2026-01-16)
- **AI调用点配置 + 隐藏设置入口**：
  - 新增按调用点配置 OpenRouter/DeepSeek 模型；视觉调用点仅允许 OpenRouter。
  - 前端设置页支持 DeepSeek Key 与调用点模型配置；Logo 10 秒内连点 10 次一次性解锁设置页入口。
  - 默认模型统一为 `google/gemini-2.5-flash-preview-09-2025`。
- 影响文件：`backend/simple_app.py`、`core/gemini_pipeline.py`、`core/ai_matcher.py`、`core/hierarchical_bom_matcher_v2.py`、`agents/base_gemini_agent.py`、`agents/component_assembly_agent.py`、`agents/product_assembly_agent.py`、`agents/welding_agent.py`、`agents/safety_faq_agent.py`、`frontend/src/App.vue`、`frontend/src/main.ts`、`frontend/src/views/Settings.vue`、`Memory_Development/index.md`、`Memory_Development/backend/api.md`、`VERSION`

## v2.0.90 (2026-01-15)
- **步骤导航位置调整 + 工具输入修复**：
  - 桌面端“下一步/查看步骤”位置互换，确保下一步按钮更靠近主操作区。
  - 所需工具输入回车后保留文字的问题修复，新增“回车添加”提示文案。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.89 (2026-01-15)
- **移动端步骤入口顺序 + 抽屉返回修复**：
  - 导航按钮顺序调整为“上一步 → 下一步 → 步骤”，避免步骤按钮插在中间造成误触。
  - 移动端抽屉关闭不再触发历史回退，新增路由守卫优先关闭抽屉/预览，避免返回导致页面刷新与步骤重置。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.88 (2026-01-15)
- **移动端步骤跳转 + 进度显示优化**：
  - 导航“上一步/下一步”区域新增移动端步骤跳转按钮，打开抽屉列表点击即跳转并自动关闭。
  - 进度条百分比改为整数显示，避免长小数占位。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.87 (2026-01-14)
- **步骤跳转 + 物料代码描述**：
  - ManualViewer 顶部导航新增步骤下拉选择，点击可直接跳转到目标步骤（保留标题展示）。
  - Agent3/Agent4 提示词要求描述同时包含“序号 + 物料代码”，并调整 BOM 列表输入格式为“物料代码优先”。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`prompts/agent_3_component_assembly.py`、`prompts/agent_4_product_assembly.py`、`Memory_Development/index.md`、`VERSION`

## v2.0.86 (2026-01-14)
- **爆炸方向文案优化**：
  - 将选项文案改为“默认/分散/强分散”，保持逻辑不变，降低用户理解成本。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.85 (2026-01-14)
- **ManualViewer 超大模型缩放兜底 + 爆炸方向模式**：
  - `computeAdaptiveScale` 在默认缩放超过阈值时使用 `TARGET_MAX_DIM=90`（S2）避免极端放大导致网格比例失衡。
  - 爆炸视图新增方向模式：原始（mesh 原点方向）、几何中心、距离加权；默认 `legacy` 保持旧逻辑。
- 影响文件：`frontend/src/views/ManualViewer.vue`、`Memory_Development/index.md`、`VERSION`

## v2.0.84 (2026-01-14)
- **管理员可编辑步骤所需工具**：
  - ManualViewer 编辑弹窗新增“所需工具”页签，支持输入并创建多项工具名称。
  - 打开编辑时从步骤读取 `tools_required`，保存草稿时同步写回步骤（为空则移除字段）。
- 影响文件：`frontend/src/views/ManualViewer.vue`

## v2.0.83 (2026-01-13)
- **生成任务可中断**：
  - 后端生成线程记录到 `tasks[task_id]["thread"]`，删除/覆盖/残留清理时会标记 `cancelled` 并向线程注入 `SystemExit`，避免 AI 匹配继续跑。
  - `/api/manual/{task_id}` 删除接口清理目录前先尝试中断后台线程，任务状态写入 `cancelled`。
  - 同名覆盖前也会中断旧线程，防止覆盖期间仍在写日志/占用算力。
- 影响文件：`backend/simple_app.py`、`Memory_Development/index.md`、`VERSION`

## v2.0.82 (2026-01-13)
- **生成冲突处理（覆盖/复制可选）**：
  - `/api/generate` 新增 `conflict_strategy`（prompt/overwrite/duplicate），同名任务返回 409 并附 `suggested_duplicate_id`、任务/手册时间信息。
  - 选择覆盖时，先将原 `output/{task_id}` 目录移动到 `output_archive/{task_id}/<timestamp>/` 并写入 `archive_meta.json`，确保可恢复；运行中的任务禁止覆盖。
  - 选择生成第二套时，后端统一分配下一个可用的 `{task_id}_v_n`，避免前端与后端编号冲突。
- **前端生成器交互**：
  - 冲突弹窗改为自定义对话框，提供明确三按钮：覆盖并备份、生成第二套（显示建议 ID）、取消；重复点击覆盖/复制会带策略再次调用生成接口。
  - 生成请求携带 `conflict_strategy`，duplicate 场景返回的新 `task_id` 会同步到前端状态和项目名。
- **冲突弹窗可见性修复**：显式开启取消按钮并使用次要样式，确保“生成第二套”选项在弹窗中可见。
- **取消返回上传页**：冲突弹窗点“取消”会将生成器恢复到上传步骤（保留已选文件，退出日志页）。
- 影响文件：`backend/simple_app.py`、`frontend/src/views/Generator.vue`、`Memory_Development/index.md`、`Memory_Development/backend/api.md`、`VERSION`

## v2.0.81 (2026-01-13)
- **自动简化（仅在超大模型触发）**：在 STEP→GLB 转换成功后、导出 GLB 前自动执行一次“渲染友好化”简化，用于解决“刷丝/毛刷”这类高精度建模导致的节点爆炸（万级 nodes）问题。
  - **触发条件（默认）**：`nodes_geometry >= 5000` 且识别到“毛刷类父节点”并满足折叠规模阈值；常规模型不触发，不改变原有逻辑。
  - **识别策略**：在 `SceneGraph` 中寻找 **无 geometry 的父节点**（装配/组件节点），名称包含 `毛刷/刷片/刷丝/brush/bristle` 且带数字后缀（如 `...毛刷片090`）。
  - **折叠规则**：对每个命中的父节点：收集其所有带 geometry 的后代节点（geometry descendants），把这些子 mesh 变换到父节点局部坐标后合并为 1 个 mesh；删除原子节点；父节点保持 world 变换，作为“盘/组件级” mesh 输出。
  - **产物与回传**：`ModelProcessor.step_to_glb` 返回新增 `simplification` 字段（是否触发、前后 nodes 统计、合并组信息），便于排查与前端提示。
  - **环境变量**：`AUTO_SIMPLIFY_GLB`（开关，默认 true）、`AUTO_SIMPLIFY_TRIGGER_NODES_GEOMETRY`、`AUTO_SIMPLIFY_MIN_ROOT_DESC_GEOM`、`AUTO_SIMPLIFY_MIN_TOTAL_COLLAPSED`。
  - **样本（AS3000 连接器）**：`nodes_geometry 35900 -> 16738`；合并 67 组“盘级父节点”，移除 19229 个刷丝节点（每盘 287 个）。注意：合并会破坏实例化复用，GLB 文件体积可能变大，但 draw calls 与拾取/高亮压力显著下降。
    - 示例产物：`output/03.02.10.0007T-AS3000-BIG BM清除器Big BM连接器/glb_files/product_total.simplified.glb` + `output/03.02.10.0007T-AS3000-BIG BM清除器Big BM连接器/glb_files/product_total.simplified.glb.simplify_report.json`
  - **本地验证脚本**：`python scripts/simplify_glb.py <input.glb> <output.glb> --force`（会同时输出 `*.simplify_report.json` 统计报告）。
- **OCP(OpenCASCADE) 兜底转换（解决 Step4 卡死/超时）**：
  - **触发方式**：`trimesh.load(..., force='scene')` 超时/失败时自动回退到 OCP；对命中“超长参数行”的 STEP，会预检后优先走 OCP（避免先等 120s 硬超时）。
  - **实现**：新增 `processors/ocp_step_to_glb.py`，使用 `cadquery-ocp` 的 XDE(STEPCAFControl) 读取 STEP 并按“组件/刷毛特征层折叠”策略导出 GLB。
  - **粒度策略**：默认尽量下钻拿到组件层级；刷毛类（名称含 `毛刷/刷片/刷丝/brush/bristle` 且带数字后缀）优先折叠为组件级 mesh；若输出 mesh 仍过多则回退到更粗层级以保证可生成与可渲染。
  - **环境变量**：`OCP_STEP_FALLBACK`、`OCP_STEP_FALLBACK_TIMEOUT_SECONDS`、`OCP_MESH_LINEAR_DEFLECTION`、`OCP_MESH_ANGULAR_DEFLECTION`、`OCP_MAX_MESHES`、`OCP_COLLAPSE_LEAF_THRESHOLD`、`STEP_TO_GLB_PREFER_OCP`、`STEP_LONG_LINE_THRESHOLD`、`STEP_LONG_LINE_HIT_COUNT`。
- **Windows 兼容修复（spawn/pickle）**：将 `trimesh` 子进程 worker 从嵌套函数移到模块顶层，避免 Windows `multiprocessing` 的 pickling 失败。
- 影响文件：`processors/glb_simplifier.py`、`processors/ocp_step_to_glb.py`、`processors/file_processor.py`、`scripts/simplify_glb.py`、`requirements.txt`、`docker_requirements.txt`、`Memory_Development/index.md`

## v2.0.80 (2026-01-12)
- **移除 OCP 兜底依赖**：撤回 `ocp_tessellate` 低精度兜底路径，保持 `trimesh` 子进程 120s 硬超时（超时强制终止）以防卡死，依赖不再包含 OCP/ocp-tessellate。
- 影响文件：`processors/file_processor.py`、`docker_requirements.txt`、`Memory_Development/index.md`

## v2.0.78 (2026-01-12)
- **STEP→GLB 硬超时兜底**：
  - 将 STEP 转 GLB 的 `trimesh.load` 转换放入子进程，默认 120s 硬超时，超时直接终止子进程并返回失败，避免接口/流水线被卡死。
  - 失败返回明确 `trimesh转换超时`，便于前端展示和重试/删除卡任务。
- 影响文件：`processors/file_processor.py`、`Memory_Development/index.md`

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
