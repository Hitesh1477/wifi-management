# Firewall-Based Web Filtering Setup Script
# Run this as Administrator to enable automatic website blocking

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Firewall-Based Web Filtering Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Step 1: Creating initial firewall rules for existing blocked sites..." -ForegroundColor Yellow
Write-Host ""

# Navigate to Backend directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Run the IP refresh script to create initial rules
Write-Host "Running IP refresh service to create firewall rules..." -ForegroundColor Cyan
python refresh_blocked_ips.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Failed to create initial firewall rules" -ForegroundColor Yellow
    Write-Host "You can try running refresh_blocked_ips.py manually later" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2: Setting up Task Scheduler for automatic IP refresh..." -ForegroundColor Yellow
Write-Host ""

# Define task parameters
$taskName = "VDT_Firewall_IP_Refresh"
$pythonPath = (Get-Command python).Path
$scriptPath = Join-Path $scriptDir "refresh_blocked_ips.py"
$taskDescription = "Refreshes firewall rules every 6 hours for VDT Web Filtering"

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create scheduled task action
$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory $scriptDir

# Create trigger (every 6 hours)
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 6)

# Create principal (run as SYSTEM with highest privileges)
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings | Out-Null
    
    Write-Host "✅ Task Scheduler job created successfully!" -ForegroundColor Green
    Write-Host "   Task Name: $taskName" -ForegroundColor Cyan
    Write-Host "   Runs every: 6 hours" -ForegroundColor Cyan
    Write-Host "   Next run: $((Get-Date).AddHours(6).ToString('yyyy-MM-dd HH:mm'))" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ Failed to create Task Scheduler job: $_" -ForegroundColor Red
    Write-Host "You may need to create it manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Firewall-based blocking is now active!" -ForegroundColor Green
Write-Host "✅ IP refresh service will run every 6 hours automatically" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Add blocked sites in the admin panel" -ForegroundColor White
Write-Host "2. Firewall rules will be created automatically" -ForegroundColor White
Write-Host "3. Students connected to hotspot will be blocked (no client config needed!)" -ForegroundColor White
Write-Host ""
Write-Host "To manually trigger IP refresh, run:" -ForegroundColor Yellow
Write-Host "  python refresh_blocked_ips.py" -ForegroundColor Cyan
Write-Host ""
pause
