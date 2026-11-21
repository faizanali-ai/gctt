# GCTT — Django site

Marketing site, careers, training registrations and enquiries for GCTT.

## Access levels & visibility

- **Admin** (`role=admin`) — merged CEO/owner/superadmin level. Only admins can list users, see account totals or subgroup membership, manage accounts.
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

- Ink neutrals, one copper accent.
- Space Grotesk + Inter + JetBrains Mono, self-hosted in `static/fonts/` (SIL OFL).
- One icon sprite, one vanilla JS file (plus the pre-paint theme script), no front-end framework or CDN.
- Marketing shell in `templates/base.html`, auth shell in `templates/accounts/base_auth.html`, portal shell in `templates/portals/base_portal.html`.
- Light/dark toggle in the shared header, auth header and portal header; OS default until the visitor chooses.
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

Sign in at `/accounts/login/` (portal). Staff/admin logins require an email code by default (`REQUIRE_EMAIL_OTP=1`); locally the code is printed to the console when no Resend key or SMTP host is configured. Set `REQUIRE_EMAIL_OTP=0` only for a deliberate password-only fallback. `seed_demo` creates sample jobs and programmes only, not users. Never reuse local credentials in production.

## Admin dashboard

Admins use the portal at `/dashboard/`:

- **Users & roles** — every account type (Admin, Staff, Candidate, Training Student), designation editing, activation, email verification, password reset and deletion.
- **Team profiles** — About-page people, including designation, bio, photo URL and visibility.
- **Mandates, Programmes, Categories** — create, edit, publish and delete public content.
- **Applications, Registrations, Enquiries** — review records, change status, issue/revoke certificates and delete.
- **Audit log** — read-only record of changes.
- **Site settings** — company name, legal name, contact addresses and home-hero copy. Other page copy stays in templates.

Django admin has been removed. All user, team, audit, content and site-settings data is managed in the portal. For emergency database recovery use the management commands and backups described in `RUNBOOK.md`.

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
+ **Supabase Storage** or **Cloudflare R2** (private media) + **GitHub Actions** (CI, free minutes).

1. Create a Neon project (free plan, no expiry) and copy the **pooled** connection
   string (`...-pooler...`) — it becomes `DATABASE_URL`.
2. In Render, **New → Blueprint**, point it at this repo. `render.yaml` provisions the
   free web service; fill the `sync: false` variables when prompted:
   `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS` (e.g. `gctt.onrender.com`),
   `DJANGO_CSRF_TRUSTED_ORIGINS` (`https://gctt.onrender.com`), the Resend API key,
   and the R2 keys or the complete Supabase storage set.
3. The start command runs `migrate`, `createcachetable`, `collectstatic` and gunicorn
   on every boot — no paid release phase needed.
4. Verify `/wake/` returns `ok` (liveness) and `/healthz/` returns `ok`, then create the admin account with a Render one-off job or locally against the production database:
   `uv run python manage.py createsuperuser --email <owner-email>`.
5. Optional custom domain: add it in Render, then append it to
   `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`; DNS is free on Cloudflare.

Free-tier realities (plan for them):

- The Render service **sleeps after 15 minutes** of inactivity; the first request
  afterwards takes ~30–60s. Neon also suspends idle compute (~0.5s wake).
- 512 MB RAM — fine for this app; PDF generation runs one request at a time.
- Resend free allows 3,000 emails/month (100/day).
- R2 free allows 10 GB storage with free egress (a payment method is required to
  activate R2, but usage within the free tier costs $0).
- Render free has **no persistent disk** — media must go to R2 or Supabase. The
  app refuses to start gunicorn in production with FileSystemStorage.
- The GitHub keepalive calls `/wake/`, which does not touch the database, so a
  free Neon compute can still scale to zero.

Railway/paid hosts still work unchanged via `Procfile` if you outgrow the free tier.


## Operations

- **Internal email OTP** — every staff and admin account requires an email code at login; this is enabled by default. Candidates/students keep normal password login. Set `REQUIRE_EMAIL_OTP=0` in Render only for an emergency password-only fallback.
- **Email confirmation** — new training registrations are created only after the student confirms the emailed link; staff/admin accounts never use magic links.
- **Welcome email** — sent once after the first successful login. Existing users are backfilled so they do not receive a retroactive welcome.
- **Enrollment email** — sent when a training registration is confirmed; it is transactional and cannot be opted out of.
- **Promotional email** — double opt-in only. Users request offers on signup or in their profile, then must click a confirmation link. Use `uv run python manage.py send_promotional --subject "..." --body-file campaign.txt` to preview; add `--send` to deliver. The command defaults to 50 recipients, one second between messages, and prints a `--after-id` bookmark so the next run continues without resending the first batch.
- **Unsubscribe** — every promotional email includes signed confirmation and RFC 8058 one-click unsubscribe links. They work without signing in and never affect transactional mail.
- **Account security email** — changing a password or email address, or deleting an account, sends a notification email. These are transactional and cannot be opted out of.
- **No authenticator app** — TOTP login and enrollment are disabled. Old 2FA URLs redirect to login; existing authenticator tables are kept for rollback only.
- **Email OTP delivery** — requires a verified Resend domain and `RESEND_API_KEY`. Email is sent through Resend’s HTTPS API, which works on Render Free. Configure `EMAIL_OTP_TTL_SECONDS`, `EMAIL_OTP_MAX_ATTEMPTS`, and `EMAIL_OTP_RESEND_SECONDS`; run `manage.py purge_email_otp` periodically.
- **Email templates** — new transactional and promotional mail lives in `templates/emails/`, with HTML and plain-text versions. Existing transactional messages in `config/emails.py` are unchanged.
- **Email provider variables** — configure `EMAIL_BACKEND=config.email_backends.ResendEmailBackend`, `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL`, and `SITE_URL` (public origin used in email links). `RESEND_API_KEY` must never be committed. `EMAIL_SEND_RETRIES` (default 1) and `EMAIL_RETRY_DELAY_SECONDS` (default 0.5) control short retry behaviour, and Resend requests carry an idempotency key. SMTP variables remain only for local or paid-host fallback; production web processes refuse the console/dummy email backend.
- **Verified-email actions** — set `REQUIRE_VERIFIED_EMAIL_ACTIONS=1` after auditing existing accounts to require email verification for job applications and programme registrations. It is off by default to avoid locking out existing users.
- **Résumés** — uploads are PDF-only, size-limited, and content-signature checked. Office documents are rejected because they can carry macros and are not malware-scanned.
- **Email test mode** — tests use Django’s `locmem` backend; local development prints email to the console when no Resend key or SMTP host is configured. Use Resend’s test mode or a controlled mailbox in staging; do not add a production redirect.
- **Audit log** — staff actions (application/registration/enquiry status, job publishing, programme toggles, certificates) are recorded and visible read-only at `/manage/audit/`.
- **Error monitoring** — set `SENTRY_DSN` to report exceptions.
- **Backups** — enable point-in-time recovery on Neon, enable object versioning on the R2 or Supabase bucket, and take a periodic `pg_dump "$DATABASE_URL" > backup-$(date +%F).sql`. Treat dumps as sensitive because they contain PII.


