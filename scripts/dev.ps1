# Launch BrandGuard AI (backend + frontend) in two PowerShell windows.
# Usage: .\scripts\dev.ps1

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $backend ".venv\Scripts\python.exe"))) {
    Write-Host "Backend virtualenv missing. Creating it..." -ForegroundColor Yellow
    Push-Location $backend
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Frontend dependencies missing. Installing..." -ForegroundColor Yellow
    Push-Location $frontend
    npm.cmd install --no-audit --no-fund
    Pop-Location
}

Write-Host "Starting FastAPI on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
)

Write-Host "Starting Next.js on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$frontend'; npm.cmd run dev"
)

Write-Host ""
Write-Host "BrandGuard AI is starting. Open http://localhost:3000" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
