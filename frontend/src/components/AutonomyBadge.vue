<script setup lang="ts">
import type { Autonomy } from "../types";

// The four levels the challenge asks us to distinguish – always visible next to every agent step.
defineProps<{ level: Autonomy }>();
</script>

<script lang="ts">
export const AUTONOMY: Record<Autonomy, { label: string; icon: string; cls: string }> = {
  analyzed: { label: "Analysed by agent", icon: "🔍", cls: "bg-sky-100 text-sky-800" },
  recommendation: { label: "Recommendation", icon: "💡", cls: "bg-amber-100 text-amber-800" },
  approval: { label: "Needs your approval", icon: "✋", cls: "bg-rose-100 text-rose-800" },
  simulated: { label: "Simulated execution", icon: "🧪", cls: "bg-violet-100 text-violet-800" },
};
</script>

<template>
  <span :class="['inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold', AUTONOMY[level].cls]">
    <span aria-hidden="true">{{ AUTONOMY[level].icon }}</span>
    {{ AUTONOMY[level].label }}
  </span>
</template>
