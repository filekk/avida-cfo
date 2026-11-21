<script setup lang="ts">
/** Section heading inside a view (prototype ".sec-head"). */
defineProps<{ title: string; eyebrow?: string; description?: string }>();
</script>

<template>
  <div class="flex flex-wrap items-end justify-between gap-3">
    <div class="grid gap-2">
      <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
      <h2 class="text-xl font-semibold sm:text-2xl">{{ title }}</h2>
      <p v-if="description" class="max-w-prose text-muted">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap gap-2"><slot /></div>
  </div>
</template>
