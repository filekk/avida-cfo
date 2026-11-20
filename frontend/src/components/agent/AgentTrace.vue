<script setup lang="ts">
import BaseCard from "@/components/ui/BaseCard.vue";
import type { TraceEvent } from "@/types/api";
import AutonomyBadge from "./AutonomyBadge.vue";
import SourceTag from "./SourceTag.vue";

/** Live log of agent steps streamed from /api/sync. */
defineProps<{ events: TraceEvent[]; running: boolean }>();
</script>

<template>
  <BaseCard v-if="events.length || running" eyebrow="Live" title="What your assistant is doing">
    <ol class="grid gap-2.5" aria-live="polite">
      <li
        v-for="(e, i) in events"
        :key="i"
        class="grid gap-1 border-l-2 border-line pl-3 sm:grid-cols-[8.5rem_auto_1fr] sm:items-center sm:gap-3"
      >
        <span class="text-sm font-semibold text-muted">{{ e.agent }}</span>
        <AutonomyBadge :level="e.autonomy" />
        <span>{{ e.message }} <SourceTag :source="e.source" /></span>
      </li>
      <li v-if="running" class="animate-pulse border-l-2 border-sun pl-3 text-muted">Working…</li>
    </ol>
  </BaseCard>
</template>
