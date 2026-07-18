# Configura o PC para gerar vídeos na nuvem (Railway)
#
# Uso:
#   .\scripts\cloud\configurar_pc.ps1
#   .\scripts\cloud\configurar_pc.ps1 -CloudUrl "https://meu-app.up.railway.app" -ApiKey "abc123..."

param(
    [string]$CloudUrl = "",
    [string]$ApiKey = ""
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

Write-Host ""
Write-Host "=== Configurar PC para Railway (nuvem) ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "Criado .env a partir de .env.example" -ForegroundColor Yellow
    } else {
        New-Item -Path $EnvFile -ItemType File -Force | Out-Null
    }
}

if (-not $CloudUrl) {
    Write-Host "Cole a URL do Railway (ex: https://ai-commerce-os.up.railway.app):"
    $CloudUrl = Read-Host "CLOUD_API_URL"
}

if (-not $ApiKey) {
    Write-Host ""
    Write-Host "Cole a PIPELINE_API_KEY (mesma do painel Railway):"
    $ApiKey = Read-Host "CLOUD_API_KEY"
}

$CloudUrl = $CloudUrl.Trim().TrimEnd("/")

function Set-EnvVar {
    param([string]$Path, [string]$Name, [string]$Value)
    $lines = @()
    if (Test-Path $Path) {
        $lines = Get-Content $Path -Encoding UTF8
    }
    $found = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=") {
            $found = $true
            "$Name=$Value"
        } else {
            $line
        }
    }
    if (-not $found) {
        $newLines += "$Name=$Value"
    }
    $newLines | Set-Content $Path -Encoding UTF8
}

Set-EnvVar -Path $EnvFile -Name "CLOUD_API_URL" -Value $CloudUrl
Set-EnvVar -Path $EnvFile -Name "CLOUD_API_KEY" -Value $ApiKey

Write-Host ""
Write-Host "Salvo em $EnvFile" -ForegroundColor Green
Write-Host ""
Write-Host "Teste a conexao:" -ForegroundColor Cyan
Write-Host "  python scripts/cloud/gerar_video.py --topic `"teste de conexao`"" -ForegroundColor White
Write-Host ""
Write-Host "Gerar video:" -ForegroundColor Cyan
Write-Host "  .\scripts\cloud\gerar_video.ps1 -Topic `"Seu tema aqui`"" -ForegroundColor White
Write-Host ""
