# GCTT Design System

This is the single source of truth for the GCTT interface and user experience.

---

## 1. Direction & Institutional Identity

Warm institutional modernism. Ink neutrals, warm paper, a single copper signal, editorial grid discipline, hairline rules, and abstract line geometry instead of photography. The aesthetic register embodies an executive search and technical staffing institution executed with luxury digital craft: neither SaaS gradient-marketing, nor playful bento grids, nor raw neo-brutalism.

### Core Design Principles
1. **Divide by capability, not audience:** Clear architectural modules over marketing fluff.
2. **One accent, used as a disciplined signal:** High-contrast copper in light mode and luminous warm amber in dark mode guide action without visual fatigue.
3. **Typography and hairline rules do the work:** Spatial restraint and typographic hierarchy convey institutional authority without decorative clutter.
4. **Nothing product-level above the fold:** Uncompromised clarity and immediate executive reassurance.
5. **Motion reveals structure; it never delays reading:** Micro-interactions feel physical and instantaneous, respecting reduced-motion settings unconditionally.
6. **Both themes are first-class:** Engineered simultaneously with uncompromising contrast and tactile depth.
7. **Every surface is tokenised:** Zero raw hex values in application markup; 100% semantic CSS token consumption.

---

## 2. Authoritative Token Reference

Defined in `static/css/input.css` using CSS custom properties. Runtime tokens live in `:root` (Light Mode), are overridden in `:root[data-theme="dark"]` (Dark Mode), and automatically respond to `@media (prefers-color-scheme: dark)` when scoped to `:root:not([data-theme="light"])`. Utilities are mapped cleanly via `@theme inline`.

### Core Color Palette

| Token | Light Mode | Dark Mode | Role & Material Origin |
| :--- | :--- | :--- | :--- |
| `--canvas` | `#FAF9F7` | `#0B0C0E` | Page ground (warm rag paper / deep charcoal night) |
| `--surface` | `#FFFFFF` | `#14161A` | Cards, header, and form plates |
| `--raised` | `#F2EFE9` | `#1C1F24` | Alternate bands, table headers |
| `--ink` | `#14161A` | `#F4F3F0` | Primary typography |
| `--muted` | `#4A4F57` | `#C3C7CD` | Secondary body copy |
| `--subtle` | `#6B7078` | `#949AA3` | Captions & metadata |
| `--line` | `#E2DED6` | `#2A2E34` | Hairline borders |
| `--line-strong` | `#C9C3B8` | `#3A3F47` | Interactive boundaries & input borders |
| `--accent` | `#A84A06` | `#E9A85C` | Primary interactive CTA signal (burnished copper / luminous amber) |
| `--accent-hover` | `#8A3B05` | `#F3C088` | Interactive hover & pressed state |
| `--accent-soft` | `#F8EDE1` | `rgba(233, 168, 92, 0.12)` | Badges and callouts |
| `--on-accent` | `#FFFFFF` | `#14161A` | Foreground text on accent buttons |
| `--warning` | `#9A3412` | `#F0A45C` | Warning alerts |
| `--danger` | `#B42318` | `#F0776C` | Destructive alerts & errors |
| `--success` | `#1B6B45` | `#57C08A` | Verified and completed status |
| `--focus` | `#A84A06` | `#E9A85C` | Primary focus indicator |
| `--overlay` | `rgb(0 0 0 / 0.18)` | `rgb(0 0 0 / 0.5)` | Modal and drawer backdrop wash |
| `--night` | `#14161A` | `#14161A` | Fixed dark hero ground |
| `--night-ink` | `#FAF9F7` | `#FAF9F7` | Fixed dark hero display text |
| `--night-muted` | `#C9C4BB` | `#C9C4BB` | Fixed dark hero supporting copy |
| `--night-accent` | `#E9A85C` | `#E9A85C` | Fixed dark hero luminous amber signal |

### Contrast & Legibility Benchmarks (WCAG 2.2 AA/AAA)

Every pair is mathematically verified to exceed standard requirements:
- `ink` on `canvas`: Light `17.21:1` (AAA) / Dark `17.63:1` (AAA)
- `ink` on `surface`: Light `18.11:1` (AAA) / Dark `16.32:1` (AAA)
- `ink` on `raised`: Light `15.78:1` (AAA) / Dark `14.89:1` (AAA)
- `muted` on `surface`: Light `8.24:1` (AAA) / Dark `10.67:1` (AAA)
- `muted` on `raised`: Light `7.18:1` (AAA) / Dark `9.73:1` (AAA)
- `subtle` on `surface`: Light `4.98:1` (AA) / Dark `6.39:1` (AA)
- `accent` on `surface`: Light `5.76:1` (AA) / Dark `8.81:1` (AAA)
- `accent` on `canvas`: Light `5.47:1` (AA) / Dark `9.52:1` (AAA)
- `accent` on `raised`: Light `5.02:1` (AA) / Dark `8.04:1` (AAA)
- `on-accent` on `accent`: Light `5.76:1` (AA) / Dark `8.81:1` (AAA)
- `warning` on `surface`: Light `7.31:1` (AAA) / Dark `8.77:1` (AAA)
- `danger` on `surface`: Light `6.57:1` (AA) / Dark `6.52:1` (AA)
- `success` on `surface`: Light `6.49:1` (AA) / Dark `8.03:1` (AAA)
- `night-ink` on `night`: Light `17.21:1` (AAA) / Dark `17.21:1` (AAA)
- `night-muted` on `night`: Light `10.43:1` (AAA) / Dark `10.43:1` (AAA)
- `night-accent` on `night`: Light `8.81:1` (AAA) / Dark `8.81:1` (AAA)

---

## 3. Typography & Anti-Chrome Governance

### Type Families
Self-hosted WOFF2 in `static/fonts/` (SIL OFL licences included):
- **Display:** Space Grotesk, 500–700 (headings, architectural titles)
- **UI & Body:** Inter, 400–600 (body copy, form controls, interface actions)
- **Data & Verification:** JetBrains Mono, 500–600 (cryptographic hashes, certificate UUIDs, audit codes)

### Typographic Scale
`display-1`, `display-2`, `h1`, `h2`, `h3`, `h4`, `body-lg`, `body`, `small`, `2xs`, `3xs`. Body measure is constrained to `62–68ch`. Max three type sizes per viewport band.

### Anti-Chrome Rules
1. **Permanent Ban on Middle-Dot Separators:** Do not use middle-dot metadata separators (`A · B · C`). Use semantic badges, spacing, or explicit layout containers.
2. **Permanent Ban on Tracked-Out Eyebrows:** Do not place tracked-out all-caps kicker/eyebrow labels above headings. Let the typographic scale and section structure establish hierarchy.
3. **No Decorative Monospace Numerals:** Do not render numbers or metrics in monospace simply for aesthetic styling. Monospace is strictly reserved for verification hashes, certificate IDs, and system audit codes.
4. **Mandatory Tabular Numerals:** All financial metrics, candidate counts, cohort dates, and tabular data tables must enforce `font-variant-numeric: tabular-nums` (`.tabular-nums`) to prevent columnar jitter.

---

## 4. Browser Surface Craft Floor & Tier-1 Detail

### 1. Impeccable Surface Floor
- **Selection:** `background: color-mix(in oklab, var(--accent) 26%, transparent)` across all surfaces.
- **Caret Color:** Form inputs, selects, and textareas adopt `caret-color: var(--accent)`.
- **Multi-Layer Diffuse Focus Ring:** On `:focus-visible`, an inner 1px surface boundary, 3px accent ring, and outer 6–7px diffuse bloom (`color-mix(in oklab, var(--accent) 30%, transparent)`) eliminate harsh browser default outlines while preserving high visibility.
- **Forced Colors Resilience:** When `@media (forced-colors: active)` is detected, focus outlines automatically revert to `2px solid Highlight`.

### 2. Physical Micro-Tactility & Lighting
- **Button Active Compression:** Primary and secondary buttons compress by `transform: scale(0.982)` on `:active:not(:disabled)` with a 120ms cubic-bezier transition.
- **Top-Edge Specular Bevel Lighting:** Primary buttons receive top-edge specular lighting (`inset 0 1px 0 rgba(255, 255, 255, 0.22)` in Light Mode; `inset 0 1px 0 rgba(255, 255, 255, 0.35)` in Dark Mode). Dark cards feature a hairline top specular rim (`inset 0 1px 0 rgba(255, 255, 255, 0.06)`).
- **Ambient Elevation Blooms:** Elevated `.card-interactive` surfaces lift `translateY(-2px)` on hover, with a warm ambient bloom in Light Mode (`0 4px 12px -2px rgb(0 0 0 / 0.08), 0 12px 28px -6px color-mix(in oklab, var(--accent) 15%, transparent)`) and in Dark Mode (`0 6px 16px -2px rgba(0, 0, 0, 0.45), 0 14px 32px -6px color-mix(in oklab, var(--accent) 18%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.08)`).
- **Physical Inset Recess on Inputs:** Text fields, selects, and textareas feature a subtle physical inset recess (`box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.04)` in Light Mode; `box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.32)` in Dark Mode).
- **iOS Safari 16px Minimum Input Floor:** On viewports `<= 640px`, text inputs enforce `font-size: 1rem` to defeat iOS auto-zoom without sacrificing desktop typography.

---

## 5. Kinetic Motion Standard

All motion is purposeful, instantaneous, and strictly disabled under `@media (prefers-reduced-motion: reduce)`:
- **Kinetic Step Entrance (`stepSlideIn`):** 220ms smooth physical entrance (`translateY(8px)` to `0`) for wizard steps and tab panels.
- **Validation Spring Shake (`errorShake`):** 320ms spring cubic-bezier (`.is-shaking`, `[data-step].is-shaking`, `.animate-error-shake`) for form steps and inputs failing validation.
- **Holographic Security Shimmer (`credentialShimmer`):** 2.2s continuous 105° gradient sweep across verified credential reference badges.
- **Toast Drain (`toastDrain`):** Animated 2px bottom bar dynamically synchronized with `--toast-delay` autodismiss timer.

---

## 6. Structural Components & Layout

- **Container:** 76rem base, 84rem at ≥1536px, 90rem at ≥1920px; gutters 20 / 24 / 32 / 48px.
- **Grid:** 12-column grid, 24px gap (16px mobile).
- **Section Rhythm:** `clamp(4.5rem, 8vw, 8rem)`.
- **Radii:** 6px field (`--radius-field`), 10px card (`--radius-card`), 14px media (`--radius-media`).
- **Data Tables:** `.data-table` renders desktop sticky headers at `md` breakpoint and responsive labelled card layouts on mobile.
- **Overlays:** Native `<dialog class="drawer">`, `#confirm-dialog`, `#toast-stack`.
- **Dropzone:** Tactile drag-and-drop zone wrapping native Django `form.resume` with pre-flight PDF format verification, <=5 MB size checks, live file card, and remove action.

---

## 7. Guardrails & Automated Quality Verification

1. **`TemplateGuardTests` in `tests/test_ui_system.py`:** Fails if any 6-digit hex color (`#[0-9a-fA-F]{6}`) appears in non-email HTML templates, or if legacy font/component classes are introduced.
2. **`check_contrast.py`:** Verifies all 16 theme token contrast pairs against WCAG AA 4.5:1 minimums across both Light and Dark palettes.
3. **Owner Protection:** Never alter account `mohdfaizanali038@gmail.com`.
4. **Deterministic CSS Payload:** Standalone `./tailwindcss` compiles `static/css/input.css` into `static/css/output.css` with a strict <= 65 KB minified budget.
