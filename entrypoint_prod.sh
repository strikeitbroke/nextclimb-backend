#!/bin/bash
set -e

# NO 'exec' here.
# We want this to finish so the script can continue.
echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# USE 'exec' here.
# This is the final step. Uvicorn replaces the shell.
echo "Starting server..."
exec uvicorn core.asgi:application --host 0.0.0.0 --port 8000
