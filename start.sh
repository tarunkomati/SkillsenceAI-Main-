#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py bootstrap_initial_users

exec gunicorn skillsence.wsgi:application --bind 0.0.0.0:${PORT:-8000}
