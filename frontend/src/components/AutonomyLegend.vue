<script setup lang="ts">
import type { Autonomy } from "../types";
import AutonomyBadge, { AUTONOMY } from "./AutonomyBadge.vue";

const levels = Object.keys(AUTONOMY) as Autonomy[];
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <AutonomyBadge v-for="l in levels" :key="l" :level="l" />
  </div>
</template>
