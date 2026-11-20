<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";
import { TONE_SOFT, type Tone } from "./tones";

/**
 * The rounded square (or circle) with an icon – used everywhere (KPIs, stats, lists, timelines).
 * ONE place for sizes so every tile in the app matches:
 *   sm 40px (dense rows, timelines) · md 48px (KPIs, stat tiles – default) · lg 56px (hero/pipeline/empty states)
 * Default slot replaces the icon (e.g. a supplier's initial). Decorative → aria-hidden.
 */
withDefaults(defineProps<{ icon?: IconName; tone?: Tone; size?: "sm" | "md" | "lg"; round?: boolean }>(), {
  tone: "info",
  size: "md",
  round: false,
});

const BOX = {
  sm: "h-10 w-10 text-base",
  md: "h-12 w-12 text-lg",
  lg: "h-14 w-14 text-xl",
};
const RADIUS = { sm: "rounded-lg", md: "rounded-xl", lg: "rounded-2xl" };
const ICON = { sm: 18, md: 22, lg: 26 };
</script>

<template>
  <span
    :class="[
      'grid shrink-0 place-items-center font-display font-extrabold',
      BOX[size],
      round ? 'rounded-full' : RADIUS[size],
      TONE_SOFT[tone],
    ]"
    aria-hidden="true"
  >
    <slot><AppIcon v-if="icon" :name="icon" :size="ICON[size]" /></slot>
  </span>
</template>
