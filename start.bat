@echo off
cd /d "%~dp0code\algae_image_v2"

echo ============================================
echo   Algae Image V2 - Launching...
echo ============================================

REM Kill any leftover Python from last run
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Start uvicorn in its own titled window
start "AlgaeV2-Server" "A:\Anaconda_envs\envs\ican\python.exe" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

REM Wait for backend to be ready (poll with PowerShell, max 45s)
echo Waiting for backend...
set RETRIES=0
:wait
timeout /t 3 /nobreak >nul
powershell -Command "try {$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -UseBasicParsing -TimeoutSec 2; exit 0} catch {exit 1}" >nul 2>&1
if %errorlevel% equ 0 goto ready
set /a RETRIES+=1
if %RETRIES% lss 15 goto wait

echo [FAIL] Backend did not start within 45 seconds!
echo Check the AlgaeV2-Server window for errors.
pause
exit /b 1

:ready
echo Backend is ready!

REM Open Firefox
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" "http://127.0.0.1:8000/app/"

echo ============================================
echo   All set!
echo   Backend : http://127.0.0.1:8000
echo   Frontend: http://127.0.0.1:8000/app/
echo   API docs: http://127.0.0.1:8000/docs
echo ============================================
echo To stop: double-click stop.bat, or close the AlgaeV2-Server window
pause
