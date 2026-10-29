# Run all SupplyLens tests
# Usage: powershell -File scripts/run_tests.ps1

Write-Host "=== SupplyLens Test Suite ===" -ForegroundColor Cyan

# Generate synthetic data first
python data/synthetic/generate_dataset.py

# Run pytest from backend directory
Set-Location backend
python -m pytest tests/ -v --tb=short 2>&1 | Tee-Object -FilePath ..\docs\test_results.txt
$exitCode = $LASTEXITCODE
Set-Location ..

Write-Host ""
Write-Host "Test results saved to docs/test_results.txt"
Write-Host "Exit code: $exitCode"
exit $exitCode
