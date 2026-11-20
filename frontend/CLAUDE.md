# Front-end — Vue 3 + Tailwind

Stack: **Vue 3.5 (`<script setup lang="ts">`) · TypeScript strict · Vite 5 · Tailwind 3.4 · Pinia 3 · vue-router 4**.
No UI library and no chart library. Plain SVG keeps the demo robust and the bundle small.

## Directory layout (`src/`)

```
main.ts              app bootstrap (Pinia + router + styles)
App.vue              picks the layout from route.meta.layout ("app" | "blank")
router/index.ts      routes (lazy views), RouteMeta typing, document.title
layouts/             AppLayout (navy sidebar + topbar, Aurum "Panel aplikacji"), BlankLayout
views/               one file per route, named *View.vue. Composes components and reads stores
components/
  ui/                generic building blocks: BaseButton, BaseCard, StatusPill, StatTile, IconTile, EmptyState,
                     AlertBanner, SkeletonBlock, PageHeader, CollapseTransition, AnimatedNumber,
                     AppIcon (+ icons.ts), tones.ts (shared tone → colour maps)
  layout/            AppSidebar, AppTopbar, NavLinks, ThemeToggle, AccessibilityMenu, AppLogo, AppFooter
  agent/             AutonomyBadge, AutonomyLegend, AgentTrace, AgentPipeline, SourceTag (challenge-specific)
  dashboard/         HeadlineBanner, SafetyRing, KpiCard, ForecastChart, PeriodPicker, PaymentsDonut (+ chart.ts)
  findings/          FindingCard (list item), FindingSplit (email ↔ contract ↔ calculation)
  actions/           ActionCard (editable email / credit offer + Legal review + Approve / Not now)
  ask/               SuggestionChips, AskTurnItem, AskTeaser ("Ask your CFO")
  contracts/         ContractUpload (drop zone, type/size check)
api/                 the only place that talks HTTP: http.ts (fetch wrapper, ApiError), one module per area, index.ts
stores/              Pinia setup stores: dashboard (demo flow), system (config, LLM health),
                     ask (conversation + suggestions, re-fetched on sync / reset / language switch)
composables/         useTheme, useA11y (accessibility menu), useForecastPeriod (chart window),
                     useTweenedNumber, useAsyncData (view-local fetches)
types/api.ts         TS mirror of docs/API.md, the single source of types
constants/           autonomy labels/colours, verdicts, navigation
utils/format.ts      eur(), fmtDate()… all formatting lives here
styles/              main.css (Tailwind + base), tokens.css (Aurum CSS variables, light/dark)
assets/fonts/        Plus Jakarta Sans, Inter, JetBrains Mono (local woff2, OFL)
```

## Data flow

`view → store (Pinia) → api/* → fetch('/api/...')`. Components get data through props and report back with
emits. They never import `api/`. View-local, read-only data (policy, audit) goes through `useAsyncData(getX)`.
SSE (`/api/sync`) is wrapped in `api/sync.ts → startSync()` and driven by `useDashboardStore().sync()`, so a
running sync survives navigation.

## Conventions

- `<script setup lang="ts">`, typed `defineProps<{…}>()` / `defineEmits<{…}>()`. No Options API.
- Files: components `PascalCase.vue`, views `XxxView.vue`, composables `useXxx.ts`, stores `useXxxStore`.
- Imports use the `@/` alias. Don't put `export` statements in `<script setup>`. Put shared types/helpers in a sibling `.ts`.
- **Colours: semantic tokens only** (`bg-surface`, `text-muted`, `bg-sun`, `text-positive`…). The default Tailwind
  palette is disabled on purpose, so `bg-slate-100` won't compile. Dark mode works by swapping variables, so you
  don't need `dark:` variants for colours. See `.claude/rules/design-system.md`.
- Money and dates go through `utils/format.ts` (dates follow the UI language, money is always de-DE). Never call
  `toLocaleString` ad hoc in templates.
- UI copy: **English source + German translation** via `src/i18n` (`t()` / `tn()`, dictionaries in `src/i18n/de/<area>.ts`,
  language switch in the top bar, `?lang=` sent with every API call – see `CONTRACT_PROPOSALS.md`). Keep it plain and
  short, aimed at a non-finance owner. Backend messages are shown as delivered (English today).
- Top-bar pop-ups (inbox check, language, accessibility) share `composables/usePopover.ts` – same open/close behaviour.
- Accessibility: real `<button>` / `<a>` elements (`BaseButton :to` renders a RouterLink), visible focus (global sun outline),
  `aria-live` for streaming content, `role="alert"` for errors, labels on inputs, contrast ≥ 4.5:1.
- Loading → `SkeletonBlock`. Empty → `EmptyState` with a way forward. Error → `AlertBanner` with "Try again".

## Env

`frontend/.env.local` (git-ignored, template in `.env.example`):
`VITE_API_TARGET` = where the dev proxy sends `/api` (local uvicorn or the live cluster URL).

## Definition of done for a front-end change

`npm run build` passes (vue-tsc + vite), there are no console errors, the flow works against a local backend
(`LLM_ENABLED=false`), and it has been checked at 390 px width, in dark mode, in German (no missing strings) and in
high contrast. Use the `frontend-verify` skill.
