# GCTT Runbook

Operational steps for the deployed site. Assumes the free-tier stack: Render (web),
Neon (Postgres), R2 (media), Resend (email).

## Deploy

1. Merge to `main` (Render auto-deploys from the branch).
2. Render builds, then the start command runs: `migrate`, `createcachetable`,
   `collectstatic`, gunicorn.
3. Confirm `/wake/` and `/healthz/` return `ok` and the deploy log has no errors.

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

## Email service

Required provider variables: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, and `SITE_URL`.
`SITE_URL` must be the public origin because welcome, enrollment and unsubscribe
links are built from it. Promotional commands use command flags rather than new
environment variables.

`config/emails.py` is the single email service. It sends through Resend SMTP and
supports HTML plus plain-text alternatives. Plain transactional messages are
sent immediately; the promotional command runs outside the request path.

- Welcome: sent exactly once, after the first successful login.
- Enrollment: sent after a registration is confirmed. Transactional, no opt-out.
- Promotional: double opt-in. A request sends a confirmation email; only confirmed
  users (`promotional_opt_in=True`) are eligible. Preview with
  `uv run python manage.py send_promotional --subject "..." --body-file file.txt`;
  add `--send` to deliver. Defaults: 50 recipients, one second between sends.
  Use the printed `--after-id` value on the next run to avoid resending the first batch.
- Unsubscribe: signed link in every promotional email. It opens a confirmation page
  and never blocks transactional mail.
- Test mode: tests use Django’s `locmem` backend; local development uses the
  console backend when `EMAIL_HOST` is empty. Use Resend’s test mode or a
  controlled mailbox in staging.
- Retry: transient send failures are retried once by default. Configure
  `EMAIL_SEND_RETRIES` and `EMAIL_RETRY_DELAY_SECONDS`; permanent failures are
  logged and do not block account or registration completion.
- Provider limits: Resend Free currently allows 100 emails/day and 3,000/month.
  The promotional command’s 50-recipient default leaves headroom for OTP and
  transactional mail.

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
records it provides, then test delivery with
`uv run python manage.py test_email <your-mailbox>`. Email OTP is enabled by
default for every staff/admin login. If Resend is unavailable, an operator can
set `REQUIRE_EMAIL_OTP=0` in Render for emergency password-only access and
restart; change it back after delivery is restored.

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

Email OTP is required for every staff account and every `role=admin` account,
including an admin whose `is_staff` flag is temporarily inconsistent. The
default is `1`; `render.yaml` sets it explicitly. Candidates/students always use
normal password login. There is no authenticator app/TOTP step. The old
`REQUIRE_STAFF_2FA` environment variable is ignored.

If a staff member cannot receive mail, confirm the Resend sender/DNS, check
Render logs and the `auth.email_otp_send_failed` audit event, then use
`REQUIRE_EMAIL_OTP=0` only as a short emergency rollback with a restart.

## Client IP and rate limits

Render documents that the first `X-Forwarded-For` entry is the real client IP.
The rate-limit and audit helpers use that first entry and fall back to
`REMOTE_ADDR`. `CF-Connecting-IP` is ignored while Cloudflare is not linked.
Verify this behavior after any proxy change; an incorrect trust assumption can
weaken login and enrollment limits.

## Django admin and emergency recovery

Django admin is not installed. Manage users, team profiles, content, audit
history and site settings at `/manage/` and `/dashboard/`. For emergency
recovery, use `manage.py shell`, `manage.py audit_access`, the JSON backup
command and Neon backups. The historical `django_admin_log` table may remain in
the database but is unused.

## Liveness and readiness

`/wake/` is the database-free liveness endpoint used by Render and the GitHub
keepalive. `/healthz/` checks the database and is the readiness/monitoring
endpoint. Keep the keepalive on `/wake/` so a free Neon database can sleep.

## Media storage

Production requires R2 or a complete Supabase storage configuration. Run
`uv run python manage.py check_storage` after deployment and whenever storage
credentials change. FileSystemStorage is ephemeral on Render and is rejected
when gunicorn starts without a remote backend.

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
  `purge_retention --apply`, `purge_pending` and `purge_email_otp` using the
  `production` environment secrets, then fails once the legacy sunset date has
  passed. Use **Run workflow** to trigger it manually.

## Access repair policy

Run `uv run python manage.py audit_access --strict` first; it is read-only.
After review, run `uv run python manage.py repair_internal_accounts --apply` to
repair admin/staff flags and groups. Direct permissions are cleared by design;
the role + subgroup model is the source of truth. Staff without a valid subgroup
are reported and left unchanged so a human can assign the correct subgroup in
`/manage/users/`. Neither command should be run against production without a
backup and an approved window.
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
the site follows the operating system.

## Content security policy

Public, auth and portal pages use per-request nonces with no `unsafe-inline`.
The two JSON-LD blocks carry the nonce. Django admin is not installed, so there
is no admin exception to maintain.

## Legacy URLs and retention

The four numeric legacy routes (`withdraw_application_legacy` and the three
staff status/certificate aliases) return `Deprecation`/`Sunset` headers until
**2027-02-19**, then `410 Gone`. `uv run python manage.py check_legacy_urls`
lists them and exits non-zero after that date while they remain registered.

`uv run python manage.py purge_retention` previews the 24-month cleanup:
applications and uncertified registrations are deleted, certified registrations
are kept with their message cleared, and audit logs are never touched. Add
`--apply` to write. Pending submissions are out of scope.
