<script setup lang="ts">
import { ICONS, type IconName } from "./icons";

// v-html below is safe: static, trusted SVG paths from icons.ts.
// Keep the template to ONE root element and NO leading HTML comment: in dev Vue keeps comments, a comment +
// <svg> becomes a fragment, and <Transition mode="out-in"> never finishes leaving a fragment → the icon vanished.
withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 16 });
</script>

<template>
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
