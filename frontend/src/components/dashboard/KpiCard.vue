<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import StatusPill from "@/components/ui/StatusPill.vue";

/** Prototype ".kpi" + icon tile. `highlight` = sun card – use for at most ONE KPI per screen. */
defineProps<{
  label: string;
  value: string;
  icon?: IconName;
  sub?: string;
  delta?: { text: string; tone: "positive" | "negative" | "neutral" };
  highlight?: boolean;
}>();

const TREND = { positive: "trendingUp", negative: "trendingDown", neutral: "chart" } as const;
</script>

<template>
  <div
    :class="[
      'flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-start lg:p-5',
      highlight ? 'border-sun bg-sun text-sun-on' : 'border-line bg-surface shadow-card',
    ]"
  >
    <span
      v-if="icon"
      :class="['grid h-11 w-11 shrink-0 place-items-center rounded-xl', highlight ? 'bg-sun-on/10' : 'bg-mist text-mist-fg']"
    >
      <AppIcon :name="icon" :size="20" />
    </span>
    <div class="grid min-w-0 content-start gap-1">
      <span :class="['text-[0.8rem] font-medium leading-tight', highlight ? 'opacity-80' : 'text-muted']">{{ label }}</span>
      <span class="font-display text-[1.45rem] font-bold leading-tight tabular-nums tracking-tight">{{ value }}</span>
      <span v-if="sub" :class="['text-[0.8rem]', highlight ? 'opacity-80' : 'text-muted']">{{ sub }}</span>
      <StatusPill v-if="delta && !highlight" :tone="delta.tone" class="mt-0.5">
        <AppIcon :name="TREND[delta.tone]" :size="13" />{{ delta.text }}
      </StatusPill>
    </div>
  </div>
</template>
