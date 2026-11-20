<script setup lang="ts">
import { computed } from "vue";
import { eur, eurSigned } from "@/utils/format";

/**
 * Old vs new monthly price as one stacked bar: the old price in sky, the increase in the verdict colour.
 * negative = not allowed · warn = unclear · neutral = allowed (still a cost, but a legitimate one).
 */
const props = withDefaults(defineProps<{ from: number; to: number; tone?: "negative" | "warn" | "neutral" }>(), {
  tone: "neutral",
});

const DELTA = { negative: "bg-negative", warn: "bg-warn", neutral: "bg-muted/50" };
const DELTA_TEXT = { negative: "text-negative", warn: "text-warn", neutral: "text-muted" };

const oldShare = computed(() => {
  const top = Math.max(props.from, props.to, 1);
  return (Math.min(props.from, props.to) / top) * 100;
});
</script>

<template>
  <div class="grid gap-1.5">
    <div
      class="flex h-3 overflow-hidden rounded-full bg-input"
      role="img"
      :aria-label="`Monthly price goes from ${eur(from)} to ${eur(to)}`"
    >
      <div class="h-full bg-sky" :style="{ width: `${oldShare}%` }" />
      <div :class="['h-full', DELTA[tone]]" :style="{ width: `${100 - oldShare}%` }" />
    </div>
    <div class="flex flex-wrap items-baseline justify-between gap-x-3 text-[0.8rem] tabular-nums text-muted" aria-hidden="true">
      <span>Before <b class="text-fg">{{ eur(from) }}</b></span>
      <b :class="DELTA_TEXT[tone]">{{ eurSigned(to - from) }}</b>
      <span>Now <b class="text-fg">{{ eur(to) }}</b> /month</span>
    </div>
  </div>
</template>
