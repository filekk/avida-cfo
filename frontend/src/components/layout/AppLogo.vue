<script setup lang="ts">
import logoUrl from "@/assets/brand/avida-logo.png";
import { t } from "@/i18n";

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
    :class="['flex w-fit items-center gap-2.5 font-display text-lg font-semibold', onDark ? 'text-white' : 'text-fg']"
    :aria-label="t('Avida CFO, go to overview')"
  >
    <img
      :src="logoUrl"
      alt=""
      :width="size"
      :height="size"
      decoding="async"
      class="shrink-0 object-contain"
    />
    <span v-if="showText" aria-hidden="true">
      Avida <span :class="['font-medium', onDark ? 'text-side-fg' : 'text-muted']">CFO</span>
    </span>
  </RouterLink>
</template>
