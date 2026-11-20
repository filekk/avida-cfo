<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";

/**
 * Small "icon + label + number" tile – replaces sentences like "Extra cost: 1.470 €/month".
 * Tone colours the icon (and the value for positive/negative money). Same 4 tones as StatusPill.
 */
type Tone = "neutral" | "info" | "positive" | "negative" | "warn";
withDefaults(defineProps<{ icon: IconName; label: string; value: string; tone?: Tone; sub?: string }>(), {
  tone: "neutral",
});

const ICON_TILE: Record<Tone, string> = {
  neutral: "bg-input text-muted",
  info: "bg-mist text-mist-fg",
  positive: "bg-positive-soft text-positive",
  negative: "bg-negative-soft text-negative",
  warn: "bg-warn-soft text-warn",
};
const VALUE: Record<Tone, string> = {
  neutral: "",
  info: "",
  positive: "text-positive",
  negative: "text-negative",
  warn: "",
};
</script>

<template>
  <div class="flex min-w-0 items-center gap-3">
    <span :class="['grid h-10 w-10 shrink-0 place-items-center rounded-xl', ICON_TILE[tone]]">
      <AppIcon :name="icon" :size="18" />
    </span>
    <span class="grid min-w-0 leading-tight">
      <span class="truncate text-[0.78rem] text-muted">{{ label }}</span>
      <span :class="['font-display text-lg font-bold tabular-nums', VALUE[tone]]">{{ value }}</span>
      <span v-if="sub" class="truncate text-[0.75rem] text-muted">{{ sub }}</span>
    </span>
  </div>
</template>
