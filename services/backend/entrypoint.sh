#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z db 5432; do
    sleep 0.1
done

echo "PostgresSQL started"

python manage.py collectstatic --no-input
python manage.py makemigrations app
python manage.py migrate
gunicorn -b 0.0.0.0:8000 usr.src.app.backend.wsgi