# Configura botões, ícones, navegação e plugin — sem editar manualmente no Touch Portal.
#
# IMPORTANTE: feche o Touch Portal antes (bandeja -> Exit).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\touchportal\configure-all.ps1
#   powershell -ExecutionPolicy Bypass -File .\touchportal\configure-all.ps1 -ProjectRoot "D:\Dev\AI-Commerce-OS"

param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$RepoRoot = Split-Path -Parent $Here
$TouchPortalRoot = Join-Path $env:APPDATA "TouchPortal"
$IconsDest = Join-Path $TouchPortalRoot "icons"
$PagesDest = Join-Path $TouchPortalRoot "pages"
$PluginDest = Join-Path $TouchPortalRoot "plugins\AI-Commerce-OS"
$PluginSrc = Join-Path $Here "plugin\AI-Commerce-OS"
$IconsSrc = Join-Path $Here "source\icons"
$BuildScript = Join-Path $Here "build\build_pack.py"

if (-not $ProjectRoot) {
    $ProjectRoot = $RepoRoot
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

Write-Host ""
Write-Host "=== AI-Commerce-OS — Configurar Touch Portal ===" -ForegroundColor Cyan
Write-Host "Projeto: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# Verifica se Touch Portal esta aberto
$tpProc = Get-Process -Name "TouchPortal" -ErrorAction SilentlyContinue
if ($tpProc) {
    Write-Host "AVISO: Touch Portal esta aberto (PID $($tpProc.Id))." -ForegroundColor Yellow
    Write-Host "Feche pelo icone da bandeja -> Exit e rode este script de novo." -ForegroundColor Yellow
    Write-Host ""
}

# 1) Backup das pages atuais
$backupDir = Join-Path $TouchPortalRoot ("backups\aicommerce-" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
if (Test-Path $PagesDest) {
    Copy-Item "$PagesDest\*.tml" $backupDir -ErrorAction SilentlyContinue
    Write-Host "[1/6] Backup em $backupDir" -ForegroundColor Green
} else {
    Write-Host "[1/6] Pasta pages nova — sem backup anterior" -ForegroundColor Yellow
}

# 2) Icones
New-Item -ItemType Directory -Force -Path $IconsDest | Out-Null
$pngs = Get-ChildItem $IconsSrc -Filter "*.png" -ErrorAction SilentlyContinue
foreach ($png in $pngs) {
    Copy-Item $png.FullName (Join-Path $IconsDest $png.Name) -Force
}
Write-Host "[2/6] $($pngs.Count) icones copiados" -ForegroundColor Green

# 3) Plugin (somente acoes estaticas — NAO reescreve pages)
New-Item -ItemType Directory -Force -Path $PluginDest | Out-Null
Copy-Item "$PluginSrc\*" $PluginDest -Recurse -Force

$localEnv = Join-Path $PluginDest "local.env"
"PROJECT_ROOT=$ProjectRoot" | Set-Content $localEnv -Encoding UTF8

$configJson = Join-Path $PluginDest "config.json"
@{ projectRoot = $ProjectRoot } | ConvertTo-Json | Set-Content $configJson -Encoding UTF8

Write-Host "[3/6] Plugin instalado (modo estatico, sem plugin_start_cmd)" -ForegroundColor Green

# 4) Gera e implanta pages (Python escreve JSON — evita corrupcao do PowerShell)
New-Item -ItemType Directory -Force -Path $PagesDest | Out-Null
$pluginScript = Join-Path $PluginDest "aicommerce.ps1"
$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
& $python $BuildScript --plugin-script $pluginScript --deploy $PagesDest
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_pack.py falhou"
}
Write-Host "[4/6] Pages implantadas em $PagesDest" -ForegroundColor Green

# 5) Copia TPZ para Desktop (import manual opcional)
$tpz = Join-Path $Here "dist\AI-Commerce-OS-Panels.tpz"
if (Test-Path $tpz) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    Copy-Item $tpz (Join-Path $desktop "AI-Commerce-OS-Panels.tpz") -Force
    Write-Host "[5/6] TPZ copiado para Desktop (backup/import)" -ForegroundColor Green
}

# 6) Verificacao
$mainPage = Join-Path $PagesDest "(main).tml"
if (-not (Test-Path $mainPage)) {
    Write-Error "(main).tml nao foi criado"
}

$raw = [System.IO.File]::ReadAllBytes($mainPage)
if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
    Write-Host "AVISO: BOM detectado em (main).tml — removendo..." -ForegroundColor Yellow
    [System.IO.File]::WriteAllBytes($mainPage, $raw[3..($raw.Length - 1)])
}

$json = Get-Content $mainPage -Raw -Encoding UTF8 | ConvertFrom-Json
$btnCount = 0
$iconCount = 0
foreach ($row in $json.BUTTONS) {
    foreach ($btn in $row) {
        if ($btn -and $btn.PSObject.Properties.Name.Count -gt 0) {
            $btnCount++
            if ($btn.I) { $iconCount++ }
        }
    }
}

Write-Host "[6/6] Verificacao: $btnCount botoes, $iconCount com icone" -ForegroundColor Green
Write-Host ""
Write-Host "=== Pronto ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pages configuradas:" -ForegroundColor White
Write-Host "  (main)       — 8 botoes com icones (Cursor, VS Code, Pipeline, etc.)" -ForegroundColor DarkGray
Write-Host "  ACOS Home    — apps + navegacao Producao/Nuvem/Git" -ForegroundColor DarkGray
Write-Host "  ACOS Producao, Pipeline, Git, Nuvem — com voltar" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Touch Portal GRATIS: celular navega entre 2 pages ((main) + 1)." -ForegroundColor Yellow
Write-Host "No PC todas as 6 pages funcionam." -ForegroundColor Yellow
Write-Host ""
Write-Host "Proximo passo:" -ForegroundColor Cyan
Write-Host "  1. Abra o Touch Portal" -ForegroundColor White
Write-Host "  2. Settings -> Plug-ins -> confie no AI-Commerce-OS (Trust Always)" -ForegroundColor White
Write-Host "  3. Settings -> Backups -> criar backup agora" -ForegroundColor White
Write-Host "  4. Conecte o celular e teste (main)" -ForegroundColor White
Write-Host ""
