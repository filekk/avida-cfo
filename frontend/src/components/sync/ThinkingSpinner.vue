<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";

/**
 * "Avida is working" indicator (think: Claude while it writes): a sun comet-ring that keeps turning around
 * the icon of the agent at work. When the agent changes, the centre icon morphs into the next one
 * (fade + turn + scale, both layers in one cell → never empty), and it breathes gently while working.
 * The ring is plain CSS geometry (conic gradient + mask) – no icon asset. Reduced motion: main.css stops it.
 */
withDefaults(defineProps<{ icon: IconName; size?: "sm" | "md"; spinning?: boolean }>(), {
  size: "md",
  spinning: true,
});

const BOX = { sm: "h-6 w-6", md: "h-12 w-12" };
const ICON = { sm: 13, md: 22 };
</script>

<template>
  <span :class="['relative grid shrink-0 place-items-center rounded-full', BOX[size]]" aria-hidden="true">
    <!-- track -->
    <span :class="['absolute inset-0 rounded-full', size === 'sm' ? 'ring-[1.5px]' : 'ring-[3px]', 'ring-inset ring-line']" />
    <!-- turning comet arc -->
    <span
      :class="[
        'thinking-ring absolute inset-0 rounded-full transition-opacity duration-base',
        size === 'sm' ? 'thinking-ring--sm' : '',
        spinning ? 'opacity-100' : 'opacity-0',
      ]"
    />
    <!-- centre icon: morphs between agents -->
    <TransitionGroup
      name="thinking-icon"
      tag="span"
      :class="['relative grid place-items-center [&>*]:col-start-1 [&>*]:row-start-1', spinning ? 'thinking-breathe' : '']"
    >
      <AppIcon :key="icon" :name="icon" :size="ICON[size]" />
    </TransitionGroup>
  </span>
</template>

<style scoped>
.thinking-ring {
  background: conic-gradient(from 0deg, rgb(var(--c-sun) / 0) 0deg, rgb(var(--c-sun) / 0.15) 90deg, rgb(var(--c-sun)) 300deg, rgb(var(--c-sun) / 0) 301deg);
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 3px));
  mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 3px));
  animation: thinking-turn 1.1s linear infinite;
}
.thinking-ring--sm {
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px));
  mask: radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px));
}
.thinking-breathe {
  animation: thinking-breathe 1.8s ease-in-out infinite;
}
@keyframes thinking-turn {
  to {
    transform: rotate(360deg);
  }
}
@keyframes thinking-breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.14);
  }
}
.thinking-icon-enter-active,
.thinking-icon-leave-active {
  transition: opacity var(--dur-slow) var(--ease-out), transform var(--dur-slow) var(--ease-out);
}
.thinking-icon-enter-from {
  opacity: 0;
  transform: scale(0.5) rotate(-60deg);
}
.thinking-icon-leave-to {
  opacity: 0;
  transform: scale(0.5) rotate(60deg);
}
</style>
