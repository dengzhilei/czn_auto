@echo off
setlocal
cd /d "%~dp0.."
type nul > .\czn_auto\STOP
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*czn_detector.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Stop signal sent.
pause
