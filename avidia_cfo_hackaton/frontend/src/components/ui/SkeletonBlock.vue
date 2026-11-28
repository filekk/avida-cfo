<script setup lang="ts">
/**
 * Loading placeholder for content areas – static (no pulsing). Line colour at half strength, so it still shows
 * on the grey page background (the input colour would vanish there).
 */
withDefaults(defineProps<{ height?: string }>(), { height: "h-24" });
</script>

<template>
  <div :class="['rounded-xl bg-line/50', height]" aria-hidden="true" />
</template>
