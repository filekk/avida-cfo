<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { useTheme } from "@/composables/useTheme";
import { t } from "@/i18n";

/**
 * One-click light/dark switch. Shares state with the "Colours" choice in the accessibility menu.
 *
 * Both icons are ALWAYS rendered, stacked in one grid cell, and cross-fade/rotate purely with classes.
 * (It used to be <Transition mode="out-in"> around a keyed <AppIcon>: in dev AppIcon renders a fragment
 * – template comment + <svg> – so the leave hook never fired and the button stayed empty for good.
 * With nothing mounted/unmounted there is no state in which the button can end up empty.)
 */
const { isDark, toggle } = useTheme();

const ICON = "col-start-1 row-start-1 grid place-items-center transition-[opacity,transform] duration-base ease-out";
</script>

<template>
  <button
    type="button"
    class="group grid h-10 w-10 place-items-center rounded-lg border border-line bg-surface text-fg hover:bg-mist"
    :aria-label="isDark ? t('Switch to light mode') : t('Switch to dark mode')"
    :title="isDark ? t('Light mode') : t('Dark mode')"
    @click="toggle"
  >
    <span class="grid" aria-hidden="true">
      <!-- moon = "switch to dark" (shown in light mode) -->
      <span :class="[ICON, isDark ? 'rotate-90 scale-50 opacity-0' : 'rotate-0 scale-100 opacity-100 group-hover:-rotate-12']">
        <AppIcon name="moon" :size="19" />
      </span>
      <!-- sun = "switch to light" (shown in dark mode) -->
      <span :class="[ICON, isDark ? 'rotate-0 scale-100 opacity-100 group-hover:rotate-45' : '-rotate-90 scale-50 opacity-0']">
        <AppIcon name="sun" :size="19" />
      </span>
    </span>
  </button>
</template>
