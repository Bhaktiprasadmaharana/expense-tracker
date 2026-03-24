#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd expense_tracker
python manage.py collectstatic --no-input
python manage.py migrate
