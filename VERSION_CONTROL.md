# 📌 版本控制规范

本文档说明如何管理项目版本、发布新版本以及维护版本历史。

---

## 📖 版本号规范

本项目采用 **语义化版本控制 (Semantic Versioning)**，版本号格式为：`MAJOR.MINOR.PATCH`

### 版本号说明

```
v1.2.3
│ │ │
│ │ └─ PATCH: 修复bug、小改动（向后兼容）
│ └─── MINOR: 新增功能（向后兼容）
└───── MAJOR: 重大更新（可能不向后兼容）
```

### 版本号递增规则

| 类型 | 说明 | 示例 |
|------|------|------|
| **MAJOR** | 重大架构变更、API不兼容更新 | `1.0.0` → `2.0.0` |
| **MINOR** | 新增功能、新增API（向后兼容） | `1.0.0` → `1.1.0` |
| **PATCH** | Bug修复、小优化（向后兼容） | `1.0.0` → `1.0.1` |

### 版本号示例

- `v1.0.0` - 首个正式版本
- `v1.1.0` - 新增管理员编辑功能
- `v1.1.1` - 修复编辑对话框bug
- `v1.1.2` - 修复数据保存问题
- `v1.1.3` - 优化过滤逻辑
- `v1.1.4` - 修复组件步骤过滤bug
- `v2.0.0` - 重构后端架构（不兼容旧版本）

---

## 🔄 版本发布流程

### 步骤1: 确定版本号

根据本次更新内容，确定新版本号：

```bash
# 查看当前版本
git describe --tags --abbrev=0

# 或查看所有版本
git tag -l
```

**决策树**：
- 是否有不兼容的API变更？ → **YES**: MAJOR + 1
- 是否新增功能？ → **YES**: MINOR + 1
- 是否只是修复bug？ → **YES**: PATCH + 1

### 步骤2: 更新版本文件

需要更新以下文件中的版本号：

#### 1. `package.json` (前端版本)
```json
{
  "name": "assembly-manual-frontend",
  "version": "1.1.4",  // ← 更新这里
  ...
}
```

#### 2. `backend/simple_app.py` (后端版本)
```python
# 在文件顶部添加版本号
__version__ = "1.1.4"  # ← 更新这里

# 在 /api/version 端点返回版本信息
@app.get("/api/version")
async def get_version():
    return {
        "version": __version__,
        "name": "智能装配说明书生成系统"
    }
```

#### 3. `CHANGELOG.md` (版本历史)
在文件顶部添加新版本的更新内容（见下文）

#### 4. `Memory_Development/index.md` (项目快照)
更新"最近3个版本"部分

### 步骤3: 更新 CHANGELOG.md

在 `CHANGELOG.md` 文件顶部添加新版本信息：

```markdown
## [v1.1.4] - 2025-11-11

### 🐛 Bug修复
- 修复组件步骤过滤BUG，恢复双重过滤逻辑（步骤号 + 组件名称）
- 修复编辑对话框中组件名称可修改导致的数据不一致问题
- 修复添加新数据时使用错误字段的问题

### ✨ 改进
- 编辑对话框中步骤号和组件名称设为只读，防止用户误修改
- 保存时强制使用当前步骤的正确值，确保数据一致性
- 优化删除逻辑，避免误删其他组件的数据

### 📝 文档
- 更新 Memory_Development 文档
- 添加详细的bug修复说明
```

### 步骤4: 提交代码

```bash
# 1. 查看修改的文件
git status

# 2. 添加所有修改的文件
git add .

# 3. 提交（使用规范的提交信息）
git commit -m "chore: 发布 v1.1.4 版本

- 更新版本号到 v1.1.4
- 更新 CHANGELOG.md
- 修复组件步骤过滤BUG
"

# 4. 推送到远程仓库
git push origin main
```

### 步骤5: 创建 Git Tag

```bash
# 创建带注释的标签（推荐）
git tag -a v1.1.4 -m "v1.1.4: 修复组件步骤过滤BUG

主要更新:
- 修复组件步骤过滤BUG，恢复双重过滤逻辑
- 编辑对话框中组件名称设为只读
- 保存时强制使用正确的组件名称
"

# 推送标签到远程仓库
git push origin v1.1.4

# 或推送所有标签
git push origin --tags
```

### 步骤6: 在 GitHub 上创建 Release

1. **访问 GitHub 仓库**: https://github.com/xiaotang-12-ops/yilite
2. **点击右侧的 "Releases"** → **"Create a new release"**
3. **选择刚才创建的标签**: `v1.1.4`
4. **填写 Release 信息**:
   - **Release title**: `v1.1.4 - 修复组件步骤过滤BUG`
   - **Description**: 复制 CHANGELOG.md 中的内容
5. **点击 "Publish release"**

---

## 📝 提交信息规范

使用 **Conventional Commits** 规范：

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新增功能 | `feat: 添加管理员编辑功能` |
| `fix` | 修复bug | `fix: 修复组件步骤过滤BUG` |
| `docs` | 文档更新 | `docs: 更新部署指南` |
| `style` | 代码格式调整（不影响功能） | `style: 格式化代码` |
| `refactor` | 代码重构（不改变功能） | `refactor: 重构过滤逻辑` |
| `perf` | 性能优化 | `perf: 优化数据加载速度` |
| `test` | 测试相关 | `test: 添加单元测试` |
| `chore` | 构建/工具相关 | `chore: 更新依赖版本` |

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**示例**：
```bash
git commit -m "fix(frontend): 修复组件步骤过滤BUG

- 恢复双重过滤逻辑（步骤号 + 组件名称）
- 编辑对话框中组件名称设为只读
- 保存时强制使用正确的组件名称

Closes #123
"
```

---

## 🔍 版本查询

### 查看当前版本
```bash
# 查看最新标签
git describe --tags --abbrev=0

# 查看所有标签
git tag -l

# 查看标签详情
git show v1.1.4
```

### 查看版本历史
```bash
# 查看提交历史
git log --oneline --decorate --graph

# 查看某个版本的详细信息
git show v1.1.4

# 查看两个版本之间的差异
git diff v1.1.3..v1.1.4
```

### 切换到特定版本
```bash
# 切换到某个版本（只读模式）
git checkout v1.1.4

# 基于某个版本创建新分支
git checkout -b hotfix/v1.1.4 v1.1.4

# 返回最新版本
git checkout main
```

---

## 🌿 分支管理策略

### 主要分支

| 分支 | 说明 | 保护 |
|------|------|------|
| `main` | 主分支，始终保持稳定可发布状态 | ✅ |
| `develop` | 开发分支，集成最新开发功能 | ✅ |

### 辅助分支

| 分支类型 | 命名规范 | 说明 | 示例 |
|---------|---------|------|------|
| 功能分支 | `feature/*` | 开发新功能 | `feature/admin-edit` |
| 修复分支 | `fix/*` | 修复bug | `fix/filter-bug` |
| 热修复分支 | `hotfix/*` | 紧急修复生产bug | `hotfix/v1.1.5` |
| 发布分支 | `release/*` | 准备发布新版本 | `release/v1.2.0` |

### 工作流程

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/new-feature

# 2. 开发功能，提交代码
git add .
git commit -m "feat: 添加新功能"

# 3. 推送到远程
git push origin feature/new-feature

# 4. 在 GitHub 上创建 Pull Request
# 5. 代码审查通过后，合并到 main
# 6. 删除功能分支
git branch -d feature/new-feature
git push origin --delete feature/new-feature
```

---

## 📦 发布检查清单

发布新版本前，请确认以下事项：

### 代码质量
- [ ] 所有功能已测试通过
- [ ] 没有已知的严重bug
- [ ] 代码已经过审查
- [ ] 所有测试用例通过

### 文档更新
- [ ] 更新 `CHANGELOG.md`
- [ ] 更新 `Memory_Development/index.md`
- [ ] 更新 `package.json` 版本号
- [ ] 更新 `backend/simple_app.py` 版本号
- [ ] 更新 README.md（如有必要）

### 版本控制
- [ ] 确定正确的版本号
- [ ] 提交所有代码更改
- [ ] 创建 Git Tag
- [ ] 推送 Tag 到远程仓库
- [ ] 在 GitHub 上创建 Release

### 部署验证
- [ ] 本地 Docker 部署测试通过
- [ ] 前端页面正常访问
- [ ] 后端 API 正常工作
- [ ] 数据持久化正常

---

## 🚀 快速发布命令

创建一个快速发布脚本 `release.sh`（Linux/Mac）或 `release.bat`（Windows）：

### release.sh (Linux/Mac)
```bash
#!/bin/bash

# 获取版本号参数
VERSION=$1

if [ -z "$VERSION" ]; then
    echo "❌ 请提供版本号，例如: ./release.sh v1.1.5"
    exit 1
fi

echo "🚀 开始发布 $VERSION..."

# 1. 确保在 main 分支
git checkout main
git pull origin main

# 2. 提交所有更改
git add .
git commit -m "chore: 发布 $VERSION 版本"

# 3. 创建标签
git tag -a $VERSION -m "Release $VERSION"

# 4. 推送代码和标签
git push origin main
git push origin $VERSION

echo "✅ 发布完成！"
echo "📝 请访问 GitHub 创建 Release: https://github.com/xiaotang-12-ops/yilite/releases/new"
```

### release.bat (Windows)
```batch
@echo off
set VERSION=%1

if "%VERSION%"=="" (
    echo ❌ 请提供版本号，例如: release.bat v1.1.5
    exit /b 1
)

echo 🚀 开始发布 %VERSION%...

REM 1. 确保在 main 分支
git checkout main
git pull origin main

REM 2. 提交所有更改
git add .
git commit -m "chore: 发布 %VERSION% 版本"

REM 3. 创建标签
git tag -a %VERSION% -m "Release %VERSION%"

REM 4. 推送代码和标签
git push origin main
git push origin %VERSION%

echo ✅ 发布完成！
echo 📝 请访问 GitHub 创建 Release: https://github.com/xiaotang-12-ops/yilite/releases/new
```

### 使用方法
```bash
# Linux/Mac
chmod +x release.sh
./release.sh v1.1.5

# Windows
release.bat v1.1.5
```

---

## 📚 参考资源

- [语义化版本控制](https://semver.org/lang/zh-CN/)
- [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)
- [Git 分支管理策略](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Releases 文档](https://docs.github.com/en/repositories/releasing-projects-on-github)

---

**版本控制是软件开发的重要环节，规范的版本管理能让项目更易维护！** 🎯

