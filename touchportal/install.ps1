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
    Write-Host "Arquivos nao gerados. Rode primeiro:" -ForegroundColor Yellow
    Write-Host "  python touchportal\build\build_assets.py" -ForegroundColor White
    exit 1
}

foreach ($dir in @($IconsDest, $PagesDest, (Join-Path $PluginsDest "AI-Commerce-OS"))) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

# Icones
Copy-Item (Join-Path $IconsSrc "*.png") $IconsDest -Force
Write-Host "Icones copiados para $IconsDest" -ForegroundColor Green

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
