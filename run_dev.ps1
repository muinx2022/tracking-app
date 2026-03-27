$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not $env:DJANGO_DEV_PORT) {
    $env:DJANGO_DEV_PORT = "8777"
}
$port = $env:DJANGO_DEV_PORT
Write-Host "Starting Django on http://127.0.0.1:$port/ (set DJANGO_DEV_PORT to change)" -ForegroundColor Cyan
& .\venv\Scripts\python.exe manage.py runserver "127.0.0.1:$port"
