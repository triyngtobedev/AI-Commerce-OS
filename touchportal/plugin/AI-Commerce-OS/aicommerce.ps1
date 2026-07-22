# AI-Commerce-OS — acoes do plugin Touch Portal
param(
    [Parameter(Mandatory = $true)]
    [string]$Action,

    [string]$Topic = ""
)

$PluginDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $PluginDir "config.json"

function Get-ProjectRoot {
    if ($env:AICOMMERCE_PROJECT_ROOT -and (Test-Path $env:AICOMMERCE_PROJECT_ROOT)) {
        return $env:AICOMMERCE_PROJECT_ROOT
    }
    if (Test-Path $ConfigFile) {
        try {
            $cfg = Get-Content $ConfigFile -Raw | ConvertFrom-Json
            if ($cfg.projectRoot -and (Test-Path $cfg.projectRoot)) {
                return $cfg.projectRoot
            }
        } catch {}
    }
    $candidates = @(
        "C:\Projetos\AI-Commerce-OS",
        "D:\Projetos\AI-Commerce-OS",
        "$env:USERPROFILE\Projects\AI-Commerce-OS",
        "$env:USERPROFILE\Documents\AI-Commerce-OS"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "Projeto AI-Commerce-OS nao encontrado. Edite touchportal\plugin\AI-Commerce-OS\config.json"
}

function Open-App {
    param([string]$Path, [string]$Args = "")
    if (-not (Test-Path $Path)) {
        Start-Process $Path -ErrorAction SilentlyContinue
        return
    }
    if ($Args) { Start-Process $Path -ArgumentList $Args }
    else { Start-Process $Path }
}

$Root = Get-ProjectRoot

switch ($Action) {
    "pipeline-ia" {
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (-not (Test-Path $script)) { throw "Script nao encontrado: $script" }
        & $script -Topic "Tema automatico do pipeline"
    }
    "pipeline-tema" {
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (-not $Topic) { $Topic = "Novo tema" }
        & $script -Topic $Topic
    }
    "pipeline-rerun" {
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        & $script -Topic "Reprocessar ultimo job"
    }
    "last-video" {
        $output = Join-Path $Root "output"
        if (-not (Test-Path $output)) { New-Item -ItemType Directory -Path $output | Out-Null }
        $video = Get-ChildItem $output -Filter "*.mp4" -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($video) { Start-Process $video.FullName }
        else { Start-Process explorer.exe $output }
    }
    "outputs" {
        $output = Join-Path $Root "output"
        if (-not (Test-Path $output)) { New-Item -ItemType Directory -Path $output | Out-Null }
        Start-Process explorer.exe $output
    }
    "git-commit" {
        Set-Location $Root
        git add -A
        git commit -m "chore: update from Touch Portal"
    }
    "git-push" {
        Set-Location $Root
        git push
    }
    "clear-cache" {
        Get-ChildItem $Root -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem $Root -Directory -Recurse -Filter ".pytest_cache" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    "open-project" { Start-Process explorer.exe $Root }
    "restart-api" {
        $apiScript = Join-Path $Root "api\run_api.ps1"
        if (Test-Path $apiScript) {
            Start-Process powershell.exe -ArgumentList "-NoExit", "-File", "`"$apiScript`""
        }
    }
    "open-terminal" {
        $wt = "$env:LOCALAPPDATA\Microsoft\WindowsApps\wt.exe"
        if (Test-Path $wt) { Start-Process $wt -ArgumentList "-d", $Root }
        else { Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'" }
    }
    "open-docker" {
        $docker = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
        Open-App $docker
    }
    "open-cursor" {
        $cursor = "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe"
        if (-not (Test-Path $cursor)) { $cursor = "$env:LOCALAPPDATA\cursor\Cursor.exe" }
        Open-App $cursor $Root
    }
    "open-vscode" {
        $code = "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe"
        if (-not (Test-Path $code)) { $code = "code" }
        Open-App $code $Root
    }
    "open-youtube-studio" {
        Start-Process "https://studio.youtube.com"
    }
    "open-railway" {
        Start-Process "https://railway.app/dashboard"
    }
    "logs" {
        $logs = Join-Path $Root "logs"
        if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
        Start-Process explorer.exe $logs
    }
    default { throw "Acao desconhecida: $Action" }
}
