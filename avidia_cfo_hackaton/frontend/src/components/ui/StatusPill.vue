<script setup lang="ts">
import { TONE_SOFT, type Tone } from "./tones";

/**
 * THE status label of the app (trends, verdicts, statuses): a small flat rectangle – 6px radius, 13px, weight 500,
 * soft background + text in its tone. Same red, same green everywhere; positive/negative are for money & status only.
 * Transparent 1px border → exactly the height of AutonomyBadge (whose "simulated" level is dashed).
 */
withDefaults(defineProps<{ tone?: Tone }>(), { tone: "neutral" });
</script>

<template>
  <span
    :class="[
      'inline-flex w-fit max-w-full items-center gap-1.5 rounded-md border border-transparent px-2 py-0.5 text-caption font-medium leading-snug',
      TONE_SOFT[tone],
    ]"
  >
    <slot />
  </span>
</template>
