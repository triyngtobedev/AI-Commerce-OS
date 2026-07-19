# Ativa automacao n8n -> Railway (1 comando)
#
# Uso:
#   .\infra\ativar-n8n.ps1
#
# Pre-requisitos:
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
    throw "Docker nao encontrado. Abra o Docker Desktop e reinicie o terminal."
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

function Test-RailwayApiKey {
    param(
        [string]$CloudUrl,
        [string]$ApiKey
    )

    $headers = @{
        "X-API-Key"    = $ApiKey
        "Content-Type" = "application/json"
    }
    $body = '{"platform":"youtube_dark","topic":"teste n8n"}'
    $uri = "$CloudUrl/api/v1/pipeline/run"

    try {
        $response = Invoke-WebRequest -Uri $uri -Method POST -Headers $headers -Body $body -UseBasicParsing -TimeoutSec 30
        Write-Host "Chave OK - Railway retornou $($response.StatusCode)" -ForegroundColor Green
        return $true
    }
    catch {
        $status = $null
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }

        if ($status -eq 401) {
            Write-Host ""
            Write-Host "ERRO 401 - a chave local e diferente da chave configurada no Railway." -ForegroundColor Red
            Write-Host ""
            Write-Host "  A chave enviada no header X-API-Key nao coincide com PIPELINE_API_KEY do Railway."
            Write-Host ""
            Write-Host "  1. Abra railway.app -> seu projeto -> Variables"
            Write-Host "     Verifique Service Variables E Shared Variables (ambiente production)"
            Write-Host "  2. Copie o valor de PIPELINE_API_KEY do Railway"
            Write-Host "  3. Cole no .env do PC — PIPELINE_API_KEY e CLOUD_API_KEY devem ter"
            Write-Host "     EXATAMENTE o mesmo valor:"
            Write-Host "     PIPELINE_API_KEY=cole_aqui"
            Write-Host "     CLOUD_API_KEY=cole_aqui"
            Write-Host "  4. Atalho: .\scripts\cloud\configurar_pc.ps1 (grava as duas automaticamente)"
            Write-Host "  5. Rode .\infra\ativar-n8n.ps1 de novo"
            Write-Host ""
            exit 1
        }

        Write-Warning "Teste Railway retornou HTTP $status - continuando mesmo assim..."
        return $false
    }
}

$Root = Split-Path $PSScriptRoot -Parent
$InfraDir = $PSScriptRoot
$EnvMain = Join-Path $Root ".env"
$EnvN8n = Join-Path $InfraDir ".env.n8n"
$EnvN8nExample = Join-Path $InfraDir ".env.n8n.example"

Write-Host ""
Write-Host "=== Ativar automacao n8n -> Railway ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $EnvMain)) {
    Write-Error "Arquivo .env nao encontrado em $Root. Copie .env.example para .env e preencha CLOUD_API_URL + PIPELINE_API_KEY."
}

$envMain = Read-EnvFile $EnvMain
$cloudUrl = $envMain["CLOUD_API_URL"]

# Nome canonico: PIPELINE_API_KEY (CLOUD_API_KEY e alias de compatibilidade)
$apiKey = $envMain["PIPELINE_API_KEY"]
if (-not $apiKey) {
    $apiKey = $envMain["CLOUD_API_KEY"]
}

$cloudKey = $envMain["CLOUD_API_KEY"]
$pipelineKey = $envMain["PIPELINE_API_KEY"]
if ($cloudKey -and $pipelineKey -and ($cloudKey -ne $pipelineKey)) {
    Write-Warning "CLOUD_API_KEY e PIPELINE_API_KEY diferem no .env - usando PIPELINE_API_KEY (nome canonico)"
    $apiKey = $pipelineKey
}

if (-not $cloudUrl) {
    Write-Error "CLOUD_API_URL ausente no .env. Guia: docs/deploy-railway.md"
}
if (-not $apiKey) {
    Write-Error "CLOUD_API_KEY ou PIPELINE_API_KEY ausente no .env."
}

Write-Host "Railway URL: $cloudUrl" -ForegroundColor Green
$keyPreview = $apiKey.Substring(0, [Math]::Min(8, $apiKey.Length))
Write-Host "API Key:     ${keyPreview}..." -ForegroundColor Green
Write-Host ""

Write-Host "Testando chave no Railway..."
Test-RailwayApiKey -CloudUrl $cloudUrl -ApiKey $apiKey | Out-Null
Write-Host ""

if (-not (Test-Path $EnvN8n)) {
    Write-Host "Criando infra/.env.n8n a partir do template..."
    Copy-Item $EnvN8nExample $EnvN8n
}

$n8nContent = Get-Content $EnvN8n -Raw

$replacements = @{
    "N8N_HOST=n8n.seudominio.com" = "N8N_HOST=localhost"
    "WEBHOOK_URL=https://n8n.seudominio.com/" = "WEBHOOK_URL=http://localhost:5678/"
    "N8N_BASIC_AUTH_PASSWORD=altere_esta_senha_forte" = "N8N_BASIC_AUTH_PASSWORD=n8nLocal!2026"
}

foreach ($pair in $replacements.GetEnumerator()) {
    $n8nContent = $n8nContent -replace [regex]::Escape($pair.Key), $pair.Value
}

if ($n8nContent -match "N8N_ENCRYPTION_KEY=\s*$" -or $n8nContent -match "N8N_ENCRYPTION_KEY=$") {
    $encKey = New-RandomHex 32
    $n8nContent = $n8nContent -replace "N8N_ENCRYPTION_KEY=", "N8N_ENCRYPTION_KEY=$encKey"
    Write-Host "N8N_ENCRYPTION_KEY gerada automaticamente."
}

$webhookSecret = $envMain["N8N_WEBHOOK_SECRET"]
if ($webhookSecret -and $n8nContent -match "N8N_WEBHOOK_SECRET=\s*$") {
    $n8nContent = $n8nContent -replace "N8N_WEBHOOK_SECRET=", "N8N_WEBHOOK_SECRET=$webhookSecret"
}

if ($n8nContent -match "PIPELINE_API_BASE_URL=") {
    $n8nContent = $n8nContent -replace "PIPELINE_API_BASE_URL=.*", "PIPELINE_API_BASE_URL=$cloudUrl"
}
else {
    $n8nContent += "`nPIPELINE_API_BASE_URL=$cloudUrl`n"
}

if ($n8nContent -match "PIPELINE_API_KEY=") {
    $n8nContent = $n8nContent -replace "PIPELINE_API_KEY=.*", "PIPELINE_API_KEY=$apiKey"
}
else {
    $n8nContent += "`nPIPELINE_API_KEY=$apiKey`n"
}

Set-Content -Path $EnvN8n -Value $n8nContent -NoNewline
Write-Host "infra/.env.n8n configurado." -ForegroundColor Green

$Docker = Get-DockerExe
Set-Location $InfraDir

Write-Host ""
Write-Host "Subindo n8n (localhost:5678)..."
& $Docker compose -f docker-compose.local.yml up -d --force-recreate

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
    }
    catch {
        # aguarda n8n subir
    }

    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "  ... $waited s"
}

if (-not $ready) {
    Write-Warning "n8n demorou para responder. Tente acessar http://localhost:5678 manualmente."
}
else {
    Write-Host "n8n online!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Importando workflows e ativando..."
Set-Location $Root

$pythonCmd = "python"
$venvPython = Join-Path $Root "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
}

& $pythonCmd (Join-Path $InfraDir "setup_n8n.py")
if ($LASTEXITCODE -ne 0) {
    Write-Warning "setup_n8n.py retornou erro. Voce pode importar workflows manualmente no painel n8n."
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Automacao n8n ATIVADA" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Painel n8n:  http://localhost:5678"
Write-Host "  Login:       admin@local.dev / n8nLocal!2026"
Write-Host "  Railway:     $cloudUrl"
Write-Host "  Agendamento: todo dia as 8h (Brasilia)"
Write-Host ""
Write-Host "  Guia completo: docs/ATIVAR-N8N.md"
Write-Host ""
Write-Host "  IMPORTANTE: mantenha o PC ligado as 8h da manha"
Write-Host "  para o video ser gerado automaticamente."
Write-Host ""
