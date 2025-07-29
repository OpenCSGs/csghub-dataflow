@echo off
setlocal enabledelayedexpansion

for /f "delims=" %%u in ('powershell -Command "$uuid = [guid]::NewGuid().ToString(); Write-Output $uuid"') do set uuid=%%u

for /f "delims=" %%h in ('powershell -Command "$hostname = [System.Net.Dns]::GetHostName(); Write-Output $hostname"') do set hostname=%%h

set nodeName=worker_!uuid!@!hostname!

celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet -n %nodeName%