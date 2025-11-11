@echo off
chcp 65001 >nul
echo ========================================
echo    智能装配说明书生成系统 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    pause
    exit /b 1
)
echo ✅ Python 已安装

cd frontend
call npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js/npm 未安装或未添加到 PATH
    pause
    exit /b 1
)
echo ✅ Node.js/npm 已安装
cd ..

echo.
echo [2/3] 启动后端服务器...
start "后端服务器" cmd /k "cd /d %~dp0 && python backend/simple_app.py"
timeout /t 3 >nul

echo.
echo [3/3] 启动前端开发服务器...
start "前端服务器" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo ✅ 启动完成！
echo.
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173
echo.
echo 请等待几秒钟，然后在浏览器中访问：
echo http://localhost:5173/viewer
echo.
echo 按任意键打开浏览器...
echo ========================================
pause >nul

start http://localhost:5173/viewer

