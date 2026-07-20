# Dispatcher de acoes do AI-Commerce-OS para Touch Portal.
# Executa tudo no processo atual (sem abrir janela extra do PowerShell).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "pipeline-ia",
        "pipeline-tema",
        "pipeline-rerun",
        "pipeline-local",
        "last-video",
        "outputs",
        "git-commit",
        "git-push",
        "git-status",
        "clear-cache",
        "open-project",
        "open-cursor",
        "open-vscode",
        "open-terminal",
        "open-explorer",
        "open-docker",
        "open-firefox",
        "open-youtube-studio",
        "open-railway",
        "restart-api",
        "logs"
    )]
    [string]$Action,

    [string]$Topic = "",

    [switch]$Pause
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

$Root = Get-AICommerceProjectRoot
if (-not (Test-Path $Root)) {
    Write-Host "ERRO: projeto nao encontrado em $Root" -ForegroundColor Red
    exit 1
}

Set-Location $Root

function Wait-IfNeeded {
    if ($Pause) {
        Read-Host "Pressione Enter para fechar"
    }
}

function Find-LastVideo {
    $paths = @(
        (Join-Path $Root "output\youtube_dark"),
        (Join-Path $Root "downloads")
    )

    $video = Get-ChildItem -Path $paths -Recurse -Filter "video_final.mp4" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $video) {
        Write-Host "Nenhum video_final.mp4 encontrado." -ForegroundColor Yellow
        exit 1
    }

    return $video
}

switch ($Action) {
    "pipeline-ia" {
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (Test-Path $script) {
            & $script -Research
        }
        else {
            python main.py --platform youtube_dark --research --production
        }
        Wait-IfNeeded
    }

    "pipeline-tema" {
        if (-not $Topic) {
            Write-Host "Tema nao informado. Use a acao Pipeline Tema do plugin (campo no celular)." -ForegroundColor Red
            exit 1
        }
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (Test-Path $script) {
            & $script -Topic $Topic
        }
        else {
            python main.py --platform youtube_dark --production
        }
        Wait-IfNeeded
    }

    "pipeline-rerun" {
        python main.py --platform youtube_dark --rerun
        Wait-IfNeeded
    }

    "pipeline-local" {
        python main.py --platform youtube_dark --research
        Wait-IfNeeded
    }

    "last-video" {
        $video = Find-LastVideo
        Start-Process $video.FullName
    }

    "outputs" {
        $out = Join-Path $Root "output\youtube_dark"
        $dl = Join-Path $Root "downloads"
        New-Item -ItemType Directory -Force -Path $out, $dl | Out-Null
        Start-Process explorer.exe $out
        Start-Sleep -Milliseconds 300
        Start-Process explorer.exe $dl
    }

    "git-commit" {
        git add -A
        git status
        Wait-IfNeeded
    }

    "git-push" {
        git push
        Wait-IfNeeded
    }

    "git-status" {
        git status
        Wait-IfNeeded
    }

    "clear-cache" {
        python scripts\maintenance\clear_cache.py
        Wait-IfNeeded
    }

    "open-project" { Start-Process explorer.exe $Root }
    "open-explorer" { Start-Process explorer.exe $Root }

    "open-cursor" {
        $cursor = Join-Path $env:LOCALAPPDATA "Programs\cursor\Cursor.exe"
        if (Test-Path $cursor) { Start-Process $cursor $Root }
        else { Start-Process explorer.exe $Root }
    }

    "open-vscode" { Start-Process code $Root }

    "open-terminal" {
        Start-Process powershell.exe -ArgumentList @(
            "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command", "Set-Location '$Root'"
        ) -WindowStyle Normal -WorkingDirectory $Root
    }

    "open-docker" {
        $docker = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $docker) { Start-Process $docker }
    }

    "open-firefox" {
        $firefox = "${env:ProgramFiles}\Mozilla Firefox\firefox.exe"
        if (Test-Path $firefox) { Start-Process $firefox }
    }

    "open-youtube-studio" { Start-Process "https://studio.youtube.com" }
    "open-railway" { Start-Process "https://railway.app" }

    "restart-api" {
        $api = Join-Path $Root "api\run_api.ps1"
        Start-Process powershell.exe -ArgumentList @(
            "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", $api
        ) -WindowStyle Normal -WorkingDirectory $Root
    }

    "logs" {
        Start-Process "https://railway.app"
    }
}

exit 0
