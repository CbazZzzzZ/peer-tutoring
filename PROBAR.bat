@echo off
cd /d "%~dp0"
set "RUNPY=%CD%\.venv-local\Scripts\python.exe"
set "BUNDLED=C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe"
if exist ".packages\pytest\__init__.py" if exist "%BUNDLED%" (
  set "PYTHONPATH=%CD%\.packages"
  set "RUNPY=%BUNDLED%"
)
if not exist .test-runs mkdir .test-runs
"%RUNPY%" -m pytest tests -v --basetemp=.test-runs/run_%RANDOM%_%RANDOM%
pause
