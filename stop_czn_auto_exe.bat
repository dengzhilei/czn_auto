@echo off
setlocal
cd /d "%~dp0"
type nul > .\STOP
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*CZNAuto.exe*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Stop signal sent.
pause
