# Release Notes - v1.1.6

**发布日期**: 2025-11-13  
**GitHub**: https://github.com/xiaotang-12-ops/yilite

---

## 🎉 主要更新

本版本主要修复了 Agent 2 的 3D 零件识别问题，并修复了前端组件名称同步的 Bug。

---

## ✨ 新增功能

### 1. Agent 2 规则优化
- ✅ 修复 3D 零件识别不全问题
- ✅ 优化 BOM-3D 匹配逻辑
- ✅ 提高零件识别准确率

---

## 🐛 Bug 修复

### 1. 焊接模块组件名称同步问题 ⭐

**问题描述**:
- 修改焊接模块的组件名称无法同步到 `component_name`
- 安全警告模块可以同步，但焊接模块不行
- 导致前端显示的组件名称与编辑的不一致

**根本原因**:
保存时执行顺序导致数据覆盖：
1. 焊接模块先更新 `component.component_name = updatedComponentName`（新值 ✅）
2. 安全警告模块后更新 `component.component_name = updatedComponentNameFromSafety`（旧值 ❌）
3. 因为用户只修改了焊接模块的组件名称，安全警告模块的 `warning.component` 还是旧值
4. 导致安全警告模块用旧值覆盖了焊接模块的更新

**修复方案**:
采用**实时同步**方案：
- ✅ 添加 `watch` 监听焊接模块的组件名称变化
- ✅ 自动同步到安全警告模块的所有警告
- ✅ 安全警告模块的组件名称设为只读（灰色背景）
- ✅ 焊接模块增加醒目的警告提示（橙色 + 图标）

**修改文件**:
- `frontend/src/views/ManualViewer.vue`
  - 第383-392行: 焊接模块组件名称提示增强
  - 第484-494行: 安全警告模块组件名称设为只读
  - 第587-592行: 导入 Warning 图标
  - 第1206-1220行: 添加 watch 监听逻辑

**技术细节**:
```javascript
// 监听焊接模块的组件名称变化
watch(
  () => editData.value.welding_requirements.length > 0
    ? editData.value.welding_requirements[0].component
    : null,
  (newComponentName) => {
    if (newComponentName && editData.value.safety_warnings.length > 0) {
      // 同步到所有安全警告
      editData.value.safety_warnings.forEach(warning => {
        warning.component = newComponentName
      })
      console.log('🔄 [组件名称同步] 焊接模块 → 安全警告模块:', newComponentName)
    }
  }
)
```

### 2. 登录修改功能正常运行
- ✅ 管理员登录功能正常
- ✅ 编辑功能正常
- ✅ 数据保存正常

---

## ⚠️ 已知问题

### 1. 三色原则未实现
- ❌ 当前版本未实现三色原则（红色/黄色/绿色标注）
- 📝 计划在后续版本中实现

---

## 🎯 用户体验提升

- ✅ **视觉提示**: 焊接模块有醒目的橙色警告提示
- ✅ **自动同步**: 修改焊接模块时，安全警告模块实时同步
- ✅ **防止混淆**: 安全警告模块的组件名称设为只读（灰色）
- ✅ **调试友好**: 控制台会输出同步日志 `🔄 [组件名称同步]`

---

## 📝 修改文件清单

### 前端
- ✅ `frontend/src/views/ManualViewer.vue` - 组件名称同步逻辑
- ✅ `VERSION` - 版本号更新为 1.1.6

### 后端
- ✅ Agent 2 规则优化（具体文件待补充）

### 文档
- ✅ `Memory_Development/project.md` - 更新项目快照
- ✅ `Memory_Development/changelog.md` - 添加 v1.1.6 版本记录
- ✅ `RELEASE_v1.1.6.md` - 本发布说明

---

## 🧪 测试建议

### 测试场景1：修改焊接模块组件名称
1. 打开装配说明书页面
2. 登录管理员账号（密码：`admin123`）
3. 点击"编辑内容"按钮
4. 切换到"焊接要求"标签页
5. 修改组件名称为 "测试组件A"
6. 切换到"安全警告"标签页
7. **预期结果**: 安全警告模块的组件名称自动变为 "测试组件A"（灰色只读状态）
8. 点击"保存"按钮
9. 刷新页面
10. **预期结果**: 步骤标题显示 "测试组件A"

### 测试场景2：Agent 2 零件识别
1. 上传包含多个零件的 STEP 文件
2. 运行生成流程
3. **预期结果**: 所有零件都能被正确识别和匹配

---

## 📦 部署指南

### Docker 部署（推荐）

```bash
# 1. 拉取最新代码
git pull origin main

# 或者切换到 v1.1.6 标签
git checkout v1.1.6

# 2. 重启服务
docker-compose down
docker-compose up -d --build
```

### 本地开发

```bash
# 前端
cd frontend
npm install
npm run dev

# 后端
pip install -r requirements.txt
python api.py
```

---

## 🔄 从 v1.1.5 升级

### 数据兼容性
- ✅ 完全兼容 v1.1.5 的数据格式
- ✅ 无需迁移数据

### 配置变更
- 无配置变更

---

## ⚠️ 注意事项

1. **组件名称同步**:
   - 现在只能通过焊接模块修改组件名称
   - 安全警告模块的组件名称是只读的
   - 修改焊接模块的组件名称会自动同步到安全警告模块

2. **三色原则**:
   - 当前版本未实现三色原则
   - 如需此功能，请等待后续版本更新

3. **Docker 部署**:
   - 前后端都基于 Docker 运行
   - 不要直接用 `npm run dev` 启动，应该使用 Docker 命令

---

## 📞 问题反馈

如果遇到问题，请在 GitHub 上提交 Issue：
https://github.com/xiaotang-12-ops/yilite/issues

---

## 🙏 致谢

感谢所有贡献者和用户的反馈！

---

**完整更新日志**: https://github.com/xiaotang-12-ops/yilite/blob/main/Memory_Development/changelog.md

**上一版本**: [v1.1.5](./RELEASE_v1.1.5.md)

