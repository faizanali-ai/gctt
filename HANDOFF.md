# GCTT Session Handoff

## Goal & Core Objective
Keep the Django GCTT site secure and working. Roles are Admin, Staff, Candidate, Student. Login is now password-based; email OTP is optional for admin/staff only. Authenticator-app login is disabled.

## Current UI & Local Access (2026-11-20)
- The public site, auth screens, candidate/student portal, staff queues and Django admin use the new GCTT UI.
- Local login is not seeded. Create an admin with `DJANGO_DEBUG=1 uv run python manage.py createsuperuser`; see README “Local login”.
- `REQUIRE_EMAIL_OTP=0` keeps password-only staff/admin login for local work.
- `seed_demo` creates sample jobs and programmes only.

## Completed Work
- Roles: Admin (owner/CEO merged), Staff (one subgroup), Candidate, Student.
- Staff subgroups: Recruiter, Trainer, Enquiry Manager. No cross-group access.
- Admin-only: user list, account totals, subgroup membership, Django Admin.
- Staff and candidate/student data isolation is enforced.
- Guest apply/register uses 24h single-use link and private temp resume.
- Application/Registration URLs use UUIDs; old numeric routes still work.
- New certificate refs use 16 hex chars; old refs still valid.
- Email OTP service: 6 digits, 10-minute expiry, attempts, cooldown, hashed code.
- TOTP/authenticator login, enrollment, middleware, and UI are removed/disabled.
- Old `/login/2fa/` URLs redirect to normal login.
- Authenticator tables/package are kept for rollback only.
- `REQUIRE_EMAIL_OTP=0`: password-only fallback. `REQUIRE_EMAIL_OTP=1`: admin/staff need email OTP.
- Candidate/student password login and public signup stay normal.
- Admin login: password when flag is 0; email OTP when flag is 1.
- OTP failure is logged as `auth.email_otp_send_failed`; code is never logged.

## Verification
- 190 tests pass.
- Ruff, Django check, migration check, and deploy check pass.
- Commit `0e52863` pushed; Render redeployed.
- Live checks: `/healthz/` = `ok`; `/admin/login/` = 200; OTP page redirects to login while flag is 0; OTP link hidden.
- Working tree clean.

## Modified / Deleted Files
- `HANDOFF.md` — this handoff.
- `.env.example` — replaced old 2FA flag with `REQUIRE_EMAIL_OTP=0`.
- `README.md` — email OTP is optional; no authenticator; candidate login normal.
- `RUNBOOK.md` — removed 2FA ops; added Resend domain/DNS steps and OTP flag.
- `apps/accounts/views.py` — removed TOTP login; optional email OTP for admin/staff; normal candidate login; simple security page.
- `apps/accounts/urls.py` — old 2FA routes redirect to login; password-change no 2FA wrapper.
- `apps/accounts/decorators.py` — `staff_required` only; no 2FA redirects.
- `apps/accounts/management/commands/audit_access.py` — removed 2FA readiness check.
- `apps/training/views.py` — removed 2FA check from certificate download.
- `config/settings.py` — removed OTP/2FA middleware; added `REQUIRE_EMAIL_OTP`.
- `config/middleware.py` — removed `StaffTwoFactorMiddleware`.
- `config/urls.py` — admin login uses password when flag 0, email OTP when flag 1.
- `config/context_processors.py` — exposes `EMAIL_OTP_ENABLED` to hide the link.
- `templates/accounts/login.html` — OTP link hidden when disabled.
- `templates/accounts/security.html` — simple account security page; no TOTP.
- `templates/accounts/dashboard.html` — link renamed to Account security.
- `templates/accounts/staff_dashboard.html` — removed 2FA status.
- `templates/portals/base_portal.html` — removed 2FA wording.
- `templates/accounts/login_2fa.html` — deleted.
- `templates/accounts/login_2fa_enroll.html` — deleted.
- `tests/test_2fa_login.py` — replaced TOTP tests with password/OTP fallback tests.
- `tests/test_2fa_enforcement.py` — replaced with email-OTP enforcement and admin access tests.
- `tests/test_email_otp_login.py` — staff/admin OTP; candidates/students no OTP.
- `tests/test_google_oauth.py` — admin Google OTP only when flag is on.
- `tests/test_ops.py`, `tests/test_bugfixes.py`, `tests/test_security_hardening.py`, `tests/test_audit_access_command.py` — removed TOTP tests/imports.

## Known Issues & Blockers
- Resend domain `gctekton.com` shows **Not Started**; no Resend DKIM/send records; SPF only allows Outlook.
- Email OTP cannot be enabled until the domain owner verifies Resend DNS.
- Keep `REQUIRE_EMAIL_OTP=0` until then; password fallback is required.
- Old `REQUIRE_STAFF_2FA` env is ignored; use `REQUIRE_EMAIL_OTP`.
- Production access audit still needs review; no Render Shell on free tier.
- Legacy staff with multiple subgroups still need manual review.
- Legacy numeric operational URLs remain temporarily.
- Cleanup schedule, PII retention, and public redesign copy approval are pending.

## Exact Next Steps
1. Domain owner adds Resend DKIM/send/SPF records; verify `gctekton.com` in Resend.
2. After verification, set `REQUIRE_EMAIL_OTP=1` in Render and test admin/staff OTP login.
3. Review production users/groups in Django Admin; fix multi/no-subgroup staff.
4. Approve final public copy; the UI redesign is complete.
5. Decide cleanup schedule, PII retention, and legacy URL removal.
