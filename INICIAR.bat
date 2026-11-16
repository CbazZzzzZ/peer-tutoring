@echo off
setlocal
cd /d "%~dp0"
set "BUNDLED=C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe"
if exist ".packages\flask\__init__.py" if exist "%BUNDLED%" (
  set "PYTHONPATH=%CD%\.packages"
  set "RUNPY=%BUNDLED%"
  goto initialize
)
if exist ".venv-local\Scripts\python.exe" goto ready
where py >nul 2>nul
if errorlevel 1 (
  echo Instala Python 3.12 o superior desde python.org y vuelve a abrir este archivo.
  pause
  exit /b 1
)
py -3 -m venv .venv-local
if errorlevel 1 goto failed
.venv-local\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
:ready
set "RUNPY=%CD%\.venv-local\Scripts\python.exe"
:initialize
"%RUNPY%" manage.py init
if errorlevel 1 goto failed
"%RUNPY%" manage.py seed
if errorlevel 1 goto failed
start "" http://127.0.0.1:5055
echo Peer Tutoring: http://127.0.0.1:5055
echo Mantenga esta ventana abierta. Ctrl+C para detener.
"%RUNPY%" run.py
pause
exit /b
:failed
echo No se pudo iniciar. Revise el error anterior y README.md.
pause
