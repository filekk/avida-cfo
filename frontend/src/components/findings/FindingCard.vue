<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { RECOMMENDATION, VERDICT } from "@/constants/autonomy";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";
import PriceBar from "./PriceBar.vue";
import { verdictTone } from "./verdict";

/**
 * Compact, visual summary of one detected price change. Links to the split-screen detail.
 * Built to read well at half width (2-column grids on the overview and the findings page).
 */
const props = defineProps<{ finding: Finding }>();
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const tone = computed(() => verdictTone(props.finding.contract.verdict));
const ex = computed(() => props.finding.extraction);
</script>

<template>
  <RouterLink
    :to="{ name: 'finding-detail', params: { id: finding.id } }"
    class="group grid content-start gap-4 rounded-xl border border-line bg-surface p-4 shadow-card transition-[border-color,box-shadow,transform] duration-base hover:-translate-y-0.5 hover:border-fg/30 hover:shadow-lift sm:p-5"
  >
    <div class="flex items-start gap-3">
      <IconTile tone="neutral" class="!text-fg">{{ ex.supplier.charAt(0) }}</IconTile>
      <div class="grid min-w-0 flex-1 gap-1">
        <h3 class="text-lg font-bold leading-tight">{{ ex.supplier }}</h3>
        <span class="flex flex-wrap items-center gap-x-1.5 text-label text-muted">
          <AppIcon name="calendar" :size="14" /> from {{ fmtDate(ex.effective_date) }}
        </span>
      </div>
      <div class="grid shrink-0 justify-items-end gap-1 leading-tight">
        <span :class="['font-display text-2xl font-extrabold tabular-nums', tone.text]">{{ pct(ex.increase_pct) }}</span>
        <span :class="['text-label font-semibold tabular-nums', tone.text === 'text-fg' ? 'text-muted' : tone.text]">
          {{ eur(finding.impact.next_12_months) }} / year
        </span>
      </div>
    </div>

    <PriceBar :from="ex.old_monthly" :to="ex.new_monthly" :tone="tone.bar" />

    <StatusPill :tone="v.tone"><AppIcon :name="v.icon" :size="14" />{{ v.label }}</StatusPill>

    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-t border-line pt-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <AutonomyBadge level="recommendation" />
        <span class="text-sm font-semibold">{{ RECOMMENDATION[finding.recommendation] }}</span>
      </div>
      <span class="flex items-center gap-1 text-label font-semibold text-gold">
        Details
        <AppIcon name="arrowRight" :size="18" class="transition-transform duration-base group-hover:translate-x-1" />
      </span>
    </div>
  </RouterLink>
</template>
