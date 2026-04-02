$ErrorActionPreference = "Stop"

$automationRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $automationRoot

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Se creo .env local desde .env.example. Ajustelo solo si necesita otro comando o puerto."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    C:\Python314\python.exe -m venv .\.venv
}

& ".\.venv\Scripts\python.exe" -m pip install -r ".\requirements.txt"
& ".\.venv\Scripts\python.exe" -m app.server
