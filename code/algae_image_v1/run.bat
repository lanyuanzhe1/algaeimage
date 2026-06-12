@echo off
chcp 65001 >nul
title 藻影卫士 V1.0

echo ============================================
echo   藻影卫士 - Algae Guardian V1.0
echo   偏振显微藻类智能检测系统
echo ============================================
echo.

:: Check weights exist
IF NOT EXIST "weights\rdn_polarization.pth" (
    echo [错误] 未找到 RDN 权重: weights\rdn_polarization.pth
    pause
    exit /b 1
)
IF NOT EXIST "weights\best.pt" (
    echo [错误] 未找到 YOLO 权重: weights\best.pt
    pause
    exit /b 1
)

echo [1/3] 激活 Conda 环境 ican...
call conda activate ican
IF ERRORLEVEL 1 (
    echo [错误] 无法激活 conda 环境 ican，请先创建环境
    pause
    exit /b 1
)

echo [2/3] 检查依赖...
python -c "import fastapi, uvicorn, torch, ultralytics, cv2" 2>nul
IF ERRORLEVEL 1 (
    echo [警告] 部分依赖缺失，正在安装...
    pip install -r requirements.txt
)

echo [3/3] 启动藻影卫士 V1.0...
echo.
echo   后端服务: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:8000/app/
echo.
echo   按 Ctrl+C 停止服务
echo ============================================

start "" http://localhost:8000/app/
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
