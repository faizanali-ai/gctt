# GCTT Session Handoff

## Goal & Core Objective
Harden the existing Django GCTT site backend-first. Access is three levels: Admin (owner/superadmin/CEO merged), Staff (one subgroup), Candidate/Student. Access model, audit, 2FA, certificate hardening, tokenized guest continuation, UUID URLs, and email OTP login are complete.

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
- Staff 2FA enforcement + enrollment flow; read-only `audit_access` with `--strict`.
- Email OTP login at `/accounts/login/email/`: 6-digit code, 10-minute expiry, attempt limits, resend cooldown, generic responses.
- OTP routing is 2FA-aware: internal users still complete TOTP/enrollment; candidates/students go to their dashboard.
- OTP request/verify/resend audited without logging codes; expired/consumed rows purged via `purge_email_otp`.
- Expired pending submissions/temp resumes purged via `purge_pending`.

## Verification
- 195 tests pass.
- `ruff check .`, `manage.py check`, `makemigrations --check`, `check --deploy` clean.
- Local migrations applied through `accounts.0011`, `jobs.0006`, `training.0005`; local `audit_access --strict` clean.
- Commits include access, enforcement/UI, certificate refs, tokenized continuation, UUID routes, OTP foundation/login/cleanup, and OTP docs.

## Key Files
- `apps/accounts/models.py` — roles, `is_admin`, `sync_access` (clears direct perms).
- `apps/accounts/migrations/0010_consolidate_roles.py` — merged top-level -> admin; subgroup normalization; reverse restore.
- `apps/accounts/management/commands/audit_access.py` — read-only access audit.
- `apps/accounts/email_otp.py` — OTP issue/verify/purge service.
- `apps/accounts/migrations/0011_emailotp.py` — email OTP table.
- `apps/accounts/management/commands/purge_email_otp.py` — expired/consumed OTP cleanup.
- `apps/accounts/pending.py` — 24h pending token helpers.
- `apps/accounts/management/commands/purge_pending.py` — expired pending/temp file cleanup.
- `apps/accounts/decorators.py` — `staff_required`, 2FA redirect helpers.
- `apps/accounts/views.py`, `admin.py`, `urls.py` — 2FA, role management, scoped dashboards, admin guards.
- `apps/jobs/models.py` — `PendingApplication`, `Application.uuid`.
- `apps/jobs/views.py`, `urls.py` — tokenized application continuation, UUID/legacy routes.
- `apps/jobs/migrations/0005_pendingapplication.py`, `0006_application_uuid.py`.
- `apps/training/models.py` — `PendingRegistration`, `Registration.uuid`, 16-char refs.
- `apps/training/views.py`, `urls.py` — tokenized registration, certificate privacy, UUID/legacy routes.
- `apps/training/migrations/0004_pendingregistration.py`, `0005_registration_uuid.py`.
- `config/emails.py` — subgroup notifications, individual sends, password setup, pending links, OTP email.
- `config/middleware.py`, `config/urls.py` — internal 2FA; single admin gate.
- `templates/accounts/login_email_otp.html`, `login_email_otp_verify.html` — OTP request/verify pages.
- `templates/jobs/pending_application.html`, `templates/training/pending_registration.html` — confirm pages.
- Other templates — visibility scoping, counters removed, UUID form actions, subgroup UI.
- Tests — access/visibility, enumeration, 2FA, migration, audit, pending submissions, OTP service/login.
- `README.md`, `RUNBOOK.md` — access contract, 2FA, audit, pending cleanup.

## Known Issues & Blockers
- Production `migrate` and `audit_access --strict` still need to be run by the user.
- Live SMTP OTP delivery has not been verified in production.
- Legacy staff with multiple subgroups reduce to `Recruiter` priority; admin review required.
- Staff queues contain candidate/student PII by design (permitted subgroup context).
- Numeric operational URLs remain as temporary compatibility routes.
- `REQUIRE_STAFF_2FA=1` is set in `render.yaml`; ensure internal users enroll.
- Public redesign not started; it requires page-by-page copy approval, starting with Home.

## Exact Next Steps
1. Deploy `migrate`; run `audit_access --strict` and request one real OTP in production.
2. Review and approve the Home page copy draft.
3. Implement the full public redesign page-by-page using current Stitch CSS; Home first.
4. After monitoring, remove legacy numeric operational routes; final verification and handoff refresh.
