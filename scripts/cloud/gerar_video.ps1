# Gera vídeo na nuvem e baixa para o PC (sem travar a máquina)
#
# Uso:
#   .\scripts\cloud\gerar_video.ps1 -Topic "A verdade sobre a Biblioteca de Alexandria"
#   .\scripts\cloud\gerar_video.ps1 -Topic "Tunguska" -Template lofi_dark
#   .\scripts\cloud\gerar_video.ps1 -Topic "Emus vs Austrália" -Production

param(
    [Parameter(Mandatory = $false)]
    [string]$Topic = "",

    [switch]$Production,

    [switch]$Research,

    [string]$Platform = "youtube_dark",

    [ValidateSet("documentario", "dark5", "lofi_dark")]
    [string]$Template = "",

    [string]$OutputDir = ""
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

$Args = @(
    "$ProjectRoot\scripts\cloud\gerar_video.py",
    "--platform", $Platform
)

if ($Topic) { $Args += @("--topic", $Topic) }

if ($Production) { $Args += "--production" }
if ($Research) { $Args += "--research" }
if ($OutputDir) { $Args += @("--output-dir", $OutputDir) }

python @Args
