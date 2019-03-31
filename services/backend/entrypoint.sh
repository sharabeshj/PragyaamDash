#!/bin/sh

# echo "Waiting for postgres..."
# echo $SQL_HOST $SQL_PORT

while ! nc -z $RDS_HOST 3306; do
    sleep 0.1
done

echo "Remote DB connected"

while ! nc -z $SQL_HOST $SQL_PORT; do
    sleep 0.1
done

echo "Postgres DB connected"

rm -rf app/migrations/
python manage.py collectstatic --no-input
python manage.py flush --no-input
python manage.py makemigrations app
python manage.py migrate --database=default
gunicorn -b 0.0.0.0:8000 backend.wsgi:application
exec "$@"