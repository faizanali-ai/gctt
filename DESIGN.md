# GCTEKTON DESIGN SYSTEM CONSTITUTION
## THE ULTIMATE FLAGSHIP SPECIFICATION: OBSIDIAN & NEON LIME KINETIC CRAFT

---

## 1. Visual Philosophy & Core Pillars
The GCTekton interface is an ultra-modern, high-performance enterprise platform merging three architectural paradigms:
1. **Obsidian & Neon Lime Glassmorphism**: Deep black outer viewport (`#000000`) enclosing a floating hardware-like shell (`#0c0c0c`, `rounded-[2.5rem]`, `ring-1 ring-white/10`, `shadow-2xl`), high-voltage Neon Lime (`#ccff00`) and Emerald Glow (`#10b981`) accents, 16px backdrop-blur glass cards, and 60px linear cyber grids.
2. **The Maker's Kinetic Craft**: An interactive technical vetting pipeline that *draws itself* in SVG using `getTotalLength()` and `strokeDashoffset`, paired with a 3-way variant switcher (`aria-pressed`), hairline-ruled measurement rows, and a full-width spread baseline wordmark (`G C T E K T O N`) that sinks and expands on scroll.
3. **Neo-Brutalist Layout Rhythm**: High-energy stacked sections, interactive MacOS-styled browser mockup dashboard, continuous infinite marquee, "Problem vs. Solution" comparison bento, 4-column bento feature matrix, 3-step numbered pipeline with colored glow rings, and asymmetric testimonial cards.

---

## 2. Color Palette & Materiality
| Token Name | Hex / Value | Role |
| :--- | :--- | :--- |
| **Viewport Background** | `#000000` | Deepest black outer shell surrounding floating container |
| **Shell Container** | `#0c0c0c` | Hardware surface of the main 1600px application container |
| **Primary Accent** | `#ccff00` | Neon Lime — high-visibility CTA buttons, badges, glowing active states |
| **Secondary Accent** | `#10b981` | Emerald Glow — verification badges, positive deltas, secondary glows |
| **Dark Gray / Borders** | `#171e19` / `#272727` | Inner card fills, step connector lines, neutral darks |
| **Hairlines & Rings** | `rgba(255, 255, 255, 0.1)` | 1px border rules, container rings, separator lines |
| **Glass Surface** | `rgba(255, 255, 255, 0.03)` | 16px backdrop blur, soft elevated panels |
| **Primary Text** | `#ebebeb` | High-contrast off-white heading and body copy |
| **Secondary Text** | `rgba(235, 235, 235, 0.65)` | Subheadings, descriptions, supporting data |
| **Muted Metadata** | `rgba(235, 235, 235, 0.35)` | Fine print, inactive tabs, hairline labels |

---

## 3. Typography Hierarchy
- **Display Headings**: `Space Grotesk` (Weights 300 to 700, tight tracking `-0.06em` to `-0.02em`, leading `0.9` to `1.15`).
- **Technical Metadata & Code**: `JetBrains Mono` (Weights 400, 500, 700, uppercase, tracking `0.15em` to `0.2em`).
- **Body & Editorial Copy**: `Space Grotesk` (Weight 400, leading relaxed).

---

## 4. Key Interactive Components
1. **Neon Pulse Button**:
   - `background: #ccff00`, `color: #000000`, `font-weight: 700`, `border-radius: 9999px`.
   - `box-shadow: 0 0 30px rgba(204, 255, 0, 0.3)`. Hover: `transform: scale(1.05)`.
2. **Glass Floating Card**:
   - `background: rgba(255, 255, 255, 0.03)`, `backdrop-filter: blur(16px)`, `border: 1px solid rgba(255, 255, 255, 0.1)`, `border-radius: 1.5rem`.
   - Hover state: `border-color: rgba(204, 255, 0, 0.4)`.
3. **Pulsing System Status Indicator**:
   - `JetBrains Mono`, `text-[10px] tracking-widest uppercase`, with 6px pulsing lime circle (`bg-[#ccff00] animate-pulse`).
4. **Self-Drawing SVG Pipeline**:
   - Live SVG architectural pipeline whose paths dynamically draw on scroll and re-draw when variant buttons are toggled.
5. **Spread Baseline Wordmark**:
   - Letter-by-letter flex row (`G · C · T · E · K · T · O · N`) with `justify-between` across the foot of the hero, cropped by the baseline.
6. **Browser Mockup Shell**:
   - MacOS window header with Red (`#ff5f57`), Yellow (`#febc2e`), and Green (`#28c840`) dots, displaying live candidate telemetry and placement speed indicators.
