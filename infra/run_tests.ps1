# Roda testes a partir de infra/ — sobe um nivel ate a raiz do repo.
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runner = Join-Path $Root "run_tests.py"

if (-not (Test-Path $Runner)) {
    Write-Host ""
    Write-Host "ERRO: run_tests.py nao existe em:" -ForegroundColor Red
    Write-Host "  $Root" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Faca git pull (branch cursor/lofi-dark-template-1dee ou main apos merge)." -ForegroundColor Cyan
    exit 1
}

Set-Location $Root
Write-Host "Repo: $Root" -ForegroundColor DarkGray
& python $Runner @args
exit $LASTEXITCODE
