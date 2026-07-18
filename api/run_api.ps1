# Inicia a API FastAPI de integração n8n (Windows)
#
# Uso:
#   .\api\run_api.ps1
#
# Variáveis opcionais:
#   $env:API_HOST  (padrão: 127.0.0.1)
#   $env:API_PORT  (padrão: 8000)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$HostAddr = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$Port = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

Write-Host "Starting AI-Commerce-OS Pipeline API on ${HostAddr}:${Port}"

python -m uvicorn api.main_api:app `
    --host $HostAddr `
    --port $Port `
    --workers 1 `
    --log-level info
