<script setup lang="ts">
/** Prototype ".panel": white card, 1px line border, 12px radius. No shadow – the border carries the depth. */
withDefaults(defineProps<{ title?: string; eyebrow?: string; padded?: boolean; as?: string }>(), {
  padded: true,
  as: "section",
});
</script>

<template>
  <component :is="as" class="min-w-0 rounded-xl border border-line bg-surface">
    <header
      v-if="title || eyebrow || $slots.actions"
      :class="['flex flex-wrap items-center justify-between gap-x-3 gap-y-2', padded ? 'px-4 pt-4 sm:px-5 sm:pt-5' : 'px-4 py-3 sm:px-5']"
    >
      <div class="grid gap-2">
        <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
        <h2 v-if="title" class="text-lg font-semibold leading-tight">{{ title }}</h2>
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2"><slot name="actions" /></div>
    </header>
    <div :class="padded ? 'p-4 sm:p-5' : ''"><slot /></div>
  </component>
</template>
