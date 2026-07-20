# Dispatcher de acoes do AI-Commerce-OS para Touch Portal.
#
# Uso:
#   .\infra\touchportal\aicommerce.ps1 -Action pipeline-ia
#   .\infra\touchportal\aicommerce.ps1 -Action pipeline-tema -Topic "Seu tema"
#   .\infra\touchportal\aicommerce.ps1 -Action last-video

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

    [switch]$Wait
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\config.ps1"

$Root = Get-AICommerceProjectRoot
if (-not (Test-Path $Root)) {
    Write-Host "ERRO: projeto nao encontrado em $Root" -ForegroundColor Red
    Write-Host "Edite infra/touchportal/local.env ou config.ps1" -ForegroundColor Yellow
    exit 1
}

Set-Location $Root

function Invoke-ProjectPowerShell {
    param(
        [string]$Command,
        [switch]$NewWindow
    )

    if ($NewWindow) {
        Start-Process powershell.exe -ArgumentList @(
            "-NoExit",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "Set-Location '$Root'; $Command"
        )
        return
    }

    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $Command
}

function Open-Url {
    param([string]$Url)
    Start-Process $Url
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
        Write-Host "Nenhum video_final.mp4 encontrado em output/ ou downloads/" -ForegroundColor Yellow
        exit 1
    }

    return $video
}

switch ($Action) {
    "pipeline-ia" {
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (Test-Path $script) {
            Invoke-ProjectPowerShell -Command "& '$script' -Research" -NewWindow:(-not $Wait)
        }
        else {
            Invoke-ProjectPowerShell -Command "python main.py --platform youtube_dark --research --production" -NewWindow:(-not $Wait)
        }
    }

    "pipeline-tema" {
        if (-not $Topic) {
            Write-Host "Informe -Topic `"Seu tema`"" -ForegroundColor Red
            exit 1
        }
        $escaped = $Topic.Replace("'", "''")
        $script = Join-Path $Root "scripts\cloud\gerar_video.ps1"
        if (Test-Path $script) {
            Invoke-ProjectPowerShell -Command "& '$script' -Topic '$escaped'" -NewWindow:(-not $Wait)
        }
        else {
            Invoke-ProjectPowerShell -Command "python main.py --platform youtube_dark --production" -NewWindow:(-not $Wait)
        }
    }

    "pipeline-rerun" {
        Invoke-ProjectPowerShell -Command "python main.py --platform youtube_dark --rerun" -NewWindow:(-not $Wait)
    }

    "pipeline-local" {
        Invoke-ProjectPowerShell -Command "python main.py --platform youtube_dark --research" -NewWindow:(-not $Wait)
    }

    "last-video" {
        $video = Find-LastVideo
        Start-Process $video.FullName
        Write-Host "Abrindo: $($video.FullName)" -ForegroundColor Green
    }

    "outputs" {
        $out = Join-Path $Root "output\youtube_dark"
        $dl = Join-Path $Root "downloads"
        New-Item -ItemType Directory -Force -Path $out, $dl | Out-Null
        Start-Process explorer.exe $out
        Start-Sleep -Milliseconds 400
        Start-Process explorer.exe $dl
    }

    "git-commit" {
        Invoke-ProjectPowerShell -Command "git add -A; git status" -NewWindow
    }

    "git-push" {
        Invoke-ProjectPowerShell -Command "git push" -NewWindow
    }

    "git-status" {
        Invoke-ProjectPowerShell -Command "git status" -NewWindow
    }

    "clear-cache" {
        Invoke-ProjectPowerShell -Command "python scripts\maintenance\clear_cache.py" -NewWindow
    }

    "open-project" {
        Start-Process explorer.exe $Root
    }

    "open-cursor" {
        $cursor = Join-Path $env:LOCALAPPDATA "Programs\cursor\Cursor.exe"
        if (Test-Path $cursor) {
            Start-Process $cursor $Root
        }
        else {
            Start-Process explorer.exe $Root
        }
    }

    "open-vscode" {
        Start-Process code $Root
    }

    "open-terminal" {
        Invoke-ProjectPowerShell -Command "# Terminal AI-Commerce-OS" -NewWindow
    }

    "open-explorer" {
        Start-Process explorer.exe $Root
    }

    "open-docker" {
        $docker = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $docker) {
            Start-Process $docker
        }
        else {
            Write-Host "Docker Desktop nao encontrado em $docker" -ForegroundColor Yellow
        }
    }

    "open-firefox" {
        $firefox = "${env:ProgramFiles}\Mozilla Firefox\firefox.exe"
        if (Test-Path $firefox) {
            Start-Process $firefox
        }
        else {
            Write-Host "Firefox nao encontrado" -ForegroundColor Yellow
        }
    }

    "open-youtube-studio" {
        Open-Url "https://studio.youtube.com"
    }

    "open-railway" {
        Open-Url "https://railway.app"
    }

    "restart-api" {
        $api = Join-Path $Root "api\run_api.ps1"
        Invoke-ProjectPowerShell -Command "& '$api'" -NewWindow
    }

    "logs" {
        Invoke-ProjectPowerShell -Command "# Logs: acompanhe aqui ou abra Railway Deploy Logs" -NewWindow
        Start-Process "https://railway.app"
    }
}

exit 0
