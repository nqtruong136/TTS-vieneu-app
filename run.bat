@echo off
chcp 65001 > nul
title VieNeu-TTS Studio

pushd "%~dp0"
set "APP_DIR=%CD%"
popd
cd /d "%APP_DIR%"

set "PYTHON_EXE=%APP_DIR%\.venv\Scripts\python.exe"
set "PYTHONW_EXE=%APP_DIR%\.venv\Scripts\pythonw.exe"
set "MAIN_SCRIPT=%APP_DIR%\main.py"

if exist "%PYTHONW_EXE%" goto :check_mode

:setup_venv
echo ======================================================
echo [THONG BAO] Dang khoi tao moi truong ao .venv...
echo ======================================================

set "UV_CMD=uv"
where uv >nul 2>nul
if %errorlevel% equ 0 goto :do_uv_install

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
    goto :do_uv_install
)

if exist "%LOCALAPPDATA%\bin\uv.exe" (
    set "UV_CMD=%LOCALAPPDATA%\bin\uv.exe"
    goto :do_uv_install
)

echo [LOI] Khong tim thay cong cu 'uv'. Vui long cai dat uv hoac Python 3.12.
pause
exit /b 1

:do_uv_install
"%UV_CMD%" venv "%APP_DIR%\.venv" --python 3.12
if %errorlevel% neq 0 (
    echo [LOI] Tao moi truong ao that bai!
    pause
    exit /b 1
)

echo [THONG BAO] Dang cai dat cac thu vien can thiet...
"%UV_CMD%" pip install --python "%PYTHON_EXE%" -r "%APP_DIR%\requirements.txt"
if %errorlevel% neq 0 (
    echo [LOI] Cai dat thu vien that bai!
    pause
    exit /b 1
)

:check_mode
if /i "%~1"=="--console" goto :run_console
if /i "%~1"=="--debug" goto :run_console

:run_gui
echo [INFO] Dang khoi dong VieNeu-TTS Studio...
start "" /d "%APP_DIR%" "%PYTHONW_EXE%" "%MAIN_SCRIPT%"
exit /b 0

:run_console
echo [INFO] Dang khoi dong VieNeu-TTS Studio (Che do Debug Console)...
"%PYTHON_EXE%" "%MAIN_SCRIPT%"
echo.
echo [INFO] Ung dung da dung. Nhan phim bat ky de dong...
pause > nul
exit /b 0