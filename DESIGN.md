# GCT (GC Tekton) Design System — World 1: Admiralty Hydrography

This is the single source of truth for the GCT (GC Tekton) digital experience and user interface.

---

## 1. Direction & Institutional Identity

**World 1: Admiralty Hydrography** is GCT's permanent institutional design system.

The physical and philosophical grounding draws from 20th-century British Admiralty nautical charts, NOAA bathymetric depth surveys, and precision brass-caliper maritime instrumentation. The aesthetic register embodies an elite technical search and industrial staffing institution executed with luxury digital craft: neither SaaS gradient-marketing, nor playful bento grids, nor raw neo-brutalism.

The design system fuses natively with GCT's dual vectorized brand identity:
- **Light Logo (`logo-horizontal.svg` / `logo-main.png`):** Deep oceanic navy (`#092853`, `#1A375E`), nautical cobalt (`#158CC9`), and vibrant hydro cyan (`#0FB1E5`, `#26ADDC`).
- **Dark Logo (`logo-horizontal-dark.svg` / `logo-main-dark.png`):** Crisp platinum-ink (`#ECECEC`, `#E3E3E3`), abyssal navy plate (`#153461`), and luminous cyan signal (`#2CD1EE`, `#35B7DF`).

### Core Design Principles
1. **Divide by capability, not audience:** Clear architectural modules over marketing fluff.
2. **One accent, used as a disciplined signal:** High-contrast marine cobalt in light mode and luminous hydro cyan in dark mode guide action without visual fatigue.
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
| `--canvas` | `#F4F7FA` | `#071426` | Page ground (cool hydrographic chart rag / abyssal bathysphere navy) |
| `--surface` | `#FFFFFF` | `#0D1F38` | Card & header plate (mirrors dark logo `#153461` tone) |
| `--raised` | `#E8EFF6` | `#142B4B` | Secondary elevation / table header bands |
| `--ink` | `#091E3A` | `#ECF1F6` | Primary typography (deep oceanic navy / crisp platinum) |
| `--muted` | `#364B63` | `#A9BFD6` | Secondary body copy |
| `--subtle` | `#4D6278` | `#87A3C0` | Captions & metadata |
| `--line` | `#CEDAE6` | `#1E3758` | Structural hairline rule |
| `--line-strong` | `#768BA0` | `#5D7B9D` | Interactive boundary & input border (≥ 3:1 UI contrast) |
| `--accent` | `#005F91` | `#35C9EA` | Primary interactive CTA signal (marine cobalt / hydro cyan) |
| `--accent-hover` | `#004970` | `#62DAF3` | Interactive hover & pressed state |
| `--accent-soft` | `#E1F2FA` | `#103552` | Tinted badge / chip wash |
| `--on-accent` | `#FFFFFF` | `#06182B` | Foreground text on accent buttons |
| `--warning` | `#9A5700` | `#F0B429` | Maritime brass ochre alert |
| `--danger` | `#B42318` | `#F87171` | Signal buoy crimson alert |
| `--success` | `#0D6E48` | `#34D399` | Soundings emerald confirmation |
| `--focus` | `#005F91` | `#35C9EA` | Primary focus indicator |
| `--overlay` | `rgb(9 30 58 / 0.18)` | `rgb(0 0 0 / 0.5)` | Modal and drawer backdrop wash |
| `--night` | `#081C38` | `#05101F` | Fixed dark hero ground |
| `--night-ink` | `#F2F6FA` | `#F2F6FA` | Fixed dark hero display text |
| `--night-muted` | `#A8C0D8` | `#A8C0D8` | Fixed dark hero supporting copy |
| `--night-accent` | `#2CD1EE` | `#2CD1EE` | Fixed dark hero luminous cyan signal |

### Contrast & Legibility Benchmarks (WCAG 2.2 AA/AAA)

Every pair is mathematically verified to exceed standard requirements:
- `ink` on `canvas`: Light `15.52:1` (AAA) / Dark `16.25:1` (AAA)
- `ink` on `surface`: Light `16.69:1` (AAA) / Dark `14.55:1` (AAA)
- `ink` on `raised`: Light `14.39:1` (AAA) / Dark `12.51:1` (AAA)
- `muted` on `surface`: Light `8.96:1` (AAA) / Dark `8.75:1` (AAA)
- `muted` on `raised`: Light `7.73:1` (AAA) / Dark `7.52:1` (AAA)
- `subtle` on `surface`: Light `6.30:1` (AA) / Dark `6.32:1` (AA)
- `subtle` on `raised`: Light `5.43:1` (AA) / Dark `5.44:1` (AA)
- `accent` on `surface`: Light `6.89:1` (AA) / Dark `8.42:1` (AAA)
- `accent` on `canvas`: Light `6.41:1` (AA) / Dark `9.40:1` (AAA)
- `accent` on `raised`: Light `5.95:1` (AA) / Dark `7.24:1` (AAA)
- `on-accent` on `accent`: Light `6.89:1` (AA) / Dark `9.11:1` (AAA)
- `line-strong` on `surface`: Light `3.52:1` (UI Component ≥ 3:1) / Dark `3.77:1` (UI Component ≥ 3:1)
- `warning` on `surface`: Light `5.62:1` (AA) / Dark `8.87:1` (AAA)
- `danger` on `surface`: Light `6.57:1` (AA) / Dark `5.98:1` (AA)
- `success` on `surface`: Light `6.29:1` (AA) / Dark `8.60:1` (AAA)
- `night-ink` on `night`: Light `15.68:1` (AAA) / Dark `17.57:1` (AAA)
- `night-muted` on `night`: Light `9.08:1` (AAA) / Dark `10.18:1` (AAA)
- `night-accent` on `night`: Light `9.29:1` (AAA) / Dark `10.42:1` (AAA)

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
- **Selection:** Light mode uses `rgba(0, 95, 145, 0.18)` with ink `#091E3A`; Dark mode uses `rgba(53, 201, 234, 0.26)` with ink `#ECF1F6`.
- **Caret Color:** Form inputs, selects, and textareas adopt `caret-color: var(--accent)`.
- **Multi-Layer Diffuse Focus Ring:** On `:focus-visible`, an inner 1px surface boundary, 3px accent ring, and outer 6–7px hydrocyan bloom eliminate harsh browser default outlines while preserving high visibility.
- **Forced Colors Resilience:** When `@media (forced-colors: active)` is detected, focus outlines automatically revert to `2px solid Highlight`.

### 2. Physical Micro-Tactility & Lighting
- **Button Active Compression:** Primary and secondary buttons compress by `transform: scale(0.982)` on `:active:not(:disabled)` with a 120ms cubic-bezier transition.
- **Top-Edge Specular Bevel Lighting:** Primary buttons receive top-edge specular lighting (`inset 0 1px 0 rgba(255, 255, 255, 0.22)` in Light Mode; `inset 0 1px 0 rgba(255, 255, 255, 0.35)` in Dark Mode). Dark cards feature a hairline top specular rim (`inset 0 1px 0 rgba(255, 255, 255, 0.06)`).
- **Ambient Elevation Blooms:** Elevated `.card-interactive` surfaces lift `translateY(-2px)` on hover, with a deep navy ambient bloom in Light Mode (`0 4px 12px -2px rgba(9, 30, 58, 0.08), 0 12px 28px -6px rgba(0, 95, 145, 0.10)`) and an abyssal cyan bloom in Dark Mode (`0 6px 16px -2px rgba(0, 0, 0, 0.45), 0 14px 32px -6px rgba(53, 201, 234, 0.12)`).
- **Physical Inset Recess on Inputs:** Text fields, selects, and textareas feature a subtle physical inset recess (`box-shadow: inset 0 1px 2px rgba(9, 30, 58, 0.07)` in Light Mode; `box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.32)` in Dark Mode).
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
