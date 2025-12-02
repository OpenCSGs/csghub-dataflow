@echo off
setlocal enabledelayedexpansion

echo Checking and stopping all celery processes...
powershell -Command "Get-Process | Where-Object {$_.ProcessName -eq 'python' -or $_.ProcessName -eq 'pythonw'} | ForEach-Object { $cmdLine = (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine; if ($cmdLine -match 'celery') { Write-Host \"Stopping celery process: PID $($_.Id)\"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } }"
timeout /t 2 /nobreak >nul
echo Celery processes check completed.

for /f "delims=" %%u in ('powershell -Command "$uuid = [guid]::NewGuid().ToString(); Write-Output $uuid"') do set uuid=%%u

for /f "delims=" %%h in ('powershell -Command "$hostname = [System.Net.Dns]::GetHostName(); Write-Output $hostname"') do set hostname=%%h

set nodeName=worker_!uuid!@!hostname!
celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet -n %nodeName%
