<script setup lang="ts">
import { ICONS, type IconName } from "./icons";

withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 16 });
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html – static, trusted paths from icons.ts -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    aria-hidden="true"
    v-html="ICONS[name]"
  />
</template>
