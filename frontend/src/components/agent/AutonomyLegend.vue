<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { AUTONOMY, AUTONOMY_ORDER } from "@/constants/autonomy";
import AutonomyBadge from "./AutonomyBadge.vue";

/** detailed = the four levels as a left-to-right flow (agent alone → you decide → sandbox); otherwise a row of badges. */
withDefaults(defineProps<{ detailed?: boolean }>(), { detailed: false });
</script>

<template>
  <ol v-if="detailed" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <li v-for="(l, i) in AUTONOMY_ORDER" :key="l" class="relative grid content-start gap-3 rounded-xl bg-input/70 p-4">
      <div class="flex items-center gap-3">
        <span :class="['grid h-10 w-10 shrink-0 place-items-center rounded-xl', AUTONOMY[l].classes]">
          <AppIcon :name="AUTONOMY[l].icon" :size="19" />
        </span>
        <span class="font-display text-2xl font-extrabold text-line" aria-hidden="true">{{ i + 1 }}</span>
      </div>
      <AutonomyBadge :level="l" />
      <span class="text-sm leading-snug text-muted">{{ AUTONOMY[l].description }}</span>
      <!-- arrow to the next level (single row on lg) -->
      <span
        v-if="i < AUTONOMY_ORDER.length - 1"
        class="absolute -right-[1.05rem] top-7 z-10 hidden h-6 w-6 place-items-center rounded-full border border-line bg-surface text-muted lg:grid"
        aria-hidden="true"
      >
        <AppIcon name="arrowRight" :size="13" />
      </span>
    </li>
  </ol>
  <div v-else class="flex flex-wrap gap-2">
    <AutonomyBadge v-for="l in AUTONOMY_ORDER" :key="l" :level="l" />
  </div>
</template>
