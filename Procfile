web: python manage.py collectstatic --noinput && python manage.py bootstrap_initial_users && gunicorn skillsence.wsgi:application --bind 0.0.0.0:$PORT
