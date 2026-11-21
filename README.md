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

CSS is precompiled to `static/css/output.css` and committed. Rebuild after any template or style change:

```bash
curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.5/tailwindcss-linux-x64
chmod +x tailwindcss
./tailwindcss -i static/css/input.css -o static/css/output.css --minify
```

The pin matches CI, which rebuilds and fails if `output.css` is stale. `tests/test_ui_system.py` also checks that the compiled file contains the utilities the interface relies on, so rebuild before running tests.

## UI

The design system is documented in [`DESIGN.md`](DESIGN.md). In short:

- Ink neutrals, one copper accent, system dark mode (no toggle).
- Space Grotesk + Inter + JetBrains Mono, self-hosted in `static/fonts/` (SIL OFL).
- One icon sprite, one vanilla JS file, no front-end framework or CDN.
- Marketing shell in `templates/base.html`, auth shell in `templates/accounts/base_auth.html`, portal shell in `templates/portals/base_portal.html`.
- Templates must use tokens and components, not hardcoded colours; the UI test enforces it.

## Local login

There is **no committed local password or user fixture**. Create a local admin interactively:

```bash
DJANGO_DEBUG=1 uv run python manage.py createsuperuser
```

Or non-interactively:

```bash
DJANGO_DEBUG=1 DJANGO_SUPERUSER_PASSWORD='choose-a-local-password' \
  uv run python manage.py createsuperuser --noinput --email local-admin@gctt.local
```

Sign in at `/accounts/login/` (portal) or `/admin/login/`. Keep `REQUIRE_EMAIL_OTP=0` for password-only staff/admin login; it defaults to `0`. `seed_demo` creates sample jobs and programmes only, not users. Never reuse local credentials in production.

## Admin dashboard

Admins use the portal at `/dashboard/`, not Django admin:

- **Users & roles** — every account type (Admin, Staff, Candidate, Training Student), designation editing, activation, email verification, password reset and deletion.
- **Team profiles** — About-page people, including designation, bio, photo URL and visibility.
- **Mandates, Programmes, Categories** — create, edit, publish and delete public content.
- **Applications, Registrations, Enquiries** — review records, change status, issue/revoke certificates and delete.
- **Audit log** — read-only record of changes.

Django admin remains at `/admin/` as a break-glass tool for superusers. Non-admin staff who open `/admin/login/` are sent to the portal instead of being looped back to the login form.

If accounts were created before the designation fix, repair internal flags once:

```bash
uv run python manage.py repair_internal_accounts          # dry run
uv run python manage.py repair_internal_accounts --apply  # write
```

## Test

```bash
uv run python manage.py test tests
uv run ruff check .
uv run python scripts/check_contrast.py
node --check static/js/ui.js
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

- **Internal email OTP** — set `REQUIRE_EMAIL_OTP=1` to require an email code for admin/staff logins. Keep it at `0` as the password-only fallback until email delivery is verified. Candidates/students keep normal password login.
- **No authenticator app** — TOTP login and enrollment are disabled. Old 2FA URLs redirect to login; existing authenticator tables are kept for rollback only.
- **Email OTP delivery** — requires a verified Resend domain and working SMTP. Configure `EMAIL_OTP_TTL_SECONDS`, `EMAIL_OTP_MAX_ATTEMPTS`, and `EMAIL_OTP_RESEND_SECONDS`; run `manage.py purge_email_otp` periodically.
- **Audit log** — staff actions (application/registration/enquiry status, job publishing, programme toggles, certificates) are recorded and visible read-only in Django Admin → Audit log entries.
- **Error monitoring** — set `SENTRY_DSN` to report exceptions.
- **Backups** — enable point-in-time recovery on Neon, enable object versioning on the R2 bucket, and take a periodic dump: `pg_dump "$DATABASE_URL" > backup-$(date +%F).sql`.


