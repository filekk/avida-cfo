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

## Look & feel: a calm finance product, not a generated demo

Benchmarks: Agicap (cash-flow charts), Mercury (restraint), Qonto (depth without shadows), Stripe/lexoffice
(dense number tables). Common denominator: **no gradients, glows, blur, pulsing or floating cards.**
Before adding anything visual, ask: "does this carry information?" If not, leave it out.

## Rules

- **60 / 30 / 10:** ~60 % background and white cards, ~30 % navy and mist (text, navigation, sections),
  7–10 % sun (buttons, highlights), ~3 % mint/coral (numbers and statuses only).
- **Sun is never text on white** (1.6:1). Use it as a fill with navy text (9:1), or use `text-gold` for links.
- **At most ONE large sun element per screen:** its main button (`BaseButton variant="primary"`). Small count badges
  (decisions waiting) may be sun. No sun borders on cards/tiles, no sun icon tiles, no sun status labels.
- Positive/negative colours mean money and status. Don't use them for decoration.
- Dark mode = variable swap via `[data-theme="dark"]` or the OS preference (`useTheme()`), so no `dark:` colour variants.
  Check every new screen in both themes.

## Surfaces & depth

- Three levels, all in the palette: `bg` (page) → `surface` (card) → `input` (inside a card: fields, read-outs, code).
- Card = `rounded-xl border border-line bg-surface` (`BaseCard`). **No shadow** – the 1px line carries the depth.
- **One shadow token, `shadow-pop`**, only for things that really float above the content: top-bar pop-ups
  (inbox check, language, accessibility), tooltips, the chat panel and its bubble. Never on cards or buttons.
- Hover on a card / row / button = background or border colour (`hover:bg-input/60`, `hover:border-fg/30`).
  **Never a shadow, never a lift or translate** (no `hover:-translate-*`, no moving arrows).
- No `blur`, `backdrop-blur`, glows, decorative `isolate`/`-z-10` layers. The sticky top bar is a solid `bg-bg` + `border-b`.
- **No gradients in the UI.** One technical exception: the scroll-edge alpha mask in `AgentTrace` (an edge, not a colour).

## Shapes

- Two radii + the full circle:
  `rounded-lg` (8px) – buttons, fields, chips, small inner panels · `rounded-md` (6px) – status labels, count badges ·
  `rounded-xl` (12px) – cards, panels, pop-ups.
- `rounded-full` only for: status dots, avatars/initials, the spinner ring, toggle switches, the floating chat button,
  legend/step markers. **No pills** for statuses, chips or badges. No `rounded-2xl`/`3xl`, no chat-bubble "tails".

## Typography

- `font-display` (Plus Jakarta Sans): headings, KPI values, logo. `font-sans` (Inter 400–600): body, **16px** base
  (`text-body`), line-height 1.6. `font-mono` (JetBrains Mono 500): calculations, email drafts, codes.
- **Weights: 400 text · 500 labels, statuses · 600 headings, buttons, numbers. 800 nowhere, `font-bold` nowhere**
  (`<b>`/`<strong>` are 600 via main.css). Hierarchy comes from size and colour (`fg` / `muted`), not weight.
  At most two semibold elements per card.
- **Financial numbers:** `font-display font-semibold tracking-tight tabular-nums`; in lists and tables right-aligned.
  The minus is the real `−` (U+2212) – `utils/format.ts` (`eur`, `eurSigned`, `pct`…) does it, never format by hand.
- **Eyebrow (`.eyebrow`) is the exception:** only where it tells apart sections of the same type (the two chart cards
  on the overview, Pending/Resolved groups, sub-sections of a summary). Never above a page title, never just to
  repeat the title. Table headers are sentence case, not uppercase.
- **Type scale (tailwind.config.js) – the only sizes to use, no `text-[0.7rem]` one-offs:**
  `text-caption` 13px = the floor (statuses, badges, axis labels, eyebrows) · `text-label` 14px (secondary text,
  sub lines) · `text-sm`/`text-base`/`text-lg`/`text-xl`… · `text-kpi` 26px (KPI values). Everything is rem-based,
  so the accessibility menu's text size (font-size on `<html>`) scales the whole UI. Never put text below 13px,
  never glue a label to a number (keep a gap).

## Shared building blocks (use these, don't re-type the classes)

- **Tones** – `components/ui/tones.ts`: `TONE_SOFT` (status background + text), `TONE_TEXT` (value colour),
  `TONE_TREND` (trend icon). Green = good for the owner's money, red = bad. Same red/green everywhere.
- **`StatusPill`** – every status label (trend, verdict, status): flat `rounded-md` rectangle, 13px, weight 500,
  `*-soft` background + text in its tone. Add an icon only when it tells states apart without colour (check / x / alert).
  "Waiting for you" = `warn` (pending), never sun.
- **`AutonomyBadge`** – same size/shape as `StatusPill`. "Needs your approval" is **outlined** sun (navy text), not filled.
  `plain` = the same icon + label as muted text, for the second level in a row.
- **Max. 2 badges per row.** Action headers: status + autonomy as badges; "Simulated execution" (`AutonomyBadge plain`),
  the author ("by Negotiator Agent") and `SourceTag` as muted text on their own line.
- **`SourceTag`** – discreet italic muted "(cached answer)". Keep it that way.
- **`IconTile`** (coloured square/circle) – **an exception, not the default.** Only: the four dashboard KPIs (`KpiCard`),
  empty states (`EmptyState`, empty donut, the upload drop zone), the agent pipeline + autonomy legend, the inbox-check
  status. A counterparty's initial is an avatar (`tone="neutral" round`).
  Everywhere else (lists, rows, card headers, chat, timelines, tables): a plain 16–18px `text-muted` `<AppIcon>` –
  or no icon at all when the text says enough. One icon size per component.
- **`StatTile`** – label (with a small muted icon) + value. No tile. `tone` colours only the value.
  `value` = ready text (dates, ranges) · `amount` (+ optional `format`) = a number that counts up via `AnimatedNumber`.
- **`KpiCard`** – dashboard KPIs (`tone` colours value + tile, amount counts up via `AnimatedNumber`).

## Motion — only as a response, nothing moves at rest

- Tokens: `duration-fast` 150ms · `duration-base` 250ms · `duration-slow` 400ms, default easing
  `cubic-bezier(.22,1,.36,1)` (CSS vars `--dur-*`, `--ease-out` in main.css).
- **Nothing moves on its own:** no `animate-pulse`, no infinite glows/halos, no shimmering text, no breathing icons,
  no bouncing "typing" dots. Waiting decisions = a static sun count badge.
- Allowed reactions: hover/focus colour (150ms), `<CollapseTransition>` for anything that opens/closes (measured
  height – no max-height hacks), `fade` for swaps, `page` for route changes (App.vue), `rise` for blocks that appear.
- `animate-rise` **only for items that arrive live** (agent trace steps, a new chat answer, an alert). Never for lists
  loaded at once (tables, legends, chips, timelines, cards).
- **Agent results delivered together** (e.g. what Avida read from an uploaded contract, `UploadSummary`) may fill in
  in reading order: `animate-rise` + `:style="stagger(i, n)"` from `utils/motion.ts` (whole cascade < 1 s).
- **Chat bubbles** (`AskTurnItem`): the question fades in and rises 8px from its corner (scale .98 → 1); thinking line →
  answer is an out-in swap where the slot grows its height smoothly, so the text below never jumps.
- **Wheel scrolling** is smoothed page-wide by Lenis (`utils/smoothScroll.ts`, MIT): it eases the native window scroll
  (no transforms → text stays sharp), lerp 0.15 ≈ 0.4 s per notch. Boxes with their own scroll keep it
  (`allowNestedScroll`); touch, keyboard and scrollbar stay native; off under reduced motion. Don't add CSS
  `scroll-behavior: smooth` or a second smooth-scroll library.
- Loading: `ThinkingSpinner` (a plain 2px ring, one turning arc; `md` keeps the agent icon) or a **static**
  `SkeletonBlock`. One loading indicator per place.
- **Key numbers count up and glide** (`AnimatedNumber`, `StatTile :amount`): they count up from 0 when they appear
  (0.9 s, ease-out – every time the page opens) and glide to every new value (0.7 s). Used for the four KPIs, the donut
  total, the forecast read-out, the Action center counters, "You save" and the sidebar "Saved by Avida". Not for hover
  read-outs, legends, axis labels or table/list rows. A read-out that is re-created on a mode switch passes
  `:count-up="false"` after the first show (see `ForecastChart`). The box keeps the final value's width → no layout shift.
  Ring arcs animate too. Reserve space for hover read-outs → no layout shift.
- Reduced motion: the OS setting and the accessibility menu (`html[data-motion="reduce"]`) cut every
  transition to 1ms and drop delays. JS animations must check it too (see `useTweenedNumber`, `smoothScroll`).
  Keep `data-motion` support intact.

## Charts (plain SVG)

- Lines 2px, no shadow/glow. Points only on hover and at the lowest point.
- Area under the main line: one **flat** fill at 6 % opacity (or none) – never a fading gradient. Scenarios differ by
  palette colour + line style (solid / dashed), no fill under each series. The zone below the safety cushion stays
  a flat `negative-soft` band (it is information).
- Grid: horizontal 1px `stroke-grid`, no verticals. Axis labels 13px `fill-muted tabular-nums`.
- Donut: flat segments with a 2px gap, no shadows; legend = rows with amounts right-aligned.

## Layout (from the prototype mock)

- App shell: 232px navy sidebar (≥ lg), sticky topbar, content `max-w-6xl`, gaps 12–20px.
- KPI row: `auto-fit` grid with a rem minimum (4 columns on desktop, 2 on phones, 1 on phones at large text);
  `KpiCard` switches icon-beside/icon-above via a container query. Good/bad numbers use `tone` (green/red), not the sun.
- Below `lg` the sidebar disappears and `NavLinks orientation="horizontal"` shows in the topbar.
- Icons: **Lucide only** (ISC licence), 24×24 stroke-2 inline SVG in `components/ui/icons.ts`, rendered with
  `<AppIcon name>`. To add one, copy the inner SVG from lucide.dev and keep the Lucide name in a comment.
- **No emoji in the UI, ever** (not in badges, buttons, copy or status messages), and no ✓/✕ text symbols either:
  use `checkCircle` / `xCircle`. No icon fonts or paid icon sets. Any new asset needs a free licence and an
  entry in `frontend/THIRD_PARTY_LICENSES.md`.

## Check before handing over

`frontend/src` must give 0 hits except the `AgentTrace` scroll mask:

```
grep -rn "gradient\|blur-\|backdrop-blur\|glow\|shimmer\|animate-pulse\|font-extrabold\|font-bold\|rounded-2xl\|rounded-3xl\|hover:-translate\|shadow-card\|shadow-float\|shadow-lift" frontend/src
```
