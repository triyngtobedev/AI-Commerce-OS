# Caminho local do projeto AI-Commerce-OS para Touch Portal.
$ProjectRoot = "C:\Projetos\AI-Commerce-OS"

$LocalConfig = Join-Path $PSScriptRoot "local.env"
if (Test-Path $LocalConfig) {
    Get-Content $LocalConfig | ForEach-Object {
        if ($_ -match '^\s*PROJECT_ROOT\s*=\s*(.+)$') {
            $ProjectRoot = $matches[1].Trim().Trim('"')
        }
    }
}

$JsonConfig = Join-Path $PSScriptRoot "config.json"
if (Test-Path $JsonConfig) {
    try {
        $cfg = Get-Content $JsonConfig -Raw | ConvertFrom-Json
        if ($cfg.projectRoot) { $ProjectRoot = $cfg.projectRoot }
    } catch {}
}

$TouchPortalRoot = Join-Path $env:APPDATA "TouchPortal"
$TouchPortalPluginDir = Join-Path $TouchPortalRoot "plugins\AI-Commerce-OS"
$DispatcherScript = Join-Path $PSScriptRoot "aicommerce.ps1"

function Get-AICommerceProjectRoot {
    return $ProjectRoot
}

function Get-AICommerceDispatcherScript {
    return $DispatcherScript
}
