---
name: vue-view
description: Add a new page (view + route + navigation entry) to the Avida CFO Vue front-end, wired to the Pinia store or useAsyncData with loading/empty/error states. Use when asked to add a screen, page, route, tab or section reachable from the sidebar.
---

# Add a view (page) to Avida CFO

## Steps

1. **View file:** `frontend/src/views/<Name>View.vue`.
2. **Route** in `frontend/src/router/index.ts`:
   ```ts
   {
     path: "/cash-calendar",
     name: "cash-calendar",                       // kebab-case, unique
     component: () => import("@/views/CashCalendarView.vue"),   // always lazy
     meta: { title: "Cash calendar" },            // shown in topbar + tab title
     // props: true,                              // for /:id params
     // meta.layout: "blank"                      // full-screen page without app chrome
   },
   ```
   Keep the catch-all `/:pathMatch(.*)*` route **last**.
3. **Navigation** (if it belongs in the sidebar): add to `frontend/src/constants/navigation.ts`
   `{ to: "cash-calendar", label: "Cash calendar", icon: "chart" }` (icon from `components/ui/icons.ts`).
4. **Data:**
   - part of the demo flow / shared across views → `useDashboardStore()` (+ `storeToRefs`)
   - read-only and only for this page → `const { data, loading, error, reload } = useAsyncData(getX)`
   - new endpoint → run the `api-endpoint` skill first.

## Skeleton

```vue
<script setup lang="ts">
import { getPolicy } from "@/api";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useAsyncData } from "@/composables/useAsyncData";

/** What this page is for (one sentence). */
const { data, loading, error, reload } = useAsyncData(getPolicy);
</script>

<template>
  <PageHeader eyebrow="Section" title="Plain-language title" description="One sentence for the owner." />

  <AlertBanner v-if="error">{{ error }} <button type="button" class="ml-2 underline" @click="reload">Try again</button></AlertBanner>
  <SkeletonBlock v-else-if="loading && !data" height="h-48" />
  <BaseCard v-else-if="data?.length"> … </BaseCard>
  <EmptyState v-else title="Nothing here yet" description="What the owner should do next." />
</template>
```

The view renders inside `AppLayout` → `<main class="grid gap-5">`. Don't add page padding and don't add an `<h1>`
(the topbar renders `meta.title` as h1). Section titles go through `PageHeader` (h2).

## Checklist

- [ ] Loading, empty and error states. The empty state offers a way forward.
- [ ] Autonomy badges anywhere agent output appears. Owner actions only on click.
- [ ] 390 px + dark mode checked. `npm --prefix frontend run build` green.
