<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import { AUTONOMY, AUTONOMY_ORDER } from "@/constants/autonomy";
import AutonomyBadge from "./AutonomyBadge.vue";

/** detailed = the four levels as a left-to-right flow (agent alone → you decide → sandbox); otherwise a row of badges. */
withDefaults(defineProps<{ detailed?: boolean }>(), { detailed: false });
</script>

<template>
  <ol v-if="detailed" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <li v-for="(l, i) in AUTONOMY_ORDER" :key="l" class="relative grid content-start gap-3 rounded-xl bg-input p-4">
      <div class="flex items-center gap-3">
        <!-- step number: readable (muted on surface ≈ 6.5:1), not decorative grey; left of the tile so the
             arrow to the next level on the right edge has room -->
        <span
          class="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-line bg-surface font-display text-label font-bold text-muted"
          aria-hidden="true"
        >{{ i + 1 }}</span>
        <IconTile :icon="AUTONOMY[l].icon" :tone="AUTONOMY[l].tone" :class="AUTONOMY[l].tile" />
      </div>
      <AutonomyBadge :level="l" />
      <span class="text-label leading-snug text-muted">{{ AUTONOMY[l].description }}</span>
      <!-- arrow to the next level (single row on lg), centred on the 12px gap -->
      <span
        v-if="i < AUTONOMY_ORDER.length - 1"
        class="absolute -right-5 top-[1.625rem] z-10 hidden h-7 w-7 place-items-center rounded-full border border-line bg-surface text-muted lg:grid"
        aria-hidden="true"
      >
        <AppIcon name="arrowRight" :size="14" />
      </span>
    </li>
  </ol>
  <div v-else class="flex flex-wrap gap-2">
    <AutonomyBadge v-for="l in AUTONOMY_ORDER" :key="l" :level="l" />
  </div>
</template>
