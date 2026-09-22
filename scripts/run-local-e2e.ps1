# QAZen - one-shot local LLM run + e2e (Ollama).
#
# From repo root (PowerShell):
#   .\scripts\run-local-e2e.ps1              # start everything + full H1-H5 e2e
#   .\scripts\run-local-e2e.ps1 -SmokeOnly   # start everything + quick S1 check
#   .\scripts\run-local-e2e.ps1 -SkipE2e     # start services only
#   .\scripts\run-local-e2e.ps1 -Stop        # stop gateway/orch/review started by this script
#
# Requires: Docker, .venv, repo-root .env with LLM_PROFILE=ollama, Ollama + qwen2.5:7b
# Full e2e often takes 30-90+ minutes on CPU.

param(
    [switch]$SmokeOnly,
    [switch]$SkipE2e,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "reports\local-run-logs"
$PidFile = Join-Path $LogDir "service-pids.txt"
$DbUrl = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"

function Write-Step([string]$msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "OK  $msg" -ForegroundColor Green }
function Write-WarnMsg([string]$msg) { Write-Host "WARN $msg" -ForegroundColor Yellow }

function Get-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $candidate) { return $candidate }
    return $null
}

function Stop-TrackedServices {
    if (-not (Test-Path $PidFile)) {
        Write-WarnMsg "No pid file at $PidFile"
        return
    }
    Get-Content $PidFile | ForEach-Object {
        $procId = $_.Trim()
        if ($procId -match '^\d+$') {
            try {
                Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop
                Write-Ok "Stopped PID $procId"
            } catch {
                Write-WarnMsg "PID $procId already gone"
            }
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-RestMethod -Uri $Url -TimeoutSec 3
            return $r
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Timed out waiting for $Url"
}

function Ensure-PortFree([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($conn) {
        $owner = $conn.OwningProcess
        Write-WarnMsg "Port $Port in use by PID $owner - stopping it"
        Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

function Start-ServiceProcess([string]$Name, [string]$WorkDir, [string[]]$ArgumentList, [hashtable]$ExtraEnv) {
    foreach ($k in $ExtraEnv.Keys) {
        Set-Item -Path "Env:$k" -Value $ExtraEnv[$k]
    }
    if ($Name -eq "gateway") {
        Remove-Item Env:LLM_PROVIDER -ErrorAction SilentlyContinue
    }
    $logOut = Join-Path $LogDir "$Name.out.log"
    $logErr = Join-Path $LogDir "$Name.err.log"
    $p = Start-Process -FilePath $Python `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkDir `
        -RedirectStandardOutput $logOut `
        -RedirectStandardError $logErr `
        -PassThru `
        -WindowStyle Hidden | Select-Object -First 1
    Add-Content -Path $PidFile -Value $p.Id
    Write-Ok "Started $Name PID $($p.Id) logs=$logOut"
    return $p
}

if ($Stop) {
    Write-Step "Stopping services tracked by this script"
    Stop-TrackedServices
    exit 0
}

if (-not (Test-Path $Python)) {
    Write-Host "Missing .venv at $Python - create it and install requirements see README." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
if (Test-Path $PidFile) {
    Write-Step "Stopping previous run-local-e2e services"
    Stop-TrackedServices
}

Write-Step "1/5 Docker infra Postgres + MinIO"
Push-Location (Join-Path $RepoRoot "infra")
try {
    docker compose up -d
} finally {
    Pop-Location
}
Write-Ok "docker compose up -d"

Write-Step "2/5 Ollama"
$ollama = Get-OllamaExe
if (-not $ollama) {
    Write-Host "Ollama not found. Install via winget: winget install Ollama.Ollama" -ForegroundColor Red
    exit 1
}
Write-Ok "ollama exe: $ollama"
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
} catch {
    Write-WarnMsg "Ollama API down - starting serve"
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}
$tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
$names = @($tags.models | ForEach-Object { $_.name })
if ($names -notcontains "qwen2.5:7b") {
    Write-WarnMsg "Pulling qwen2.5:7b - one-time large download"
    & $ollama pull "qwen2.5:7b"
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
    $names = @($tags.models | ForEach-Object { $_.name })
}
Write-Ok ("Ollama ready models=" + ($names -join ", "))

Write-Step "3/5 Start gateway :8000 orchestrator :8002 review-api :8001"
Ensure-PortFree 8000
Ensure-PortFree 8001
Ensure-PortFree 8002

$env:LLM_PROFILE = "ollama"
$env:LLM_GATEWAY_TIMEOUT_SECONDS = "600"
$env:DATABASE_URL = $DbUrl
$env:LLM_GATEWAY_URL = "http://127.0.0.1:8000"
$env:ORCHESTRATOR_URL = "http://127.0.0.1:8002"
$env:S6_EXECUTION_MODE = "mock"
$env:CI_GATE_MODE = "mock"

Start-ServiceProcess "gateway" (Join-Path $RepoRoot "llm-gateway") `
    @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    @{ LLM_PROFILE = "ollama" }

Start-ServiceProcess "orchestrator" (Join-Path $RepoRoot "orchestrator") `
    @("-m", "uvicorn", "app.api:app", "--host", "127.0.0.1", "--port", "8002") `
    @{
        DATABASE_URL = $DbUrl
        LLM_GATEWAY_URL = "http://127.0.0.1:8000"
        LLM_GATEWAY_TIMEOUT_SECONDS = "600"
        S6_EXECUTION_MODE = "mock"
        CI_GATE_MODE = "mock"
    }

Start-ServiceProcess "review" (Join-Path $RepoRoot "review-api") `
    @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001") `
    @{
        DATABASE_URL = $DbUrl
        ORCHESTRATOR_URL = "http://127.0.0.1:8002"
    }

Write-Step "4/5 Health checks"
$gw = Wait-HttpOk "http://127.0.0.1:8000/health" 90
Wait-HttpOk "http://127.0.0.1:8002/health" 60 | Out-Null
Wait-HttpOk "http://127.0.0.1:8001/health" 60 | Out-Null
Write-Ok ("gateway provider=" + $gw.provider + " profile=" + $gw.llm_profile + " model=" + $gw.openai_model)
if ($gw.provider -eq "mock") {
    Write-Host "Gateway is on mock - refuse live local LLM run. Unset LLM_PROVIDER and restart." -ForegroundColor Red
    exit 1
}
if ($gw.openai_base_url -notmatch "11434") {
    Write-WarnMsg ("Gateway base_url is " + $gw.openai_base_url + " expected Ollama :11434")
}

Write-Host "Review UI: http://127.0.0.1:8001/ui/" -ForegroundColor Cyan

if ($SkipE2e) {
    Write-Ok "Services up -SkipE2e. Stop later with: .\scripts\run-local-e2e.ps1 -Stop"
    exit 0
}

if ($SmokeOnly) {
    Write-Step "5/5 Smoke: invoke S1 via gateway local LLM"
    $body = @{ input = @{ raw = "Users must log in with valid credentials." } } | ConvertTo-Json -Compress
    $smoke = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/skills/S1/invoke" `
        -ContentType "application/json" -Body $body -TimeoutSec 600
    if ($smoke.escalated) {
        Write-Host ("S1 escalated: " + $smoke.escalation_reason) -ForegroundColor Red
        exit 1
    }
    Write-Ok ("S1 smoke OK attempts=" + $smoke.attempts)
    Write-Ok "RUN_LOCAL_SMOKE_OK"
    exit 0
}

Write-Step "5/5 Full e2e H1-H5 S6=mock - may take 30-90+ min on CPU"
$env:PYTHONPATH = Join-Path $RepoRoot "orchestrator"
$env:DATABASE_URL = $DbUrl
$env:LLM_GATEWAY_URL = "http://127.0.0.1:8000"
$env:S6_EXECUTION_MODE = "mock"
$env:CI_GATE_MODE = "mock"
$env:LLM_GATEWAY_TIMEOUT_SECONDS = "600"
& $Python (Join-Path $RepoRoot "orchestrator\scripts\e2e_ollama.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host ("e2e failed exit=" + $LASTEXITCODE + " logs under " + $LogDir) -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Ok "RUN_LOCAL_E2E_OK"
Write-Host "Services still running. Stop with: .\scripts\run-local-e2e.ps1 -Stop"
