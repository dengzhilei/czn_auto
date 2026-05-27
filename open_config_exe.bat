@echo off
setlocal
set "CONFIG_DIR=%~dp0"
set "CONFIG_FILE=%CONFIG_DIR%\config.json"
if not exist "%CONFIG_FILE%" (
  copy /y "%~dp0config.example.json" "%CONFIG_FILE%" >nul
)
start "" notepad "%CONFIG_FILE%"
