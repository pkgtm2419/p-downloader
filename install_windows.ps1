<#
.SYNOPSIS
    Automated Windows 11 / 10 Installer for P-Downloader.
.DESCRIPTION
    Configures shortcuts, Windows Registry, browser native messaging, and App registration.
    Fully compatible with Windows 11 Smart App Control (SAC).
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  P-Downloader Windows 11 / 10 Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$python = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
if (-not $python) {
    Write-Warning "Python was not found in PATH."
    Write-Host "Please install Python 3.10+ via: winget install Python.Python.3.12" -ForegroundColor Yellow
    exit 1
}

& python "$PSScriptRoot\scripts\install_windows.py" @args
