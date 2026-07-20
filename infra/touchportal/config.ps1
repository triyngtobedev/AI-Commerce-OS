# Caminho local do projeto — ajuste se o clone estiver em outro lugar.
$ProjectRoot = "C:\Projetos\AI-Commerce-OS"

$LocalConfig = Join-Path $PSScriptRoot "local.env"
if (Test-Path $LocalConfig) {
    Get-Content $LocalConfig | ForEach-Object {
        if ($_ -match '^\s*PROJECT_ROOT\s*=\s*(.+)$') {
            $ProjectRoot = $matches[1].Trim().Trim('"')
        }
    }
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
