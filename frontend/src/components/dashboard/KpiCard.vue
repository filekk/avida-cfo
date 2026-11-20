<script setup lang="ts">
import StatusPill from "@/components/ui/StatusPill.vue";

/** Prototype ".kpi". `highlight` = sun card – use for at most ONE KPI per screen. */
defineProps<{
  label: string;
  value: string;
  sub?: string;
  delta?: { text: string; tone: "positive" | "negative" | "neutral" };
  highlight?: boolean;
}>();
</script>

<template>
  <div
    :class="[
      'grid content-start gap-1 rounded-xl border p-4',
      highlight ? 'border-sun bg-sun text-sun-on' : 'border-line bg-surface',
    ]"
  >
    <span :class="['text-[0.78rem] font-medium', highlight ? 'opacity-75' : 'text-muted']">{{ label }}</span>
    <span class="font-display text-[1.4rem] font-bold tabular-nums tracking-tight">{{ value }}</span>
    <span v-if="sub" :class="['text-[0.8rem]', highlight ? 'opacity-75' : 'text-muted']">{{ sub }}</span>
    <StatusPill v-if="delta && !highlight" :tone="delta.tone">{{ delta.text }}</StatusPill>
    <span v-else-if="delta" class="w-fit rounded-full bg-sun-on/10 px-2 py-0.5 text-[0.75rem] font-semibold">{{ delta.text }}</span>
  </div>
</template>
