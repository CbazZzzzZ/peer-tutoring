@echo off
cd /d "%~dp0"
docker compose exec -T db createdb -U peer peer_tutoring_test
echo Si la base de pruebas ya existe, se reutilizara SOLO esa base.
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://peer:peer_local_demo_only@db:5432/peer_tutoring_test web python -m pytest tests -v
pause
