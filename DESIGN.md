# GCTT Design System Specification: Modern Atmospheric

> **Identity**: Modern Atmospheric — High-trust, executive IT staffing, recruitment, and academy platform.
> **Guiding Principle**: Pairs dark, deep backgrounds (`#0f172a`) in the hero, testimonials, and statutory footers with clean, off-white surfaces (`#f8f9fa`) for detailed features, candidate matrices, and job listings. Typography is a critical pillar, using **Lora** (serif) for large expressive headlines, **Inter** (sans) for high-legibility body/UI text, and **Space Grotesk** (display) for accents and branding.

---

## 1. Visual Language & Token Definitions

### Base Palette
| Token | Value | Role / Usage |
|:---|:---|:---|
| `--color-brand-dark` | `#0f172a` | Primary Dark (Hero, Testimonials, Dark CTA, Statutory Footer) |
| `--color-brand-indigo` | `#6366f1` | Brand Indigo (Primary buttons, active indicators, accent glows) |
| `--color-brand-indigo-hover` | `#4f46e5` | Indigo hover state |
| `--color-surface-white` | `#f8f9fa` | Surface White (Feature cards canvas, practice bento grids) |
| `--color-card-white` | `#ffffff` | Pure white cards on off-white surfaces |
| `--color-border-white` | `rgba(255, 255, 255, 0.1)` | Hairline border for dark & glassmorphic surfaces |
| `--color-border-slate` | `#e2e8f0` | Hairline border for light feature surfaces |
| `--color-ink` | `#0f172a` | Primary typography on light surfaces |
| `--color-ink-muted` | `#475569` | Secondary text, descriptions |
| `--color-ink-subtle` | `#64748b` | Metadata, tags, captions |
| `--color-text-white` | `#f8fafc` | Primary typography on dark surfaces |

### Typography Hierarchy
| Role | Family Stack | Spec |
|:---|:---|:---|
| **Headlines** | `"Lora", Georgia, Cambria, serif` | 400-700 weight, `tracking-tight`, `leading-[1.1]` |
| **UI / Body** | `"Inter", -apple-system, BlinkMacSystemFont, sans-serif` | 400-600 weight, `leading-relaxed` |
| **Accents / Branding** | `"Space Grotesk", sans-serif` | 500-700 weight, `tracking-tight` |

### Glassmorphism Tokens
- **Soft Glass (`.glass-soft`)**:
  ```css
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  ```
- **Strong Glass (`.glass-strong`)**:
  ```css
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  ```

### Effects & Atmosphere
- **Outer Glow (`.outer-glow-indigo`)**:
  `radial-gradient(from-indigo-500 via-purple-500 to-pink-500), blur(20px), opacity(0.3)`
- **Grid Overlays (`.grid-overlay`)**:
  Subtle 1px grid pattern with radial/linear-gradient mask:
  ```css
  background-image: 
    linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 50%, #000 70%, transparent 100%);
  ```

### Signature Micro-Animations
1. **Typing Cursor (`.typing-cursor`)**:
   Flashing terminal cursor after highlighted text:
   `content: '|'; animation: cursor-blink 1s step-end infinite;`
2. **180-Degree Logo Rotation (`.logo-hover-180`)**:
   Rotates smoothly 180 degrees on hover:
   `transform: rotate(180deg); transition: transform 600ms cubic-bezier(0.34, 1.56, 0.64, 1);`
3. **500ms Sticky Navigation State (`.nav-sticky-atmospheric`)**:
   Smooth 500ms transition for background, border, and shadow when header becomes sticky.

---

## 2. Layout & Architectural Rhythm

1. **Top Utility Strip**: Deep dark ground (`#0b1120`), emerald pulsing dot, E-Verify & Direct Texas W2 badges.
2. **Hero Band**: Deep dark `#0f172a`, grid overlay, radial outer glow, Lora headline, typing cursor, Brand Indigo CTA.
3. **Features & Practices**: High-contrast transition to `#f8f9fa` off-white canvas with pure white elevated cards (`#ffffff`).
4. **Testimonials**: Deep dark `#0f172a` canvas, soft glass cards (`.glass-soft`), Lora italic quotes.
5. **Academy & Training Sandbox**: Off-white `#f8f9fa` canvas with interactive tabs and verified certificate preview.
6. **Statutory Footer**: Deep dark `#0f172a` with Space Grotesk section titles and Irving, Texas corporate anchor.
