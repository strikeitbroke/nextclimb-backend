#!/bin/sh
set -e

# Run migration
python manage.py migrate

python manage.py runserver 0.0.0.0:8000
