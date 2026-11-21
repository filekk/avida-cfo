<script setup lang="ts">
import AnimatedNumber from "./AnimatedNumber.vue";
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";
import { TONE_TEXT, type Tone } from "./tones";

/**
 * Small "label + number" stat – replaces sentences like "Extra cost: 1.470 €/month".
 * The icon is a small muted mark next to the label, not a coloured tile (tiles are reserved for the four KPIs,
 * empty states and the agent pipeline). Tone colours only the value: money green = good / red = bad, warn = waiting for you.
 * `value` = ready text (dates, ranges…) · `amount` = a number that counts up and glides (AnimatedNumber, money by
 * default; pass `format` for anything else, e.g. a count).
 */
withDefaults(
  defineProps<{
    icon?: IconName;
    label: string;
    value?: string;
    amount?: number;
    format?: (n: number) => string;
    tone?: Tone;
    sub?: string;
  }>(),
  { tone: "neutral" },
);
</script>

<template>
  <div class="grid min-w-0 content-start gap-1 leading-tight">
    <span class="flex items-center gap-1.5 text-label text-muted">
      <AppIcon v-if="icon" :name="icon" :size="16" class="shrink-0" />{{ label }}
    </span>
    <span :class="['font-display text-xl font-semibold tracking-tight tabular-nums', TONE_TEXT[tone]]">
      <!-- format undefined → AnimatedNumber's default (eur) -->
      <AnimatedNumber v-if="amount !== undefined" :value="amount" :format="format" />
      <template v-else>{{ value }}</template>
    </span>
    <span v-if="sub" class="text-caption text-muted">{{ sub }}</span>
  </div>
</template>
