@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto with background window input.
echo Stop keys: F8, ESC, PAUSE, END
if not exist "%~dp0CZNAuto.exe" (
  net session >nul 2>nul
  if errorlevel 1 (
    echo Source mode needs administrator permission for background window input.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
  )
)
set "UI_LANGUAGE=auto"
if exist "%~dp0choose_ui_language.ps1" (
  for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0choose_ui_language.ps1"`) do set "UI_LANGUAGE=%%L"
)
if /i "%UI_LANGUAGE%"=="cancel" (
  echo Startup canceled.
  exit /b
)
echo UI language: %UI_LANGUAGE%
if exist "%~dp0CZNAuto.exe" (
  CZNAuto.exe --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language %UI_LANGUAGE%
) else (
  python czn_detector.py --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language %UI_LANGUAGE%
)
pause
