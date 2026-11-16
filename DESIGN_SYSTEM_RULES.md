# GCTT & Kani-Inspired Design System Architecture

This document establishes the official Design System structure, token contracts, styling conventions, component patterns, and motion standards for **GCTT** (`gctekton.com`), incorporating the high-impact visual design language of **Kani Solutions**.

---

## 1. Design System Structure & Token Definitions

### Token Location
- **Primary Source of Truth**: `static/css/input.css` and compiled output `static/css/output.css`.
- **Theme Variables**: Defined in CSS `:root` and `html.dark` blocks, mapped to Tailwind CSS utilities.

### Color Palette (Deep Sapphire, Electric Violet & Sky Luminous Gradient)
```css
:root {
  /* Canvas Surfaces (Light Mode) */
  --paper: #FFFFFF;
  --surface: #F8FAFC;
  --card: #FFFFFF;
  --line: #E2E8F0;
  --line-subtle: #F1F5F9;

  /* Typography */
  --ink: #0B192C;
  --ink-muted: #334155;
  --ink-subtle: #64748B;

  /* Primary Brand: Royal Sapphire & Electric Violet */
  --brand: #0B192C;
  --brand-2: #1E3E62;
  --accent: #2563EB;
  --accent-hover: #1D4ED8;

  /* Kani Gradient Tokens */
  --kani-gradient-start: #3D1DFF;
  --kani-gradient-mid: #6147FF;
  --kani-gradient-end: #00B4D8;

  /* Status & Compliance */
  --status-verified: #10B981;
  --status-verified-subtle: rgba(16, 185, 129, 0.12);
  --status-tech: #38BDF8;
}

html.dark {
  /* Canvas Surfaces (Dark Mode - Midnight Slate) */
  --paper: #080D16;
  --surface: #0F172A;
  --card: #131E33;
  --line: #1E293B;
  --line-subtle: #141F36;

  /* Typography */
  --ink: #F8FAFC;
  --ink-muted: #CBD5E1;
  --ink-subtle: #94A3B8;

  /* Primary Brand */
  --brand: #0B192C;
  --brand-2: #1E3E62;
  --accent: #3B82F6;
  --accent-hover: #60A5FA;

  /* Kani Gradient Tokens (Dark Mode) */
  --kani-gradient-start: #818CF8;
  --kani-gradient-mid: #60A5FA;
  --kani-gradient-end: #34D399;

  /* Status & Compliance */
  --status-verified: #10B981;
  --status-verified-subtle: rgba(16, 185, 129, 0.15);
  --status-tech: #38BDF8;
}
```

### Typography Hierarchy
- **Display Headings**: `font-display` (`Plus Jakarta Sans` / `Playfair Display`, 800/900 weight, `tracking-tight`).
- **Body & Controls**: `font-sans` (`Plus Jakarta Sans`, `system-ui`, `-apple-system`, 400/500/600 weight, `leading-relaxed`).
- **Data, Codes & Metrics**: `font-mono` (`JetBrains Mono`, `ui-monospace`, 600/700 weight, uppercase tracking).

---

## 2. Component Library & Architecture

Components in this Django project follow a modular partial architecture:
- `templates/partials/_header.html` — Sticky executive navigation bar, adaptive vector SVG logo, mobile slide-over drawer, and theme controller.
- `templates/partials/_footer.html` — Full statutory corporate footer, Irving TX legal notices, directory, and contact coordinates.
- `templates/partials/_messages.html` — Dismissible flash feedback notifications.
- `templates/partials/_pagination.html` — Accessible pagination controls.
- `templates/pages/home.html` — Kani-inspired high-impact homepage layout (Hero, Industries Metric Grid, Core Services Bento, Specialized Solutions, Achievements, Academy Sandbox, Portal Preview, Testimonials, FAQ, Corporate Governance).

### Key Component Patterns
1. **Avatar Social Proof Stack**:
   Circular multi-element badge (`TX`, `W2`, `DFW`) + live pulsing green dot + institutional text.
2. **Kani Gradient Highlight**:
   Vibrant linear gradient clipped to text: `bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400 bg-clip-text text-transparent`.
3. **Glassmorphic Metric Tiles (`.industries-grid`)**:
   Clean white rounded-2xl cards with subtle box-shadow (`box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06)`), prominent stat, uppercase tag, and subtext.
4. **Bento Grid Architecture (`.core-services`)**:
   Responsive multi-column cards with large hero spans, vector icon illustrations, and interactive hover lifts.
5. **Interactive Console**:
   Tabbed switcher switching between live vetting metrics and Texas SOW terms.

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
  - Rocket glyph: `<path stroke-linecap="round" stroke-linejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />`.

---

## 6. Styling Approach & Motion Standards

### Motion Timing & Curves
- **Standard Transitions**: `duration-200 ease-out` (150ms–250ms).
- **Spring Curves**: `cubic-bezier(0.16, 1, 0.3, 1)` for smooth card lifts and tab reveals.
- **Typewriter Animation**: Dynamic real-time cycling of core technical values with blinking cursor.
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
