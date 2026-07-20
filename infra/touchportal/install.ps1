# Instala plugin + gera pacote Touch Portal (.tpz2)
#
# Uso (PowerShell na raiz do repo):
#   .\infra\touchportal\install.ps1
#   .\infra\touchportal\install.ps1 -ProjectRoot "D:\Dev\AI-Commerce-OS"

param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $ProjectRoot) {
    $ProjectRoot = Split-Path -Parent (Split-Path -Parent $Here)
}

$ProjectRoot = (Resolve-Path $ProjectRoot).Path

Write-Host ""
Write-Host "=== AI-Commerce-OS — Touch Portal ===" -ForegroundColor Cyan
Write-Host "Projeto: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# 1) Salva caminho local
$LocalEnv = Join-Path $Here "local.env"
"PROJECT_ROOT=$ProjectRoot" | Set-Content -Path $LocalEnv -Encoding UTF8
Write-Host "[1/4] local.env atualizado" -ForegroundColor Green

# 2) Instala plugin no Touch Portal
$TpPluginDir = Join-Path $env:APPDATA "TouchPortal\plugins\AI-Commerce-OS"
New-Item -ItemType Directory -Force -Path $TpPluginDir | Out-Null

$FilesToCopy = @(
    "aicommerce.ps1",
    "config.ps1",
    "local.env"
)
foreach ($file in $FilesToCopy) {
    Copy-Item (Join-Path $Here $file) (Join-Path $TpPluginDir $file) -Force
}
Copy-Item (Join-Path $Here "plugin\AI-Commerce-OS\entry.tp") (Join-Path $TpPluginDir "entry.tp") -Force

Write-Host "[2/4] Plugin instalado em:" -ForegroundColor Green
Write-Host "       $TpPluginDir" -ForegroundColor DarkGray

# 3) Gera pacote .tpz2
Write-Host "[3/4] Gerando AI-Commerce-OS-Panels.tpz2 ..." -ForegroundColor Yellow
python (Join-Path $Here "build_pack.py") --project-root $ProjectRoot --use-installed-plugin-path
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_pack.py falhou"
}

$Pack = Join-Path $Here "dist\AI-Commerce-OS-Panels.tpz2"

# 4) Instrucoes
Write-Host "[4/4] Pronto" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos passos no PC:" -ForegroundColor Cyan
Write-Host "  1. Reinicie o Touch Portal (para carregar o plugin)"
Write-Host "  2. Pages -> engrenagem -> Import page"
Write-Host "  3. Selecione: $Pack"
Write-Host "  4. Abra a pagina '🚀 Producao' no iPhone"
Write-Host ""
Write-Host "Botao Pipeline Tema pede texto no celular (plugin AI-Commerce-OS)." -ForegroundColor DarkGray
Write-Host "Git separado: Commit (add+status) e Push." -ForegroundColor DarkGray
Write-Host ""
