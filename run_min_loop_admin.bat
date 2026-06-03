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
echo Admin minimal loop for default CZN game window.
echo Stop keys: F8, ESC, PAUSE, END
echo Emergency kill: run czn_auto\stop_czn_auto.bat
python .\czn_auto\czn_detector.py --live --game-window --capture-method printwindow --click-method postmessage --no-postmessage-fallback-sendinput --act --advance-on-unknown --fast-start-to-team --wide-match-scales
pause
