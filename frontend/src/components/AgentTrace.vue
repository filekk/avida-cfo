<script setup lang="ts">
import type { TraceEvent } from "../types";
import AutonomyBadge from "./AutonomyBadge.vue";

defineProps<{ events: TraceEvent[]; running: boolean }>();
</script>

<template>
  <section v-if="events.length || running" class="rounded-2xl bg-white p-5 shadow-sm">
    <h2 class="mb-3 text-lg font-bold">What your assistant did</h2>
    <ol class="space-y-2">
      <li
        v-for="(e, i) in events"
        :key="i"
        class="flex flex-col gap-1 border-l-4 border-slate-200 pl-3 sm:flex-row sm:items-center sm:gap-3"
      >
        <span class="w-36 shrink-0 text-sm font-semibold text-slate-500">{{ e.agent }}</span>
        <AutonomyBadge :level="e.autonomy" />
        <span>{{ e.message }}</span>
        <span v-if="e.source === 'fallback'" class="text-xs text-slate-400">(cached answer)</span>
      </li>
      <li v-if="running" class="animate-pulse pl-4 text-slate-400">Working…</li>
    </ol>
  </section>
</template>
