# 如何发布 v1.0.0 版本

## 方法1：使用批处理脚本（推荐）

### 步骤：

1. **运行发布脚本**
   ```bash
   release_v1.0.0.bat
   ```

2. **脚本会自动完成：**
   - ✅ 添加所有更改到暂存区
   - ✅ 提交更改
   - ✅ 创建标签 v1.0.0
   - ✅ 推送到远程仓库
   - ✅ 推送标签到远程仓库

3. **在GitHub上创建Release**
   - 访问 https://github.com/sga-jerrylin/Mecagent/releases
   - 点击 "Draft a new release"
   - 选择标签 `v1.0.0`
   - 标题填写：`v1.0.0 - 首个正式版本 🎉`
   - 复制 `RELEASE_NOTES_v1.0.0.md` 的内容到描述框
   - 点击 "Publish release"

---

## 方法2：手动执行命令

### 步骤：

**1. 添加所有更改**
```bash
git add -A
```

**2. 提交更改**
```bash
git commit -m "Release v1.0.0: 首个正式版本

✨ 新增功能:
- AI模型切换到Gemini 2.5 Flash Preview
- JSON解析自动重试机制（最多3次）
- BOM名称验证优化（去除数量后缀）
- BOM覆盖率保障系统（组件级≥95%，产品级≥80%）
- 用户输入产品名称功能

🐛 Bug修复:
- 修复BOM名称验证误报问题
- 修复产品名称显示为'未命名产品'的问题
- 修复JSON解析失败导致流程中断的问题
- 修复BOM覆盖率计算不准确的问题

📝 文档更新:
- 新增 OPTIMIZATION_SUMMARY.md
- 新增 RELEASE_NOTES_v1.0.0.md
- 更新 CHANGELOG.md

🚀 性能提升:
- JSON解析成功率: 70% → 95%+
- 组件级BOM覆盖率: 55.6% → 95%+
- 产品级BOM覆盖率: 32.1% → 80%+
- BOM名称误报率降低: 90%+"
```

**3. 创建标签**
```bash
git tag -a v1.0.0 -m "MecAgent v1.0.0 - 首个正式版本

🎉 主要特性:
- 6-Agent智能协作系统
- BOM-3D智能匹配
- 交互式Web装配说明书
- Gemini 2.5 Flash AI模型
- 自动重试和质量保障机制

详见 RELEASE_NOTES_v1.0.0.md"
```

**4. 推送到远程仓库**
```bash
git push origin main
```

**5. 推送标签**
```bash
git push origin v1.0.0
```

**6. 在GitHub上创建Release**
   - 访问 https://github.com/sga-jerrylin/Mecagent/releases
   - 点击 "Draft a new release"
   - 选择标签 `v1.0.0`
   - 标题填写：`v1.0.0 - 首个正式版本 🎉`
   - 复制 `RELEASE_NOTES_v1.0.0.md` 的内容到描述框
   - 点击 "Publish release"

---

## 方法3：使用GitHub CLI（如果已安装）

```bash
# 1. 添加和提交
git add -A
git commit -m "Release v1.0.0: 首个正式版本"

# 2. 推送
git push origin main

# 3. 创建Release（自动创建tag）
gh release create v1.0.0 \
  --title "v1.0.0 - 首个正式版本 🎉" \
  --notes-file RELEASE_NOTES_v1.0.0.md
```

---

## 📋 发布检查清单

在发布前，请确认：

- [ ] 所有代码已测试通过
- [ ] CHANGELOG.md 已更新
- [ ] RELEASE_NOTES_v1.0.0.md 已创建
- [ ] OPTIMIZATION_SUMMARY.md 已创建
- [ ] 版本号正确（v1.0.0）
- [ ] 所有文档链接有效
- [ ] .env 文件未提交（在.gitignore中）
- [ ] 敏感信息已移除

---

## 📝 Release Notes 内容预览

标题：
```
v1.0.0 - 首个正式版本 🎉
```

描述：
```
复制 RELEASE_NOTES_v1.0.0.md 的全部内容
```

---

## 🎯 发布后的工作

1. **验证Release**
   - 检查 https://github.com/sga-jerrylin/Mecagent/releases/tag/v1.0.0
   - 确认Release Notes显示正确
   - 确认标签已创建

2. **更新文档**
   - 在README.md中添加版本徽章
   - 更新安装说明中的版本号

3. **通知用户**
   - 发布公告
   - 更新项目主页

---

## ❓ 常见问题

**Q: 如果推送失败怎么办？**
A: 检查网络连接和GitHub权限，然后重新运行推送命令。

**Q: 如何撤销已发布的Release？**
A: 在GitHub Release页面点击"Delete"，然后删除本地和远程的tag：
```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

**Q: 如何修改Release Notes？**
A: 在GitHub Release页面点击"Edit release"，修改后保存。

---

**准备好了吗？运行 `release_v1.0.0.bat` 开始发布！** 🚀

