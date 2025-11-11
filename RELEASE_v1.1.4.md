# v1.1.4 - 修复组件步骤过滤BUG

**发布日期**: 2025-11-10

---

## 🐛 严重BUG修复（组件步骤数据混乱问题）

### 问题描述

**严重级别**: 🔴 严重（会导致数据显示错误和混乱）  
**影响范围**: 前端页面显示、编辑功能

**现象**:
1. 编辑页面显示有内容（可以看到编辑器里有数据）
2. 但前端页面没有渲染这些内容（页面显示为空或显示其他内容）
3. 不同组件的相同步骤号数据混在一起显示
4. 例如：主框架组件的步骤1 显示了 挂架组件的步骤1 的焊接数据

### 根本原因

**数据结构特点**:
- 每个组件都有独立的步骤序列
- 例如：主框架组件有步骤1-13，挂架组件有步骤1-7
- 这些步骤是完全不同的，不应该混在一起

**代码问题**:
1. **过滤逻辑错误**（v1.1.3引入）:
   - 之前的修复中，为了解决"编辑后数据不显示"的问题，把过滤逻辑改为只按步骤号过滤
   - 这导致不同组件的相同步骤号数据混乱
   - 例如：显示主框架组件步骤1时，会把所有组件的步骤1数据都显示出来

2. **用户可以手动修改组件名称**:
   - 编辑对话框中，组件名称是可编辑的
   - 用户可能会输入错误的组件名称（例如把"主框架组件-漆后"改成"主连架组件-漆后"）
   - 导致数据不一致，前端页面无法正确过滤显示

3. **添加数据时使用错误的字段**:
   - `addWeldingRequirement()` 和 `addSafetyWarning()` 使用 `currentStep.action` 作为组件名称
   - 应该使用 `currentStep.component_name`

### 解决方案

**核心原则**:
- 必须同时匹配 `step_number` 和 `component` 才能正确过滤数据
- 组件名称必须由系统自动确定，不允许用户修改

**具体修改**:

1. **恢复双重过滤逻辑**:
   - `currentStepWeldingRequirements`: 必须同时匹配 `step_number` 和 `component`
   - `currentStepSafetyWarnings`: 必须同时匹配 `step_number` 和 `component`

2. **编辑对话框中组件名称设为只读**:
   - 步骤号设为禁用（`disabled`）+ 提示文字："步骤号由当前步骤自动确定"
   - 组件名称设为禁用（`disabled` + 灰色背景）+ 提示文字："组件名称由当前步骤自动确定，不可修改"

3. **添加数据时自动填充正确的组件名称**:
   - `addWeldingRequirement()`: 使用 `currentStep.component_name` 而不是 `currentStep.action`
   - `addSafetyWarning()`: 使用 `currentStep.component_name` 而不是 `currentStep.action`

4. **保存时强制使用当前步骤的组件名称**:
   - 焊接数据保存：强制使用 `currentStepNumber` 和 `currentComponentName`
   - 安全警告保存：强制使用 `currentStepNumber` 和 `currentComponentName`
   - 删除逻辑：按 `step_number + component` 删除（避免误删其他组件的数据）

---

## 📝 修改文件

### ManualViewer.vue

**第957-996行**: 恢复焊接数据双重过滤逻辑
```javascript
const filtered = allWelding.filter(req => {
  const stepMatch = req.step_number === currentStepNumber
  const componentMatch = currentComponentName ? req.component === currentComponentName : false
  return stepMatch && componentMatch
})
```

**第998-1026行**: 恢复安全警告双重过滤逻辑
```javascript
const filtered = allSafetyWarnings.filter(warning => {
  const stepMatch = warning.step_number === currentStepNumber
  const componentMatch = currentComponentName ? warning.component === currentComponentName : false
  return stepMatch && componentMatch
})
```

**第400-422行**: 焊接数据编辑表单 - 组件名称设为只读
```vue
<el-form-item label="组件名称">
  <el-input
    v-model="req.component"
    placeholder="例如：固定座组件"
    disabled
    style="background-color: #f5f7fa;"
  />
  <el-text type="info" size="small" style="margin-left: 8px;">
    组件名称由当前步骤自动确定，不可修改
  </el-text>
</el-form-item>
```

**第501-524行**: 安全警告编辑表单 - 组件名称设为只读（同上）

**第1183-1220行**: 修复添加函数使用正确的字段
```javascript
const addWeldingRequirement = () => {
  const currentStep = currentStepData.value
  const stepNumber = currentStep?.step_number || 1
  const componentName = currentStep?.component_name || ''  // 🔥 使用 component_name
  
  editData.value.welding_requirements.push({
    step_number: stepNumber,
    component: componentName,  // 🔥 使用 component_name
    welding_info: { ... }
  })
}
```

**第1252-1287行**: 保存焊接数据时强制使用正确的值
```javascript
const validWeldingReqs = editData.value.welding_requirements
  .filter(r => r.welding_info && ...)
  .map(r => ({
    ...r,
    step_number: currentStepNumber,  // 🔥 强制使用当前步骤号
    component: currentComponentName   // 🔥 强制使用当前组件名称
  }))
```

**第1296-1328行**: 保存安全警告时强制使用正确的值（同上）

---

## 📚 文档更新

- `Memory_Development/index.md`: 更新版本号为 v1.1.4
- `Memory_Development/changelog.md`: 添加 v1.1.4 版本详细记录

---

## ⚠️ 注意事项

- 如果之前手动修改过组件名称的数据（例如"主连架组件-漆后"），这些数据不会自动修正，需要重新编辑保存一次
- 如果发现某个步骤的数据不显示，可以打开编辑对话框，直接保存一次（不需要修改任何内容），系统会自动修正组件名称

---

## 🔄 升级指南

从 v1.1.3 升级到 v1.1.4：

```bash
# 1. 拉取最新代码
git pull origin main

# 或者切换到 v1.1.4 标签
git checkout v1.1.4

# 2. 重启服务
docker-compose down
docker-compose up -d --build
```

---

## 📞 问题反馈

如果遇到问题，请在 GitHub 上提交 Issue：
https://github.com/xiaotang-12-ops/yilite/issues

---

**完整更新日志**: https://github.com/xiaotang-12-ops/yilite/blob/main/Memory_Development/changelog.md

