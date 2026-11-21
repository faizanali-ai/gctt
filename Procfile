web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --worker-class gthread --workers 2 --threads 2 --timeout 120
release: python manage.py migrate --noinput && python manage.py createcachetable && python manage.py collectstatic --noinput --ignore=input.css
