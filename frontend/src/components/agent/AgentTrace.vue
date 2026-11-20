<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import IconTile from "@/components/ui/IconTile.vue";
import { agentIcon } from "@/constants/agents";
import type { Autonomy, TraceEvent } from "@/types/api";
import type { Tone } from "@/components/ui/tones";
import AutonomyBadge from "./AutonomyBadge.vue";
import SourceTag from "./SourceTag.vue";

/**
 * Log of agent steps streamed from /api/sync, drawn as a timeline (agent icon on a line).
 * Folded: the first 3 steps + a faded peek of the 4th; the arrow at the bottom unfolds the rest.
 * Height is measured and animated, so opening/closing and new streamed steps never jump.
 */
const props = defineProps<{ events: TraceEvent[]; running: boolean }>();

const VISIBLE = 3;
const open = ref(false);
const canFold = computed(() => props.events.length > VISIBLE);

const NODE: Record<Autonomy, Tone> = {
  analyzed: "info",
  recommendation: "warn",
  approval: "accent",
  simulated: "neutral",
};

// --- measured height --------------------------------------------------------------------------
const list = ref<HTMLOListElement | null>(null);
const height = ref<number | null>(null);
/** px of the 4th step left visible (faded) – the fade covers only this strip, never the 3rd step */
const peekPx = ref(0);

function measure() {
  const ol = list.value;
  if (!ol) return;
  const items = ol.children as HTMLCollectionOf<HTMLElement>;
  const peek = items[VISIBLE];
  // ~half of the 4th step's first line peeks out under the 3 full steps
  peekPx.value = peek ? Math.round(Math.min(peek.offsetHeight, 80) * 0.55) : 0;
  height.value = open.value || !peek ? ol.scrollHeight : peek.offsetTop + peekPx.value;
}

let ro: ResizeObserver | null = null;
onMounted(() => {
  ro = new ResizeObserver(measure);
  watch(list, (el, prev) => {
    if (prev) ro?.unobserve(prev);
    if (el) ro?.observe(el);
    measure();
  }, { immediate: true });
});
onBeforeUnmount(() => ro?.disconnect());
watch([() => props.events.length, open], () => nextTick(measure));
// a new sync starts folded again
watch(() => props.running, (r) => r && (open.value = false));
</script>

<template>
  <BaseCard v-if="events.length || running" title="What your assistant did">
    <template #actions>
      <span
        :class="[
          'inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-caption font-semibold',
          running ? 'bg-warn-soft text-warn' : 'bg-positive-soft text-positive',
        ]"
        aria-live="polite"
      >
        <span :class="['h-2 w-2 rounded-full', running ? 'animate-pulse bg-warn' : 'bg-positive']" aria-hidden="true" />
        {{ running ? "Working" : "Done" }} · {{ events.length }} {{ events.length === 1 ? "step" : "steps" }}
      </span>
    </template>

    <div
      id="trace-steps"
      class="relative overflow-hidden transition-[height] duration-slow ease-out"
      :style="height !== null ? { height: `${height}px` } : undefined"
    >
      <ol ref="list" class="grid" aria-label="Steps">
        <li v-for="(e, i) in events" :key="i" class="relative grid grid-cols-[2.5rem_1fr] gap-3 pb-5 last:pb-0 animate-rise">
          <span
            v-if="i < events.length - 1 || running"
            class="absolute bottom-0 left-5 top-11 w-px -translate-x-1/2 bg-line"
            aria-hidden="true"
          />
          <IconTile :icon="agentIcon(e.agent)" :tone="NODE[e.autonomy]" size="sm" round />
          <div class="grid gap-1.5 pt-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-label font-semibold text-muted">{{ e.agent }}</span>
              <AutonomyBadge :level="e.autonomy" />
            </div>
            <p class="leading-snug">{{ e.message }} <SourceTag :source="e.source" /></p>
          </div>
        </li>
        <li v-if="running" class="grid grid-cols-[2.5rem_1fr] items-center gap-3 text-muted">
          <span class="grid h-10 w-10 place-items-center rounded-full border-2 border-dashed border-sun" aria-hidden="true">
            <AppIcon name="loader" :size="16" class="animate-spin" />
          </span>
          Working…
        </li>
      </ol>
      <!-- fade-out over the peeking 4th step -->
      <div
        :class="[
          'pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-surface via-surface/70 to-surface/20 transition-opacity duration-slow',
          canFold && !open ? 'opacity-100' : 'opacity-0',
        ]"
        :style="{ height: `${peekPx + 4}px` }"
        aria-hidden="true"
      />
    </div>

    <div v-if="canFold" class="mt-2 flex justify-center">
      <button
        type="button"
        class="group flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-label font-semibold text-fg hover:border-fg/40 hover:shadow-lift"
        aria-controls="trace-steps"
        :aria-expanded="open"
        @click="open = !open"
      >
        {{ open ? "Show less" : `Show all ${events.length} steps` }}
        <AppIcon name="chevronDown" :size="18" :class="['transition-transform duration-base', open ? 'rotate-180' : 'group-hover:translate-y-0.5']" />
      </button>
    </div>
  </BaseCard>
</template>
