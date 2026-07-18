# Gera video lofi_dark — sobe um nivel ate a raiz do repo.
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runner = Join-Path $Root "gerar_lofi_dark.py"

if (-not (Test-Path $Runner)) {
    Write-Host "ERRO: gerar_lofi_dark.py nao encontrado em $Root" -ForegroundColor Red
    Write-Host "Faca: git pull origin cursor/lofi-dark-template-1dee" -ForegroundColor Cyan
    exit 1
}

Set-Location $Root
& python $Runner @args
exit $LASTEXITCODE
