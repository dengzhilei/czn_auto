@echo off
setlocal EnableDelayedExpansion
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
set "REWARD_SETTLE=1.5"
if exist "%~dp0choose_ui_language.ps1" (
  set "CHOICE_LINE=0"
  for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0choose_ui_language.ps1"`) do (
    set /a CHOICE_LINE+=1
    if !CHOICE_LINE! EQU 1 set "UI_LANGUAGE=%%L"
    if !CHOICE_LINE! EQU 2 set "REWARD_SETTLE=%%L"
  )
)
if /i "%UI_LANGUAGE%"=="cancel" (
  echo Startup canceled.
  exit /b
)
echo UI language: %UI_LANGUAGE%
echo Reward settle before checking dream card: %REWARD_SETTLE%s
if exist "%~dp0CZNAuto.exe" (
  CZNAuto.exe --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language "%UI_LANGUAGE%" --reward-settle-before-action "%REWARD_SETTLE%"
) else (
  python czn_detector.py --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --wide-match-scales --ui-language "%UI_LANGUAGE%" --reward-settle-before-action "%REWARD_SETTLE%"
)
pause
