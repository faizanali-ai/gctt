web: uv run gunicorn config.wsgi --bind 0.0.0.0:$PORT --worker-class gthread --workers 2 --threads 2 --timeout 120
release: uv run python manage.py migrate --noinput && uv run python manage.py createcachetable
