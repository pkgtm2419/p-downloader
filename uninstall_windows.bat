@echo off
setlocal
title P-Downloader Uninstaller
echo ============================================================
echo   P-Downloader Windows Uninstaller
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    pause
    exit /b 1
)

python "%~dp0scripts\install_windows.py" --uninstall %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Uninstallation encountered an issue.
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
