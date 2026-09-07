@echo off
chcp 65001 >nul

cd /d "%~dp0code\algae_image_v2"

echo ============================================
echo   Algae Image V2 - Launching...
echo ============================================
echo.

REM ═══════════════════════════════════════════════════
REM Step 1: Verify model weights exist
REM ═══════════════════════════════════════════════════
IF NOT EXIST "weights\best_v8s.pt" (
    echo [WARN] YOLO weights not found: weights\best_v8s.pt
    echo        Detection will fail — place .pt files in weights\
)
IF NOT EXIST "weights\rdn_polarization.pth" (
    echo [WARN] RDN weights not found: weights\rdn_polarization.pth
    echo        Pipeline will run without RDN denoising
)

REM ═══════════════════════════════════════════════════
REM Step 1.5: Warn if MVS client is running (camera exclusive access)
REM ═══════════════════════════════════════════════════
tasklist /FI "IMAGENAME eq MVS.exe" 2>nul | find /I "MVS.exe" >nul
if %errorlevel% equ 0 (
    echo [WARN] MVS client is running! Camera will be occupied.
    echo        Close MVS client first, or camera will fail to connect.
    echo.
)

REM ═══════════════════════════════════════════════════
REM Step 2: Clean up port 8000 (targeted, not kill-all-python)
REM ═══════════════════════════════════════════════════
echo [INFO] Checking port 8000...
set PORT_CLEAR=1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":8000 "') do (
    taskkill /F /PID %%a >nul 2>&1
    echo [INFO] Killed PID %%a on port 8000, waiting for release...
    timeout /t 3 /nobreak >nul
    set PORT_CLEAR=0
)

REM Double-check port is truly free
:check_port
netstat -ano 2>nul | findstr /R ":8000.*LISTENING" >nul
if %errorlevel% equ 0 (
    echo [INFO] Port still in use, waiting...
    timeout /t 3 /nobreak >nul
    goto :check_port
)
echo [OK] Port 8000 is free

REM ═══════════════════════════════════════════════════
REM Step 3: Verify Python (conda ican)
REM ═══════════════════════════════════════════════════
set PYTHON_EXE=A:\Anaconda_envs\envs\ican\python.exe
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Conda environment not found: A:\Anaconda_envs\envs\ican
    echo         Install conda ican or edit this script's PYTHON_EXE path.
    pause
    exit /b 1
)
echo [INFO] Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if %errorlevel% neq 0 (
    echo [ERROR] Python failed to launch
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════════
REM Step 4: Start uvicorn in a titled window
REM ═══════════════════════════════════════════════════
echo [INFO] Starting backend server...
start "AlgaeV2-Server" "%PYTHON_EXE%" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

REM ═══════════════════════════════════════════════════
REM Step 5: Wait for backend to be ready (poll, max 60s)
REM ═══════════════════════════════════════════════════
echo [INFO] Waiting for backend to start (may take 20-40s while loading models)...
set RETRIES=0
:wait
timeout /t 3 /nobreak >nul
powershell -Command "try {$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -UseBasicParsing -TimeoutSec 2; exit 0} catch {exit 1}" >nul 2>&1
if %errorlevel% equ 0 goto ready
set /a RETRIES+=1
if %RETRIES% lss 20 goto wait

echo [FAIL] Backend did not start within 60 seconds!
echo        Check the "AlgaeV2-Server" window for errors.
pause
exit /b 1

REM ═══════════════════════════════════════════════════
REM Step 6: Open browser
REM ═══════════════════════════════════════════════════
:ready
echo [OK] Backend is ready!
echo [INFO] Opening browser...
start "" "http://127.0.0.1:8000/app/"

echo.
echo ============================================
echo   All set!
echo.
echo   Frontend : http://127.0.0.1:8000/app/
echo   API docs : http://127.0.0.1:8000/docs
echo ============================================
echo.
echo To stop: double-click stop.bat
echo    Or close the "AlgaeV2-Server" window
echo.
pause
