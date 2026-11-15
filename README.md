# GCTT — Django site

Marketing site, careers, training registrations and enquiries for GCTT.

## Run

Debug is off by default; enable it for local development:

```bash
uv sync
DJANGO_DEBUG=1 uv run python manage.py migrate
DJANGO_DEBUG=1 uv run python manage.py createsuperuser
DJANGO_DEBUG=1 uv run python manage.py runserver
```

CSS is precompiled to `static/css/output.css`. Rebuild after template/style changes:

```bash
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64 && mv tailwindcss-linux-x64 tailwindcss
./tailwindcss -i static/css/input.css -o static/css/output.css --minify
```

## Test

```bash
uv run python manage.py test tests
uv run ruff check .
```

## Deploy (Railway + Neon + R2 + Resend)

1. Create a Neon Postgres database and copy its connection string.
2. Create a Railway project from this repo; add the variables from `.env.example`
   (`DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `R2_*`).
3. Railway runs `Procfile`: release migrates + collects static; web serves via gunicorn.
4. Point your domain's DNS at Railway, then add the domain to `DJANGO_ALLOWED_HOSTS`
   and `DJANGO_CSRF_TRUSTED_ORIGINS`.
5. Health check endpoint: `/healthz/`.

Media files go to R2 only when `R2_BUCKET` is set; otherwise they stay on local disk.
Email stays on the console backend until `EMAIL_BACKEND` is set to SMTP.

