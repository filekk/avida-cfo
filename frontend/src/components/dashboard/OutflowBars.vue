<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { Outflow } from "@/types/api";
import { eur, fmtDayMonth } from "@/utils/format";
import { categoryIcon } from "./chart";

/** "Biggest payments ahead" – horizontal bars instead of a list of sentences. Outflows arrive as negative numbers. */
const props = defineProps<{ outflows: Outflow[] }>();

const rows = computed(() => {
  const max = Math.max(1, ...props.outflows.map((o) => Math.abs(o.amount)));
  return props.outflows.map((o) => ({ ...o, abs: Math.abs(o.amount), width: `${(Math.abs(o.amount) / max) * 100}%` }));
});
</script>

<template>
  <ul v-if="rows.length" class="grid gap-4">
    <li v-for="(o, i) in rows" :key="`${o.date}-${i}`" class="grid gap-1.5">
      <div class="flex items-center gap-3">
        <span class="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-input text-muted">
          <AppIcon :name="categoryIcon(o.category)" :size="16" />
        </span>
        <span class="grid min-w-0 flex-1 leading-tight">
          <span class="truncate text-sm font-semibold">{{ o.label }}</span>
          <span class="text-[0.75rem] text-muted">{{ fmtDayMonth(o.date) }}</span>
        </span>
        <span class="font-display text-sm font-bold tabular-nums">{{ eur(o.abs) }}</span>
      </div>
      <div class="ml-12 h-1.5 overflow-hidden rounded-full bg-input" aria-hidden="true">
        <div class="h-full rounded-full bg-sky" :style="{ width: o.width }" />
      </div>
    </li>
  </ul>
  <p v-else class="text-sm text-muted">No large payments in this period.</p>
</template>
