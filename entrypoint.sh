python manage.py migrate
python manage.py createsuperuser --noinput
python manage.py collectstatic --no-input --clear
gunicorn app.wsgi:application --workers=2 --log-level=info --bind 0.0.0.0:80
