<script setup lang="ts">
import IconTile from "./IconTile.vue";
import type { IconName } from "./icons";
import { TONE_TEXT, type Tone } from "./tones";

/**
 * Small "icon + label + number" tile – replaces sentences like "Extra cost: 1.470 €/month".
 * Tone colours the icon tile and – for positive/negative money – the value (green = good, red = bad).
 */
withDefaults(defineProps<{ icon: IconName; label: string; value: string; tone?: Tone; sub?: string }>(), {
  tone: "neutral",
});
</script>

<template>
  <div class="flex min-w-0 items-center gap-3">
    <IconTile :icon="icon" :tone="tone" />
    <span class="grid min-w-0 gap-0.5 leading-tight">
      <span class="text-label text-muted">{{ label }}</span>
      <span :class="['font-display text-xl font-bold tabular-nums', TONE_TEXT[tone]]">{{ value }}</span>
      <span v-if="sub" class="text-caption text-muted">{{ sub }}</span>
    </span>
  </div>
</template>
