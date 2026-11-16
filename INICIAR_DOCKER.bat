@echo off
cd /d "%~dp0"
docker compose up -d --build --wait
if errorlevel 1 goto failed
docker compose exec -T web python manage.py seed
if errorlevel 1 goto failed
start "" http://127.0.0.1:5055
echo Peer Tutoring listo en http://127.0.0.1:5055
pause
exit /b
:failed
echo Revise que Docker Desktop este iniciado y que el puerto 5055 este libre.
pause
