@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Algae Image V2 - FMPD

echo ============================================
echo   Algae Image V2
echo   FMPD 明场藻类检测 - HSV偏振 + YOLO
echo ============================================
echo.

REM ═══════════════════════════════════════════════════════════
REM Step 1: Verify model weights
REM ═══════════════════════════════════════════════════════════
IF NOT EXIST "weights\best_v8l.pt" (
    echo [错误] 未找到 YOLO 权重: weights\best_v8l.pt
    echo        请将模型权重文件放入 weights\ 目录
    echo        需要的文件: best_v8l.pt, best_v8s.pt, best.pt, rdn_polarization.pth
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════════════════
REM Step 2: Find Python — support conda, venv, system Python
REM ═══════════════════════════════════════════════════════════
set PYTHON_EXE=

REM Priority 1: CONDA_PREFIX (if conda is activated in this shell)
if defined CONDA_PREFIX (
    set PYTHON_EXE=%CONDA_PREFIX%\python.exe
    echo [INFO] Using conda environment from CONDA_PREFIX: %CONDA_PREFIX%
    goto :check_python
)

REM Priority 2: conda activate + where python (handles conda in PATH)
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        set PYTHON_EXE=%%i
        goto :check_python
    )
)

REM Priority 3: Search common conda install locations
for %%d in (
    "%USERPROFILE%\miniconda3"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\AppData\Local\miniconda3"
    "C:\ProgramData\miniconda3"
    "C:\ProgramData\anaconda3"
    "A:\Anaconda_envs"
) do (
    if exist "%%d\envs\ican\python.exe" (
        set PYTHON_EXE=%%d\envs\ican\python.exe
        echo [INFO] Found conda ican at: %%d\envs\ican
        goto :check_python
    )
)

REM Priority 4: system Python (last resort)
for %%d in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist "%%d" (
        set PYTHON_EXE=%%d
        echo [INFO] Using system Python: %%d
        goto :check_python
    )
)

echo [错误] 未找到 Python! 请先安装 Miniconda 或设置 PATH
echo.
echo 安装方法:
echo   1. 下载 Miniconda: https://docs.conda.io/en/latest/miniconda.html
echo   2. 安装后运行: setup.bat
echo.
pause
exit /b 1

:check_python
echo [INFO] Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if %errorlevel% neq 0 (
    echo [错误] Python 无法运行: %PYTHON_EXE%
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════════════════
REM Step 3: Check dependencies (fast path — skip if OK)
REM ═══════════════════════════════════════════════════════════
echo [检查] 依赖...
"%PYTHON_EXE%" -c "import fastapi, uvicorn, torch, ultralytics, cv2" 2>nul
if %errorlevel% neq 0 (
    echo [安装] 部分依赖缺失，正在自动安装...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请检查网络连接后重试
        echo        或手动运行: "%PYTHON_EXE%" -m pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
)

REM ═══════════════════════════════════════════════════════════
REM Step 4: Start server
REM ═══════════════════════════════════════════════════════════
echo.
echo ============================================
echo   启动 Algae Image V2...
echo.
echo   后端服务:  http://localhost:8000
echo   API 文档:  http://localhost:8000/docs
echo   前端界面:  http://localhost:8000/app/
echo   管线:      HSV偏振 -(skip RDN)- I_enh v2 - YOLOv8s/v8l
echo.
echo   按 Ctrl+C 停止服务
echo ============================================
echo.

start "" http://localhost:8000/app/
"%PYTHON_EXE%" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
