---
paths:
  - "frontend/src/**/*.vue"
  - "frontend/src/styles/**"
  - "frontend/tailwind.config.js"
---

# Design system — "Aurum" (from `../ProjektPrototyp/index.html`)

Tokens live in `frontend/src/styles/tokens.css` (RGB channels, light + dark) and are exposed as Tailwind
colours in `tailwind.config.js`. **The default Tailwind palette is disabled.** Use these names only:

| Tailwind | Light | Role |
|---|---|---|
| `bg` | #F5F9FD | page background |
| `surface` | #FFFFFF | cards, panels |
| `line` | #DCE6F0 | borders, dividers |
| `input` | #F0F5FA | fields, bar tracks, code blocks |
| `fg` | #0E2A47 navy | text, headings (structure colour) |
| `muted` | #4A5D73 steel | secondary text, axis labels |
| `side` / `side-fg` | navy / #AFC3D9 | sidebar, dark bands |
| `sun` / `sun-hover` / `sun-on` | #FFC72C / #F2B705 / navy | **primary CTA, the ONE highlighted thing** |
| `gold` | #8A6200 | sun used as text/link on light backgrounds |
| `sky` | #B6DCFE | chart bars, selection |
| `mist` / `mist-fg` | #CDEDFD / #0E4A7A | section backgrounds, info chips |
| `mint` | #81F7E5 | **profit/growth only**, small doses |
| `positive(-soft)` | #0B6E63 / #D5FBF5 | positive amounts, "paid", passed checks |
| `negative(-soft)` | #B42318 / #FDE3E3 | losses, overdue, errors, failed checks |
| `warn(-soft)` | #7A5600 / #FFF4D6 | pending, needs attention |
| `chart-line` / `chart-alt` | navy (mint in dark) / coral | forecast lines |

## Rules

- **60 / 30 / 10:** ~60 % background and white cards, ~30 % navy and mist (text, navigation, sections),
  7–10 % sun (buttons, highlights), ~3 % mint/coral (numbers and statuses only).
- **Sun is never text on white** (1.6:1). Use it as a fill with navy text (9:1), or use `text-gold` for links.
- Only **one** `BaseButton variant="primary"` (sun) per screen region. Everything else is `secondary`/`ghost`.
- Positive/negative colours mean money and status. Don't use them for decoration.
- Dark mode = variable swap via `[data-theme="dark"]` or the OS preference (`useTheme()`), so no `dark:` colour variants.
  Check every new screen in both themes.

## Typography

- `font-display` (Plus Jakarta Sans 500–800): headings, KPI values, logo.
- `font-sans` (Inter 400–600): body, **16px** base (`text-body`), line-height 1.6.
- `font-mono` (JetBrains Mono 500): calculations, email drafts, codes.
- Numbers in tables/KPIs: `tabular-nums`. Small uppercase labels: `.eyebrow` utility.
- **Type scale (tailwind.config.js) – the only sizes to use, no `text-[0.7rem]` one-offs:**
  `text-caption` 13px = the floor (pills, badges, axis labels, eyebrows) · `text-label` 14px (secondary text,
  sub lines) · `text-sm`/`text-base`/`text-lg`/`text-xl`… · `text-kpi` 26px (KPI values). Everything is rem-based,
  so the accessibility menu's text size (font-size on `<html>`) scales the whole UI. Never put text below 13px,
  never glue a label to a number (keep a gap).

## Shared building blocks (use these, don't re-type the classes)

- **Tones** – `components/ui/tones.ts`: `TONE_SOFT` (pill/tile background + text), `TONE_TEXT` (value colour),
  `TONE_TREND` (trend icon). Green = good for the owner's money, red = bad. Same red/green everywhere.
- **`IconTile`** – every icon square/circle: `sm` 40px (dense rows, timelines) · `md` 48px (KPIs, stat tiles) ·
  `lg` 56px (pipeline, empty states); `tone`, `round`, default slot for a letter.
- **`StatusPill`** – every pill (trend, verdict, status). `AutonomyBadge` has the same size/shape.
- **`StatTile`** – icon + label + value; `KpiCard` – dashboard KPIs (`tone` colours value + tile, amount glides
  via `AnimatedNumber`).

## Motion (no jumps, ever)

- Tokens: `duration-fast` 150ms · `duration-base` 250ms · `duration-slow` 400ms, default easing
  `cubic-bezier(.22,1,.36,1)` (CSS vars `--dur-*`, `--ease-out` in main.css). Interactive elements ease
  colours/shadow/transform by default (base layer rule).
- Vue transitions: `fade`, `rise` (blocks appearing), `page` (route change, App.vue), `<CollapseTransition>` for
  anything that opens/closes (measured height – no max-height hacks), `animate-rise` for list items.
- Values that change animate (`AnimatedNumber`, ring arcs). Reserve space for hover read-outs → no layout shift.
- Reduced motion: the OS setting and the accessibility menu (`html[data-motion="reduce"]`) cut every
  transition to 1ms. JS animations must check it too (see `useTweenedNumber`).

## Shapes & layout (from the prototype mock)

- Cards: `rounded-xl border border-line bg-surface` (`BaseCard`). Pills: `rounded-full` (`StatusPill`).
- App shell: 232px navy sidebar (≥ lg), sticky topbar, content `max-w-6xl`, gaps 12–20px.
- KPI row: `auto-fit` grid with a rem minimum (4 columns on desktop, 2 on phones, 1 on phones at large text);
  `KpiCard` switches icon-beside/icon-above via a container query. Good/bad numbers use `tone` (green/red), not the sun.
- Below `lg` the sidebar disappears and `NavLinks orientation="horizontal"` shows in the topbar.
- Icons: **Lucide only** (ISC licence), 24×24 stroke-2 inline SVG in `components/ui/icons.ts`, rendered with
  `<AppIcon name>`. To add one, copy the inner SVG from lucide.dev and keep the Lucide name in a comment.
- **No emoji in the UI, ever** (not in badges, buttons, copy or status messages), and no ✓/✕ text symbols either:
  use `checkCircle` / `xCircle`. No icon fonts or paid icon sets. Any new asset needs a free licence and an
  entry in `frontend/THIRD_PARTY_LICENSES.md`.
