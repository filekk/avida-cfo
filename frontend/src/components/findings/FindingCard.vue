<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { RECOMMENDATION, VERDICT } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { Finding } from "@/types/api";
import { describeFinding } from "./describe";
import PriceBar from "./PriceBar.vue";
import { verdictTone } from "./verdict";

/**
 * Compact, visual summary of one detected price change. Links to the split-screen detail
 * (/findings/:id → the Action center focus view). Built to read well at half width (2-column grid on the overview).
 */
const props = defineProps<{ finding: Finding }>();
const v = computed(() => VERDICT[props.finding.contract.verdict]);
const tone = computed(() => verdictTone(props.finding.contract.verdict));
const d = computed(() => describeFinding(props.finding));
const advice = computed(() => RECOMMENDATION[props.finding.recommendation] ?? props.finding.recommendation);
</script>

<template>
  <RouterLink
    :to="{ name: 'finding-detail', params: { id: finding.id } }"
    class="group grid content-start gap-4 rounded-xl border border-line bg-surface p-4 shadow-card transition-[border-color,box-shadow,transform] duration-base hover:-translate-y-0.5 hover:border-fg/30 hover:shadow-lift sm:p-5"
  >
    <!-- flex-wrap + rem min-width: a long name ("Bauer Maschinenbau AG") and a long figure ("30 Tage zu spät")
         never squeeze each other – the figure moves under the name when the card is narrow -->
    <div class="flex flex-wrap items-start gap-x-3 gap-y-2">
      <div class="flex min-w-[min(100%,13rem)] flex-1 items-start gap-3">
        <IconTile tone="neutral" class="!text-fg">{{ d.party.charAt(0) }}</IconTile>
        <div class="grid min-w-0 flex-1 gap-1">
          <h3 class="text-lg font-bold leading-tight [overflow-wrap:anywhere]">{{ d.party }}</h3>
          <span class="flex items-start gap-1.5 text-label text-muted">
            <AppIcon :name="finding.extraction.figures_stated === false ? 'info' : 'calendar'" :size="14" class="mt-0.5 shrink-0" />
            <span>{{ d.sub }}</span>
          </span>
        </div>
      </div>
      <div class="ml-auto grid justify-items-end gap-1 text-right leading-tight">
        <span :class="['font-display text-2xl font-extrabold tabular-nums', tone.text]">{{ d.figure }}</span>
        <span v-if="d.key" :class="['text-label font-semibold tabular-nums', tone.text === 'text-fg' ? 'text-muted' : tone.text]">
          {{ d.key.label }} {{ d.key.value }}
        </span>
      </div>
    </div>

    <PriceBar v-if="d.priceBar" :from="d.priceBar.from" :to="d.priceBar.to" :tone="tone.bar" />

    <StatusPill :tone="v.tone"><AppIcon :name="v.icon" :size="14" />{{ t(v.label) }}</StatusPill>

    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-t border-line pt-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <AutonomyBadge level="recommendation" />
        <span class="text-sm font-semibold">{{ t(advice) }}</span>
      </div>
      <span class="flex items-center gap-1 text-label font-semibold text-gold">
        {{ t("Details") }}
        <AppIcon name="arrowRight" :size="18" class="transition-transform duration-base group-hover:translate-x-1" />
      </span>
    </div>
  </RouterLink>
</template>
