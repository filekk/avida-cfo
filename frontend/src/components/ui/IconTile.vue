<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";
import { TONE_SOFT, type Tone } from "./tones";

/**
 * The coloured square (or circle) with an icon – a deliberate EXCEPTION, not the default:
 * only the four dashboard KPIs, empty states, the agent pipeline / autonomy legend and the inbox-check status.
 * Everywhere else (lists, rows, card headers, chat, timelines) an icon is a plain 16–18px muted <AppIcon> – or nothing.
 *   sm 40px (pipeline, status) · md 48px (KPIs – default) · lg 56px (empty states)
 * Default slot replaces the icon (a counterparty's initial = an avatar: `tone="neutral" round`). Decorative → aria-hidden.
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
const RADIUS = { sm: "rounded-lg", md: "rounded-xl", lg: "rounded-xl" };
const ICON = { sm: 18, md: 22, lg: 26 };
</script>

<template>
  <span
    :class="[
      'grid shrink-0 place-items-center font-display font-semibold',
      BOX[size],
      round ? 'rounded-full' : RADIUS[size],
      TONE_SOFT[tone],
    ]"
    aria-hidden="true"
  >
    <slot><AppIcon v-if="icon" :name="icon" :size="ICON[size]" /></slot>
  </span>
</template>
