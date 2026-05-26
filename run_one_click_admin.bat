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
echo Admin one-click test on monitor 1.
echo Stop keys: F8, ESC, PAUSE, END
python .\czn_auto\czn_detector.py --live --act --advance-on-unknown --fast-start-to-team --max-seconds 8 --max-clicks 1
pause
