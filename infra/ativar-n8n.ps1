# Ativa automação n8n → Railway (1 comando)
#
# Uso:
#   .\infra\ativar-n8n.ps1
#
# Pré-requisitos:
#   - Docker Desktop aberto
#   - .env na raiz com CLOUD_API_URL e PIPELINE_API_KEY
#   - Railway com deploy Active

$ErrorActionPreference = "Stop"

function Get-DockerExe {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        return "docker"
    }
    $defaultPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $defaultPath) {
        return $defaultPath
    }
    throw "Docker não encontrado. Abra o Docker Desktop e reinicie o terminal."
}

function Read-EnvFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path $Path)) { return $result }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "=") {
            $parts = $line -split "=", 2
            $result[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
    return $result
}

function New-RandomHex {
    param([int]$Bytes = 32)
    -join ((1..($Bytes * 2)) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
}

$Root = Split-Path $PSScriptRoot -Parent
$InfraDir = $PSScriptRoot
$EnvMain = Join-Path $Root ".env"
$EnvN8n = Join-Path $InfraDir ".env.n8n"
$EnvN8nExample = Join-Path $InfraDir ".env.n8n.example"

Write-Host ""
Write-Host "=== Ativar automação n8n → Railway ===" -ForegroundColor Cyan
Write-Host ""

# --- Validar .env principal ---
if (-not (Test-Path $EnvMain)) {
    Write-Error "Arquivo .env não encontrado em $Root`nCopie .env.example para .env e preencha CLOUD_API_URL + PIPELINE_API_KEY."
}

$envMain = Read-EnvFile $EnvMain
$cloudUrl = $envMain["CLOUD_API_URL"]

# Mesma ordem do gerar_video.py: CLOUD_API_KEY → PIPELINE_API_KEY
$apiKey = $envMain["CLOUD_API_KEY"]
if (-not $apiKey) { $apiKey = $envMain["PIPELINE_API_KEY"] }

if ($envMain["CLOUD_API_KEY"] -and $envMain["PIPELINE_API_KEY"] -and
    $envMain["CLOUD_API_KEY"] -ne $envMain["PIPELINE_API_KEY"]) {
    Write-Warning "CLOUD_API_KEY e PIPELINE_API_KEY diferem no .env — usando CLOUD_API_KEY"
    $apiKey = $envMain["CLOUD_API_KEY"]
}

if (-not $cloudUrl) {
    Write-Error "CLOUD_API_URL ausente no .env.`nGuia: docs/deploy-railway.md"
}
if (-not $apiKey) {
    Write-Error "CLOUD_API_KEY ou PIPELINE_API_KEY ausente no .env."
}

Write-Host "Railway URL: $cloudUrl" -ForegroundColor Green
Write-Host "API Key:     $($apiKey.Substring(0, [Math]::Min(8, $apiKey.Length)))..." -ForegroundColor Green
Write-Host ""

# --- Testar chave no Railway antes de continuar ---
Write-Host "Testando chave no Railway..."
try {
    $testBody = '{"platform":"youtube_dark","topic":"teste n8n"}'
    $testResp = Invoke-WebRequest -Uri "$cloudUrl/api/v1/pipeline/run" `
        -Method POST `
        -Headers @{ "X-API-Key" = $apiKey; "Content-Type" = "application/json" } `
        -Body $testBody `
        -UseBasicParsing `
        -TimeoutSec 30
    Write-Host "Chave OK — Railway retornou $($testResp.StatusCode)" -ForegroundColor Green
} catch {
    $status = $_.Exception.Response.StatusCode.value__
    if ($status -eq 401) {
        Write-Host ""
        Write-Host "ERRO 401 — chave local NAO bate com o Railway." -ForegroundColor Red
        Write-Host ""
        Write-Host "  1. Abra railway.app -> seu projeto -> Variables"
        Write-Host "  2. Copie o valor de PIPELINE_API_KEY"
        Write-Host "  3. Cole no .env do PC (CLOUD_API_KEY e PIPELINE_API_KEY = mesmo valor):"
        Write-Host "     CLOUD_API_KEY=cole_aqui"
        Write-Host "     PIPELINE_API_KEY=cole_aqui"
        Write-Host "  4. Rode .\infra\ativar-n8n.ps1 de novo"
        Write-Host ""
        exit 1
    }
    Write-Warning "Teste Railway retornou HTTP $status — continuando mesmo assim..."
}
Write-Host ""

# --- Criar/atualizar infra/.env.n8n ---
if (-not (Test-Path $EnvN8n)) {
    Write-Host "Criando infra/.env.n8n a partir do template..."
    Copy-Item $EnvN8nExample $EnvN8n
}

$n8nContent = Get-Content $EnvN8n -Raw

# Valores locais padrão
$replacements = @{
    "N8N_HOST=n8n.seudominio.com"           = "N8N_HOST=localhost"
    "WEBHOOK_URL=https://n8n.seudominio.com/" = "WEBHOOK_URL=http://localhost:5678/"
    "N8N_BASIC_AUTH_PASSWORD=altere_esta_senha_forte" = "N8N_BASIC_AUTH_PASSWORD=n8nLocal!2026"
}

foreach ($pair in $replacements.GetEnumerator()) {
    $n8nContent = $n8nContent -replace [regex]::Escape($pair.Key), $pair.Value
}

# Encryption key
if ($n8nContent -match "N8N_ENCRYPTION_KEY=\s*$" -or $n8nContent -match "N8N_ENCRYPTION_KEY=$") {
    $encKey = New-RandomHex 32
    $n8nContent = $n8nContent -replace "N8N_ENCRYPTION_KEY=", "N8N_ENCRYPTION_KEY=$encKey"
    Write-Host "N8N_ENCRYPTION_KEY gerada automaticamente."
}

# Webhook secret (mesmo do .env principal se existir)
$webhookSecret = $envMain["N8N_WEBHOOK_SECRET"]
if ($webhookSecret -and $n8nContent -match "N8N_WEBHOOK_SECRET=\s*$") {
    $n8nContent = $n8nContent -replace "N8N_WEBHOOK_SECRET=", "N8N_WEBHOOK_SECRET=$webhookSecret"
}

# PIPELINE_API_BASE_URL → Railway
if ($n8nContent -match "PIPELINE_API_BASE_URL=") {
    $n8nContent = $n8nContent -replace "PIPELINE_API_BASE_URL=.*", "PIPELINE_API_BASE_URL=$cloudUrl"
} else {
    $n8nContent += "`nPIPELINE_API_BASE_URL=$cloudUrl`n"
}

# PIPELINE_API_KEY → mesma chave validada no Railway
if ($n8nContent -match "PIPELINE_API_KEY=") {
    $n8nContent = $n8nContent -replace "PIPELINE_API_KEY=.*", "PIPELINE_API_KEY=$apiKey"
} else {
    $n8nContent += "`nPIPELINE_API_KEY=$apiKey`n"
}

Set-Content -Path $EnvN8n -Value $n8nContent -NoNewline
Write-Host "infra/.env.n8n configurado." -ForegroundColor Green

# --- Subir n8n ---
$Docker = Get-DockerExe
Set-Location $InfraDir

Write-Host ""
Write-Host "Subindo n8n (localhost:5678)..."
& $Docker compose -f docker-compose.local.yml up -d --force-recreate

# --- Aguardar healthcheck ---
Write-Host "Aguardando n8n ficar pronto..."
$maxWait = 90
$waited = 0
$ready = $false
while ($waited -lt $maxWait) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "  ... $waited s"
}

if (-not $ready) {
    Write-Warning "n8n demorou para responder. Tente acessar http://localhost:5678 manualmente."
} else {
    Write-Host "n8n online!" -ForegroundColor Green
}

# --- Importar workflows e ativar ---
Write-Host ""
Write-Host "Importando workflows e ativando..."
Set-Location $Root

$pythonCmd = "python"
if (Test-Path (Join-Path $Root "venv\Scripts\python.exe")) {
    $pythonCmd = Join-Path $Root "venv\Scripts\python.exe"
}

& $pythonCmd (Join-Path $InfraDir "setup_n8n.py")
if ($LASTEXITCODE -ne 0) {
    Write-Warning "setup_n8n.py retornou erro. Você pode importar workflows manualmente no painel n8n."
}

# --- Resumo ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Automação n8n ATIVADA" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Painel n8n:  http://localhost:5678"
Write-Host "  Login:       admin@local.dev / n8nLocal!2026"
Write-Host "  Railway:     $cloudUrl"
Write-Host "  Agendamento: todo dia às 8h (Brasília)"
Write-Host ""
Write-Host "  Guia completo: docs/ATIVAR-N8N.md"
Write-Host ""
Write-Host "  IMPORTANTE: mantenha o PC ligado às 8h da manhã"
Write-Host "  para o vídeo ser gerado automaticamente."
Write-Host ""
