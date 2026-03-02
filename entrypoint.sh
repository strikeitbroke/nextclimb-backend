#!/bin/sh
set -e

# Run migration
python manage.py migrate

# Collect static files for Django admin
python manage.py collectstatic --noinput

python manage.py runserver 0.0.0.0:8000
