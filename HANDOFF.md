# GCTT Project Handoff

**Audience:** Antigravity Gemini 3.8 Flash  
**Repository:** `faizanali-ai/gctt`  
**Current branch:** `main`  
**Current deployed commit:** `13d1718` — merge of the dark-logo variants  
**Production:** https://gctekton.com  
**Status:** deployed and live; this `HANDOFF.md` is the only local modification

---

## 1. Project overview and purpose

GCTT is a Django 5.2 website for Global Center for Technology & Training, a
technology staffing, recruitment and training company in Irving, Texas.

The site has three main surfaces:

1. Public marketing, careers, training and enquiry pages.
2. Candidate/student portal for applications, registrations, certificates and profile/security settings.
3. Admin/staff portal for candidate records, staff queues, content, users, audit history and site settings.

Production constraints:

- Render Free web service, 512 MB RAM, 2 Gunicorn workers.
- Neon Postgres free tier; compute may suspend when idle.
- Resend HTTPS API for email; Render Free blocks outbound SMTP.
- Supabase Storage is the production media backend; R2 remains supported.
- No paid Render shell. Use a one-off job or a local command against the production database.

The app handles PII: résumés, applications, registrations, enquiries and account records. Treat backups, media and database access as sensitive.

---

## 2. Current status and working state

- `main` is synced with `origin/main`; only this handoff file is locally modified.
- Latest deployed commit: `13d1718` (merge PR #3, dark logo variants).
- CI is green; the `test` job passed for the latest merge.
- Production is live at `https://gctekton.com`.
- `/wake/` and `/healthz/` return 200.
- 301 tests pass on SQLite locally and on Postgres 16 locally (via Podman).
- Coverage is about 87% excluding tests; CI enforces 80%.
- `ruff`, Django check, migration check, contrast check, JS syntax and
  `check --deploy` pass.
- Render cold starts are real: a sleeping free service can take ~40 seconds to
  answer; it returned 200 after waking in the latest check.
- The previous deploy failure was fixed: Render’s generated 256-bit base64
  secret is shorter than the original 50-character minimum. The minimum is now
  32 characters.

---

## 3. Chronological summary of completed work

### Initial MVP and feature build

- `89d017c` — initial Django site: marketing pages, auth, careers, training,
  enquiries and Django admin.
- `48304f8` / `1910f01` — account types and staff portal; replaced an
  employer-facing portal with role-based internal staff access.
- `350d9d8` / `355ea4c` — email notifications, email verification,
  certificates, pagination, filters, team profiles, structured enquiry fields,
  sitemap, robots, JSON-LD, OG image and custom 404/500 pages.
- `80cb17e` / `d094aad` / `40e4910` — deployment prep, Postgres, storage,
  health checks, CI, proxy-aware rate limits, private UUID résumés, upload
  signature checks, audit log, Sentry and backups.
- `917c3c9` / `dd01228` / `f349b72` — moved to the free-tier Render + Neon +
  Resend + R2 stack and added Supabase Storage support.

### UI and access model rebuild

- `9e0d09e`, `9289ce1`, `cd561d3`, `3f1d09f` and related commits — rebuilt the
  UI around ink/copper tokens, self-hosted fonts, new public/auth/portal shells,
  staff queues and a unified admin shell.
- `053ff87` / `38650f6` / `a0d1b20` — consolidated roles, staff subgroups,
  access audit, visibility controls and security hardening.
- Django admin was removed. The portal at `/dashboard/` and `/manage/` is the
  only business-data UI.
- `278ab29` / `3322e6b` — portal CRUD for users, team, jobs, programmes,
  applications, registrations, enquiries, settings and audit history.
- `e6ad272` — metadata, CSP nonces, theme toggle, legacy URL sunset, retention
  command, maintenance workflow and final UI polish.

### Email and authentication

- `0923d74` / `6103536` / `30106c5` — email OTP model, verification service,
  OTP-aware login routing and cleanup command.
- `0e52863` / `0bf13a8` — staff/admin email OTP login; candidates/students keep
  password login.
- `dc8ee04` / `4f81bfb` / `4652490` — Resend HTTPS backend, transactional and
  promotional email flows, welcome/enrollment/account notifications.
- Cloudflare was blocking Python’s default `urllib` User-Agent with HTTP 403
  error 1010. `4652490` added a stable `GCTT-Mailer/1.0` User-Agent. OTP sending
  then worked in production.
- OTP codes are hashed with Django’s password hasher, single-use, attempt-limited
  and TTL-limited. Staff/admin login requires OTP by default.

### Production hardening

- `2dba70f` — the 20-finding production-hardening pass:
  - owner-seeding migrations became no-ops; added `inspect_seeded_owner`;
  - inactive sessions are logged out;
  - console/dummy email is rejected for production web processes;
  - empty/short secret keys rejected;
  - admin user validation, guest phone length and registration-note bounds;
  - PDF-only résumés;
  - one-click unsubscribe;
  - PDF caching/rate limiting;
  - Resend idempotency keys;
  - admin email-change re-verification;
  - pending-email cooldown;
  - backup file permissions;
  - repair command direct-permission cleanup;
  - Postgres CI, migration check, dependency audit and coverage gate;
  - storage-aware/manual maintenance workflow;
  - manifest static storage, stale-doc/dead-code cleanup and logo refresh.
- `9e07ce2` — accept Render’s generated secret length (minimum now 32
  characters, 50+ recommended).
- `5096ddb` — theme-aware dark logo PNGs for header, footer, auth, portal,
  mobile drawer, 500 page and email header.
- `13d1718` — merge of the dark-logo PR.

### Logo/vector attempts not integrated

- Stitch was tested. It generated an approximate “GCTT” logo sheet, not the
  actual GCT mark, and clipped the horizontal tagline. It was not integrated.
- A VTracer SVG of the checkerboard image was inspected. It contains ~2,902
  paths and traces the checkerboard as vector background. Background paths can
  be removed to recover usable dark-theme traces, but they are still auto-traced,
  larger, and imperfect. They were not integrated.
- Current production logos are the supplied light and dark PNGs with matching
  plates. Light artwork is on white plates; dark artwork is on dark plates.
  There is no true transparent vector logo yet.

---

## 4. Key decisions, assumptions and constraints

### Stack

- Django 5.2, Python 3.12.8.
- Render Free web service in Oregon; Gunicorn gthread, 2 workers × 2 threads.
- Neon Postgres with pooled connection; `conn_max_age=600` and
  `CONN_HEALTH_CHECKS=True`.
- Resend HTTPS email; no SMTP on Render Free.
- Supabase Storage primary; R2 optional. Production rejects FileSystemStorage
  for web processes.
- GitHub Actions for CI, keepalive and maintenance.

### Access model

- Roles: `admin`, `staff`, `candidate`, `student`.
- Staff must have exactly one subgroup: `Recruiter`, `Trainer` or
  `Enquiry Manager`.
- Admin is the only user manager and content manager.
- Staff see only their own queue; candidates/students see only their own records.
- Django admin is not installed.
- Staff/admin login requires email OTP by default.
- `REQUIRE_EMAIL_OTP=0` is an emergency fallback only.

### Email

- Resend API key is environment-only.
- `EMAIL_BACKEND=config.email_backends.ResendEmailBackend`.
- Transactional email is sent synchronously with one retry and an idempotency key.
- Promotional email requires double opt-in.
- One-click unsubscribe is supported through a signed POST endpoint.
- `REQUIRE_VERIFIED_EMAIL_ACTIONS` is off by default; enable it only after
  auditing existing unverified candidates/students.

### Uploads and certificates

- Résumés are PDF-only, max 5 MB, signature-checked and stored privately.
- Certificates are generated on demand with WeasyPrint and cached/rate-limited.
- Certificate download requires login and role-appropriate access.
- Public certificate verification shows programme/validity, not holder identity.

### Owner and migrations

- The owner account is `mohdfaizanali038@gmail.com`. Do not delete it.
- Historical migrations `0008` and `0009` are no-ops for fresh databases.
  Existing production already applied them; do not re-add account seeding.
- Run `inspect_seeded_owner` before deleting any legacy account. No automatic
  deletion is implemented.

### Static assets

- Production uses `CompressedManifestStaticFilesStorage`; hashed URLs are served.
- `static/css/input.css` must be excluded from `collectstatic` because it imports
  Tailwind; build commands use `--ignore=input.css`.
- Rebuild `static/css/output.css` after template/style changes.

---

## 5. Files and modules

### Configuration

- `config/settings.py` — env handling, security headers, secret/email/storage
  guards, database/cache, static/manifest storage, OTP and verification flags.
- `config/urls.py` — public, auth, portal, staff, legacy, sitemap and health routes.
- `config/middleware.py` — CSP/security headers, inactive-user logout, legacy URL sunset.
- `config/ratelimit.py` — Render-aware client IP helper.
- `config/views.py` — `/wake/`, `/healthz/`, static page helpers.
- `config/site.py` — cached editable company identity.
- `config/context_processors.py`, `config/constants.py`, `config/legacy.py`,
  `config/sitemaps.py`.
- `config/email_backends.py` — Resend HTTPS backend with User-Agent and idempotency.
- `config/emails.py` — single transactional/promotional email service.

### Accounts

- `apps/accounts/models.py` — custom User, roles/groups, SiteSettings, EmailOTP,
  TeamProfile, AuditLog.
- `apps/accounts/forms.py` — signup, profile, team, site settings and auth forms.
- `apps/accounts/views.py` — auth, OTP, Google OAuth, dashboards, user/team/content
  management, account deletion, promotional opt-in/unsubscribe.
- `apps/accounts/email_otp.py` — hashed OTP issue/verify/purge.
- `apps/accounts/pending.py` — hashed 24-hour guest continuation tokens.
- `apps/accounts/tokens.py` — email verification token.
- `apps/accounts/decorators.py` — staff access guard.
- `apps/accounts/audit.py` — best-effort audit logging.
- `apps/accounts/apps.py` — role/group permission assignment.
- Migrations `0001`–`0014`; `0008`/`0009` are intentional no-ops.
- Commands: `audit_access`, `backup_db`, `check_legacy_urls`, `check_storage`,
  `inspect_seeded_owner`, `purge_email_otp`, `purge_pending`, `purge_retention`,
  `repair_internal_accounts`, `seed_demo`, `send_promotional`, `test_email`.

### Jobs

- `apps/jobs/models.py` — Job, Application, PendingApplication; PDF-only résumés;
  private file cleanup signals.
- `apps/jobs/forms.py` — job and application forms; PDF magic-byte check.
- `apps/jobs/views.py` — job list/detail/apply, guest continuation, staff queues,
  status/bulk/delete, LinkedIn posting.
- `apps/jobs/linkedin.py` — optional LinkedIn organisation posting.
- Migrations `0001`–`0007`; `0007` changes résumé validators to PDF-only.

### Training

- `apps/training/models.py` — Category, Programme, Registration,
  PendingRegistration.
- `apps/training/forms.py` — programme/category/registration/inbound enrollment.
- `apps/training/views.py` — public programmes, advisor API, registration,
  guest confirmation, staff queues, certificate issue/revoke/download.
- `apps/training/certificates.py` — WeasyPrint certificate generation.
- `apps/training/ai_advisor.py` — static career-track advisor content.
- Migrations `0001`–`0006`.

### Enquiries

- `apps/enquiries/models.py`, `forms.py`, `views.py`, `urls.py` — public enquiry
  capture with honeypot and staff queue/status/delete.

### Templates and assets

- `templates/base.html` — public shell, metadata, favicon, manifest assets.
- `templates/partials/_header.html`, `_footer.html`, `_field.html`,
  `_messages.html`, `_theme_toggle.html`, hero/art partials.
- `templates/accounts/*` — auth, OTP, profile, security, dashboards,
  unsubscribe/opt-in.
- `templates/portals/*` — admin/portal shell, users, settings.
- `templates/staff/*` — jobs, applications, categories, programmes,
  registrations, enquiries, team, audit.
- `templates/jobs/*`, `templates/training/*`, `templates/pages/*`,
  `templates/emails/*`, `templates/404.html`, `templates/500.html`,
  `templates/robots.txt`.
- `templates/emails/_logo.html` — dark horizontal email logo.
- `static/css/input.css` / `output.css` — design tokens, components, theme logos,
  compiled CSS.
- `static/js/ui.js`, `theme-init.js`.
- `static/images/logo-horizontal.png`, `logo-main.png`, `logo-stacked.png`,
  `logo-horizontal-dark.png`, `logo-main-dark.png`, `logo-stacked-dark.png`,
  `logo-icon-512.png`, `og-gctt-v3.jpg`, `icons.svg`, `google.svg`.
- `static/fonts/*` — self-hosted Inter, Space Grotesk, JetBrains Mono and OFL files.
- Removed: `static/images/logo-icon.svg`.

### Tests

31 test files, 301 tests. Main coverage areas: smoke/public pages, auth/OTP,
roles/access visibility, candidate privacy, account enumeration, admin/portal
CRUD, email service/Resend, pending submissions, retention, legacy URLs,
hardening, UI system, theme, site settings, Google OAuth, production hardening.

### CI/CD and docs

- `.github/workflows/ci.yml` — Postgres 16, CSS freshness, JS syntax, contrast,
  ruff, Django check, migration check, pip-audit, coverage (80%), deploy check.
- `.github/workflows/keepalive.yml` — fails on non-200 `/wake/`.
- `.github/workflows/maintenance.yml` — dry-run schedule, manual
  `confirm_apply=apply`, storage verification, OTP/session cleanup.
- `render.yaml` — Render build/start/env, manifest static, gthread.
- `Procfile`, `runtime.txt`, `.env.example`, `pyproject.toml`, `uv.lock`,
  `.gitignore`.
- Docs: `README.md`, `DEPLOY.md`, `RUNBOOK.md`, `DESIGN.md`, `HANDOFF.md`.
- Deleted: stale `gctt-django-master-plan.md`, `DESIGN_SYSTEM_RULES.md`,
  dead `apps/*/admin.py`, stale `test_smtp.py`.

---

## 6. Setup, run, build and test

### Local setup

```bash
uv sync
DJANGO_DEBUG=1 uv run python manage.py migrate
DJANGO_DEBUG=1 uv run python manage.py createsuperuser --email local-admin@gctt.local
DJANGO_DEBUG=1 uv run python manage.py runserver
```

### CSS build

```bash
./tailwindcss -i static/css/input.css -o static/css/output.css --minify
```

The Tailwind binary is downloaded separately on CI at v4.3.5 and is gitignored.
Production `collectstatic` must exclude the source file:

```bash
DJANGO_DEBUG=0 uv run python manage.py collectstatic --noinput --ignore=input.css
```

### Tests and checks

```bash
uv run ruff check .
DJANGO_DEBUG=1 uv run python manage.py check
DJANGO_DEBUG=1 uv run python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=1 uv run python manage.py test tests
DJANGO_DEBUG=1 uv run python scripts/check_contrast.py
node --check static/js/ui.js
node --check static/js/theme-init.js
```

### Coverage, audit and deploy check

```bash
DJANGO_DEBUG=1 uv run coverage run manage.py test tests
uv run coverage report --omit='tests/*' --fail-under=80
uv run pip-audit
DJANGO_DEBUG=0 DJANGO_SECRET_KEY='<long-random>' \
  DJANGO_ALLOWED_HOSTS='gctekton.com' \
  DJANGO_CSRF_TRUSTED_ORIGINS='https://gctekton.com' \
  DATABASE_URL='<postgres-url>' \
  uv run python manage.py check --deploy
```

### Postgres parity test

```bash
DJANGO_DEBUG=0 \
DJANGO_SECRET_KEY='<ci-secret>' \
DATABASE_URL='postgresql://user:pass@host:5432/db' \
uv run python manage.py test tests
```

### Production deploy

Render builds with:

```bash
uv sync --frozen --no-dev
uv run python manage.py collectstatic --noinput --ignore=input.css
```

Render starts with:

```bash
uv run python manage.py migrate --noinput
uv run python manage.py createcachetable
uv run gunicorn config.wsgi --bind 0.0.0.0:$PORT \
  --worker-class gthread --workers 2 --threads 2 --timeout 120
```

---

## 7. Known issues, bugs, limitations and unfinished work

1. **No true transparent SVG logo.** Current light and dark PNGs are opaque and
   sit on matching plates. Stitch and VTracer attempts were rejected because
   they approximated or traced the checkerboard.
2. **Footer contrast nuance.** In dark mode the `.ink-band` footer becomes light,
   so the dark stacked logo sits on a dark plate on a light footer. It works but
   is visually inverse.
3. **WeasyPrint on Render not fully verified.** Local PDF generation works; a
   real certificate download on the deployed Render runtime still needs a check.
4. **Maintenance storage deletion not exercised.** The workflow can delete
   Supabase/R2 objects only when the production storage secrets are present.
   `check_storage` must pass before manual apply.
5. **No production owner audit run.** `inspect_seeded_owner` exists but has not
   been run against production.
6. **No automated pre-apply database backup.** Maintenance relies on Neon PITR
   plus the manual `confirm_apply=apply` gate.
7. **Sentry/alert delivery not configured.** `SENTRY_DSN` is optional; no
   external alert channel is wired.
8. **Legacy `django-otp` tables remain.** TOTP is disabled but the tables are
   kept for rollback; `qrcode` was removed.
9. **Unused/deferred model fields.** `Programme.image_url` and
   `TeamProfile.photo_url` remain but are not part of the current public design.
10. **No one-click unsubscribe test in production.** The endpoint is covered by
    tests and returns 400 for invalid tokens, but a real mailbox-provider POST
    has not been verified.
11. **Email delivery receipt not independently confirmed.** OTP send was
    accepted in production, but the inbox was not read by the agent.
12. **Cold starts.** Render Free can take ~40 seconds to wake after sleep.
13. **Word résumés are intentionally rejected.** PDF-only is a security choice;
    if Word is required, malware scanning must be added first.
14. **No project license file.** Dependency/license checks are not automated
    beyond `pip-audit`.

---

## 8. Recommended next steps

1. Run `uv run python manage.py inspect_seeded_owner` against production.
   Keep `mohdfaizanali038@gmail.com`; remove only reviewed duplicates, with a
   Neon snapshot first.
2. Log in as a student, issue a certificate as staff, and download the PDF on
   deployed Render to verify WeasyPrint.
3. Set production storage secrets, run `check_storage`, run maintenance dry-run,
   then one controlled `confirm_apply=apply`; confirm the résumé object is gone.
4. Configure Sentry and an alert destination; test a 500 and an email failure.
5. Decide on the logo path:
   - obtain a true transparent vector/SVG from VectorCraft or a designer, or
   - accept the current themed PNG plates, or
   - use a cleaned trace as a temporary fallback and document it.
6. Run a complete production smoke test: signup, verification, OTP, job apply,
   guest continuation, training registration, certificate, unsubscribe.
7. Decide whether to enable `REQUIRE_VERIFIED_EMAIL_ACTIONS=1` after auditing
   existing unverified accounts.
8. Remove `django-otp` tables and unused model fields only in a dedicated,
   backed-up migration.
9. Consider consolidating duplicated `_mask_email`/`_notify_safely` helpers.
10. Add a project license and a dependency/license check if the repo will be
    distributed.

---

## 9. Open questions / confirmation needed

1. Is `mohdfaizanali038@gmail.com` the permanent owner account? Should its
   password be rotated now?
2. Was `ceo@gctekton.com` ever a real account? If yes, restore it from a backup;
   if not, leave it deleted.
3. Do we want true transparent vector logos, or are the current light/dark PNG
   plates acceptable?
4. Should the footer use the light logo in dark mode instead of the dark stacked
   logo on a light inverse band?
5. Should `REQUIRE_VERIFIED_EMAIL_ACTIONS` be enabled, and when?
6. Should Word résumés be supported with a malware scanner, or stay PDF-only?
7. Is Supabase definitely the active production media backend (not R2)?
8. Which alert channel should receive production failures?
9. Should maintenance ever run `--apply` automatically, or stay manual?
10. Should legacy TOTP tables and unused `image_url`/`photo_url` fields be
    removed in the next maintenance release?

---

## 10. Context for Antigravity Gemini 3.8 Flash

- Work on `main`; it is protected and requires the `test` check. Create a
  feature branch and PR; do not force-push or delete `main`.
- Do not redo the completed hardening. Read this file, `README.md`,
  `RUNBOOK.md`, `DEPLOY.md` and `DESIGN.md` before changing behavior.
- Never commit real secrets. `.env` is ignored; `RESEND_API_KEY`, database URLs,
  storage keys and `DJANGO_SECRET_KEY` are environment-only.
- Keep the production minimum secret length at 32 characters. Do not raise it
  back to 50 without verifying Render’s generated value; the last deploy failed
  for that reason.
- The owner account must not be deleted. Do not add account-seeding code to
  migrations.
- Production media must be remote. FileSystemStorage is rejected for web
  processes; maintenance must run with Supabase/R2 secrets to delete objects.
- Use `collectstatic --ignore=input.css`; `input.css` is source only.
- Rebuild `output.css` after template/style changes. Run the full checklist
  before pushing.
- The current logo implementation is `.logo-light` / `.logo-dark` with
  `data-theme="dark"` and OS `prefers-color-scheme` fallback. The dark assets
  are opaque PNGs with matching plates. Stitch/VTracer/SVG experiments are not
  integrated.
- Production is live, but Render Free sleeps. A 40-second timeout on the first
  request is not necessarily an outage; retry before diagnosing.
- The last known good deploy is merge `13d1718`. Any new deploy should be a PR
  with green `test` CI and a fresh Neon PITR snapshot before migrations or
  destructive maintenance.
