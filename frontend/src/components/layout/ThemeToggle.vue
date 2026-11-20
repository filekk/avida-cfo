<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { useTheme } from "@/composables/useTheme";

const { isDark, toggle } = useTheme();
</script>

<template>
  <button
    type="button"
    class="grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface text-fg hover:bg-mist"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Light mode' : 'Dark mode'"
    @click="toggle"
  >
    <AppIcon :name="isDark ? 'sun' : 'moon'" :size="17" />
  </button>
</template>
