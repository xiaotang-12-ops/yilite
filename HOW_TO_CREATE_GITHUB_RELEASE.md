# 📦 如何创建 GitHub Release

本文档说明如何在 GitHub 上为 v1.1.4 版本创建 Release。

---

## 🎯 步骤1: 访问 GitHub 仓库

打开浏览器，访问你的 GitHub 仓库：

```
https://github.com/xiaotang-12-ops/yilite
```

---

## 🎯 步骤2: 进入 Releases 页面

### 方法1: 通过右侧边栏

1. 在仓库主页右侧，找到 **"Releases"** 区域
2. 点击 **"Create a new release"** 或 **"Draft a new release"**

### 方法2: 直接访问

访问以下链接：
```
https://github.com/xiaotang-12-ops/yilite/releases/new
```

---

## 🎯 步骤3: 填写 Release 信息

### 3.1 选择标签 (Choose a tag)

在 **"Choose a tag"** 下拉框中：
- 输入或选择: `v1.1.4`
- 如果标签已存在（我们已经推送了），会显示 "Existing tag"
- 如果标签不存在，会提示 "Create new tag: v1.1.4 on publish"

**确认**: 选择 `v1.1.4` 标签

### 3.2 设置目标分支 (Target)

- 保持默认: `main` 分支
- 或者选择: `v1.1.4` 标签对应的提交

### 3.3 填写 Release 标题 (Release title)

输入：
```
v1.1.4 - 修复组件步骤过滤BUG
```

### 3.4 填写 Release 说明 (Describe this release)

**方法1: 复制 RELEASE_v1.1.4.md 的内容**

打开 `Mecagent/RELEASE_v1.1.4.md` 文件，复制全部内容，粘贴到 Release 说明框中。

**方法2: 手动输入（简化版）**

```markdown
## 🐛 严重BUG修复（组件步骤数据混乱问题）

### 问题描述

**严重级别**: 🔴 严重（会导致数据显示错误和混乱）  
**影响范围**: 前端页面显示、编辑功能

**现象**:
1. 编辑页面显示有内容（可以看到编辑器里有数据）
2. 但前端页面没有渲染这些内容（页面显示为空或显示其他内容）
3. 不同组件的相同步骤号数据混在一起显示
4. 例如：主框架组件的步骤1 显示了 挂架组件的步骤1 的焊接数据

### 解决方案

**核心原则**:
- 必须同时匹配 `step_number` 和 `component` 才能正确过滤数据
- 组件名称必须由系统自动确定，不允许用户修改

**具体修改**:
1. ✅ 恢复双重过滤逻辑（步骤号 + 组件名称）
2. ✅ 编辑对话框中组件名称和步骤号设为只读
3. ✅ 修复添加数据时使用错误字段的问题
4. ✅ 强制保存时使用当前步骤的正确信息

### 修改文件

- `frontend/src/views/ManualViewer.vue`: 修复过滤逻辑、编辑表单、保存逻辑

### 文档更新

- `Memory_Development/index.md`: 更新版本号
- `Memory_Development/changelog.md`: 添加详细记录

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

**完整更新日志**: https://github.com/xiaotang-12-ops/yilite/blob/main/Memory_Development/changelog.md
```

### 3.5 附加文件（可选）

如果你想附加一些文件（例如：编译好的二进制文件、压缩包等），可以在 **"Attach binaries by dropping them here or selecting them"** 区域上传。

**对于本项目**，通常不需要附加文件，因为用户可以直接通过 Docker 部署。

### 3.6 设置为预发布版本（可选）

如果这是一个测试版本或预发布版本，可以勾选：
- ☑️ **"Set as a pre-release"**

**对于 v1.1.4**，这是一个正式版本，**不要勾选**。

### 3.7 设置为最新版本

勾选：
- ☑️ **"Set as the latest release"**

这样用户访问仓库时，会在右侧看到这个版本作为最新版本。

---

## 🎯 步骤4: 发布 Release

1. **预览**: 点击 **"Preview"** 标签页，查看 Release 说明的渲染效果
2. **发布**: 确认无误后，点击绿色按钮 **"Publish release"**

---

## ✅ 步骤5: 验证 Release

发布成功后：

1. **访问 Releases 页面**: https://github.com/xiaotang-12-ops/yilite/releases
2. **确认显示**: 应该能看到 `v1.1.4` 版本
3. **检查右侧边栏**: 仓库主页右侧的 "Releases" 区域应该显示 "1 release"
4. **检查标签**: 访问 https://github.com/xiaotang-12-ops/yilite/tags，应该能看到 `v1.1.4` 标签

---

## 📸 截图参考

### Release 创建页面示例

```
┌─────────────────────────────────────────────────────────┐
│ Create a new release                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Choose a tag                                            │
│ ┌─────────────────────────────────────────────────┐   │
│ │ v1.1.4                                    ▼     │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Target: main ▼                                          │
│                                                         │
│ Release title                                           │
│ ┌─────────────────────────────────────────────────┐   │
│ │ v1.1.4 - 修复组件步骤过滤BUG                    │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Describe this release                                   │
│ ┌─────────────────────────────────────────────────┐   │
│ │ ## 🐛 严重BUG修复                                │   │
│ │                                                 │   │
│ │ ### 问题描述                                     │   │
│ │ ...                                             │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ Attach binaries (optional)                              │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Drag and drop files here                        │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ ☐ Set as a pre-release                                  │
│ ☑ Set as the latest release                             │
│                                                         │
│ ┌─────────────────────────────────────────────────┐   │
│ │          Publish release                        │   │
│ └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 🎉 完成！

现在你的 GitHub 仓库已经有了正式的 v1.1.4 Release！

用户可以：
- 在 Releases 页面查看所有版本
- 下载特定版本的代码（ZIP 或 tar.gz）
- 查看每个版本的更新说明
- 通过标签切换到特定版本

---

## 📝 未来版本发布

以后发布新版本时，按照以下流程：

1. ✅ 修改代码并测试
2. ✅ 更新 `VERSION` 文件
3. ✅ 更新 `Memory_Development/index.md` 和 `changelog.md`
4. ✅ 提交代码: `git commit -m "v1.1.5: 描述"`
5. ✅ 创建标签: `git tag -a v1.1.5 -m "描述"`
6. ✅ 推送代码和标签: `git push origin main && git push origin v1.1.5`
7. ✅ 在 GitHub 上创建 Release（按照本文档的步骤）

**详细流程**: 请查看 `VERSION_CONTROL.md` 文档

---

## 🔗 相关链接

- **仓库地址**: https://github.com/xiaotang-12-ops/yilite
- **Releases 页面**: https://github.com/xiaotang-12-ops/yilite/releases
- **Tags 页面**: https://github.com/xiaotang-12-ops/yilite/tags
- **版本控制规范**: [VERSION_CONTROL.md](VERSION_CONTROL.md)
- **部署指南**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

**最后更新**: 2025-11-11

