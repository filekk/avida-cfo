<script setup lang="ts">
/** Loading placeholder. Use instead of spinners for content areas. */
withDefaults(defineProps<{ height?: string }>(), { height: "h-24" });
</script>

<template>
  <div :class="['animate-pulse rounded-xl bg-input', height]" aria-hidden="true" />
</template>
