<script setup lang="ts">
import { computed } from "vue";
import { prefersReducedMotion } from "@/utils/motion";

/**
 * Text with a soft light sweep while something is in progress (the "thinking" line).
 * Both ends of the sweep are plain text colour, so the text is always fully readable – also when animations
 * are cut short by reduced motion (then the sweep is not applied at all).
 */
const props = withDefaults(defineProps<{ active?: boolean }>(), { active: true });
const on = computed(() => props.active && !prefersReducedMotion());
</script>

<template>
  <span :class="on ? 'shimmer-text' : ''"><slot /></span>
</template>

<style scoped>
.shimmer-text {
  background-image: linear-gradient(
    100deg,
    rgb(var(--c-fg)) 0%,
    rgb(var(--c-fg)) 42%,
    rgb(var(--c-muted) / 0.4) 50%,
    rgb(var(--c-fg)) 58%,
    rgb(var(--c-fg)) 100%
  );
  background-size: 300% 100%;
  background-position: 100% 0;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: shimmer-sweep 2.2s ease-in-out infinite;
}
@keyframes shimmer-sweep {
  to {
    background-position: 0% 0;
  }
}
</style>
