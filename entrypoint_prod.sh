#!/bin/bash
set -e

# NO 'exec' here.
# We want this to finish so the script can continue.
echo "Running migrations..."
python manage.py migrate --noinput

# USE 'exec' here.
# This is the final step. Uvicorn replaces the shell.
echo "Starting server..."
exec uvicorn core.asgi:application --host 0.0.0.0 --port 8000
