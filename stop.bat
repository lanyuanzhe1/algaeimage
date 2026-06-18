@echo off
chcp 65001 >nul
echo ============================================
echo   Algae Image V2 — 关闭中...
echo ============================================

REM 杀掉所有 Python 进程
taskkill /F /IM python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python 进程已终止
) else (
    echo [--] 无 Python 进程运行
)

REM 杀掉所有 Firefox 进程
taskkill /F /IM firefox.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Firefox 进程已终止
) else (
    echo [--] 无 Firefox 进程运行
)

echo ============================================
echo   已全部关闭
echo ============================================
pause
