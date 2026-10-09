@echo off
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt
echo Initializing alembic...
alembic init migrations
echo Done.
