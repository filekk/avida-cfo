<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { useTheme } from "@/composables/useTheme";

/** One-click light/dark switch. Shares state with the "Colours" choice in the accessibility menu. */
const { isDark, toggle } = useTheme();
</script>

<template>
  <button
    type="button"
    class="group grid h-10 w-10 place-items-center rounded-lg border border-line bg-surface text-fg hover:bg-mist"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Light mode' : 'Dark mode'"
    @click="toggle"
  >
    <Transition name="fade" mode="out-in">
      <AppIcon :key="isDark ? 'sun' : 'moon'" :name="isDark ? 'sun' : 'moon'" :size="19" class="transition-transform duration-base group-hover:rotate-12" />
    </Transition>
  </button>
</template>
