# SupplyLens — Exasol Personal Setup Script (Windows PowerShell)
# =============================================================
# This script installs Exasol Personal Local using the official
# Exasol starter kit and verifies the connection.
#
# Prerequisites:
#   - Windows 10/11 with 8 GB+ RAM and 20 GB+ free disk
#   - PowerShell 5.1 or later (as Administrator recommended)
#   - Python 3.11+ in PATH
#
# Run:
#   powershell -ExecutionPolicy Bypass -File scripts/setup_exasol.ps1

Write-Host "=== SupplyLens: Exasol Personal Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install Exasol Personal via official starter kit
Write-Host "Step 1: Installing Exasol Personal Local starter kit..." -ForegroundColor Yellow
Write-Host "This installs: Exasol Personal, pyexasol, exapump, MCP server"
Write-Host ""
Write-Host "Running official installer (requires network access):"
Write-Host "  irm https://www.exasol.com/install/starter-kit.ps1 | iex"
Write-Host ""

$answer = Read-Host "Run installer now? [y/N]"
if ($answer -eq 'y' -or $answer -eq 'Y') {
    irm https://www.exasol.com/install/starter-kit.ps1 | iex
} else {
    Write-Host "Skipping installer. If already installed, continue." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 2: Verifying Exasol connectivity..." -ForegroundColor Yellow

# Check if Exasol is listening on port 8563
$portOpen = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("localhost", 8563)
    $portOpen = $true
    $conn.Close()
} catch {}

if ($portOpen) {
    Write-Host "  [OK] Exasol Personal is listening on localhost:8563" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Port 8563 not reachable. Exasol may still be starting." -ForegroundColor Yellow
    Write-Host "  Wait 30–60 seconds and try again, or check Podman Desktop." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Setting up Python environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "  .venv already exists; activating" -ForegroundColor Gray
} else {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt --quiet

Write-Host ""
Write-Host "Step 4: Copying .env.example to .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created .env — edit EXASOL_PASSWORD if needed" -ForegroundColor Green
} else {
    Write-Host "  .env already exists" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 5: Generating synthetic dataset..." -ForegroundColor Yellow
python data/synthetic/generate_dataset.py

Write-Host ""
Write-Host "Step 6: Initialising Exasol schema and loading demo data..." -ForegroundColor Yellow
cd backend
python -m app.db.seed_loader
cd ..

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Start the backend:  cd backend && uvicorn app.main:app --reload"
Write-Host "Start the frontend: cd frontend && npm install && npm run dev"
Write-Host "API docs:           http://localhost:8000/docs"
Write-Host "Frontend:           http://localhost:5173"
