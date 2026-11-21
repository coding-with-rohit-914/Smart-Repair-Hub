@echo off
REM One-shot backend setup & run (Windows)
cd /d "%~dp0backend"
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed
python manage.py runserver
