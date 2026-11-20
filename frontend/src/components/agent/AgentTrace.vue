<script setup lang="ts">
import { computed, ref } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import { agentIcon } from "@/constants/agents";
import type { Autonomy, TraceEvent } from "@/types/api";
import AutonomyBadge from "./AutonomyBadge.vue";
import SourceTag from "./SourceTag.vue";

/**
 * Live log of agent steps streamed from /api/sync, drawn as a timeline (agent icon on a line).
 * While running it is always open; once done it folds to one line so the result isn't buried in text.
 */
const props = defineProps<{ events: TraceEvent[]; running: boolean }>();
const open = ref(false);
const expanded = computed(() => props.running || open.value);

const NODE: Record<Autonomy, string> = {
  analyzed: "bg-mist text-mist-fg",
  recommendation: "bg-warn-soft text-warn",
  approval: "bg-sun text-sun-on",
  simulated: "bg-input text-muted",
};
</script>

<template>
  <BaseCard
    v-if="events.length || running"
    :eyebrow="running ? 'Live' : 'Done'"
    title="What your assistant did"
    :padded="expanded"
  >
    <template v-if="!running" #actions>
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold text-gold hover:bg-mist"
        :aria-expanded="open"
        @click="open = !open"
      >
        {{ open ? "Hide steps" : `Show all ${events.length} steps` }}
        <AppIcon name="chevronDown" :class="['transition-transform', open ? 'rotate-180' : '']" />
      </button>
    </template>

    <ol v-if="expanded" class="grid" aria-live="polite">
      <li v-for="(e, i) in events" :key="i" class="relative grid grid-cols-[2rem_1fr] gap-3 pb-4 last:pb-0">
        <span
          v-if="i < events.length - 1 || running"
          class="absolute bottom-0 left-4 top-9 w-px -translate-x-1/2 bg-line"
          aria-hidden="true"
        />
        <span :class="['grid h-8 w-8 place-items-center rounded-full', NODE[e.autonomy]]" aria-hidden="true">
          <AppIcon :name="agentIcon(e.agent)" :size="15" />
        </span>
        <div class="grid gap-1 pt-0.5">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-[0.8rem] font-semibold text-muted">{{ e.agent }}</span>
            <AutonomyBadge :level="e.autonomy" />
          </div>
          <p class="text-[0.92rem] leading-snug">{{ e.message }} <SourceTag :source="e.source" /></p>
        </div>
      </li>
      <li v-if="running" class="grid grid-cols-[2rem_1fr] items-center gap-3 text-muted">
        <span class="grid h-8 w-8 place-items-center rounded-full border-2 border-dashed border-sun" aria-hidden="true">
          <AppIcon name="loader" :size="14" class="animate-spin" />
        </span>
        Working…
      </li>
    </ol>
  </BaseCard>
</template>
