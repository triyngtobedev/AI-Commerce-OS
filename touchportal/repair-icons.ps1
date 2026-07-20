# Repara icones faltando nos botoes existentes do Touch Portal
#
# Uso (feche o Touch Portal antes):
#   powershell -ExecutionPolicy Bypass -File .\touchportal\repair-icons.ps1
#
# O script:
#   1. Copia os 8 PNGs para %APPDATA%\TouchPortal\icons\
#   2. Atualiza a page (main) IN-PLACE — preserva IDs e acoes dos botoes

$ErrorActionPreference = "Stop"
$TouchPortalRoot = Join-Path $env:APPDATA "TouchPortal"
$IconsDest = Join-Path $TouchPortalRoot "icons"
$PagesDest = Join-Path $TouchPortalRoot "pages"
$MainPage = Join-Path $PagesDest "(main).tml"
$PageSrc = Join-Path $PSScriptRoot "pages\aicommerce-main.tml"
$IconsSrc = Join-Path $PSScriptRoot "source\icons"
$TpzFile = Join-Path $PSScriptRoot "dist\AI-Commerce-OS-Main.tpz"
$TempDir = Join-Path $env:TEMP "aicommerce-tp-repair"

# action suffix -> PNG filename
$ActionIconMap = @{
    "open-cursor"    = "aico-cursor.png"
    "open-vscode"    = "aico-vscode.png"
    "open-project"   = "aico-project.png"
    "pipeline-ia"    = "aico-pipeline.png"
    "open-docker"    = "aico-docker.png"
    "git-push"       = "aico-github.png"
    "open-terminal"  = "aico-terminal.png"
    "open-railway"   = "aico-railway.png"
}

function Expand-Tpz {
    param([string]$TpzPath, [string]$Dest)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($TpzPath, $Dest)
}

function Get-ActionSuffix {
    param($Button)
    if (-not $Button.A -or $Button.A.Count -eq 0) { return $null }
    $action = $Button.A[0]
    $id = $action.kID
    if (-not $id) { return $null }
    if ($id -match '\.actions\.(.+)$') { return $Matches[1] }
    return $null
}

function Patch-PageIcons {
    param([string]$PagePath)

    if (-not (Test-Path $PagePath)) {
        Write-Host "Page nao encontrada: $PagePath" -ForegroundColor Yellow
        return 0
    }

    $raw = Get-Content $PagePath -Raw -Encoding UTF8
    $json = $raw | ConvertFrom-Json
    $patched = 0

    foreach ($row in $json.BUTTONS) {
        foreach ($btn in $row) {
            $suffix = Get-ActionSuffix $btn
            if (-not $suffix) { continue }
            if (-not $ActionIconMap.ContainsKey($suffix)) { continue }

            $iconFile = $ActionIconMap[$suffix]
            if ($btn.I -eq $iconFile) { continue }

            $btn.I = $iconFile
            $btn.ITS = $true
            $btn.IiS = $true
            $patched++
            Write-Host "  + $($ActionIconMap[$suffix]) -> $suffix" -ForegroundColor Green
        }
    }

    if ($patched -gt 0) {
        $json | ConvertTo-Json -Depth 20 -Compress | Set-Content $PagePath -Encoding UTF8 -NoNewline
    }

    return $patched
}

Write-Host ""
Write-Host "=== Reparar icones Touch Portal ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $IconsSrc)) {
    Write-Error "Pasta touchportal\source\icons nao encontrada. Rode: git pull"
}

New-Item -ItemType Directory -Path $IconsDest -Force | Out-Null

# 1) Copia PNGs do repo
$pngs = Get-ChildItem $IconsSrc -Filter "*.png"
foreach ($png in $pngs) {
    Copy-Item $png.FullName (Join-Path $IconsDest $png.Name) -Force
}
Write-Host "Copiados $($pngs.Count) icones para $IconsDest" -ForegroundColor Green

# 2) Backup: extrai PNGs do TPZ
if (Test-Path $TpzFile) {
    Expand-Tpz -TpzPath $TpzFile -Dest $TempDir
    Get-ChildItem $TempDir -Filter "*.png" | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $IconsDest $_.Name) -Force
    }
    Write-Host "Extraidos icones do TPZ (backup)" -ForegroundColor Green
}

# 3) Patch in-place na page existente (preserva botoes e acoes)
Write-Host ""
Write-Host "Atualizando icones nos botoes existentes..." -ForegroundColor Cyan
$patched = Patch-PageIcons -PagePath $MainPage

if ($patched -eq 0 -and (Test-Path $PageSrc)) {
    Write-Host "Nenhum botao precisou de patch — copiando page de referencia." -ForegroundColor Yellow
    Copy-Item $PageSrc $MainPage -Force
    $patched = Patch-PageIcons -PagePath $MainPage
}

# 4) Verifica referencias
if (Test-Path $MainPage) {
    $json = Get-Content $MainPage -Raw | ConvertFrom-Json
    $missing = @()
    $found = 0
    foreach ($row in $json.BUTTONS) {
        foreach ($btn in $row) {
            if ($btn.I) {
                $found++
                if (-not (Test-Path (Join-Path $IconsDest $btn.I))) {
                    $missing += $btn.I
                }
            }
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "ATENCAO: icones ausentes no disco:" -ForegroundColor Yellow
        $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    } else {
        Write-Host ""
        Write-Host "OK: $found botoes com icones, todos os PNGs existem." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Feche o Touch Portal (bandeja -> Exit) e abra de novo." -ForegroundColor Cyan
Write-Host ""
