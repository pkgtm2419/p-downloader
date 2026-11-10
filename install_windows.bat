@echo off
setlocal
title P-Downloader Setup
echo ============================================================
echo   P-Downloader Windows 11 / 10 Installer
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ from python.org or via Windows Terminal:
    echo     winget install Python.Python.3.12
    echo.
    pause
    exit /b 1
)

python "%~dp0scripts\install_windows.py" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installation encountered an issue.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================
echo   Installation completed successfully!
echo   Launch P-Downloader from your Desktop or Start Menu.
echo ============================================================
echo.
pause
