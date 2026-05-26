@echo off
setlocal
cd /d "%~dp0"

if not exist .venv-build (
  python -m venv .venv-build
)

call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt

python -m PyInstaller --clean --noconfirm czn_auto.spec

copy /y run_min_loop_exe.bat dist\CZNAuto\run_min_loop.bat >nul
copy /y run_one_click_exe.bat dist\CZNAuto\run_one_click.bat >nul
copy /y stop_czn_auto_exe.bat dist\CZNAuto\stop_czn_auto.bat >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\CZNAuto\*' -DestinationPath 'dist\CZNAuto-portable.zip' -Force"

where ISCC >nul 2>nul
if %errorlevel% equ 0 (
  ISCC installer\czn_auto.iss
) else (
  echo Inno Setup compiler ISCC was not found. Skipping installer build.
  echo Portable app is ready at: dist\CZNAuto
)

pause
