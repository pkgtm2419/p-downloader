@echo off
setlocal
echo ============================================================
echo   Building P-Downloader Standalone Windows Executable
echo ============================================================

cd /d "%~dp0"

echo [1/2] Running PyInstaller...
python -m PyInstaller --clean -y pdownloader.spec
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Generating Windows Setup Installer (Inno Setup)...
set "ISCC_EXE="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"

if defined ISCC_EXE (
    if "%~1"=="" (
        "%ISCC_EXE%" installer.iss
    ) else (
        "%ISCC_EXE%" /DMyAppVersion="%~1" installer.iss
    )
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Inno Setup compilation failed!
        exit /b %ERRORLEVEL%
    )
    echo.
    echo ============================================================
    echo   SUCCESS! Standalone Installer created at:
    echo   %~dp0Output\P-Downloader-Setup.exe
    echo ============================================================
) else (
    echo [WARN] Inno Setup compiler (ISCC.exe) not found.
    echo Standalone portable folder is available at: %~dp0dist\P-Downloader
)

pause
