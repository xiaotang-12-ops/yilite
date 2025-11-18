# 管理员修改写回逻辑（简明版）

目标：说明前端如何把修改写回到 `output/{task_id}/assembly_manual.json` 的具体定位和步骤。

## 写回整体路径
1) 前端在编辑弹窗保存时，收集当前步骤的修改（组件名称、焊接、安全、质检，以及全局 FAQ）。
2) 通过 `PUT /api/manual/{taskId}` 把“整份手册 JSON”发送到后端。
3) 后端直接用这份 JSON 覆盖写回 `output/{task_id}/assembly_manual.json`，并自动把版本号小版本 +1、更新 `lastUpdated`。

## 定位到“当前步骤”并改名的方式
- 标识：每个步骤有全局唯一的 `step_id`（例如 `01.03.4178_step_2` 或 `product_step_1`）。
- 查找顺序：前端保存时，先在 `component_assembly[*].steps` 里按 `step_id` 找；找不到再去 `product_assembly.steps` 里找。
- 同步字段：
  - `component_name`：用弹窗顶部“组件名称”输入框的值，统一写入找到的步骤及其所属组件（组件章节的 `component.component_name` 和步骤的 `step.component_name`），确保组件名称更新后显示一致。
  - `welding`：如果有填写焊接字段，写回 `step.welding`；为空则删除该字段。
  - `safety_warnings`：写回 `step.safety_warnings`（字符串数组）。
  - `quality_check`：写回 `step.quality_check`。
  - FAQ：全局的 `safety_and_faq.faq_items` 直接覆盖。

## 为什么会生效
- 页面渲染与保存共用同一份 `assembly_manual.json`。写回后再次打开页面，前端会按版本号检查并重新拉取该文件，因此新名字/内容会被读出来显示。

## 目前确认的功能状态
- 组件名称：现在由弹窗顶部统一输入，不再依赖焊接/安全子表单；保存时同步到当前步骤和所属组件，已覆盖写回文件。
- 焊接、安全、质检、FAQ：仍按原有表单写回对应字段，逻辑保持可用。

## 注意
- 写回是整份文件覆盖，未做并发合并；同时多窗口保存会以后保存者为准。
- 后端未做登录鉴权，仍沿用前端硬编码密码。
