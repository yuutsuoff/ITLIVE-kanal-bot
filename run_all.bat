@echo off
call venv\Scripts\activate.bat

echo Checking database...
python create_db.py

echo Running migrations...
alembic upgrade head

echo Seeding database with initial questions...
python seed.py

echo Starting API server in background...
start uvicorn api.main:app --host 0.0.0.0 --port 8000

echo Starting Telegram Bot...
python -m bot.main
pause
