# GCTT Runbook

Operational steps for the deployed site. Assumes Railway + Neon + R2 + Resend.

## Deploy

1. Merge to `main` (or push, if branch protection allows).
2. Railway builds, then runs the `release` step: `migrate`, `createcachetable`, `collectstatic`.
3. Confirm `/healthz/` returns `ok` and the deploy log has no errors.

Rollback: Railway → Deployments → previous deployment → **Redeploy**. Database
migrations are forward-only — if a migration must be undone, restore a backup first.

## Backups and restore

- **Neon**: point-in-time recovery is the primary recovery path. Confirm it is enabled.
- **R2**: bucket object versioning protects uploaded resumes.
- **Portable dump** (any environment):
  ```bash
  DJANGO_DEBUG=0 uv run python manage.py backup_db
  ```
- **Full Postgres dump**:
  ```bash
  pg_dump "$DATABASE_URL" > backup-$(date +%F).sql
  ```
- **Restore drill** (do this once per quarter): restore the latest dump into a scratch
  database, run `loaddata`, start the app against it, verify `/healthz/` and one job page.

## Secrets

Rotate `DJANGO_SECRET_KEY` by generating a new value and redeploying — this signs
everyone out. Also rotate `EMAIL_HOST_PASSWORD` and the R2 keys on suspicion of leak.
Never commit `.env`; it is gitignored.

## Staff offboarding

1. Django Admin → Users → open the user → **deactivate** (`is_active` off).
2. Remove them from role groups.
3. Delete their TOTP device (Admin → TOTP devices) so they cannot re-authenticate.
4. Check **Audit log entries** for their recent actions.

## Incidents

1. Check `/healthz/` (503 means the database is unreachable).
2. Look at Railway logs and Sentry (if `SENTRY_DSN` is set).
3. If the site is compromised: rotate `DJANGO_SECRET_KEY` and DB credentials, restore
   from the last known-good backup, then review the audit log.

## Scheduled maintenance checks

- Monthly: dependency updates (`uv lock --upgrade`, run tests, redeploy).
- Quarterly: restore drill, review staff accounts and role groups, rotate R2 keys.
