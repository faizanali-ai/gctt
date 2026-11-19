# GCTT — Django site

Marketing site, careers, training registrations and enquiries for GCTT.

## Access levels & visibility

- **Admin** (`role=admin`) — merged CEO/owner/superadmin level. Only admins can list users, see account totals or subgroup membership, manage accounts, or use Django Admin.
- **Staff** (`role=staff`) — exactly one subgroup: `Recruiter`, `Trainer`, or `Enquiry Manager`. Staff see only their own account and their subgroup's work queue. They cannot discover other staff accounts or cross into another subgroup.
- **Candidate / Student** — external portal users. Candidates see their own applications; students see their own registrations. Neither can discover another external account.

Employers do not have accounts. Employer requests enter the enquiry queue and notify only the `Enquiry Manager` subgroup. Operational notifications are sent one recipient at a time; admins are not default recipients.

Certificate verification shows validity and programme only, never the holder's identity. Unauthorized certificate downloads return 404. Signup, guest applications, and guest registrations return the same generic "check your email" response for new and existing addresses.

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

## Deploy — 100% free tier

Stack: **Render** (web, free) + **Neon** (Postgres, free) + **Resend** (email, free)
+ **Cloudflare R2** (media, free within limits) + **GitHub Actions** (CI, free minutes).

1. Create a Neon project (free plan, no expiry) and copy the **pooled** connection
   string (`...-pooler...`) — it becomes `DATABASE_URL`.
2. In Render, **New → Blueprint**, point it at this repo. `render.yaml` provisions the
   free web service; fill the `sync: false` variables when prompted:
   `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` (e.g. `gctt.onrender.com`),
   `DJANGO_CSRF_TRUSTED_ORIGINS` (`https://gctt.onrender.com`), the Resend SMTP
   password, and the R2 keys.
3. The start command runs `migrate`, `createcachetable`, `collectstatic` and gunicorn
   on every boot — no paid release phase needed.
4. Verify `/healthz/` returns `ok`, then create the admin account:
   `uv run python manage.py createsuperuser` (Render shell) or via Django Admin invite.
5. Optional custom domain: add it in Render, then append it to
   `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`; DNS is free on Cloudflare.

Free-tier realities (plan for them):

- The Render service **sleeps after 15 minutes** of inactivity; the first request
  afterwards takes ~30–60s. Neon also suspends idle compute (~0.5s wake).
- 512 MB RAM — fine for this app; PDF generation runs one request at a time.
- Resend free allows 3,000 emails/month (100/day).
- R2 free allows 10 GB storage with free egress (a payment method is required to
  activate R2, but usage within the free tier costs $0).
- Render free has **no persistent disk** — media must go to R2 (the app refuses
  to rely on local disk in production only insofar as it is wiped on redeploy).

Railway/paid hosts still work unchanged via `Procfile` if you outgrow the free tier.


## Operations

- **Staff two-factor auth** — each staff member opens `/accounts/security/` once and scans the QR code with an authenticator app. After everyone has enrolled, set `REQUIRE_STAFF_2FA=1`; staff pages then require a verified session.
- **Audit log** — staff actions (application/registration/enquiry status, job publishing, programme toggles, certificates) are recorded and visible read-only in Django Admin → Audit log entries.
- **Error monitoring** — set `SENTRY_DSN` to report exceptions.
- **Backups** — enable point-in-time recovery on Neon, enable object versioning on the R2 bucket, and take a periodic dump: `pg_dump "$DATABASE_URL" > backup-$(date +%F).sql`.


