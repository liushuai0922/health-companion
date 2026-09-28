param([ValidateRange(1, 65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$baseUrl = "http://127.0.0.1:$Port"

# Check before creating demo data or attempting to start a second server.
$socket = New-Object System.Net.Sockets.TcpClient
$occupied = $false
try {
    $connect = $socket.ConnectAsync('127.0.0.1', $Port)
    if ($connect.Wait(1000)) { $occupied = $socket.Connected }
} catch {
    $occupied = $false
} finally {
    $socket.Dispose()
}
if ($occupied) {
    $isHealthCompanion = $false
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 3
        $api = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -TimeoutSec 3
        $isHealthCompanion = ($health.status -eq 'ok' -and $api.info.title -eq 'Health Companion API' -and $null -ne $api.paths.'/patients/{patient_id}/care-plan')
    } catch { }
    if ($isHealthCompanion) {
        Write-Host 'Health Companion is already running. No second server was started.'
        Write-Host "Open $baseUrl/ in your browser."
        Write-Host "API docs: $baseUrl/docs"
        Write-Host 'To restart the recorded background server, run scripts\stop-backend.ps1 first.'
        exit 0
    }
    Write-Host "Port $Port is occupied by another or unresponsive service. It has not been stopped."
    Write-Host 'Choose a free port, for example:'
    Write-Host 'powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Port 8001'
    exit 1
}

Push-Location $projectRoot
try {
    & $python scripts/seed_demo.py
    if ($LASTEXITCODE -ne 0) { throw 'Could not create demo data.' }
    Write-Host "Open $baseUrl/ in your browser. Press Ctrl+C to stop."
    & $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Backend exited with an error.' }
} finally { Pop-Location }
