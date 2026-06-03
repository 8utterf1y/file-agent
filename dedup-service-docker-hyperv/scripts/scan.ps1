param(
    [string]$ContainerPath = "/data/docs"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "curl.exe was not found."
    exit 1
}

$payload = "{`"source_path`":`"$ContainerPath`"}"
curl.exe -X POST "http://localhost:8000/scan" -H "Content-Type: application/json" -d $payload

Write-Host ""
Write-Host "Note: scan paths are container paths. To scan a Windows folder, mount it first in docker-compose.yml, for example:"
Write-Host "  D:/company_docs:/data/docs:ro"
Write-Host "Then keep passing /data/docs to this script."
