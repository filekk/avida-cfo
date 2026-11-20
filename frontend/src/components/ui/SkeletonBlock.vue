<script setup lang="ts">
/** Loading placeholder. Use instead of spinners for content areas. Line colour so it shows on grey pages too. */
withDefaults(defineProps<{ height?: string }>(), { height: "h-24" });
</script>

<template>
  <div :class="['animate-pulse rounded-xl bg-line/70', height]" aria-hidden="true" />
</template>
