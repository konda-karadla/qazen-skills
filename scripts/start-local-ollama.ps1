# Check Ollama + print the active LLM profile hints for local QAZen e2e.
# Does not start services (run gateway/orchestrator/review in separate terminals).
#
# Usage (from repo root):
#   .\scripts\start-local-ollama.ps1
#   .\scripts\start-local-ollama.ps1 -RunE2e

param(
    [switch]$RunE2e
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "QAZen local LLM helper (Ollama profile)" -ForegroundColor Cyan

$ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (Test-Path $ollamaExe) {
    $env:Path = "$(Split-Path $ollamaExe);$env:Path"
    Write-Host "Ollama CLI: $ollamaExe"
} else {
    Write-Host "Ollama CLI not found at $ollamaExe — install from https://ollama.com/download" -ForegroundColor Yellow
}

# Load LLM_PROFILE from .env if present (display only; gateway loads .env itself)
$profile = "ollama"
$envFile = Join-Path $RepoRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*LLM_PROFILE\s*=\s*(.+)\s*$') {
            $profile = $Matches[1].Trim()
        }
    }
}
Write-Host "LLM_PROFILE (from .env): $profile"

try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    $names = @($tags.models | ForEach-Object { $_.name })
    Write-Host "Ollama: up — models: $($names -join ', ')"
    if ($names -notcontains "nemotron-3-super:cloud" -and $names -notcontains "qwen2.5:7b") {
        Write-Host "WARN: no QAZen model listed. Run: ollama pull nemotron-3-super:cloud" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Ollama: DOWN — start the Ollama app, then: ollama pull nemotron-3-super:cloud" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Start gateway WITHOUT forcing mock:"
Write-Host '  $env:LLM_PROVIDER = "openai"   # or leave unset; .env LLM_PROFILE=ollama applies'
Write-Host "  cd llm-gateway; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Write-Host ""
Write-Host "Also start orchestrator :8002 and review-api :8001 (see README / PROGRESS)."
Write-Host "Claude Code (not used by the QAZen gateway):"
Write-Host '  ollama launch claude --model nemotron-3-super:cloud'
Write-Host "Switch to Gemini later: set LLM_PROFILE=gemini in .env, comment Ollama OPENAI_* lines, restart gateway."
Write-Host ""

if ($RunE2e) {
    Write-Host "Running e2e_ollama.py (S6=mock, through H5) — may take a long time on CPU..." -ForegroundColor Yellow
    $env:S6_EXECUTION_MODE = "mock"
    $env:CI_GATE_MODE = "mock"
    $env:DATABASE_URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
    $env:LLM_GATEWAY_URL = "http://localhost:8000"
    $env:LLM_GATEWAY_TIMEOUT_SECONDS = "600"
    & "$RepoRoot\.venv\Scripts\python.exe" "$RepoRoot\orchestrator\scripts\e2e_ollama.py"
}
