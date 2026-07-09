@echo off
setlocal
cd /d %~dp0
set OUT=Program_Update_Commit_0002.zip
if exist %OUT% del %OUT%
powershell -NoProfile -Command "$m=@{update_type='program';version='0002';created=(Get-Date).ToString('s');description='Program files update'} | ConvertTo-Json; Set-Content -Encoding UTF8 update_manifest.json $m; Compress-Archive -Force -Path update_manifest.json,hub_app.py,launcher.py,main.py,manifest.json,app_version.json -DestinationPath %OUT%; Remove-Item update_manifest.json"
echo Created %OUT%
pause
