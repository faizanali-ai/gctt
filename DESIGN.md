# GCTT Design System

This is the single source of truth for the GCTT interface. `DESIGN_SYSTEM_RULES.md` is superseded.

## Direction

Warm institutional modernism. Ink neutrals, warm paper, a single copper signal, editorial grid discipline, hairline rules, and abstract line geometry instead of photography. The register is an executive search firm executed with modern product craft: not SaaS gradient-marketing, not bento dashboards, not neo-brutalism.

Principles:
1. Divide by capability, not audience.
2. One accent, used as a signal.
3. Type and rules do the work.
4. Nothing product-level above the fold.
5. Motion reveals structure; it never delays reading.
6. Both themes are first-class.
7. Every surface is tokenised.

## Tokens

Defined in `static/css/input.css`. Raw values live in `:root`; dark values override them under `:root[data-theme="dark"]`, with a `prefers-color-scheme` fallback while no choice is stored; utilities are mapped with `@theme inline`.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--canvas` | `#FAF9F7` | `#0B0C0E` | Page ground |
| `--surface` | `#FFFFFF` | `#14161A` | Cards, header, forms |
| `--raised` | `#F2EFE9` | `#1C1F24` | Alternate band, table header |
| `--ink` | `#14161A` | `#F4F3F0` | Primary text |
| `--muted` | `#4A4F57` | `#C3C7CD` | Secondary text |
| `--subtle` | `#6B7078` | `#949AA3` | Meta and captions |
| `--line` | `#E2DED6` | `#2A2E34` | Hairline borders |
| `--line-strong` | `#C9C3B8` | `#3A3F47` | Input borders |
| `--accent` | `#A84A06` | `#E9A85C` | Actions, links, active state |
| `--accent-hover` | `#8A3B05` | `#F3C088` | Hover and pressed |
| `--accent-soft` | `#F8EDE1` | `rgba(233,168,92,.12)` | Badges and callouts |
| `--on-accent` | `#FFFFFF` | `#14161A` | Text on accent fill |
| `--success` | `#1B6B45` | `#57C08A` | Verified and complete |
| `--warning` | `#9A3412` | `#F0A45C` | Pending |
| `--danger` | `#B42318` | `#F0776C` | Errors |

Fixed "night" surfaces (hero, proof band, job header) do not flip: `--night`, `--night-ink`, `--night-muted`, `--night-accent`. Use `text-night-accent` on night surfaces; the theme accent is too dark there (3.15:1).

Contrast rules: body ≥4.5:1, large text and UI ≥3:1, focus ring ≥3:1. Never accent for paragraph text. Status always has a text label.

## Typography

Self-hosted WOFF2 in `static/fonts/` (SIL OFL licences included).

- Display: Space Grotesk, 500–700
- UI/body: Inter, 400–600
- Data/meta: JetBrains Mono, 500–600

Scale: `display-1`, `display-2`, `h1`, `h2`, `h3`, `h4`, `body-lg`, `body`, `small`, `2xs`, `3xs`, `eyebrow`. Body measure 62–68ch. Max three sizes per viewport band.

## Layout

- Container: 76rem base, 84rem at ≥1536px, 90rem at ≥1920px; gutters 20 / 24 / 32 / 48.
- 12-column grid, 24px gap (16px mobile).
- Section rhythm `clamp(4.5rem, 8vw, 8rem)`.
- Radii: 6px field, 10px card, 14px media. Pills only for chips.
- One overlay elevation token. Cards have no resting shadow.
- Hairline bands, not alternating background colours everywhere.

## Components

`static/css/input.css` owns the base styles. Templates compose them.

- Buttons: `.btn`, `.btn-primary`, `.btn-solid`, `.btn-secondary`, `.btn-ghost`, `.btn-link`, `.btn-sm`, `.btn-lg`.
- Surfaces: `.card`, `.card-interactive`, `.ink-band`, `.rule`.
- Chips: `.chip`, `.chip-accent`, `.chip-success`, `.chip-warning`, `.chip-danger`, `.status-dot`.
- Forms: `.form`, `.field`, `.field-error`, `.hint`, `.errorlist`. Style by element inside `.form`; never inject widget classes in Python.
- Data: `.data-table` (tables on desktop, labelled cards on mobile).
- Navigation: `.nav-link`, `.nav-indicator`, `.subnav`, `.portal-link`, `.portal-group`.
- Overlays: native `<dialog class="drawer">`, `#confirm-dialog`, `#toast-stack`.
- Motion: `.reveal`, `.js-ready`, `.hover-lift`, `.marquee`.

Partials: `_header`, `_footer`, `_messages`, `_pagination`, `_hero`, `_hero-art`, `_field`, `_geometry`, `_solutions_nav`, `_academy_nav`, `_nav` (portal). Icons are one sprite at `static/images/icons.svg`.

## Theme

The OS preference sets the default. The header toggle writes `light` or `dark` to `data-theme` on `<html>` and to `localStorage` (`gctt-theme`); `static/js/theme-init.js` applies it before the stylesheet to avoid a flash. Night surfaces are intentionally fixed.

## Motion

- Scroll reveal: 260ms, 12px rise, once, intersection threshold .15.
- Hero entrance: 3 elements, 60ms stagger, on first paint only.
- Hover: 180ms.
- Nav indicator: 2px copper bar, transform-based.
- Page transitions: View Transitions API where supported.
- Marquee: 40s, pauses on hover/focus.

All motion is disabled under `prefers-reduced-motion`.

## Accessibility

WCAG 2.2 AA. Skip link, one `<h1>`, visible focus, 24×24 target minimum, native dialog focus containment, labelled tables, visible form labels, `aria-describedby` error wiring, status labels (never colour alone), 200% zoom and 320px reflow.

## Guardrails

- `tests/test_ui_system.py` fails on hardcoded hex in templates, legacy theme/font code, `alert()`/`confirm()`, inline handlers, non-JSON-LD inline scripts, legacy component classes, missing compiled utilities, or more than one `<h1>`.
- Rebuild `output.css` after any class change. CI rebuilds at v4.3.5 and fails on a diff.
- The Tailwind build uses `source(none)` with explicit `@source` roots (`templates/`, `static/js/`). Add a root here if a new directory starts carrying class names. Never let it scan `output.css`.
- Keep class names literal in templates; Tailwind cannot see classes built in Python.
- Templates must not hardcode `/static/...`; use `{% static %}`.

## Files

```
static/css/input.css          tokens, base, components, motion
static/css/output.css         compiled, committed
static/css/certificate.css    A4 print document
static/js/ui.js               dialogs, toasts, stepper, advisor, reveals
static/fonts/                 self-hosted WOFF2 + OFL licences
static/images/icons.svg       icon sprite
static/images/logo-*.png      brand logos and favicon
templates/base.html           marketing shell
templates/accounts/base_auth  minimal auth shell
templates/portals/base_portal portal shell
```
