# GCTT Session Handoff — production hardening

## Goal
Harden the GCTT Django site for production: close security and data-loss gaps,
make CI test the real database, make maintenance safe, and clean up stale code
without changing the public product.

## Current state
- Branch: `prod-hardening`.
- Logo integration is committed separately on top of `58abe79`.
- The hardening work is in progress; do not deploy until the validation steps
  below pass and the owner has taken a Neon PITR snapshot.
- The owner account is `mohdfaizanali038@gmail.com`. Do not delete it. Run
  `uv run python manage.py inspect_seeded_owner` before removing any duplicate
  legacy account.
- Production media is Supabase. Maintenance needs the Supabase secrets to
  delete résumé objects; otherwise it must stay in dry-run mode.

## Completed in this branch
- Owner-seeding migrations `0008`/`0009` are no-ops for fresh databases and
  never delete users. Added `inspect_seeded_owner`.
- Inactive users are logged out on every request.
- Console/dummy email is rejected for production web processes.
- Empty/short `DJANGO_SECRET_KEY` is rejected outside debug/test.
- Admin user fields are validated server-side; guest-apply phone length matches
  the model; registration notes are bounded.
- Résumés are PDF-only; one-click unsubscribe is implemented.
- Certificate PDFs are cached and rate-limited; Gunicorn uses gthread threads.
- Email sends include a stable Resend idempotency key.
- Admin email changes reset verification and send a verification email.
- Pending application/registration emails have a per-recipient cooldown.
- `seed_demo --cleanup` requires `--confirm` and a production override.
- Backup JSON files are written with mode `0600`.
- `repair_internal_accounts` clears leftover direct permissions.
- CI uses Postgres, checks migrations, audits dependencies, and enforces
  coverage. Maintenance is dry-run by default with a manual apply input.
- Static files use manifest storage in production; asset version query strings
  are removed.
- Stale master-plan/design-rules docs and dead admin modules are removed.
- OG image and email headers use the new GCT logo.

## External prerequisites
1. Take a Neon PITR snapshot and a portable backup before applying migrations.
2. Add `SITE_URL` in Render (public origin). Ensure `DJANGO_SECRET_KEY` is at
   least 50 random characters.
3. Add `SUPABASE_*` or `R2_*` secrets to the GitHub `production` environment so
   maintenance can delete objects.
4. Add `PRODUCTION_SITE_URL` and storage secrets to the maintenance environment.
5. Verify WeasyPrint can generate a certificate on the deployed Render runtime.
6. Configure Sentry/alert delivery if desired.

## Exact next steps
1. Run the full validation suite locally.
2. Push the branch and let CI run the Postgres/migration/audit/coverage checks.
3. Deploy to a staging Render service and run the smoke checks in `RUNBOOK.md`.
4. Take a final Neon snapshot, merge, deploy, and verify `/wake/`, `/healthz/`,
   OTP, application, registration, certificate and unsubscribe.
5. Run `inspect_seeded_owner`; keep the current owner and remove only reviewed
   duplicates. Do not run destructive maintenance until storage is verified.

## Verification commands
`uv run ruff check .` · `DJANGO_DEBUG=1 uv run python manage.py check` ·
`DJANGO_DEBUG=1 uv run python manage.py makemigrations --check --dry-run` ·
`DJANGO_DEBUG=1 uv run python manage.py test tests` ·
`DJANGO_DEBUG=1 uv run python scripts/check_contrast.py` ·
`node --check static/js/ui.js` · `node --check static/js/theme-init.js`
