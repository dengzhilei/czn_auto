@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto with Simplified Chinese templates.
echo Stop keys: F8, ESC, PAUSE, END
if exist "%~dp0CZNAuto.exe" (
  CZNAuto.exe --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language zh-Hans
) else (
  net session >nul 2>nul
  if errorlevel 1 (
    echo Source mode needs administrator permission for background window input.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
  )
  python czn_detector.py --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language zh-Hans
)
pause
