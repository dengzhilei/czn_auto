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

copy /y start_czn_auto_exe.bat dist\CZNAuto\start_czn_auto.bat >nul
copy /y start_czn_auto_mouse_exe.bat dist\CZNAuto\start_czn_auto_mouse.bat >nul
copy /y run_one_click_exe.bat dist\CZNAuto\run_one_click.bat >nul
copy /y stop_czn_auto_exe.bat dist\CZNAuto\stop_czn_auto.bat >nul
copy /y open_config_exe.bat dist\CZNAuto\open_config.bat >nul
copy /y config.example.json dist\CZNAuto\config.example.json >nul
copy /y config.example.json dist\CZNAuto\config.json >nul
copy /y CONFIG.md dist\CZNAuto\CONFIG.md >nul
copy /y README.md dist\CZNAuto\README.md >nul
xcopy /e /i /y templates dist\CZNAuto\templates >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\CZNAuto\*' -DestinationPath 'dist\CZNAuto-portable.zip' -Force"

set "ISCC_EXE="
where ISCC >nul 2>nul && set "ISCC_EXE=ISCC"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC_EXE (
  "%ISCC_EXE%" installer\czn_auto.iss
) else (
  echo Inno Setup compiler ISCC was not found. Skipping installer build.
  echo Portable app is ready at: dist\CZNAuto
)

pause
