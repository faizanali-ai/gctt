# GCTT Design System Architecture & Figma MCP Integration Rules

This document establishes the official Design System structure, token contracts, styling conventions, component patterns, and motion standards for **GCTT** (`gctekton.com`).

---

## 1. Design System Structure & Token Definitions

### Token Location
- **Primary Source of Truth**: `static/css/input.css` and compiled output `static/css/output.css`.
- **Theme Variables**: Defined in CSS `:root` and `.dark` blocks, mapped to Tailwind CSS utilities.

### Color Palette (Deep Sapphire & Institutional Trust)
```css
:root {
  /* Canvas Surfaces (Light Mode) */
  --bg-canvas: #F8FAFC;
  --bg-card: #FFFFFF;
  --bg-surface: #F1F5F9;
  --line: #E2E8F0;

  /* Typography */
  --ink: #0F172A;
  --ink-muted: #64748B;
  --ink-subtle: #94A3B8;

  /* Primary Brand: Royal Sapphire */
  --accent: #2563EB;
  --accent-hover: #1D4ED8;
  --accent-subtle: rgba(37, 99, 235, 0.1);

  /* Status & Compliance */
  --status-verified: #10B981;
  --status-verified-subtle: rgba(16, 185, 129, 0.12);
  --status-tech: #38BDF8;
}

.dark {
  /* Canvas Surfaces (Dark Mode - Midnight Slate) */
  --bg-canvas: #090D16;
  --bg-card: #0E1422;
  --bg-surface: #131B2E;
  --line: rgba(255, 255, 255, 0.08);

  /* Typography */
  --ink: #FFFFFF;
  --ink-muted: #94A3B8;
  --ink-subtle: #64748B;

  /* Primary Brand: Royal Sapphire */
  --accent: #3B82F6;
  --accent-hover: #2563EB;
  --accent-subtle: rgba(59, 130, 246, 0.15);

  /* Status & Compliance */
  --status-verified: #10B981;
  --status-verified-subtle: rgba(16, 185, 129, 0.15);
  --status-tech: #38BDF8;
}
```

### Typography Hierarchy
- **Display Headings**: `font-display` (`Plus Jakarta Sans`, 800/900 weight, `tracking-tight`).
- **Body & Controls**: `font-sans` (`system-ui`, `-apple-system`, `sans-serif`, 400/500/600 weight, `leading-relaxed`).
- **Data, Codes & Metrics**: `font-mono` (`JetBrains Mono`, `ui-monospace`, 600 weight, uppercase tracking).

---

## 2. Component Library & Architecture

Components in this Django project follow a modular partial architecture:
- `templates/partials/_header.html` — Sticky executive navigation bar, adaptive SVG logo, mobile slide-over drawer, and theme controller.
- `templates/partials/_footer.html` — Full statutory corporate footer, Irving TX legal notices, and directory.
- `templates/partials/_messages.html` — Dismissible flash feedback notifications.
- `templates/partials/_pagination.html` — Accessible pagination controls.
- `templates/pages/` — Modular full-page templates extending `templates/base.html`.

### Component Design Conventions
1. **Hairline Precision**: All borders use thin 1px lines (`border-line` or `border-white/10`). Never use heavy 2px/3px borders on cards.
2. **Glassmorphism**: Sticky and elevated elements use `backdrop-blur-md bg-paper/95` or `bg-card/95`.
3. **No Stock Photo Clutter**: Replace all generic stock photos with structured, high-conviction interactive UI components (Bento consoles, metric scorecards, practice matrices).

---

## 3. Frameworks, Libraries & Build System

- **Backend**: Python 3.12 + Django 5.x.
- **Frontend CSS Engine**: Tailwind CSS v4 standalone CLI binary (`./tailwindcss`).
- **Build Command**:
  ```bash
  ./tailwindcss -i static/css/input.css -o static/css/output.css --minify
  ```
- **Deployment Target**: Render Web Service (`render.yaml`), single domain `gctekton.com`.

---

## 4. Asset Management & Optimization

- **SVGs & Vector Marks**: Stored in `static/images/` and inlined where high-contrast dynamic theming is required.
- **Logo Asset**: `static/images/logo.svg` contains pure white text (`fill="#FFFFFF"`) and `#38BDF8` subtitle to ensure flawless dark mode contrast.
- **Zero Heavy Rasters**: No multi-megabyte unoptimized imagery on the homepage; all visual engagement is driven by CSS, vector SVGs, and responsive micro-interactions.

---

## 5. Icon System

- **Icon Standard**: Clean SVG icons rendered with `fill="none" stroke="currentColor" stroke-width="2"` and `aria-hidden="true"`.
- **Key Glyphs**:
  - Checkmarks: `<polyline points="20 6 9 17 4 12" />` in `--status-verified`.
  - Arrow links: `<path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />`.
  - Status Pulses: In-DOM pulsing dot: `<span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>`.

---

## 6. Motion & Animation Standards (Figma Motion & Impeccable)

### Motion Timing & Curves
- **Standard Transitions**: `duration-200 ease-out` (150ms–250ms).
- **Spring Curves**: `cubic-bezier(0.16, 1, 0.3, 1)` for smooth card lifts and tab reveals.
- **Reduced Motion Directive**:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```

### Micro-Interactions on GCTT:
1. **Interactive Console Tab Switch**: Smooth cross-fade between `Capability Specs` and `Texas SOW Terms`.
2. **Card Hover States**: `transition-all duration-200 hover:border-blue-500/40 hover:-translate-y-0.5`.
3. **Button Press**: Subtle scale transition `active:scale-[0.98]`.

---

## 7. Project Structure

```
/home/mohdfaizanali/Projects/GCTT/
├── config/                  # Django project configuration & root URLs
├── apps/
│   ├── accounts/            # User authentication, RBAC, 2FA, dashboard
│   ├── jobs/                # Mandates, LinkedIn posting & candidate application wizard
│   ├── training/            # Academy courses, sandboxes, AI career advisor
│   └── enquiries/           # Enterprise consultation and contact handling
├── static/
│   ├── css/                 # input.css & compiled output.css
│   └── images/              # logo.svg & brand assets
├── templates/
│   ├── base.html            # Root layout with HTML5 metadata and theme scripts
│   ├── pages/               # home.html, about.html, etc.
│   └── partials/            # _header.html, _footer.html, _messages.html
├── tests/                   # 118 unit and regression tests
├── tailwindcss              # Standalone Tailwind CLI compiler
└── render.yaml              # Render production build and deploy spec
```
