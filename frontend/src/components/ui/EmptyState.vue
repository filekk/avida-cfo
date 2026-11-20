<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import type { IconName } from "./icons";

withDefaults(defineProps<{ title: string; description?: string; icon?: IconName }>(), { icon: "inbox" });
</script>

<template>
  <div class="grid justify-items-center gap-3 rounded-xl border border-dashed border-line bg-surface px-6 py-12 text-center">
    <span class="grid h-11 w-11 place-items-center rounded-xl bg-mist text-mist-fg">
      <AppIcon :name="icon" :size="20" />
    </span>
    <h3 class="text-base font-bold">{{ title }}</h3>
    <p v-if="description" class="max-w-md text-muted">{{ description }}</p>
    <div v-if="$slots.default" class="mt-1"><slot /></div>
  </div>
</template>
