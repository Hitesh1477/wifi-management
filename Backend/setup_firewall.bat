
@echo off
REM Firewall Blocking Setup - Batch Launcher
REM This script launches the PowerShell setup script as Administrator

echo ============================================
echo Firewall-Based Web Filtering Setup
echo ============================================
echo.
echo This will:
echo 1. Create firewall rules for blocked sites
echo 2. Set up automatic IP refresh (every 6 hours)
echo.
echo Press any key to continue...
pause > nul

REM Run PowerShell script as Administrator
powershell -ExecutionPolicy Bypass -File "%~dp0setup_firewall_blocking.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup completed successfully!
) else (
    echo.
    echo Setup failed. Please check the error messages above.
)

pause
