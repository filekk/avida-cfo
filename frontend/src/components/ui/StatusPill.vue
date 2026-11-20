<script setup lang="ts">
/** Prototype ".pill" / ".chip". Tone carries meaning – positive/negative are for money & status only. */
type PillTone = "positive" | "negative" | "warn" | "info" | "neutral" | "accent";

withDefaults(defineProps<{ tone?: PillTone }>(), { tone: "neutral" });

const TONES: Record<PillTone, string> = {
  positive: "bg-positive-soft text-positive",
  negative: "bg-negative-soft text-negative",
  warn: "bg-warn-soft text-warn",
  info: "bg-mist text-mist-fg",
  neutral: "bg-input text-muted",
  accent: "bg-sun text-sun-on",
};
</script>

<template>
  <span :class="['inline-flex w-fit max-w-full items-center gap-1 rounded-full px-2.5 py-0.5 text-[0.75rem] font-semibold leading-snug', TONES[tone]]">
    <slot />
  </span>
</template>
