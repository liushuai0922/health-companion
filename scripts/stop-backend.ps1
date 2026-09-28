$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot '.run\backend.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'No background server PID recorded.'; exit 0 }
$serverProcessId = [int](Get-Content -LiteralPath $pidFile -Raw)
$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $serverProcessId"
if ($null -eq $processInfo) { Write-Host 'The recorded server has already stopped.'; exit 0 }
if (-not $processInfo.CommandLine.Contains($projectRoot) -or -not $processInfo.CommandLine.Contains('uvicorn backend.app.main:app')) {
    throw 'Recorded PID no longer belongs to this backend; refusing to stop it.'
}
Stop-Process -Id $serverProcessId
Write-Host 'Local backend stopped.'
