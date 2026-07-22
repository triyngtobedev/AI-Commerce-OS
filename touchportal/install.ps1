# Instala icones e page do AI-Commerce-OS no Touch Portal
#
# Uso (feche o Touch Portal antes):
#   .\touchportal\install.ps1
#   .\touchportal\install.ps1 -AsMainPage

param(
    [switch]$AsMainPage,
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$TouchPortalRoot = Join-Path $env:APPDATA "TouchPortal"
$IconsDest = Join-Path $TouchPortalRoot "icons"
$PagesDest = Join-Path $TouchPortalRoot "pages"
$PluginsDest = Join-Path $TouchPortalRoot "plugins"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $PSScriptRoot "dist"
$PluginSrc = Join-Path $PSScriptRoot "plugin\AI-Commerce-OS"
$IconsSrc = Join-Path $PSScriptRoot "source\icons"
$PageSrc = Join-Path $PSScriptRoot "pages\aicommerce-main.tml"

Write-Host ""
Write-Host "=== AI-Commerce-OS Touch Portal ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $PageSrc)) {
    Write-Host "Page nao encontrada: $PageSrc" -ForegroundColor Red
    Write-Host "Rode: git checkout origin/cursor/touchportal-icons-c0f0 -- touchportal" -ForegroundColor White
    exit 1
}

if (-not (Test-Path $IconsSrc) -or ((Get-ChildItem $IconsSrc -Filter "*.png").Count -lt 8)) {
    Write-Host "Icones pre-gerados nao encontrados em source\icons." -ForegroundColor Yellow
    Write-Host "Opcional (dev): pip install cairosvg pillow requests && python touchportal\build\build_assets.py" -ForegroundColor White
}

foreach ($dir in @($IconsDest, $PagesDest, (Join-Path $PluginsDest "AI-Commerce-OS"))) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

# Icones — copia todos e verifica
$pngs = Get-ChildItem $IconsSrc -Filter "*.png"
if ($pngs.Count -lt 8) {
    Write-Host "AVISO: so $($pngs.Count) icones em $IconsSrc (esperado 8)." -ForegroundColor Yellow
    Write-Host "Rode: python touchportal\build\build_assets.py" -ForegroundColor White
}
foreach ($png in $pngs) {
    Copy-Item $png.FullName (Join-Path $IconsDest $png.Name) -Force
}
Write-Host "Icones copiados ($($pngs.Count)) para $IconsDest" -ForegroundColor Green

# Backup: extrai PNGs do .tpz tambem
$tpz = Join-Path $DistDir "AI-Commerce-OS-Main.tpz"
if (Test-Path $tpz) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tmp = Join-Path $env:TEMP "aicommerce-tp-install"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($tpz, $tmp)
    Get-ChildItem $tmp -Filter "*.png" | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $IconsDest $_.Name) -Force
    }
}

# Page
$pageName = if ($AsMainPage) { "(main).tml" } else { "aicommerce-main.tml" }
Copy-Item $PageSrc (Join-Path $PagesDest $pageName) -Force
Write-Host "Page copiada como $pageName" -ForegroundColor Green

# Plugin
Copy-Item "$PluginSrc\*" (Join-Path $PluginsDest "AI-Commerce-OS") -Recurse -Force

$configPath = Join-Path $PluginsDest "AI-Commerce-OS\config.json"
if (-not (Test-Path $configPath)) {
    Copy-Item (Join-Path $PluginSrc "config.example.json") $configPath
}

if ($ProjectRoot) {
    @{ projectRoot = $ProjectRoot } | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
} elseif (-not (Test-Path $configPath)) {
    @{ projectRoot = $RepoRoot.Replace("/", "\") } | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
}

Write-Host "Plugin instalado em $(Join-Path $PluginsDest 'AI-Commerce-OS')" -ForegroundColor Green
Write-Host ""
Write-Host "Proximo passo:" -ForegroundColor Cyan
Write-Host "  1. Abra o Touch Portal" -ForegroundColor White
Write-Host "  2. Se pedir confianca no plugin, clique Trust Always" -ForegroundColor White
if (-not $AsMainPage) {
    Write-Host "  3. Pages -> selecione 'aicommerce-main'" -ForegroundColor White
} else {
    Write-Host "  3. A page principal (main) ja foi substituida" -ForegroundColor White
}
Write-Host ""
