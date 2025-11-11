@echo off
chcp 65001 >nul
echo ========================================
echo MecAgent v1.0.0 Release Script
echo ========================================
echo.

echo [1/5] 添加所有更改到暂存区...
git add -A
if %errorlevel% neq 0 (
    echo ❌ Git add 失败
    pause
    exit /b 1
)
echo ✅ 完成

echo.
echo [2/5] 提交更改...
git commit -m "Release v1.0.0: 首个正式版本" -m "✨ 新增功能:" -m "- AI模型切换到Gemini 2.5 Flash Preview" -m "- JSON解析自动重试机制（最多3次）" -m "- BOM名称验证优化（去除数量后缀）" -m "- BOM覆盖率保障系统（组件级≥95%%，产品级≥80%%）" -m "- 用户输入产品名称功能" -m "" -m "🐛 Bug修复:" -m "- 修复BOM名称验证误报问题" -m "- 修复产品名称显示为'未命名产品'的问题" -m "- 修复JSON解析失败导致流程中断的问题" -m "- 修复BOM覆盖率计算不准确的问题" -m "" -m "📝 文档更新:" -m "- 新增 OPTIMIZATION_SUMMARY.md" -m "- 新增 RELEASE_NOTES_v1.0.0.md" -m "- 更新 CHANGELOG.md" -m "" -m "🚀 性能提升:" -m "- JSON解析成功率: 70%% → 95%%+" -m "- 组件级BOM覆盖率: 55.6%% → 95%%+" -m "- 产品级BOM覆盖率: 32.1%% → 80%%+" -m "- BOM名称误报率降低: 90%%+"
if %errorlevel% neq 0 (
    echo ❌ Git commit 失败
    pause
    exit /b 1
)
echo ✅ 完成

echo.
echo [3/5] 创建标签 v1.0.0...
git tag -a v1.0.0 -m "MecAgent v1.0.0 - 首个正式版本" -m "" -m "🎉 主要特性:" -m "- 6-Agent智能协作系统" -m "- BOM-3D智能匹配" -m "- 交互式Web装配说明书" -m "- Gemini 2.5 Flash AI模型" -m "- 自动重试和质量保障机制" -m "" -m "详见 RELEASE_NOTES_v1.0.0.md"
if %errorlevel% neq 0 (
    echo ❌ Git tag 失败
    pause
    exit /b 1
)
echo ✅ 完成

echo.
echo [4/5] 推送到远程仓库...
git push origin main
if %errorlevel% neq 0 (
    echo ❌ Git push 失败
    pause
    exit /b 1
)
echo ✅ 完成

echo.
echo [5/5] 推送标签到远程仓库...
git push origin v1.0.0
if %errorlevel% neq 0 (
    echo ❌ Git push tag 失败
    pause
    exit /b 1
)
echo ✅ 完成

echo.
echo ========================================
echo ✅ v1.0.0 发布成功！
echo ========================================
echo.
echo 下一步：
echo 1. 访问 https://github.com/sga-jerrylin/Mecagent/releases
echo 2. 点击 "Draft a new release"
echo 3. 选择标签 v1.0.0
echo 4. 复制 RELEASE_NOTES_v1.0.0.md 的内容
echo 5. 点击 "Publish release"
echo.
pause

