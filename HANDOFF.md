# GCTT Session Handoff — 2026-11-22
## Goal
Keep the GCTT production Django site on Render Free while making every transactional and promotional email deliverable. Render Free blocks outbound SMTP (25/465/587), so delivery now uses Resend's HTTPS API.

## Current State
- `main` at `f7f14a5`, synced with `origin/main`; only this `HANDOFF.md` is locally modified.
- 280 tests pass; ruff, Django check, migration check, contrast, JS syntax pass.
- Latest deploy was triggered after pushing `dc8ee04..f7f14a5`; confirm Render deploy completes.
- Resend domain `gctekton.com` is verified (GoDaddy DNS, Resend Forge ready).
- Render service `gctt` is Free, region Oregon, health path `/wake/`.
- Required production email env: `EMAIL_BACKEND=config.email_backends.ResendEmailBackend`, `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL=accounts@gctekton.com`, `SITE_URL`, `REQUIRE_EMAIL_OTP=1`.
- Remove old `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `REQUIRE_STAFF_2FA` from Render.

## Completed Edits & Decisions
- Removed Django admin entirely; portal dashboard is the only business-data UI.
- OTP required for every `is_staff` or `role=admin` account; candidates/students use password login.
- Added Resend HTTP email backend with HTML/text, headers, attachments, clear HTTP errors, Retry once.
- OTP send failure now deletes the unsent code, clears resend cooldown, shows error and audits failure.
- Email flows: verification, password setup/reset, password/email-change and account-deleted notifications, first-login welcome, pending application/registration, application/registration receipts and status, staff notifications, certificate, enquiry ack/staff, double-opt-in promotional, unsubscribe.
- Double opt-in: checkbox requests confirmation; `promotional_opt_in` only after signed confirmation; `promotional_opt_in_requested_at` tracks pending.
- Promotional command supports `--after-id` resume, `--limit` 50, `--sleep` 1, dry-run default, stops on failure; unsubscribe page uses signed token.
- Account security notifications: password change/reset, admin email change (old+new), account deletion.
- Welcome sent once on first successful login (password, OTP, Google, pending link); existing users backfilled.
- Render IP fix: first `X-Forwarded-For` entry; audit uses same helper.
- `/wake/` liveness has no DB; `/healthz/` is readiness; keepalive uses `/wake/`.
- Media storage requires Supabase/R2 in production; FileSystemStorage rejected under gunicorn.
- Retention uses calendar months; certified registrations kept with message cleared; audit logs kept.
- Client IP, permissions, backup, bulk status, sitemap, CSP, theme, certificate styling and admin removal hardened.

## Modified Files
- `config/email_backends.py` — new Resend HTTPS backend.
- `config/settings.py` — Resend env/backend selection, retry settings, OTP default, storage guard.
- `config/emails.py` — send retries/HTML, welcome/enrollment/promo/account email senders.
- `config/emails.py` + `templates/emails/*` — transactional/promotional HTML+text templates (account, welcome, enrollment, promotional, opt-in).
- `config/context_processors.py`, `config/site.py` — cached company/site settings.
- `config/{middleware,ratelimit,views,urls,legacy,sitemaps}.py` — CSP, IP, wake/health, legacy/sitemap.
- `config/settings.py`, `render.yaml`, `.github/workflows/{ci,keepalive,maintenance}.yml` — deploy/email/quota/cleanup configuration.
- `apps/accounts/{models,forms,views,urls,email_otp,apps,audit}.py`, migrations `0012`–`0014` — OTP, welcome, promotional, settings, account emails.
- `apps/accounts/management/commands/{send_promotional,repair_internal_accounts,purge_retention,backup_db,check_legacy_urls}.py` — email/ops commands.
- `apps/jobs/{models,views}.py` — application welcome, notifications, bulk status, safe deletes, slug retry.
- `apps/training/{models,views,ai_advisor,certificates}.py`, migration `0006` — enrollment, certificate styling, Gemini removal, sitemap timestamp.
- `templates/emails/*`, `templates/accounts/{security,unsubscribe,promotional_opt_in_confirm}.html` — email/account UI.
- Deleted `apps/accounts/admin.py`, `templates/admin/base_site.html`, `tests/test_admin_ui.py` — admin removal.
- `templates/{base,pages/home,pages/services,partials/*,jobs/job_detail,training/certificate,staff/applications,500,robots}.html` — shell/theme/CSP/hero fixes.
- `static/css/{input,output,certificate}.css`, `static/js/{ui,theme-init}.js`, `static/images/icons.svg` — theme/hero/assets.
- Tests: `test_email_service.py`, `test_resend_backend.py`, `test_email_otp_login.py`, `test_pending_submissions.py`, `test_google_oauth.py`, `test_site_settings.py`, `test_theme.py`, `test_hardening.py`, `test_ops.py`, admin/UI tests.
- Docs: `README.md`, `RUNBOOK.md`, `DEPLOY.md`, `DESIGN.md`, `HANDOFF.md`.

## Known Issues / Blockers
- Render dashboard previously still had old SMTP keys; after redeploy verify `EMAIL_BACKEND` is Resend and `RESEND_API_KEY` exists. Dashboard overrides beat `render.yaml`.
- Live Resend delivery has not been verified from this environment; code/tests use mocked HTTP.
- Render Free still sleeps after 15 minutes; keepalive may be delayed. `/wake/` avoids keeping Neon awake, but uptime is best-effort.
- Email is synchronous with one retry; no durable outbox. A Resend outage can lose a non-OTP notification.
- Resend Free limits: 100/day, 3,000/month. Promo default 50 leaves headroom.
- Enquiry status changes do not email the visitor; profile-only changes do not email.
- Production `audit_access --strict` / `repair_internal_accounts --apply` not run.
- One-click unsubscribe is intentionally not implemented; confirmation page only.

## Exact Next Steps
1. Confirm Render deploy of `f7f14a5`; check `/wake/` and `/healthz/` return `ok`.
2. In Render environment set the Resend values and remove SMTP keys listed above; restart if needed.
3. Test staff login OTP and confirm Resend → Emails shows delivery and API-key “Last used” changes.
4. Run `uv run python manage.py test_email <mailbox>` if Render Shell is available.
5. Test verification, password reset/change, email change, account deletion, welcome, enrollment, application/status, enquiry and promo opt-in/unsubscribe.
6. If email fails: inspect Render logs for `Resend API returned HTTP ...`, `Failed to send email`, and audit `auth.email_otp_send_failed`; do not re-enable SMTP on Free.
7. Run production `audit_access --strict`; defer `repair_internal_accounts --apply` until backup/approval.
8. Optional production hardening: durable email outbox/worker, external uptime monitor, Resend delivery alerts.

## Verification Commands
`uv run ruff check .` · `DJANGO_DEBUG=1 uv run python manage.py check` · `DJANGO_DEBUG=1 uv run python manage.py makemigrations --check --dry-run` · `DJANGO_DEBUG=1 uv run python manage.py test tests` · `DJANGO_DEBUG=1 uv run python scripts/check_contrast.py` · `node --check static/js/ui.js` · `node --check static/js/theme-init.js`
