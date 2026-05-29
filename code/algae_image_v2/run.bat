@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Algae Image V2 - FMPD

echo ============================================
echo   Algae Image V2
echo   FMPD 明场藻类检测 - HSV偏振 + YOLO
echo ============================================
echo.

IF NOT EXIST "weights\best_v8l.pt" (
    echo [错误] 未找到 YOLO 权重: weights\best_v8l.pt
    pause
    exit /b 1
)

echo [1/3] 激活 Conda 环境 ican...
call A:\Anaconda_envs\envs\ican\python.exe --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [错误] 无法找到 conda 环境 ican 的 Python
    pause
    exit /b 1
)

echo [2/3] 检查依赖...
A:\Anaconda_envs\envs\ican\python.exe -c "import fastapi, uvicorn, torch, ultralytics, cv2" 2>nul
IF ERRORLEVEL 1 (
    echo [警告] 部分依赖缺失，正在安装...
    A:\Anaconda_envs\envs\ican\python.exe -m pip install -r requirements.txt
)

echo [3/3] 启动 Algae Image V2...
echo.
echo   后端服务: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:8000/app/
echo   管线: HSV偏振 -^(skip RDN^) - I_enh v2 - YOLOv8l
echo.
echo   按 Ctrl+C 停止服务
echo ============================================

start "" http://localhost:8000/app/
A:\Anaconda_envs\envs\ican\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
