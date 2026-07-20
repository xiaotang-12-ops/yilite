# 高成本取证记录

## ManualViewer 网格与模型垂直距离基线

- 首次记录：2026-07-18 12:54 +08:00
- 最后核对：2026-07-20 17:28 +08:00
- 记录负责人：只读子代理 `/root/grid_model_evidence`（初始取证）；独立可见执行任务 `019f7d02-7394-7682-aff9-5531416fc7e1`（实现复核）
- 关联计划：`plan/2026-07-18/网格与模型距离校准/计划.md`
- 当前结论：初始取证确认固定 `y=-5` 是跨模型失真的直接原因；实现已改为“归位包围盒底部 - 相对模型尺寸安全间距 + 当前 GLB 归一化偏移”，并用唯一 `THREE.Group` 承载网格与边界。桌面管理员的画面偏移同步平移相机与 `OrbitControls.target`，不会改模型根或爆炸缓存；配置通过既有草稿/发布链按 `glb_file` 保存。管理员入口显示为“调整位置”，面板挂载在默认宽 `400px` 的右侧说明栏内，不使用 `el-dialog`、遮罩或页面滚动锁；移动端和历史版本不显示入口。源码已完成生产构建、`9/9` 场景相关测试和静态契约检查；小糖自行重建最新容器后于 `2026-07-20` 明确反馈“验收好了没啥问题”，页面视觉验收已关闭。
- 初始证据路径：`frontend/src/views/ManualViewer.vue:1841`（旧固定网格常量）；`frontend/src/views/ManualViewer.vue:3985`（模型自适应缩放）；`frontend/src/views/ManualViewer.vue:4010`（旧实现忽略包围盒）；`core/storage.py:215`、`core/storage.py:251`（手册草稿/发布保留附加字段）；`backend/simple_app.py:1883`（草稿保存入口）；`output/压实轮/98d980aa-b656-442d-9c4f-6d003101c845/assembly_manual.json:11`（同一手册多 GLB）。只读统计基线仍为 `43/43` GLB 可解析，`15` 个内部、`28` 个下方、`38` 个命中 `10000` 放大上限，最终 Y 高度 `3.8~43.051`。
- 当前实现证据：`frontend/src/views/ManualViewer.vue:351`（桌面管理员入口门禁）；`:595`（面板挂载在右侧说明栏）；`:4129`（网格按 box 与配置更新）；`:4148`（相机/target 同步 pan）；`:4211`（按当前 GLB 激活）；`:4261`（单次草稿保存）；`frontend/src/views/manual-viewer/sceneCalibration.ts:146`（旧手册/按 GLB 读取）；`:167`（按 GLB 写入与恢复默认）；`frontend/src/views/manual-viewer/components/SceneCalibrationPanel.vue:101`（右侧无蒙层面板，UI 只上抛 preview/cancel/save）；`frontend/tests/sceneCalibration.test.mjs`（6 类纯函数回归）；`frontend/tests/sceneCalibrationPanel.test.mjs`（3 类非模态挂载、事件契约和用户文案回归）。
- 初始证据基线：Git `cfe1b0b7bd4a0be26b8e3e8eeb357e8da2d75b9e`；旧 `ManualViewer.vue` SHA256 `61A522600E46C6C26E0F78B82BB42F9B1649808D6594EAED5A3E604B1A01CA20`；`file_processor.py` SHA256 `043CABF8AB7FC7F97040F72277D6B860CBD36E01065C4D17210A8069C81266D3`；`ocp_step_to_glb.py` SHA256 `8BC01F82EBB904921EADFEF63B8D5781AE4E056353FC91ECCFB85C33CAA00156`；`core/storage.py` SHA256 `98BBBCC837CF36E223E214E009F4E21249B80D5BC49E1FD7EC6D21749EB3B3FB`；`simple_app.py` SHA256 `CC95B1160D89BA2511BCE817BDAB0DEDEABF7AF1115DE12DE2ECC5D1A10E4170`。
- 当前实现基线：功能源码以 Git `cfe1b0b7bd4a0be26b8e3e8eeb357e8da2d75b9e` 为父级形成 `v2.1.57` 发布候选；`ManualViewer.vue` SHA256 `50ADD6CE1BDF4EADD88134CE266A273EC04C5D6116E5A6F12EF4607BE5408434`，`sceneCalibration.ts` SHA256 `9768D9D42025F0AD844DDFB70EEE004C297260BB9EAEDEEA3C4B6E83DA31EFBF`，`SceneCalibrationPanel.vue` SHA256 `C0BCD82B8C7D7655C24AD0B272883FF7745E5BF79311263E98C7FF1369132ABD`，`sceneCalibration.test.mjs` SHA256 `47AA5D847BAEEFD40B32067EDDD3018EF8478FD25299332EC61AC3915B3B4916`，`sceneCalibrationPanel.test.mjs` SHA256 `7270A0DC835B2D120312DE452330A2C6917B57CDC208012B1FAA9005FF5C3137`。发布完成后以 `v2.1.57` tag 指向的提交作为版本基线；任何后续代码改动或 `output/` GLB 集合变化都会使本段源码/数据取证基线失效。
- 适用范围：`ManualViewer` 网格落地、模型中心化、用户网格偏移、按模型持久化、STEP/STL→GLB 轴向或包围盒异常排查。
- 失效条件：`ManualViewer` 的 `GRID_*`、`computeAdaptiveScale`、中心化、`refreshGridHelper`、相机取景或爆炸缓存流程变化；`sceneCalibration.ts` schema/归一化范围变化；Three.js `Box3` 策略变化；转换链增加轴向/落地元数据；`output/` GLB 集合变化。
- 未决项：页面视觉验收已由小糖关闭；当前没有可由 API 直接访问的多 GLB 手册做自动化页面切换回归，按 GLB 隔离由纯函数测试和现有多 GLB 数据结构取证覆盖；项目现有 `vue-tsc@1.8.27` 与 `typescript@5.9.3` 不兼容，显式类型检查未跑通；历史非法包围盒管理员会话仍可能显示“可手动调整”提示，但不会显示入口或允许保存。
- 纠正记录：2026-07-20 用户明确移动端不允许管理员登录，已撤回移动端管理员入口/面板适配，并在入口层显式增加 `!isMobile`；旧记录中的“个人偏好或共享设置未拍板、控件权限未定”已被“桌面管理员保存草稿、发布后共享、按 GLB 隔离”取代。2026-07-20 用户确认居中遮罩会挡住模型，管理员入口改名为“调整位置”，输入区改挂到右侧说明栏内的无蒙层面板，数据与保存链保持不变。
