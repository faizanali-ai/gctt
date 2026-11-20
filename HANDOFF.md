# GCTT Session Handoff

## Goal & Core Objective
Harden the existing Django GCTT site backend-first. Access is three levels: Admin (owner/superadmin/CEO merged), Staff (one subgroup), Candidate/Student. Access model, audit, certificate hardening, tokenized guest continuation, UUID URLs, and optional internal email OTP are complete. Authenticator/TOTP login is disabled.

## Completed Work
- Merged `owner`/`superadmin`/`ceo` into `admin`; kept `staff` and subgroups `Recruiter`, `Trainer`, `Enquiry Manager`.
- Kept Candidate/Student separation via `account_type`; cross-actions blocked.
- `sync_access` enforces role -> flags + one group and clears direct permissions.
- Last-active-admin/self-protection guards in portal and Django Admin.
- Admin-only user lists, account totals, subgroup membership, Django Admin.
- Staff isolation: no staff directory/counts; staff-owned records excluded from queues; notices sent individually.
- Non-admin counters removed/hidden: dashboards, per-record counts, pagination totals.
- Certificate verification hides holder identity; unauthorized downloads return 404.
- New certificate refs use 16 hex chars; legacy 8-char refs remain valid.
- Signup/guest flows use generic responses; no account-existence messages.
- Existing-email guests get a 24h single-use magic link to confirm a saved application/registration; resumes use private temp storage.
- UUIDs now drive application/registration routes; legacy numeric URLs still work.
- Authenticator/TOTP login, enrollment, middleware, and UI are disabled; old 2FA URLs redirect to login; tables are kept for rollback.
- Optional internal email OTP: 6-digit code, 10-minute expiry, attempt limits, resend cooldown, generic responses.
- `REQUIRE_EMAIL_OTP=1` requires email OTP for admin/staff; `0` keeps password-only fallback.
- Candidates/students keep normal password login; no forced OTP.
- OTP request/verify/resend audited without logging codes; expired/consumed rows purged via `purge_email_otp`.
- Expired pending submissions/temp resumes purged via `purge_pending`.

## Verification
- 195 tests pass.
- `ruff check .`, `manage.py check`, `makemigrations --check`, `check --deploy` clean.
- Local migrations applied through `accounts.0011`, `jobs.0006`, `training.0005`; local `audit_access --strict` clean.
- Production deploy `da4b7c5` applied migrations and is live; `/healthz/` and key public pages returned 200.
- Commits include access, enforcement/UI, certificate refs, tokenized continuation, UUID routes, OTP foundation/login/cleanup/docs, and admin OTP routing.

## Key Files
- `apps/accounts/models.py` — roles, `is_admin`, `sync_access` (clears direct perms).
- `apps/accounts/migrations/0010_consolidate_roles.py` — merged top-level -> admin; subgroup normalization; reverse restore.
- `apps/accounts/management/commands/audit_access.py` — read-only access audit.
- `apps/accounts/email_otp.py` — OTP issue/verify/purge service.
- `apps/accounts/migrations/0011_emailotp.py` — email OTP table.
- `apps/accounts/management/commands/purge_email_otp.py` — expired/consumed OTP cleanup.
- `apps/accounts/pending.py` — 24h pending token helpers.
- `apps/accounts/management/commands/purge_pending.py` — expired pending/temp file cleanup.
- `apps/accounts/decorators.py` — `staff_required` only; no 2FA redirects.
- `apps/accounts/views.py`, `admin.py`, `urls.py` — email OTP, role management, scoped dashboards, admin guards; no TOTP.
- `apps/jobs/models.py` — `PendingApplication`, `Application.uuid`.
- `apps/jobs/views.py`, `urls.py` — tokenized application continuation, UUID/legacy routes.
- `apps/jobs/migrations/0005_pendingapplication.py`, `0006_application_uuid.py`.
- `apps/training/models.py` — `PendingRegistration`, `Registration.uuid`, 16-char refs.
- `apps/training/views.py`, `urls.py` — tokenized registration, certificate privacy, UUID/legacy routes.
- `apps/training/migrations/0004_pendingregistration.py`, `0005_registration_uuid.py`.
- `config/emails.py` — subgroup notifications, individual sends, password setup, pending links, OTP email.
- `config/middleware.py`, `config/urls.py` — security headers; single admin gate; no 2FA middleware.
- `templates/accounts/login_email_otp.html`, `login_email_otp_verify.html` — OTP request/verify pages.
- `templates/jobs/pending_application.html`, `templates/training/pending_registration.html` — confirm pages.
- Other templates — visibility scoping, counters removed, UUID form actions, subgroup UI.
- Tests — access/visibility, enumeration, login fallback/OTP, migration, audit, pending submissions.
- `README.md`, `RUNBOOK.md` — access contract, email OTP, audit, pending cleanup.

## Known Issues & Blockers
- Latest auth/TOTP-removal commit needs the automatic Render redeploy to complete.
- Production `audit_access --strict` still needs to be run by the user.
- Live SMTP OTP delivery remains unverified; `REQUIRE_EMAIL_OTP` stays `0` until Resend domain verification.
- Legacy staff with multiple subgroups reduce to `Recruiter` priority; admin review required.
- Staff queues contain candidate/student PII by design (permitted subgroup context).
- Numeric operational URLs remain as temporary compatibility routes.
- Old `REQUIRE_STAFF_2FA` env is ignored; use `REQUIRE_EMAIL_OTP`.
- Public redesign not started; it requires page-by-page copy approval, starting with Home.

## Exact Next Steps
1. Deploy the auth/TOTP-removal commit; verify password-only fallback works for admin/staff and candidates.
2. After Resend domain verification, set `REQUIRE_EMAIL_OTP=1` and test admin/staff email OTP.
3. Review and approve the Home page copy draft.
4. Implement the public redesign page-by-page using current Stitch CSS; Home first.
5. After monitoring, remove legacy numeric operational routes; final verification and handoff refresh.
