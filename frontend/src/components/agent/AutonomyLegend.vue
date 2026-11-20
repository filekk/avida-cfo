<script setup lang="ts">
import { AUTONOMY, AUTONOMY_ORDER } from "@/constants/autonomy";
import AutonomyBadge from "./AutonomyBadge.vue";

withDefaults(defineProps<{ detailed?: boolean }>(), { detailed: false });
</script>

<template>
  <ul v-if="detailed" class="grid gap-3 sm:grid-cols-2">
    <li v-for="l in AUTONOMY_ORDER" :key="l" class="grid gap-1.5">
      <AutonomyBadge :level="l" />
      <span class="text-sm text-muted">{{ AUTONOMY[l].description }}</span>
    </li>
  </ul>
  <div v-else class="flex flex-wrap gap-2">
    <AutonomyBadge v-for="l in AUTONOMY_ORDER" :key="l" :level="l" />
  </div>
</template>
