param()

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker was not found. Install Docker Desktop with Hyper-V backend and use Linux containers."
    exit 1
}

Set-Location $projectDir
New-Item -ItemType Directory -Force -Path "data" | Out-Null

docker compose up --build
