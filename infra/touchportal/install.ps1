# Instala plugin + gera pacote Touch Portal (.tpz)
#
# Uso:
#   .\infra\touchportal\install.bat
#   powershell -ExecutionPolicy Bypass -File .\infra\touchportal\install.ps1

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

# 1) Caminho local
$LocalEnv = Join-Path $Here "local.env"
"PROJECT_ROOT=$ProjectRoot" | Set-Content -Path $LocalEnv -Encoding UTF8
Write-Host "[1/5] local.env atualizado" -ForegroundColor Green

# 2) Plugin Touch Portal
$TpPluginDir = Join-Path $env:APPDATA "TouchPortal\plugins\AI-Commerce-OS"
New-Item -ItemType Directory -Force -Path $TpPluginDir | Out-Null

foreach ($file in @("aicommerce.ps1", "config.ps1", "local.env")) {
    Copy-Item (Join-Path $Here $file) (Join-Path $TpPluginDir $file) -Force
}
Copy-Item (Join-Path $Here "plugin\AI-Commerce-OS\entry.tp") (Join-Path $TpPluginDir "entry.tp") -Force

Write-Host "[2/5] Plugin instalado em $TpPluginDir" -ForegroundColor Green

# 3) Gera .tpz
Write-Host "[3/5] Gerando pacote .tpz ..." -ForegroundColor Yellow
python (Join-Path $Here "build_pack.py") --project-root $ProjectRoot --use-installed-plugin-path
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_pack.py falhou"
}

$PackTpz = Join-Path $Here "dist\AI-Commerce-OS-Panels.tpz"
if (-not (Test-Path $PackTpz)) {
    Write-Error "Arquivo nao gerado: $PackTpz"
}

# 4) Copia para Desktop (evita erro de importacao em pastas profundas)
$Desktop = [Environment]::GetFolderPath("Desktop")
$DesktopPack = Join-Path $Desktop "AI-Commerce-OS-Panels.tpz"
Copy-Item $PackTpz $DesktopPack -Force
Write-Host "[4/5] Copiado para Desktop:" -ForegroundColor Green
Write-Host "       $DesktopPack" -ForegroundColor White

# 5) Instrucoes
Write-Host "[5/5] Pronto" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTAR NO TOUCH PORTAL (app no PC, nao no iPhone):" -ForegroundColor Cyan
Write-Host "  1. Reinicie o Touch Portal"
Write-Host "  2. Aba Pages -> icone de engrenagem -> Import page"
Write-Host "  3. Va em Desktop e selecione: AI-Commerce-OS-Panels.tpz"
Write-Host "  4. NAO de duplo clique no arquivo (.tpz pode abrir programa errado)"
Write-Host "  5. Se nao aparecer, mude filtro para 'Todos os arquivos (*.*)'"
Write-Host ""
Write-Host "Pipeline Tema com texto no celular:" -ForegroundColor DarkGray
Write-Host "  Edite o botao -> acao 'Pipeline Tema' do plugin AI-Commerce-OS" -ForegroundColor DarkGray
Write-Host ""
