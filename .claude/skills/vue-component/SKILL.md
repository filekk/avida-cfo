---
name: vue-component
description: Create a new Vue 3 component for the Avida CFO front-end that follows the project's conventions (script setup + TS, Aurum design tokens, presentational props/emits, accessibility). Use when asked to add, build or extract a UI component, card, badge, widget or form element in frontend/src/components.
---

# Create a Vue component (Avida CFO)

## 1. Decide where it lives

| Kind | Folder |
|---|---|
| Generic, domain-free (button, card, pill, modal, tabs…) | `frontend/src/components/ui/` |
| App chrome (sidebar, topbar, nav) | `components/layout/` |
| Agent/autonomy-related | `components/agent/` |
| Domain: dashboard / findings / actions / new area | `components/<area>/` |

Check `components/ui/` first. Reuse `BaseCard`, `BaseButton`, `StatusPill`, `EmptyState`, `AlertBanner`,
`SkeletonBlock`, `PageHeader`, `AppIcon`, `AutonomyBadge` and don't duplicate them.

## 2. Template

```vue
<script setup lang="ts">
import { computed } from "vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import type { Finding } from "@/types/api";
import { eur } from "@/utils/format";

/** One sentence: what this shows and where it is used. */
const props = withDefaults(defineProps<{ finding: Finding; compact?: boolean }>(), { compact: false });
const emit = defineEmits<{ select: [id: string] }>();

const total = computed(() => eur(props.finding.impact.next_12_months));
</script>

<template>
  <BaseCard :title="finding.extraction.supplier">
    <p class="text-muted">{{ total }}</p>
    <BaseButton variant="secondary" @click="emit('select', finding.id)">Open</BaseButton>
  </BaseCard>
</template>
```

## 3. Checklist

- [ ] `<script setup lang="ts">`, typed props/emits, **no `export`** (shared types go in a sibling `.ts`).
- [ ] Presentational: no `@/api` import, no store writes. Data comes in through props, actions go out through emits.
- [ ] Colours: only Aurum tokens (`bg-surface`, `text-muted`, `bg-sun`, `text-positive`…). `slate-*`/`gray-*` won't compile.
- [ ] Sun (`bg-sun`) only for the single most important element. Positive/negative only for money and status.
- [ ] Money and dates via `@/utils/format` (`eur`, `fmtDate`, `pct`). Numbers get `tabular-nums`.
- [ ] If an agent did or proposes something → `<AutonomyBadge :level="…" />` is visible.
- [ ] A11y: semantic elements, `<button type="button">`, labels for inputs, `aria-live` for streaming lists, no `<button>` inside `<a>`
      (use `BaseButton :to`).
- [ ] Works at 390 px width and in dark mode (no hard-coded hex colours).
- [ ] No emoji or ✓/✕ symbols. Icons only via `<AppIcon>`. A new icon means copying its SVG from lucide.dev (ISC) into `components/ui/icons.ts`.
- [ ] Run `npm --prefix frontend run build`.
