<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { RECOMMENDATION, VERDICT } from "@/constants/autonomy";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";
import PriceBar from "./PriceBar.vue";
import { verdictTone } from "./verdict";

/** Compact, visual summary of one detected price change. Links to the split-screen detail. */
const props = defineProps<{ finding: Finding }>();
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const tone = computed(() => verdictTone(props.finding.contract.verdict));
const ex = computed(() => props.finding.extraction);
</script>

<template>
  <RouterLink
    :to="{ name: 'finding-detail', params: { id: finding.id } }"
    class="group grid gap-4 rounded-xl border border-line bg-surface p-4 shadow-card transition-colors hover:border-fg/30 sm:p-5"
  >
    <div class="flex items-start gap-3">
      <span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-input font-display text-lg font-extrabold" aria-hidden="true">
        {{ ex.supplier.charAt(0) }}
      </span>
      <div class="grid min-w-0 flex-1 gap-0.5">
        <h3 class="truncate text-base font-bold">{{ ex.supplier }}</h3>
        <span class="flex flex-wrap items-center gap-x-1.5 text-sm text-muted">
          <AppIcon name="calendar" :size="13" /> from {{ fmtDate(ex.effective_date) }}
        </span>
      </div>
      <div class="grid justify-items-end leading-tight">
        <span :class="['font-display text-2xl font-extrabold tabular-nums', tone.text]">{{ pct(ex.increase_pct) }}</span>
        <span class="text-[0.78rem] tabular-nums text-muted">{{ eur(finding.impact.next_12_months) }} / year</span>
      </div>
    </div>

    <PriceBar :from="ex.old_monthly" :to="ex.new_monthly" :tone="tone.bar" />

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
      <StatusPill :tone="v.tone"><AppIcon :name="v.icon" :size="13" />{{ v.label }}</StatusPill>
      <div class="flex flex-wrap items-center gap-2">
        <AutonomyBadge level="recommendation" />
        <span class="text-sm font-semibold">{{ RECOMMENDATION[finding.recommendation] }}</span>
        <AppIcon name="arrowRight" class="text-muted transition-transform group-hover:translate-x-0.5" />
      </div>
    </div>
  </RouterLink>
</template>
