# Repara icones faltando no Touch Portal (main)
#
# Uso (feche o Touch Portal antes):
#   powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1

$ErrorActionPreference = "Stop"
$TouchPortalRoot = Join-Path $env:APPDATA "TouchPortal"
$IconsDest = Join-Path $TouchPortalRoot "icons"
$PagesDest = Join-Path $TouchPortalRoot "pages"
$MainPage = Join-Path $PagesDest "(main).tml"
$IconsSrc = Join-Path $PSScriptRoot "source\icons"
$TpzFile = Join-Path $PSScriptRoot "dist\AI-Commerce-OS-Main.tpz"
$TempDir = Join-Path $env:TEMP "aicommerce-tp-repair"

function Expand-Tpz {
    param([string]$TpzPath, [string]$Dest)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($TpzPath, $Dest)
}

Write-Host ""
Write-Host "=== Reparar icones Touch Portal ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $IconsSrc)) {
    Write-Error "Pasta touchportal\source\icons nao encontrada. Rode: git checkout cursor/touchportal-icons-c0f0 -- touchportal"
}

# 1) Copia todos os PNGs do repo
New-Item -ItemType Directory -Path $IconsDest -Force | Out-Null
$pngs = Get-ChildItem $IconsSrc -Filter "*.png"
foreach ($png in $pngs) {
    Copy-Item $png.FullName (Join-Path $IconsDest $png.Name) -Force
}
Write-Host "Copiados $($pngs.Count) icones para $IconsDest" -ForegroundColor Green

# 2) Extrai PNGs do .tpz (backup)
if (Test-Path $TpzFile) {
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
    Expand-Tpz -TpzPath $TpzFile -Dest $TempDir
    Get-ChildItem $TempDir -Filter "*.png" | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $IconsDest $_.Name) -Force
    }
    Write-Host "Extraidos icones do TPZ" -ForegroundColor Green
}

# 3) Verifica referencias na page (main)
if (Test-Path $MainPage) {
    $json = Get-Content $MainPage -Raw | ConvertFrom-Json
    $missing = @()
    foreach ($row in $json.BUTTONS) {
        foreach ($btn in $row) {
            if ($btn.I -and -not (Test-Path (Join-Path $IconsDest $btn.I))) {
                $missing += $btn.I
            }
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "ATENCAO: $($missing.Count) icones referenciados na page mas ausentes:" -ForegroundColor Yellow
        $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
        Write-Host ""
        Write-Host "Reinstale a page:" -ForegroundColor Cyan
        Write-Host "  Copy-Item touchportal\pages\aicommerce-main.tml `"$MainPage`" -Force" -ForegroundColor White
    } else {
        Write-Host "Todos os icones referenciados em (main) existem." -ForegroundColor Green
    }
} else {
    Write-Host "(main).tml nao encontrado — copiando page nova..." -ForegroundColor Yellow
    Copy-Item (Join-Path $PSScriptRoot "pages\aicommerce-main.tml") $MainPage -Force
}

Write-Host ""
Write-Host "Reabra o Touch Portal (feche pela bandeja e abra de novo)." -ForegroundColor Cyan
Write-Host ""
