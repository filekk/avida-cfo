<script setup lang="ts">
import { TONE_SOFT, type Tone } from "./tones";

/**
 * Prototype ".pill" / ".chip" – THE pill of the app (trends, verdicts, statuses). Same red, same green everywhere.
 * Tone carries meaning – positive/negative are for money & status only.
 */
withDefaults(defineProps<{ tone?: Tone }>(), { tone: "neutral" });
</script>

<template>
  <span
    :class="[
      'inline-flex w-fit max-w-full items-center gap-1.5 rounded-full px-2.5 py-1 text-caption font-semibold leading-tight',
      TONE_SOFT[tone],
    ]"
  >
    <slot />
  </span>
</template>
