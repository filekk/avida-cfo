<script setup lang="ts">
import { computed } from "vue";

/** Ring gauge "X of N days safe" – sits on the navy headline band, so it uses on-dark colours. */
const props = defineProps<{ days: number; horizon: number; safe: boolean }>();

const R = 34;
const C = 2 * Math.PI * R;
const dash = computed(() => {
  const frac = props.horizon > 0 ? Math.min(1, Math.max(0, props.days / props.horizon)) : 0;
  return `${(C * frac).toFixed(1)} ${C.toFixed(1)}`;
});
</script>

<template>
  <div class="relative grid h-24 w-24 shrink-0 place-items-center" role="img" :aria-label="`${days} of ${horizon} days safe`">
    <svg viewBox="0 0 84 84" class="absolute inset-0 h-full w-full -rotate-90" aria-hidden="true">
      <circle cx="42" cy="42" :r="R" fill="none" stroke-width="8" class="stroke-white/15" />
      <circle
        cx="42" cy="42" :r="R" fill="none" stroke-width="8" stroke-linecap="round"
        :stroke-dasharray="dash"
        :class="safe ? 'stroke-mint' : 'stroke-sun'"
      />
    </svg>
    <span class="relative grid text-center leading-none" aria-hidden="true">
      <b class="font-display text-[1.6rem] font-extrabold tabular-nums">{{ days }}</b>
      <span class="mt-1 text-[0.68rem] font-semibold text-side-fg">of {{ horizon }} days</span>
    </span>
  </div>
</template>
