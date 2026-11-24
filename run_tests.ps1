# Local mirror of the CI workflow.
# Usage: pwsh -File run_tests.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    python tests/validate_skill.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        ruff check .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    else {
        Write-Host "ruff not installed; skipping lint (CI runs it)"
    }

    python -m compileall -q skills/gsc-enhancements install.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python -m unittest discover -s tests -p "test_*.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python skills/gsc-enhancements/scripts/analyze_export.py analyze --input tests/fixtures/queries.csv --min-impressions 100 --json | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python install.py --list
    python install.py --target project --dry-run
}
finally {
    Pop-Location
}
