@echo off
setlocal
cd /d "%~dp0"
echo Starting CZN Auto one-click test.
echo Target window: default CZN game window
echo Stop keys: F8, ESC, PAUSE, END
CZNAuto.exe --live --game-window --capture-method printwindow --click-method postmessage --no-postmessage-fallback-sendinput --act --advance-on-unknown --fast-start-to-team --max-seconds 8 --max-clicks 1
pause
