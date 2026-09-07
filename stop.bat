@echo off
chcp 65001 >nul

echo ============================================
echo   Algae Image V2 - Shutting down...
echo ============================================

REM ── Find PID on port 8000, kill only that process ──
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":8000.*LISTENING"') do (
    echo [INFO] Found server on port 8000 (PID %%a)
    taskkill /F /PID %%a >nul 2>&1
    echo [OK] Server stopped
    set FOUND=1
    goto :done_kill
)

:done_kill
if %FOUND% equ 0 (
    echo [--] No server on port 8000 — already stopped
)
echo.
echo ============================================
echo   Done
echo ============================================
echo.
echo To restart: double-click start.bat
echo.
pause
