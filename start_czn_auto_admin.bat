@echo off
setlocal
cd /d "%~dp0.."
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator permission for game input...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
del .\STOP 2>nul
echo Starting CZN Auto with background window input as administrator on monitor 1.
echo Stop keys: F8, ESC, PAUSE, END
echo Emergency kill: run czn_auto\stop_czn_auto.bat
python .\czn_auto\czn_detector.py --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales
pause
