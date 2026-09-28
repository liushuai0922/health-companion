param([int]$Port = 18765)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) { throw "Port $Port is occupied; select another port." }
$server = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try {
    $response = $null
    for ($i = 0; $i -lt 40; $i++) {
        $server.Refresh()
        if ($server.HasExited) { throw 'Smoke test server exited before it became ready.' }
        try { $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2; break }
        catch { Start-Sleep -Milliseconds 250 }
    }
    if ($null -eq $response) { throw 'Server did not become ready.' }
    if ($response.StatusCode -ne 200) { throw 'Unexpected HTTP status.' }
    $body = $response.Content | ConvertFrom-Json
    if ($body.status -ne 'ok') { throw 'Unexpected health response.' }
    Write-Output "PASS GET /health HTTP $($response.StatusCode) $($response.Content)"
} finally {
    $server.Refresh()
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
