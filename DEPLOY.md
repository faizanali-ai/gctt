# Deploying GCTT (free tier)

Stack: **Render** (web) · **Neon** (Postgres) · **Resend** (email) · **Cloudflare R2** (media).
Total cost: $0 within free limits. Repo already has `render.yaml`.

---

## 0. Prerequisites

- GitHub repo: `faizanali-ai/gctt` (already pushed)
- Accounts: Neon, Render, Resend, Cloudflare (all free signups)

---

## 1. Neon — database

1. neon.tech → sign up with GitHub → **New Project**.
2. Name `gctt`, region closest to users (e.g. AWS us-east-2).
3. Dashboard → **Connect** → tick **Connection pooling**.
4. Copy the string that looks like:
   `postgresql://user:pass@ep-xxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require`
5. Keep it — this is `DATABASE_URL`.

---

## 2. Resend — email

1. resend.com → sign up → **Domains → Add Domain** → `gctekton.com`.
2. Add the DNS records Resend shows (SPF/DKIM) at your DNS provider. Wait for **Verified**.
3. **API Keys → Create** (sending permission). Copy the key.
4. API settings used by the app:

   | Variable | Value |
   |---|---|
   | `EMAIL_BACKEND` | `config.email_backends.ResendEmailBackend` (set in render.yaml) |
   | `RESEND_API_KEY` | the API key from step 3 |
   | `DEFAULT_FROM_EMAIL` | `accounts@gctekton.com` |

   Render Free blocks outbound SMTP ports 25, 465 and 587. The Resend HTTPS API
   runs on port 443 and works on the free tier. SMTP remains available only as
   an explicit local or paid-host fallback.

Until the domain verifies, Resend only delivers to your own signup address.

---

## 3. Media storage — Supabase (primary) or Cloudflare R2

Production refuses to start gunicorn with local FileSystemStorage. Use the
Supabase S3-compatible endpoint already declared in `render.yaml`:

| Variable | Meaning |
|---|---|
| `SUPABASE_URL` | Project URL (the `/storage/v1/s3` suffix is stripped) |
| `SUPABASE_BUCKET` | Private bucket name |
| `SUPABASE_REGION` | Usually `us-east-1` |
| `SUPABASE_ACCESS_KEY_ID` / `SUPABASE_SECRET_ACCESS_KEY` | S3 access keys |

R2 remains supported via `R2_BUCKET`, `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY`. Keep either bucket private; the app issues signed URLs.
After setting credentials run `uv run python manage.py check_storage`.

---

## 4. Render — web service

1. render.com → sign up with GitHub → allow access to `gctt`.
2. **New → Blueprint** → select the repo → **Apply**.
   `render.yaml` creates the free `gctt` web service.
3. Fill the prompted variables:
   - `DATABASE_URL` — Neon pooled string from step 1
   - `DJANGO_ALLOWED_HOSTS` — your service hostname, e.g. `gctt.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` — `https://gctt.onrender.com`
   - `RESEND_API_KEY` — Resend API key
   - `DEFAULT_FROM_EMAIL` — must be on the verified Resend domain
   - `SITE_URL` — public origin, e.g. `https://gctekton.com`
   - `EMAIL_SEND_RETRIES` — optional, default `1`
   - `R2_BUCKET`, `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
   - `SENTRY_DSN` — optional, leave blank
   - `REQUIRE_EMAIL_OTP` — `1` (default; every staff/admin login needs an email code)
4. Deploy. First build ~3–5 minutes. The start command runs
   `migrate → createcachetable → collectstatic → gunicorn` automatically.
5. Logs: Render → Logs. You should see migrations applying, then:
   `Starting gunicorn`.

### GitHub maintenance secrets

The scheduled workflow uses the GitHub `production` environment. Add these
repository environment secrets before enabling it:

- `PRODUCTION_DATABASE_URL` — Neon pooled connection string.
- `PRODUCTION_DJANGO_SECRET_KEY` — production secret key.
- R2 or Supabase credentials only if a future maintenance step needs media access.

Run **Actions → Production maintenance → Run workflow** once to confirm it can
reach the database before relying on the schedule.

### Create the CEO account

Render → your service → **Shell**:

```bash
DJANGO_DEBUG=0 DJANGO_SUPERUSER_PASSWORD='choose-a-strong-password' \
python manage.py createsuperuser --noinput --email ceo@gctekton.com
```

If Shell is unavailable, run the same command locally against the production DB:

```bash
DATABASE_URL='<neon pooled url>' DJANGO_DEBUG=0 DJANGO_SECRET_KEY='<any>' \
uv run python manage.py createsuperuser --noinput --email ceo@gctekton.com
```

Then log in at `/accounts/login/`, open `/dashboard/` and change the password.

---

## 5. Verify

| Check | Expected |
|---|---|
| `https://<host>/wake/` | `ok` |
| `https://<host>/healthz/` | `ok` |
| Signup on `/accounts/signup/` | welcome message; verification email arrives (Resend → Emails log) |
| `/contact/` enquiry | confirmation banner; alert email to `accounts@gctekton.com` |
| Apply to a job with a PDF | application appears in `/staff/applications/`; object visible in R2 |
| Trainer issues a certificate | PDF downloads; `/training/verify/<ref>/` shows **Valid certificate** |
| `/dashboard/` with CEO account | portal loads |

---

## 6. Custom domain (optional)

1. Render → service → **Settings → Custom Domains** → add `gctekton.com` and `www.gctekton.com`.
2. At Cloudflare DNS, add the CNAME records Render shows (**DNS only**, not proxied,
   to avoid double proxying).
3. Append the domain to `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`,
   then trigger a redeploy.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `400 Bad Request (DisallowedHost)` | hostname missing | add it to `DJANGO_ALLOWED_HOSTS`, redeploy |
| `403 CSRF verification failed` on login | origin mismatch | add `https://...` to `DJANGO_CSRF_TRUSTED_ORIGINS` |
| Static files 404 | collectstatic didn't run | check start command ran; Render logs |
| `database unavailable` on /healthz/ | wrong/paused Neon URL | confirm the pooled string and that the project isn't over quota |
| First request takes 30–60 s | Render free sleeps after 15 min | expected; optional free uptime pinger every 10 min |
| Emails not arriving | domain not verified | finish Resend DNS verification |
| Resume upload fails | R2 keys/scopes | recreate token with Object Read & Write on the bucket |
