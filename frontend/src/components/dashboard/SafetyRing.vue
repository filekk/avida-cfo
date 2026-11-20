<script setup lang="ts">
import { computed } from "vue";
import { t } from "@/i18n";

/**
 * Ring gauge "X of N days safe" – sits on the navy headline band, so it uses on-dark colours.
 * Sized in rem → grows with the accessibility text size; the arc animates when the value changes.
 */
const props = defineProps<{ days: number; horizon: number; safe: boolean }>();

const R = 36;
const C = 2 * Math.PI * R;
const dash = computed(() => {
  const frac = props.horizon > 0 ? Math.min(1, Math.max(0, props.days / props.horizon)) : 0;
  return `${(C * frac).toFixed(1)} ${C.toFixed(1)}`;
});
</script>

<template>
  <div class="grid shrink-0 justify-items-center gap-2" role="img" :aria-label="t('{days} of {n} days safe', { days, n: horizon })">
    <!-- number inside the ring, "of N days" underneath → nothing touches the stroke, at any text size -->
    <div class="relative grid h-24 w-24 place-items-center" aria-hidden="true">
      <svg viewBox="0 0 88 88" class="absolute inset-0 h-full w-full -rotate-90">
        <circle cx="44" cy="44" :r="R" fill="none" stroke-width="7" class="stroke-white/15" />
        <circle
          cx="44" cy="44" :r="R" fill="none" stroke-width="7" stroke-linecap="round"
          :stroke-dasharray="dash"
          :class="['transition-[stroke-dasharray,stroke] duration-slow', safe ? 'stroke-mint' : 'stroke-sun']"
        />
      </svg>
      <b class="relative font-display text-3xl font-extrabold leading-none tabular-nums">{{ days }}</b>
    </div>
    <span class="whitespace-nowrap text-caption font-semibold leading-none text-white/85" aria-hidden="true">{{ t("of {n} days", { n: horizon }) }}</span>
  </div>
</template>
