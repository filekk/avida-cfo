<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";

/**
 * Plain loading indicator: a 2px ring with one turning arc (navy on the line colour). No halo, no breathing.
 *   md (48px) – keeps the icon of whoever is at work in the middle; it swaps with one soft fade when the agent changes
 *   sm (18px) – the ring alone; the label next to it already says what is happening
 * `spinning = false` leaves the static ring. Reduced motion: main.css stops the turn.
 */
withDefaults(defineProps<{ icon?: IconName; size?: "sm" | "md"; spinning?: boolean }>(), {
  size: "md",
  spinning: true,
});

const BOX = { sm: "h-[1.125rem] w-[1.125rem]", md: "h-12 w-12" };
</script>

<template>
  <span :class="['relative grid shrink-0 place-items-center', BOX[size]]" aria-hidden="true">
    <span :class="['absolute inset-0 rounded-full border-2 border-line', spinning ? 'animate-spin border-t-fg' : '']" />
    <TransitionGroup
      v-if="size === 'md' && icon"
      name="fade"
      tag="span"
      class="grid place-items-center text-muted [&>*]:col-start-1 [&>*]:row-start-1"
    >
      <AppIcon :key="icon" :name="icon" :size="20" />
    </TransitionGroup>
  </span>
</template>
