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
zero active admins. It never changes data. Fix flagged accounts in
`/manage/users/`, then rerun with `--strict`.

## Email OTP delivery

OTP email requires a working SMTP provider and a verified sender domain. The
production settings are `smtp.resend.com`, port `587`, user `resend`, and
`DEFAULT_FROM_EMAIL=accounts@gctekton.com`. `EMAIL_HOST_PASSWORD` must contain a
valid Resend API key.

Check the public DNS records without a Render Shell:

```bash
dig +short TXT resend._domainkey.gctekton.com
dig +short TXT send.gctekton.com
dig +short TXT gctekton.com
```

The Resend DKIM record must exist, the `send` subdomain must carry Resend's
records, and the root SPF must include Resend's SPF include. If those are absent,
Resend cannot authenticate `accounts@gctekton.com`; messages may be rejected,
quarantined by DMARC, or never delivered. Add the domain in Resend, publish the
records it provides, wait for verification, then set `REQUIRE_EMAIL_OTP=1` and
retest OTP login. Keep it at `0` for password-only fallback until then.

Check the Render dashboard logs for `Failed to send email` and the Django Audit
log for `auth.email_otp_send_failed`. Common causes: unverified Resend domain,
missing SPF/DKIM, wrong API key, or a sender the Resend account does not own.

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

## Internal email OTP

`REQUIRE_EMAIL_OTP=0` keeps password-only fallback active. Set it to `1` after
email delivery is verified; admin/staff logins then require an email code.
Candidates/students always use normal password login. There is no authenticator
app/TOTP step. The old `REQUIRE_STAFF_2FA` environment variable is ignored.

## Staff offboarding (admin only)

1. `/manage/users/` → open the user → **deactivate** (`is_active` off).
2. Remove them from their staff subgroup (`Recruiter`, `Trainer`, or `Enquiry Manager`).
3. Check **Audit log** for their recent actions.

Staff cannot list, count, or discover other staff accounts. Keep user management
and subgroup changes admin-only.

## Incidents

1. Check `/healthz/` (503 means the database is unreachable).
2. Look at Render logs and Sentry (if `SENTRY_DSN` is set).
3. If the site is compromised: rotate `DJANGO_SECRET_KEY` and DB credentials, restore
   from the last known-good backup, then review the audit log.

## Scheduled maintenance checks

- Daily at 03:17 UTC, GitHub Actions runs `.github/workflows/maintenance.yml`:
  `purge_retention --apply` using the `production` environment secrets, then fails
  once the legacy sunset date has passed. Use **Run workflow** to trigger it manually.
- Daily or weekly: `uv run python manage.py purge_email_otp` and
  `uv run python manage.py purge_pending` to remove expired auth/pending records.
- Monthly: dependency updates (`uv lock --upgrade`, run tests, redeploy); run
  `audit_access --strict` and review flagged accounts.
- Quarterly: restore drill, review staff accounts and role groups, rotate R2 keys.

## Site settings and theme

Admins edit company identity, contact details and home-hero copy at
`/manage/settings/`. The context processor falls back to `config/constants.py`
if no row exists or the database is unreachable. The public/auth/portal header
toggle stores the choice in `localStorage` under `gctt-theme`; without a choice
the site follows the operating system. Django admin stays light-only.

## Content security policy

Public, auth and portal pages use per-request nonces with no `unsafe-inline`.
The two JSON-LD blocks and the admin stylesheet carry the nonce. Django admin
alone gets a `/admin/`-scoped `style-src 'unsafe-inline'` exception because its
break-glass screens include inline styles. Verify the admin in a browser after
any Django upgrade.

## Legacy URLs and retention

The four numeric legacy routes (`withdraw_application_legacy` and the three
staff status/certificate aliases) return `Deprecation`/`Sunset` headers until
**2027-02-19**, then `410 Gone`. `uv run python manage.py check_legacy_urls`
lists them and exits non-zero after that date while they remain registered.

`uv run python manage.py purge_retention` previews the 24-month cleanup:
applications and uncertified registrations are deleted, certified registrations
are kept with their message cleared, and audit logs are never touched. Add
`--apply` to write. Pending submissions are out of scope.
