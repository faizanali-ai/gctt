# GCTT Session Handoff

## Goal & Core Objective
Harden the existing Django GCTT site backend-first. Access is three levels: Admin (owner/superadmin/CEO merged), Staff (one subgroup), Candidate/Student. Task 1 (visibility/isolation), Task 2 (migration correction + audit), and the local migrate/audit are complete.

## Completed Edits & Architecture Decisions
- Merged `owner`/`superadmin`/`ceo` into `admin`; kept `staff`.
- Kept Staff subgroups `Recruiter`, `Trainer`, `Enquiry Manager` intact; no flattening.
- Kept Candidate/Student separation via `account_type`.
- `sync_access` enforces role -> flags + exactly one group and clears direct permissions.
- Last-active-admin/self-protection guards in portal and Django Admin.
- Admin-only: user lists, account totals, subgroup membership, Django Admin.
- Staff isolation: no staff directory/counts; staff-owned records excluded from operational queues; notices sent one recipient at a time.
- Candidate/Student isolation: own records only; cross-actions blocked.
- Removed non-admin aggregate counters: staff dashboard stats, per-record counts, pagination totals, candidate dashboard counts.
- Public certificate verification hides holder identity; unauthorized downloads return 404.
- Signup/guest apply/guest register return identical generic responses for new/existing emails; no auto-login.
- Notifications route only to relevant subgroup; Admin is not a default recipient.
- Added Staff 2FA enforcement + enrollment flow (`staff_required`, `login_2fa_enroll`).
- Added read-only `audit_access` command with optional `--strict`.
- Cleaned up staff subgroup UI: required selector, admin-only role hides it, renamed labels.

## Verification
- 164 tests pass.
- `ruff check .`, `manage.py check`, `makemigrations --check`, `check --deploy` clean.
- Migration `0010` verified on fresh and seeded legacy-role DBs.
- Local `migrate` applied and `audit_access --strict` is clean.
- No commit created; all changes are in the working tree.

## Modified Files
- `README.md` — access/visibility contract; admin wording.
- `RUNBOOK.md` — internal 2FA, admin-only offboarding, access audit procedure.
- `apps/accounts/admin.py` — last-admin/self guards; admin save normalization.
- `apps/accounts/apps.py` — four permission groups; single admin gate; post_migrate sync.
- `apps/accounts/forms.py` — removed public email-exists validation.
- `apps/accounts/models.py` — admin/staff roles, `is_admin`, `sync_access`, lowercased emails, direct-perm clearing.
- `apps/accounts/urls.py` — 2FA enrollment route; verified wrapper on password change.
- `apps/accounts/views.py` — 2FA login/enroll, staff_required, role/subgroup management, dashboard scoping, generic signup.
- `apps/enquiries/views.py` — staff_required on staff enquiry views.
- `apps/jobs/views.py` — guest apply without login, student block, external-only queues, staff_required.
- `apps/training/views.py` — guest register without login, candidate block, cert privacy/404, staff_required.
- `config/emails.py` — subgroup recipients, individual sends, password setup link.
- `config/middleware.py` — 2FA for all internal users.
- `config/urls.py` — removed duplicate Django Admin permission gate.
- `templates/accounts/dashboard.html` — candidate/student-only sections; removed counters.
- `templates/accounts/profile_edit.html` — admin self-deletion hidden.
- `templates/accounts/security.html` — disable requires current TOTP code.
- `templates/accounts/staff_dashboard.html` — admin-only stats/account totals; `is_admin`.
- `templates/partials/_pagination.html` — no page totals for staff.
- `templates/portals/base_portal.html` — admin link admin-only.
- `templates/portals/user_form.html` — required Staff subgroup; hidden for Admin; no read-only option.
- `templates/portals/users.html` — admin role wording/delete guard; subgroup label.
- `templates/staff/jobs.html` — per-job counts admin-only.
- `templates/staff/programmes.html` — per-programme counts admin-only.
- `templates/training/verify.html` — removed holder identity.
- `tests/test_2fa_login.py` — admin role constants.
- `tests/test_audit_security_fixes.py` — generic redirects; no session.
- `tests/test_bugfixes.py` — metrics removed; subgroup notification fixture.
- `tests/test_candidate_privacy.py` — candidate-only context; cert 404.
- `tests/test_google_oauth.py` — admin role constants.
- `tests/test_ops.py` — admin role constants.
- `tests/test_p0.py` — signup redirect, subgroup recipients, cert privacy/404.
- `tests/test_roles.py` — two-role/subgroup matrix; required-subgroup form test.
- `tests/test_security_hardening.py` — admin role constants.
- `tests/test_staff.py` — admin role constants.
- `tests/test_ui_linkedin_ai.py` — guest apply redirect/no session.

## Created Files
- `HANDOFF.md` — this handoff.
- `apps/accounts/decorators.py` — `staff_required`, 2FA redirect helpers.
- `apps/accounts/management/commands/audit_access.py` — read-only access audit.
- `apps/accounts/migrations/0010_consolidate_roles.py` — merged top-level -> admin; subgroup normalization; reverse restore.
- `templates/accounts/login_2fa_enroll.html` — pending-session 2FA enrollment.
- `tests/test_2fa_enforcement.py` — 2FA enforcement, admin guards, direct-permission isolation.
- `tests/test_access_visibility.py` — admin-only visibility, staff isolation, counts, cert access.
- `tests/test_account_enumeration.py` — generic new/existing email responses.
- `tests/test_audit_access_command.py` — audit command coverage.
- `tests/test_migration_0010.py` — migration/reverse behavior.

## Known Issues & Blockers
- Legacy staff with multiple subgroups reduce to `Recruiter` priority; admin review required.
- Staff queues contain candidate/student PII by design (permitted subgroup context).
- Existing-email guests must log in and re-submit; no tokenized continuation.
- Certificate refs are 8 hex and only IP rate-limited.
- Numeric operational record PKs remain in URLs; no account/user IDs are exposed.
- `REQUIRE_STAFF_2FA=1` is set in `render.yaml`; ensure internal users enroll.

## Exact Next Steps
1. Deploy `migrate`; run `audit_access --strict` in production and fix flagged accounts.
2. Continue UI phase: admin account summary is present; next is the public/content phase.
3. Consider tokenized guest continuation and UUID operational URLs if those gaps matter.
4. Commit the current working tree after review; no commit exists yet.
