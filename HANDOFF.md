# GCTT Session Handoff — 2026-11-21
## Goal
Finish the GCTT Django site: ship the approved full-bleed hero, site-wide light/dark toggle, editable
site/user metadata, strict CSP, legacy URL sunset, scheduled maintenance, and staff/admin email OTP.
## Current State
- Production was deployed from `e6ad272`; the next hardening slice is local and uncommitted.
- 280 tests pass; ruff, Django check, migration check, contrast, JS syntax pass.
- Django admin has been removed; all business data is managed through the portal.
- Staff/admin login loop fixed; candidate/student designations display correctly.
- Public `/training/` now renders published programmes (context bug fixed).
- Next-phase shipped: `job_title`, `SiteSettings` + `/manage/settings/`, full-bleed hero,
  light/dark toggle, CSP nonces, legacy sunset middleware, `purge_retention`, maintenance workflow.
## Confirmed Decisions
- Hero: all heroes full-bleed/left-anchored; solid sticky header; centered footer; 20/24/32px gutter;
  home stats in a full-width strip; content-driven height; keep current headline scale;
  full-bleed low-opacity art, reduced on mobile.
- Theme: two-state light/dark; OS default until chosen; persist in `localStorage`;
  public/auth/portal only.
- Django admin: removed entirely; portal is the only data UI. Recovery is shell/backups.
- Storage: Supabase is the configured remote backend; production refuses FileSystemStorage.
- Keepalive and Render health checks use `/wake/` (no DB); `/healthz/` is readiness.
- Pending magic links are candidate/student only; staff/admin use normal login/OTP.
- Retention: calendar 24 months; applications and uncertified registrations deleted;
  certified registrations kept with message cleared; audit logs kept.
- Users: designation remains Admin/Staff/Candidate/Training Student; add optional free-text `job_title`.
- Permissions: keep fixed role + subgroup model; do not expose raw group/permission matrix.
- SiteSettings: company identity/contact + home-hero copy only; other page copy stays in templates.
- Team photos: keep `photo_url`; uploads deferred.
- CSP: remove `unsafe-inline` with per-request nonces; documented admin-only style exception if required.
- Retention: 24 months; delete old applications; delete old uncertified registrations; keep certified
  registrations but clear messages; keep audit logs.
- Legacy URLs: sunset `2027-02-19`; `Deprecation`/`Sunset` headers before, `410 Gone` after.
- GitHub Actions: daily maintenance at `03:17 UTC` + manual dispatch; fail after sunset until removed.
- Production repair/access audit deferred.
## Completed Work
- Full UI rebuild: ink/copper tokens, self-hosted fonts, sprite icons, vanilla JS, responsive shell,
  new OG image/favicon, auth/portal/admin styling.
- Portal admin: all users and designations, create/edit/delete, activation, verification, password reset;
  team profiles; jobs; categories; programmes; applications (status/bulk/delete); registrations
  (status/certificate/delete); enquiries (edit/status/delete); read-only audit log.
- Admin login guard: authenticated non-admins go to `/dashboard/`, no admin-login loop.
- Designation mapping: role/account_type/flags/groups synchronized transactionally.
- Registration feedback, form error summaries, metadata/noindex, sticky staff tables, dashboard mobile fix.
- `repair_internal_accounts` command for legacy broken staff flags.
- Removed all portal links to Django admin.

## Modified Files
- `config/urls.py` — portal CRUD routes, admin login guard, content routes.
- `config/context_processors.py`, `config/constants.py` — shared COMPANY/nav context.
- `apps/accounts/models.py` — designation/designation_value, apply_designation, choices.
- `apps/accounts/views.py` — user/team/audit management, designations, dashboard labels.
- `apps/accounts/forms.py` — TeamProfileForm; profile/user form support.
- `apps/accounts/admin.py`, `apps/accounts/apps.py` — admin user consistency; team/audit permissions.
- `apps/accounts/management/commands/repair_internal_accounts.py` — new repair command.
- `apps/jobs/{models,forms,views}.py` — job/application forms, CRUD, bulk status, application count.
- `apps/training/{models,forms,views,admin}.py` — category/programme/registration CRUD; public list fix.
- `apps/enquiries/{forms,views}.py` — enquiry edit/delete.
- `static/css/{input,output,certificate}.css` — tokens/components, sticky tables, responsive rules.
- `static/fonts/*` — self-hosted Inter/Space Grotesk/JetBrains Mono + OFL files.
- `static/images/{icons.svg,logo-icon.svg,logo-icon-512.png,og-gctt-v3.jpg,google.svg}` — new assets.
- Deleted `static/images/{hero-office.jpg,logo.png,logo.svg,logo-small.webp,og-gctt-v2.jpg}`.
- `static/js/ui.js` — dialogs, nav, toasts, forms, animations.
- `templates/base.html`, `templates/partials/*` — shell, hero, fields, errors, pagination, nav.
- `templates/pages/*`, `templates/jobs/*`, `templates/training/*` — rewritten public/auth pages.
- `templates/accounts/*`, `templates/portals/*`, `templates/staff/*` — new portal UI.
- New staff pages: `team.html`, `team_form.html`, `audit.html`, `categories.html`, `category_form.html`,
  `job_form.html`, `programme_form.html`, `application_detail.html`, `registration_detail.html`, `enquiry_detail.html`.
- Deleted `templates/admin/color_theme_toggle.html`, `templates/staff/_nav.html`.
- `tests/test_admin_dashboard.py`, `test_ui_audit.py`, `test_ui_system.py` — new coverage.
- Updated `tests/test_bugfixes.py`, `test_p0.py`, `test_staff.py`, `test_ui_linkedin_ai.py`.
- `README.md`, `HANDOFF.md`, `DESIGN.md`, `DESIGN_SYSTEM_RULES.md`, `render.yaml` — docs/config.
- `.github/workflows/ci.yml`, `scripts/check_contrast.py` — UI/build guards.
- `apps/accounts/models.py` — `job_title`, singleton `SiteSettings`.
- `apps/accounts/migrations/0012_sitesettings_user_job_title.py` — new schema.
- `apps/accounts/{forms,views}.py` — metadata forms and settings page.
- `config/{context_processors,urls,middleware,settings}.py`, `config/legacy.py` — settings context, CSP nonces, sunset, middleware.
- `templates/partials/{_hero,_header,_theme_toggle}.html`, `templates/pages/{home,services}.html` — hero/stagger/theme.
- `templates/{base,accounts/base_auth,portals/base_portal,portals/site_settings,portals/user_form,portals/users,portals/_nav}.html` — theme, settings, metadata UI.
- `templates/{jobs/job_detail,training/certificate}.html` — nonce and inline-style cleanup.
- `static/js/{theme-init.js,ui.js}`, `static/css/{input,output,certificate}.css`, `static/images/icons.svg` — theme assets and tokens.
- `apps/accounts/management/commands/{check_legacy_urls,purge_retention}.py` — sunset check and retention.
- `.github/workflows/maintenance.yml`, new tests for settings, theme, legacy and retention.

## Known Issues / Blockers
- GitHub `production` secrets (`PRODUCTION_DATABASE_URL`, `PRODUCTION_DJANGO_SECRET_KEY`)
  are not set yet; the maintenance workflow cannot run until they are.
- Resend is verified; email OTP is enabled by default for every staff/admin account.
- Production `repair_internal_accounts --apply` and `audit_access --strict` not run; deferred.
- Run `manage.py check_storage` against production to confirm Supabase wiring.
- Rate limiting assumes Render appends the client address to `X-Forwarded-For`; no
  Cloudflare proxy is currently trusted.
- Legacy numeric URLs still work until `2027-02-19`, then return `410 Gone`.
- Theme and hero changes need a manual pass at all breakpoints in both themes.

## Remaining Work
1. Withdraw the four legacy routes after `2027-02-19` (the maintenance workflow fails until then).
2. Configure GitHub `production` secrets and dispatch the maintenance workflow once.
3. Run `audit_access --strict`, then `repair_internal_accounts --apply` in production with a backup.
4. Confirm `check_storage` passes and `/wake/` is the Render health check.
5. Keep an emergency rollback path: set `REQUIRE_EMAIL_OTP=0` and restart if Resend fails.

## Verification Commands
`uv run ruff check .` · `uv run python manage.py check` · `uv run python manage.py makemigrations --check --dry-run`
`uv run python manage.py test tests` · `uv run python scripts/check_contrast.py` · `node --check static/js/ui.js`
Rebuild CSS with Tailwind v4.3.5 and confirm `output.css` is deterministic.

## Assumptions
- Sunset date `2027-02-19`; maintenance daily at `03:17 UTC`, secrets scoped to GitHub `production`.
- Retention policy: applications >24m deleted; uncertified registrations >24m deleted; certified kept with
  message cleared; audit logs kept.
- Theme: OS default, then explicit localStorage choice.
- Email OTP: required for all staff and role=admin accounts; candidates/students use password login.
- Email service: first-login welcome, HTML+text enrollment, double-opt-in promotional flow, confirmation-page unsubscribe, resumable `send_promotional` command, and account security notifications.
- Resend HTTPS API is configured; `REQUIRE_EMAIL_OTP=1` is the default and is declared in `render.yaml`.
