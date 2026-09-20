param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$backendUrl = "http://127.0.0.1:8000/health"
$frontendUrl = "http://127.0.0.1:5173"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "       B3 Investment Copilot - Dashboard" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

function Test-Endpoint([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

$backendProcess = $null
$frontendProcess = $null

try {
    if (-not (Test-Endpoint $backendUrl)) {
        Write-Host "Starting B3 Orchestrator..." -ForegroundColor Yellow
        $backendInfo = New-Object System.Diagnostics.ProcessStartInfo
        $backendInfo.FileName = "python"
        $backendInfo.Arguments = "-m uvicorn b3_agent.server:app --host 127.0.0.1 --port 8000"
        $backendInfo.WorkingDirectory = $root
        $backendInfo.UseShellExecute = $false
        $backendInfo.CreateNoWindow = $false
        $backendProcess = [System.Diagnostics.Process]::Start($backendInfo)
    } else {
        Write-Host "Orchestrator already running." -ForegroundColor Green
    }

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Endpoint $backendUrl) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        throw "B3 Orchestrator did not become ready on port 8000."
    }

    if (-not (Test-Endpoint $frontendUrl)) {
        Write-Host "Starting React Dashboard..." -ForegroundColor Yellow
        $frontendInfo = New-Object System.Diagnostics.ProcessStartInfo
        $nodeCommand = Get-Command node.exe -CommandType Application -ErrorAction Stop
        $npmCmd = Join-Path (Split-Path -Parent $nodeCommand.Source) "npm.cmd"
        if (-not (Test-Path $npmCmd)) {
            throw "Could not locate npm.cmd next to node.exe at $npmCmd."
        }
        $frontendInfo.FileName = $npmCmd
        $frontendInfo.Arguments = "run dev -- --host 127.0.0.1"
        $frontendInfo.WorkingDirectory = $frontend
        $frontendInfo.UseShellExecute = $false
        $frontendInfo.CreateNoWindow = $false
        $frontendProcess = [System.Diagnostics.Process]::Start($frontendInfo)
    } else {
        Write-Host "React Dashboard already running." -ForegroundColor Green
    }

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Endpoint $frontendUrl) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        throw "React Dashboard did not become ready on port 5173."
    }

    if (-not $NoBrowser) {
        Start-Process $frontendUrl
    }

    Write-Host ""
    Write-Host "Dashboard:   $frontendUrl" -ForegroundColor Green
    Write-Host "Orchestrator: http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host ""
    Write-Host "The Dashboard communicates with the backend through /orchestrate." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop processes started by this launcher." -ForegroundColor DarkGray
    Write-Host ""

    while ($true) {
        if ($backendProcess -and $backendProcess.HasExited) {
            throw "B3 Orchestrator stopped unexpectedly."
        }
        if ($frontendProcess -and $frontendProcess.HasExited) {
            throw "React Dashboard stopped unexpectedly."
        }
        Start-Sleep -Seconds 2
    }
}
finally {
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Write-Host "Stopping React Dashboard..." -ForegroundColor Yellow
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Write-Host "Stopping B3 Orchestrator..." -ForegroundColor Yellow
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
