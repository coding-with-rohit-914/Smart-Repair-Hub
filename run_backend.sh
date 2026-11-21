#!/usr/bin/env bash
# One-shot backend setup & run (Linux/macOS)
set -e
cd "$(dirname "$0")/backend"
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed
python manage.py runserver
