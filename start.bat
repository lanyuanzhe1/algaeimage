@echo off
chcp 65001 >nul
cd /d "%~dp0..\code\algae_image_v2"

echo ============================================
echo   Algae Image V2 — 启动中...
echo ============================================

REM 检查端口是否被占用
netstat -ano | findstr ":8000.*LISTENING" >nul
if %errorlevel% equ 0 (
    echo [警告] 端口 8000 已被占用，尝试清理...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
)

REM 启动 uvicorn（新窗口，方便观察日志）
start "AlgaeV2-Server" "A:\Anaconda_envs\envs\ican\python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

REM 等待服务就绪
echo 等待服务启动...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/docs >nul 2>&1
if %errorlevel% neq 0 goto wait_loop

echo 服务已就绪！

REM 打开火狐浏览器
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" "http://127.0.0.1:8000/app/"

echo ============================================
echo   启动完成！
echo   后端: http://127.0.0.1:8000
echo   前端: http://127.0.0.1:8000/app/
echo   API:  http://127.0.0.1:8000/docs
echo ============================================
echo.
echo 关闭方法：双击 stop.bat 或关闭 AlgaeV2-Server 窗口
pause
