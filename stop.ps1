$ErrorActionPreference = 'Stop'
foreach ($mode in @('api','demo')) {
    $recordPath = Join-Path $PSScriptRoot ('runtime\' + $mode + '-process.json')
    if (Test-Path -LiteralPath $recordPath) {
        $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
        $service = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
        if ($service -and $service.Path -eq $record.Path -and $service.StartTime.ToUniversalTime().ToString('o') -eq $record.Started) {
            taskkill /PID $record.Id /T /F
            if ($LASTEXITCODE -ne 0) { throw ('Could not stop project ' + $mode + ' process.') }
        }
    }
}
$recordPath = Join-Path $PSScriptRoot 'runtime\mongodb-process.json'
if (Test-Path -LiteralPath $recordPath) {
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $service = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
    if ($service -and $service.Path -eq $record.Path -and $service.StartTime.ToUniversalTime().ToString('o') -eq $record.Started) {
        & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -c @'
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
try:
    MongoClient('mongodb://127.0.0.1:27018', serverSelectionTimeoutMS=2000).admin.command('shutdown')
except AutoReconnect:
    pass
'@
    }
}
Write-Host 'Tracked project services stopped.'
