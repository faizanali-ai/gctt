# GCTT — Django site

Marketing site, careers, training registrations and enquiries for GCTT.

## Run

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
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
