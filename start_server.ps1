#Requires -Version 5.1
<#
start_server.ps1 - one-click launcher for the AI Task Management backend (M001/M002).

Why this script exists (2026-09-11 incident):
  Two `uvicorn --reload` instances were racing for port 8010 (one system-Python
  without AT_DATABASE_URL), causing bind failures / wrong DB. This launcher
  guarantees: project venv only, correct env, single instance, port conflict cleanup.

Usage:
  .\start_server.ps1                # start single uvicorn on :8010 with acceptance.db
  .\start_server.ps1 -Db app        # use default data/app.db instead
  .\start_server.ps1 -Seed          # rebuild acceptance.db from .e2e/seed.py first
  .\start_server.ps1 -Reload        # dev mode: uvicorn --reload (single instance)
  .\start_server.ps1 -Port 8011     # custom port
  .\start_server.ps1 -Stop          # stop running uvicorn instance(s) only

Double-click entry: start_server.bat
#>
param(
    [int]$Port = 8010,
    [ValidateSet('acceptance', 'app')]
    [string]$Db = 'acceptance',
    [switch]$Seed,
    [switch]$Reload,
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$Root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$VenvPy  = Join-Path $Backend '.venv\Scripts\python.exe'
$LogOut  = Join-Path $Root 'at_server.log'
$LogErr  = Join-Path $Root 'at_server.err.log'
$BaseUrl = "http://127.0.0.1:$Port/"

if (-not (Test-Path $VenvPy)) {
    Write-Error "venv python not found: $VenvPy"
    exit 1
}

# --- helper: all uvicorn app.main python processes (any port) ---
function Get-UvicornProcesses {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'app\.main' }
}

# --- stop mode: kill uvicorn instances, keep everything else ---
if ($Stop) {
    $procs = @(Get-UvicornProcesses)
    if ($procs.Count -gt 0) {
        foreach ($pr in $procs) {
            Write-Host "Stopping uvicorn PID $($pr.ProcessId)"
            Stop-Process -Id $pr.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    } else {
        Write-Host 'No uvicorn instance found.'
    }
    exit 0
}

# --- port conflict cleanup: only stop processes that are THIS project's uvicorn ---
$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($listener) {
    $occupierPid = $listener | Select-Object -First 1 -ExpandProperty OwningProcess
    $occupier    = Get-CimInstance Win32_Process -Filter "ProcessId = $occupierPid" -ErrorAction SilentlyContinue
    $isOurServer = $occupier -and $occupier.CommandLine -and
        ($occupier.CommandLine -match 'uvicorn' -and $occupier.CommandLine -match 'app\.main')
    if ($isOurServer) {
        Write-Host "Port $Port held by stale uvicorn PID $occupierPid - stopping it..."
        Stop-Process -Id $occupierPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Error "Port $Port is occupied by PID $occupierPid ($($occupier.Name)) which is not this project's uvicorn. Stop it manually or use -Port."
        exit 1
    }
}
# also reap orphaned uvicorn processes (e.g. reloaders that failed to bind)
$orphans = @(Get-UvicornProcesses)
if ($orphans.Count -gt 0) {
    foreach ($pr in $orphans) {
        Write-Host "Stopping stale uvicorn PID $($pr.ProcessId)"
        Stop-Process -Id $pr.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# --- optional: rebuild seed database ---
if ($Seed) {
    if ($Db -ne 'acceptance') { Write-Warning '-Seed rebuilds acceptance.db only; ignoring -Db app' }
    $seedPy = Join-Path $Root '.e2e\seed.py'
    if (-not (Test-Path $seedPy)) { Write-Error "seed script not found: $seedPy"; exit 1 }
    Write-Host 'Rebuilding seed database (acceptance.db)...'
    & $VenvPy $seedPy | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error 'Seed failed.'; exit 1 }
    Write-Host 'Seed OK.'
}

# --- env: same as acceptance runbook (see .e2e/seed.py + CONFIGURATION.md) ---
$env:AT_DATABASE_URL = "sqlite:///./data/$Db.db"
$env:AT_FRONTEND_DIR = Join-Path $Root 'frontend\dist'
if (-not (Test-Path $env:AT_FRONTEND_DIR)) {
    Write-Warning "frontend dist not found: $env:AT_FRONTEND_DIR (UI will 404; run frontend build first or use Vite dev server)"
}

# --- launch single instance (cwd = backend so sqlite relative path resolves) ---
$argList = @('-m', 'uvicorn', 'app.main:app', '--port', "$Port", '--log-level', 'info')
if ($Reload) { $argList += '--reload' }
$proc = Start-Process -FilePath $VenvPy -ArgumentList $argList -WorkingDirectory $Backend `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput $LogOut -RedirectStandardError $LogErr
Write-Host "Started uvicorn (PID $($proc.Id)) -> $BaseUrl"
Write-Host "logs: $LogOut / $LogErr"

# --- wait for bind + health check ---
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { $ready = $true; break }
}
if (-not $ready) {
    Write-Warning "Server did not bind within 15s - tail of $LogErr :"
    Get-Content $LogErr -Tail 20 -ErrorAction SilentlyContinue
    exit 1
}
try {
    $resp = Invoke-WebRequest "$BaseUrl" -UseBasicParsing -TimeoutSec 10
    Write-Host "Health OK: GET $BaseUrl -> $($resp.StatusCode) ($($resp.RawContentLength) bytes)"
} catch {
    Write-Warning "GET $BaseUrl failed: $($_.Exception.Message)"
}
Write-Host "Open in browser: $BaseUrl"
