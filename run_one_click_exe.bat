@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto background one-click test.
echo Stop keys: F8, ESC, PAUSE, END
CZNAuto.exe --live --act --input-backend postmessage_activate --advance-on-unknown --fast-start-to-team --max-seconds 8 --max-clicks 1
pause
