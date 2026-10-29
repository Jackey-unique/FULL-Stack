param([switch]$Demo, [switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run setup.ps1 first.' }
$port = if ($Demo) { '5001' } else { '5000' }
$mode = if ($Demo) { 'demo' } else { 'api' }
$apiUrl = 'http://127.0.0.1:' + $port
try {
    $health = Invoke-RestMethod -Uri ($apiUrl + '/api/v1/health') -TimeoutSec 2
    if ($health.application -eq 'BrainAge Connect') {
        Write-Host ('Already running: ' + $apiUrl)
        if ($OpenBrowser) { Start-Process $apiUrl }
        exit 0
    }
} catch { }
$runtimePath = Join-Path $PSScriptRoot 'runtime'
$databasePath = Join-Path $runtimePath 'mongodb'
New-Item -ItemType Directory -Force $databasePath | Out-Null
& $pythonExe -c @'
import sys
from pymongo import MongoClient
try:
    MongoClient('mongodb://127.0.0.1:27018',serverSelectionTimeoutMS=1000).admin.command('ping')
except Exception:
    sys.exit(1)
'@
if ($LASTEXITCODE -ne 0) {
    $mongoExe = Get-Command mongod -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
    if (-not $mongoExe) { $mongoExe = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'tools') -Recurse -Filter mongod.exe | Select-Object -ExpandProperty FullName -First 1 }
    if (-not $mongoExe) { throw 'MongoDB server not found. Install it or place portable MongoDB under tools/.' }
    $logPath = Join-Path $runtimePath 'mongodb.log'
    $mongoArgs = '--bind_ip 127.0.0.1 --port 27018 --dbpath "{0}" --logpath "{1}" --logappend' -f $databasePath,$logPath
    $databaseProcess = Start-Process -FilePath $mongoExe -ArgumentList $mongoArgs -WindowStyle Hidden -PassThru
    @{Id=$databaseProcess.Id; Started=$databaseProcess.StartTime.ToUniversalTime().ToString('o'); Path=$mongoExe} | ConvertTo-Json | Set-Content (Join-Path $runtimePath 'mongodb-process.json')
    Start-Sleep -Seconds 3
}
$env:MONGO_DB = 'brainage_connect'
& $pythonExe -m scripts.bootstrap
if ($LASTEXITCODE -ne 0) { throw 'Database/configuration initialization failed.' }
if ($Demo) {
    $env:MONGO_DB = 'brainage_demo'
    & $pythonExe -c "from brainage import create_app; import sys; d=create_app().extensions['mongo_db']; sys.exit(0 if d.samples.count_documents({}) else 1)"
    if ($LASTEXITCODE -ne 0) {
        & $pythonExe -m scripts.seed_demo
        if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed.' }
    }
}
$env:PORT = $port
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList 'app.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath ($mode + '.stdout.log')) -RedirectStandardError (Join-Path $runtimePath ($mode + '.stderr.log'))
@{Id=$apiProcess.Id; Started=$apiProcess.StartTime.ToUniversalTime().ToString('o'); Path=$pythonExe} | ConvertTo-Json | Set-Content (Join-Path $runtimePath ($mode + '-process.json'))
$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod -Uri ($apiUrl + '/api/v1/health') -TimeoutSec 1
        if ($health.application -eq 'BrainAge Connect') { $ready = $true; break }
    } catch { }
}
if (-not $ready) { throw ('API failed to start. Check runtime/' + $mode + '.stderr.log') }
Write-Host ('Ready: ' + $apiUrl)
if ($Demo) { Write-Host 'Demo login: demo.admin / DemoAdmin!2026' }
else { Write-Host 'Login credentials: docs/LOCAL_ACCESS.txt' }
Write-Host 'Runs in the background. Use STOP_PROJECT.cmd to stop project services.'
if ($OpenBrowser) { Start-Process $apiUrl }
