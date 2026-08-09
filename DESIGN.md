# Design

## Project

CRASHSIM-NEURAL is a physics-informed crashworthiness prediction tool. Reference: premium analytics instruments (Linear, Stripe) in a precision-engineering register. The interface is an instrument, not a marketing dashboard: dense, quiet, exact.

## Theme

A crash-safety engineer reads HIC numbers and deflection curves on a high-DPI monitor in a dim lab, mid-analysis. The interface is a measurement instrument: near-black warm-neutral surfaces, hairline structure, one bronze-gold accent for action and selection, semantic green/amber/red reserved strictly for risk thresholds. Numbers are the story and they are set in tabular mono figures.

## Colors

Neutrals are tinted toward warm bronze (OKLCH hue ~60, chroma 0.006-0.014). No pure black, no pure white.

| Token | OKLCH | Hex |
| --- | --- | --- |
| bg | oklch(0.12 0.006 60) | #0c0b09 |
| surface | oklch(0.145 0.008 60) | #131210 |
| surface-2 | oklch(0.17 0.01 60) | #161512 |
| border | oklch(0.22 0.012 60) | #1c1b18 |
| border-s | oklch(0.28 0.014 60) | #26241f |
| text | oklch(0.925 0.008 60) | #e7e3dc |
| text-2 | oklch(0.72 0.01 60) | #a6a29b |
| muted | oklch(0.57 0.012 60) | #7a756e |
| accent | oklch(0.63 0.11 62) | #c79a55 |
| accent-h | oklch(0.69 0.1 64) | #ddb56e |
| accent-fill | oklch(0.5 0.1 58) | #967033 |
| accent-bg | oklch(0.24 0.055 62) | #3a2f1a |
| ok | oklch(0.72 0.15 150) | #53be70 |
| warn | oklch(0.8 0.15 75) | #f5ae39 |
| danger | oklch(0.65 0.2 24) | #f14d4f |
| secondary | oklch(0.72 0.09 150) | #56c09a |

Data-series palette (consistent across all charts): PINN = accent (#c79a55), FEA baseline = muted neutral (#7a756e, dashed), training/validation = accent + secondary sage green (#56c09a). Sequential surfaces use a custom bronze-to-champagne scale, never viridis/plasma. Ambient orbs are warm bronze/copper/sage/champagne, never purple or blue.

## Typography

Inter for UI, JetBrains Mono for data, Playfair Display for headings and prominent figures. UI base 13px, letterspacing -0.011em. Data figures use mono with tabular alignment. Micro-labels are 11px, letter-spacing 0.06em, uppercase, muted. Hierarchy ratio >= 1.25: page title 22px/600, section title 16px/600, body 13px/400, micro 11px/500. Italicized words are reserved for a single emphasized word per heading.

## Spacing & Radius

4px grid. Panel padding 20px, section gap 24px, control gap 8px. Hairline 1px borders. Radius: 6px controls, 8px panels. Structure with hairlines and spacing, not nested cards. Nested panels inside panels are banned.

## Layout

Linear-style application frame: fixed left sidebar (220px) with icon + label nav items, top bar with page title and actions, scrollable content column max-width 1120px. Active nav = accent-bg tint, accent text, 2px accent indicator. Top-nav with bordered pill buttons is banned.

## Components

- Button: 6px radius, 32px height, 13px/500. Primary = accent-fill with near-white text (contrast 5.88:1). Ghost = transparent, border border, text-2. Hover 150ms ease-out-quart, active pressed 0.98 scale.
- Input/select: surface-2 background, border hairline, radius 6px, 32px height. Focus = 2px accent ring.
- Range slider: accent thumb, thin track.
- Panel: surface background, hairline border, 8px radius, 20px padding. Title in 13px/600 with micro-label sub.
- Tag/chip: surface-2, hairline border, 6px radius, 11px mono.
- Table: hairline row dividers, muted mono values, tabular right-aligned numerics, hover surface-2 row, no card chrome.
- Chart card: plot on transparent panel, muted gridlines, mono tick labels, no redundant title inside plot.

## Motion

150-200ms, ease-out-quart. State and interaction transitions only (hover, focus, active, reveal). Never animate layout properties. Respect prefers-reduced-motion. The crumple deformation animation is the one data-driven motion and is kept as the product's centerpiece.
