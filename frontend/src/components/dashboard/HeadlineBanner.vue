<script setup lang="ts">
/** One sentence the owner understands at a glance (backend `headline`). Navy band, sun accent when at risk. */
defineProps<{ headline: string; safe: boolean }>();
</script>

<template>
  <section class="relative overflow-hidden rounded-xl bg-side px-5 py-5 text-white sm:px-6">
    <span
      :class="['absolute inset-y-0 left-0 w-1.5', safe ? 'bg-mint' : 'bg-sun']"
      aria-hidden="true"
    />
    <span class="eyebrow !text-side-fg">{{ safe ? "You're on track" : "Heads-up" }}</span>
    <p class="mt-2 max-w-3xl font-display text-lg font-bold leading-snug sm:text-xl">{{ headline }}</p>
  </section>
</template>
