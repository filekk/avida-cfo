---
paths:
  - "frontend/**"
---

# Vue / TypeScript conventions (front-end)

- **Templates have ONE root element and never start with an HTML comment** (put comments inside the root). In dev Vue
  keeps comments → the component becomes a fragment → `<Transition mode="out-in">` never finishes and the content
  vanishes (that was the "disappearing theme icon" bug). For swapping icons/labels prefer stacking both in one grid
  cell and cross-fading with classes over keyed out-in transitions.
- `<script setup lang="ts">` only. Use `defineProps<{…}>()` with `withDefaults` for defaults, and typed `defineEmits<{ name: [args] }>()`.
- **No `export` in `<script setup>`.** Shared types and helpers go in a sibling `.ts` file (e.g. `dashboard/chart.ts`).
- Imports: `@/…` alias, in this order: vue/pinia/router → `@/api` → components → constants/types/utils.
- Components are **presentational**: data in via props, decisions out via emits. Only views and stores touch
  `@/api` or stores. (Exception: layout widgets like `NavLinks`/`AppSidebar` may read stores.)
- Global, cross-view state → Pinia setup store in `stores/` (`useXxxStore`). Destructure with `storeToRefs`.
  View-local read-only fetch → `useAsyncData(fetcher)`.
- Never call `fetch` outside `src/api/`. New endpoint → new function in the matching `api/*.ts`, re-exported from `api/index.ts`.
- Owner actions (approve/reject/send) fire **only** from click handlers. No watchers, timers or auto-triggers.
- Every async UI has three states: loading (`SkeletonBlock`), empty (`EmptyState` + way forward), error (`AlertBanner` + retry).
- Show the autonomy badge (`AutonomyBadge`) wherever an agent did or proposes something.
- Copy: English source text, plain words, short sentences. Write "you/your" when addressing the owner, and avoid finance jargon or explain it.
- **Every visible string is translated (EN/DE):** `import { t, tn } from "@/i18n"` and wrap it – `t("Check my inbox")`,
  `t("{n} days", { n })`, `tn(n, "{n} step", "{n} steps")` – including aria-label/title/placeholder. The English text is
  the key; add the German (formal "Sie") to the matching `src/i18n/de/<area>.ts`. Never call `t()` at module level
  (constants keep English, translate where rendered). Backend texts are shown as delivered. Check with
  `localStorage.avida-lang = "de"` → dev-only `window.__i18nMissing` must stay empty. German is ~30 % longer: test at 390px.
- Routes: lazy `() => import("@/views/XxxView.vue")`, a `name` in kebab-case, `meta.title` (shown in the topbar).
  Add sidebar entries in `constants/navigation.ts`.
- Keep `npm run build` green: strict TS, `noUnusedLocals`, `noUnusedParameters`.
