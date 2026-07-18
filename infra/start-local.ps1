# Sobe o n8n em modo local (HTTP, sem nginx)
#
# Uso:
#   .\infra\start-local.ps1

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

$Docker = Get-DockerExe

$InfraDir = $PSScriptRoot
Set-Location $InfraDir

if (-not (Test-Path ".env.n8n")) {
    Write-Error "Arquivo .env.n8n não encontrado. Copie de .env.n8n.example e preencha os valores."
}

Write-Host "Subindo n8n (localhost:5678)..."
& $Docker compose -f docker-compose.local.yml up -d

Write-Host ""
& $Docker compose -f docker-compose.local.yml ps
Write-Host ""
Write-Host "n8n: http://localhost:5678"
Write-Host "Login: admin + senha definida em infra/.env.n8n"
