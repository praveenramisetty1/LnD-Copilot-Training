# start_server.ps1 — LLM Gateway POC Startup Script
# Double-click or run: powershell -ExecutionPolicy Bypass -File start_server.ps1

$projectRoot = $PSScriptRoot

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  LLM Gateway POC — Starting Server" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Set PYTHONPATH to project root
$env:PYTHONPATH = $projectRoot
Set-Location $projectRoot

# Check Python
$pyVersion = & py --version 2>&1
Write-Host "  Python : $pyVersion" -ForegroundColor Green
Write-Host "  Root   : $projectRoot" -ForegroundColor Green
Write-Host ""

# Seed data if analytics file is missing or empty
$analyticsFile = Join-Path $projectRoot "data\analytics.json"
if (-not (Test-Path $analyticsFile)) {
    Write-Host "  [Seeding demo data...]" -ForegroundColor Yellow
    & py demo/seed_demo_data.py
    Write-Host ""
}

Write-Host "  Starting gateway on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "  Swagger UI -> http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

# Start uvicorn
& py -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
