# GCTT Design System Specification (Executive Corporate IT Staffing)

> **Identity**: Savile Row / Private Capital — High-trust, elite US executive staffing & consulting aesthetic (Heidrick & Struggles / TEKsystems caliber).
> **Guiding Principle**: Zero AI-slop. No purple/cyan gradients, no floating cartoon illustrations, no generic card carousels. High restraint, crisp 1px hairline rules, editorial serif headlines with negative tracking, warm linen surfaces, and subtle GPU-accelerated motion.

---

## 1. Design Tokens Table (`static/css/input.css`)

### Color Palette

| Token | Hex Value | Role / Usage |
|:---|:---|:---|
| `--color-paper` | `#FAF9F6` | Primary background (Warm Oyster / Linen) |
| `--color-surface` | `#F3F1EC` | Secondary surface, section bands, table headers |
| `--color-card` | `#FFFFFF` | Elevated foreground cards, modal dialogs, form inputs |
| `--color-ink` | `#111827` | Primary text (Deep Obsidian Charcoal) |
| `--color-ink-muted` | `#4B5563` | Body copy, secondary metadata (Slate 600) |
| `--color-ink-subtle`| `#9CA3AF` | Timestamp, inactive labels, fine-print |
| `--color-brand` | `#0C1E36` | Primary corporate ground (Deep Lapis Navy) |
| `--color-brand-2` | `#162E4E` | Secondary navy hover, dark card borders |
| `--color-accent` | `#9E6534` | Bespoke CTA & highlight (Burnished Warm Bronze) |
| `--color-accent-hover`| `#835227` | Darker bronze on hover / active |
| `--color-line` | `#E5E0D8` | Hairline borders, structural card outlines |
| `--color-line-subtle`| `#F0EDE8` | Divider rules, light table borders |

### Typography

| Token | Family Stack | Characteristics |
|:---|:---|:---|
| `--font-display` | `"Playfair Display", Georgia, "Times New Roman", serif` | High-impact editorial display, letter-spacing -0.025em |
| `--font-sans` | `"Plus Jakarta Sans", system-ui, -apple-system, sans-serif`| Razor-sharp legibility, clean UI and body text |

---

## 2. Reusable Component Classes

### Typography Classes
- `.eyebrow`: `text-xs font-semibold uppercase tracking-[0.12em] text-accent font-sans`
- `.display-xl`: `font-display font-bold text-4xl sm:text-5xl lg:text-6xl text-ink leading-[1.05] tracking-tight`
- `.display-lg`: `font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-ink leading-[1.15] tracking-tight`
- `.display-md`: `font-display font-semibold text-xl sm:text-2xl text-ink leading-tight`
- `.body-lead`: `text-lg sm:text-xl text-ink-muted leading-relaxed font-sans`

### Buttons & Interactive
- `.btn`: Base inline-flex, rounded-md, font-semibold, transition-all duration-200.
- `.btn-primary`: Background `--color-accent` (bronze), text white, hover `--color-accent-hover`, subtle shadow.
- `.btn-brand`: Background `--color-brand` (navy), text white, hover `--color-brand-2`.
- `.btn-secondary`: Border 1px `--color-line`, background `--color-card`, text `--color-ink`, hover border `--color-brand`.
- `.btn-inverse`: Border 1px rgb(255 255 255 / 0.25), text `--color-paper`, hover bg rgb(255 255 255 / 0.1).

### Surface & Cards
- `.card`: Background `--color-card` (`#FFFFFF`), border 1px `--color-line`, rounded-md, padding 1.5rem, shadow-sm.
- `.card-hover`: Extends `.card` with `hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 hover:border-accent/40`.
- `.band-dark`: Background `--color-brand`, text `--color-paper`, subtle bronze top/bottom hairline borders.
- `.band-surface`: Background `--color-surface`, border-y 1px `--color-line`.

---

## 3. Motion & Scroll Engine

A lightweight native `IntersectionObserver` in `templates/base.html` watches all elements with class `.reveal`:

```css
.reveal {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: opacity, transform;
}

.reveal.in-view {
  opacity: 1;
  transform: translateY(0);
}

.delay-1 { transition-delay: 100ms; }
.delay-2 { transition-delay: 200ms; }
.delay-3 { transition-delay: 300ms; }

@media (prefers-reduced-motion: reduce) {
  .reveal {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }
}
```

---

## 4. Template Architecture Map

1. **Global Shells**
   - `templates/base.html`: HTML boilerplate, preconnect Google Fonts, `<a href="#main">` skip link, CSRF meta, header, messages, footer, reveal observer.
   - `templates/partials/_header.html`: Two-tier header: Top utility bar (Irving TX, email lines, portal link) + Main sticky navigation with Services dropdown & "Hire Talent" CTA.
   - `templates/partials/_footer.html`: Grounded deep lapis navy footer with legal disclaimers, Irving TX address, structured navigation links.
   - `templates/partials/_hero.html`: Reusable inner page hero with eyebrow, serif title, and optional lead paragraph.
   - `templates/portals/base_portal.html`: Authenticated staff & user portal layout with sidebar navigation, active page states, and user session badge.

2. **Public Marketing Pages (`templates/pages/`)**
   - `home.html`: Homepage with editorial hero, credentials strip, services grid, audience split (Employers vs Job Seekers), and contact section.
   - `about.html`, `services.html`, `it_staffing.html`, `recruitment.html`, `talent_acquisition.html`, `sap_scrum.html`, `career_restart.html`, `employers.html`, `contact.html`, `privacy.html`, `terms.html`.

3. **Portals & Features**
   - `templates/jobs/`: `job_list.html`, `job_detail.html`
   - `templates/training/`: `programme_list.html`, `programme_detail.html`, `verify.html`, `certificate.html`
   - `templates/accounts/`: `dashboard.html`, `login.html`, `signup.html`, `security.html`, `profile_edit.html`
   - `templates/staff/`: `jobs.html`, `applications.html`, `enquiries.html`, `programmes.html`, `registrations.html`

---

## 5. Build & Verification Commands

```bash
# Compile Tailwind CSS
./tailwindcss -i static/css/input.css -o static/css/output.css --minify

# Run test suite
uv run python manage.py test tests

# Check linting
uv run ruff check .
```
