@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto minimal loop.
echo Stop keys: F8, ESC, PAUSE, END
CZNAuto.exe --live --act --advance-on-unknown --fast-start-to-team
pause
