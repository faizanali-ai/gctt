# GCTT Runbook

Operational steps for the deployed site. Assumes the free-tier stack: Render (web),
Neon (Postgres), R2 (media), Resend (email).

## Deploy

1. Merge to `main` (Render auto-deploys from the branch).
2. Render builds, then the start command runs: `migrate`, `createcachetable`,
   `collectstatic`, gunicorn.
3. Confirm `/healthz/` returns `ok` and the deploy log has no errors.

Rollback: Render → Deploys → previous deploy → **Redeploy**. Migrations are
forward-only — if a migration must be undone, restore a backup first.

Free-tier note: the service sleeps after 15 minutes idle; the first request after
that is slow (~30–60s). That is expected, not an outage.

## Backups and restore

- **Neon**: point-in-time recovery is the primary recovery path.
- **R2**: enable bucket object versioning to protect uploaded resumes.
- **Portable dump** (any environment):
  ```bash
  DJANGO_DEBUG=0 uv run python manage.py backup_db
  ```
- **Full Postgres dump**:
  ```bash
  pg_dump "$DATABASE_URL" > backup-$(date +%F).sql
  ```
- **Restore drill** (quarterly): restore the latest dump into a scratch database,
  run `loaddata`, start the app against it, verify `/healthz/` and one job page.

## Access audit

After migrating, run the read-only access audit:

```bash
uv run python manage.py audit_access
uv run python manage.py audit_access --strict
```

It reports staff with no/multiple subgroups, unexpected or direct permissions,
invalid roles, external accounts with internal access, missing admin flags/groups,
zero active admins, and pending 2FA enrollment. It never changes data. Fix flagged
accounts in `/manage/users/` or Django Admin, then rerun with `--strict`.

## Email OTP cleanup

Expired or consumed email OTP rows are removed with:

```bash
uv run python manage.py purge_email_otp
```

Run this on a schedule or during routine maintenance.

## Pending guest submissions

Existing-email guests receive a 24-hour single-use link to confirm a saved
application or registration. Expired pending records and unreferenced temporary
resumes are removed with:

```bash
uv run python manage.py purge_pending
```

Run this on a schedule or during routine maintenance.

## Secrets

Rotate `DJANGO_SECRET_KEY` by generating a new value and redeploying — this signs
everyone out. Also rotate `EMAIL_HOST_PASSWORD` and the R2 keys on suspicion of leak.
Never commit `.env`; it is gitignored.

## Internal 2FA

When `REQUIRE_STAFF_2FA=1`, every internal user (admin and staff) must enroll at
`/accounts/security/` before using internal pages. Candidates and students are not
affected. Enroll current staff before enabling the flag.

## Staff offboarding (admin only)

1. Django Admin → Users → open the user → **deactivate** (`is_active` off).
2. Remove them from their staff subgroup (`Recruiter`, `Trainer`, or `Enquiry Manager`).
3. Delete their TOTP device (Admin → TOTP devices) so they cannot re-authenticate.
4. Check **Audit log entries** for their recent actions.

Staff cannot list, count, or discover other staff accounts. Keep user management
and subgroup changes admin-only.

## Incidents

1. Check `/healthz/` (503 means the database is unreachable).
2. Look at Railway logs and Sentry (if `SENTRY_DSN` is set).
3. If the site is compromised: rotate `DJANGO_SECRET_KEY` and DB credentials, restore
   from the last known-good backup, then review the audit log.

## Scheduled maintenance checks

- Monthly: dependency updates (`uv lock --upgrade`, run tests, redeploy).
- Quarterly: restore drill, review staff accounts and role groups, rotate R2 keys.
