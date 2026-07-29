@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Algae Image V2 - 环境安装

echo ============================================
echo   藻类检测 V2 — 环境一键安装脚本
echo ============================================
echo.

REM ═══════════════════════════════════════════════════════════
REM Step 1: 检查 Python / conda
REM ═══════════════════════════════════════════════════════════
echo [1/5] 检查 Python 环境...

set CONDA_CMD=
set PYTHON_EXE=
set USE_CONDA=0

REM Check if conda is available
where conda >nul 2>&1
if %errorlevel% equ 0 (
    set USE_CONDA=1
    echo [OK] 找到 conda
    goto :check_conda
)

REM Search common conda install paths
for %%d in (
    "%USERPROFILE%\miniconda3"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\AppData\Local\miniconda3"
    "C:\ProgramData\miniconda3"
    "C:\ProgramData\anaconda3"
) do (
    if exist "%%d\Scripts\conda.exe" (
        set "PATH=%%d\Scripts;%%d;%PATH%"
        set USE_CONDA=1
        echo [OK] 找到 conda: %%d
        goto :check_conda
    )
)

echo [警告] 未找到 conda，将使用系统 Python（如果可用）
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        set PYTHON_EXE=%%i
        goto :pip_install
    )
)
echo [错误] 未找到 Python! 请先安装 Miniconda:
echo        https://docs.conda.io/en/latest/miniconda.html
pause
exit /b 1

REM ═══════════════════════════════════════════════════════════
REM Step 2: 创建 / 更新 conda 环境 (ic an)
REM ═══════════════════════════════════════════════════════════
:check_conda
echo.
echo [2/5] 创建 Conda 环境 'ican' (Python 3.11 + PyTorch CUDA)...

REM Try conda env create; if env already exists, update it
call conda env list 2>nul | findstr /c:"ican" >nul
if %errorlevel% equ 0 (
    echo [INFO] 环境 'ican' 已存在，正在更新...
    call conda env update -f environment.yml --prune
    if %errorlevel% neq 0 (
        echo [错误] 环境更新失败
        pause
        exit /b 1
    )
) else (
    echo [INFO] 创建新环境 'ican'（请耐心等待，约需下载 2-3GB）...
    call conda env create -f environment.yml
    if %errorlevel% neq 0 (
        echo [错误] 环境创建失败
        echo        请检查网络连接，确认可否访问 pytorch / conda-forge 镜像
        pause
        exit /b 1
    )
)

REM Find the ican python.exe
for %%d in (
    "%USERPROFILE%\miniconda3\envs\ican"
    "%USERPROFILE%\anaconda3\envs\ican"
    "%USERPROFILE%\AppData\Local\miniconda3\envs\ican"
    "C:\ProgramData\miniconda3\envs\ican"
    "C:\ProgramData\anaconda3\envs\ican"
) do (
    if exist "%%d\python.exe" (
        set PYTHON_EXE=%%d\python.exe
        goto :verify_env
    )
)

REM Fallback: use conda run
for /f "delims=" %%i in ('conda run -n ican where python 2^>nul') do (
    set PYTHON_EXE=%%i
    goto :verify_env
)

echo [错误] 无法找到 conda 环境 ican 中的 Python
pause
exit /b 1

:verify_env
echo [OK] Conda 环境: %PYTHON_EXE%

REM ═══════════════════════════════════════════════════════════
REM Step 3: 验证依赖
REM ═══════════════════════════════════════════════════════════
:pip_install
echo.
echo [3/5] 验证 Python 依赖...

"%PYTHON_EXE%" -c "import torch; print(f'[OK] PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>nul
if %errorlevel% neq 0 (
    echo [安装] 正在安装 Python 依赖...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [OK] 核心依赖验证完成

REM ═══════════════════════════════════════════════════════════
REM Step 4: 检查模型权重
REM ═══════════════════════════════════════════════════════════
echo.
echo [4/5] 检查模型权重文件...

set MISSING_WEIGHTS=0
for %%f in ("weights\best_v8l.pt" "weights\best_v8s.pt" "weights\rdn_polarization.pth") do (
    if not exist %%f (
        echo [缺少] %%~nxf
        set MISSING_WEIGHTS=1
    )
)
if %MISSING_WEIGHTS% equ 1 (
    echo.
    echo [警告] 部分模型权重文件缺失!
    echo        这些文件约 129MB，不在代码仓库中。
    echo        请从以下来源获取并放入 weights\ 目录：
    echo          - best_v8l.pt    (83.6 MB) — YOLOv8l 高精度模型
    echo          - best_v8s.pt    (21.5 MB) — YOLOv8s 轻量模型
    echo          - best.pt        (21.5 MB) — YOLOv8s 95类兼容模型
    echo          - rdn_polarization.pth (2.4 MB) — RDN 去噪网络
    echo.
) else (
    echo [OK] 所有权重文件已就绪
)

REM ═══════════════════════════════════════════════════════════
REM Step 5: 创建运行时目录
REM ═══════════════════════════════════════════════════════════
echo.
echo [5/5] 创建运行时目录...

if not exist "backend\data\uploads" mkdir "backend\data\uploads"
if not exist "backend\data\results" mkdir "backend\data\results"
if not exist "backend\data\results\live" mkdir "backend\data\results\live"
echo [OK] 目录已创建

echo.
echo ============================================
echo   安装完成!
echo.
echo   启动软件: 双击 run.bat
echo   API 文档:  http://localhost:8000/docs
echo   前端界面:  http://localhost:8000/app/
echo ============================================
echo.
pause
