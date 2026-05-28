@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto with real mouse input.
echo Stop keys: F8, ESC, PAUSE, END
CZNAuto.exe --live --act --input-backend sendinput --advance-on-unknown --fast-start-to-team --wide-match-scales
pause
