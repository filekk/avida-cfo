<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { RECOMMENDATION, VERDICT } from "@/constants/autonomy";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";

/** Compact summary of one detected price change. Links to the split-screen detail. */
const props = defineProps<{ finding: Finding }>();
const v = computed(() => VERDICT[props.finding.contract.verdict]);
</script>

<template>
  <RouterLink
    :to="{ name: 'finding-detail', params: { id: finding.id } }"
    class="group grid gap-3 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-fg/30 sm:p-5"
  >
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="grid gap-1">
        <span class="text-sm text-muted">{{ finding.email.from_name }} · {{ fmtDate(finding.email.received) }}</span>
        <h3 class="text-base font-bold">
          {{ finding.extraction.supplier }}: {{ pct(finding.extraction.increase_pct) }} from {{ fmtDate(finding.extraction.effective_date) }}
        </h3>
      </div>
      <StatusPill :tone="v.tone">{{ v.label }}</StatusPill>
    </div>

    <p class="text-muted">{{ finding.contract.explanation_simple }}</p>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3 text-sm">
      <div class="flex flex-wrap items-center gap-x-5 gap-y-1">
        <span>Extra cost <b class="tabular-nums">{{ eur(finding.impact.monthly) }}</b>/month</span>
        <span>12 months <b class="tabular-nums">{{ eur(finding.impact.next_12_months) }}</b></span>
      </div>
      <div class="flex items-center gap-2">
        <AutonomyBadge level="recommendation" />
        <span class="font-semibold">{{ RECOMMENDATION[finding.recommendation] }}</span>
        <AppIcon name="arrowRight" class="text-muted transition-transform group-hover:translate-x-0.5" />
      </div>
    </div>
  </RouterLink>
</template>
