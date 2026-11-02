@echo off
setlocal
cd /d "%~dp0"
set "TAPO_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%TAPO_PYTHON%" set "TAPO_PYTHON=python"

"%TAPO_PYTHON%" -c "import sys; assert sys.version_info >= (3, 12); import tkinter; from zoneinfo import ZoneInfo; ZoneInfo('Europe/Madrid')" >nul 2>&1
if errorlevel 1 goto prerequisites

for /f "delims=" %%P in ('call "%TAPO_PYTHON%" -c "import sys;print(sys.base_prefix)"') do set "TAPO_BASE=%%P"
if not defined TAPO_BASE goto prerequisites
if exist "%TAPO_BASE%\tcl\tcl8.6\init.tcl" set "TCL_LIBRARY=%TAPO_BASE%\tcl\tcl8.6"
if exist "%TAPO_BASE%\tcl\tk8.6\tk.tcl" set "TK_LIBRARY=%TAPO_BASE%\tcl\tk8.6"

"%TAPO_PYTHON%" "%~dp0scripts\tapo_exportacion\app.py"
if errorlevel 1 goto failed
exit /b 0

:prerequisites
echo No se pudo preparar Tapo Data. Necesitas Python 3.12 o posterior, Tkinter y tzdata.
echo Consulta la seccion "Primeros pasos" del README para preparar el entorno.
pause
exit /b 1

:failed
echo No se pudo iniciar Tapo Data. Comprueba el mensaje anterior y el README.
pause
exit /b 1
