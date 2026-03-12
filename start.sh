#!/bin/bash
set -e

. /opt/venv/bin/activate

if [ "${APP_ENV:-}" = "production" ] || [ "${DJANGO_ENV:-}" = "production" ] || [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
  echo "Skipping migrations."
else
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Starting Daphne (ASGI)..."
exec daphne -b 0.0.0.0 -p 8050 core.asgi:application
