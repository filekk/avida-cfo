<script setup lang="ts">
import logoUrl from "@/assets/brand/avida-logo.png";

/**
 * Brand mark (navy tile with the sun "AV" arrow) + wordmark. `onDark` = on the navy sidebar,
 * otherwise on the page background. The PNG is 102 px, so keep `size` ≤ 48 for a sharp result on 2x screens.
 */
withDefaults(defineProps<{ onDark?: boolean; showText?: boolean; size?: number }>(), {
  onDark: true,
  showText: true,
  size: 34,
});
</script>

<template>
  <RouterLink
    :to="{ name: 'dashboard' }"
    :class="['flex w-fit items-center gap-2.5 font-display text-[1.1rem] font-extrabold', onDark ? 'text-white' : 'text-fg']"
    aria-label="Avida CFO, go to overview"
  >
    <img
      :src="logoUrl"
      alt=""
      :width="size"
      :height="size"
      decoding="async"
      :class="['shrink-0 rounded-[13%] ring-1', onDark ? 'ring-white/15' : 'ring-fg/10']"
    />
    <span v-if="showText" aria-hidden="true">
      Avida <span :class="['font-semibold', onDark ? 'text-side-fg' : 'text-muted']">CFO</span>
    </span>
  </RouterLink>
</template>
