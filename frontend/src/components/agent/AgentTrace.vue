<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { agentIcon, isHandoff } from "@/constants/agents";
import { t } from "@/i18n";
import type { TraceEvent } from "@/types/api";
import { prefersReducedMotion } from "@/utils/motion";
import AutonomyBadge from "./AutonomyBadge.vue";
import SourceTag from "./SourceTag.vue";

/**
 * The agents' steps streamed from /api/sync, as a chat-like timeline (newest at the bottom, like a conversation).
 * Lives in the inbox-check pop-up: own scroll area that follows new steps (unless you scrolled up to read),
 * new steps rise in as they arrive (the only list that animates – it is live), a small spinner shows more is coming.
 * Every step shows the agent and its autonomy badge (challenge requirement). Backend messages stay as sent.
 */
const props = defineProps<{ events: TraceEvent[]; running: boolean }>();

const list = ref<HTMLOListElement | null>(null);
let follow = true; // stop auto-scrolling when the owner scrolls up to read
/**
 * Scroll edges that have more steps behind them fade out (top when scrolled, bottom when not at the end).
 * Technical alpha mask on the scroll edge, not a colour effect – the one deliberate exception in the design rules.
 */
const edges = ref({ top: false, bottom: false });

function measureEdges() {
  const el = list.value;
  if (!el) return;
  const rest = el.scrollHeight - el.scrollTop - el.clientHeight;
  edges.value = { top: el.scrollTop > 4, bottom: rest > 4 };
}
function onScroll() {
  const el = list.value;
  if (el) follow = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
  measureEdges();
}
function toBottom(smooth: boolean) {
  const el = list.value;
  if (!el) return;
  el.scrollTo({ top: el.scrollHeight, behavior: smooth && !prefersReducedMotion() ? "smooth" : "auto" });
  measureEdges();
}

watch(
  () => props.events.length,
  (n, was) => {
    if (!n) follow = true;
    nextTick(() => (follow ? toBottom((was ?? 0) > 0) : measureEdges()));
  },
);

// The pop-up is hidden with v-show: while hidden nothing can scroll. When it is shown again (size goes 0 → N)
// jump straight to the latest step – unless the owner had scrolled up to read.
let ro: ResizeObserver | null = null;
let wasVisible = false;
onMounted(() => {
  ro = new ResizeObserver(() => {
    const visible = !!list.value?.clientHeight;
    if (visible && !wasVisible && follow) toBottom(false);
    else measureEdges();
    wasVisible = visible;
  });
  if (list.value) ro.observe(list.value);
});
onBeforeUnmount(() => ro?.disconnect());

const FADE = "1.5rem";
const mask = computed(() => {
  const { top, bottom } = edges.value;
  if (!top && !bottom) return undefined;
  const g = `linear-gradient(to bottom, ${top ? "transparent" : "#000"} 0, #000 ${FADE}, #000 calc(100% - ${FADE}), ${bottom ? "transparent" : "#000"} 100%)`;
  return { maskImage: g, WebkitMaskImage: g };
});
</script>

<template>
  <ol
    ref="list"
    class="sync-scroll grid max-h-[17rem] content-start overflow-y-auto overscroll-contain pr-1"
    aria-live="polite"
    :aria-label="t('What your assistant did')"
    :style="mask"
    @scroll.passive="onScroll"
  >
    <li
      v-for="(e, i) in events"
      :key="i"
      class="relative grid animate-rise grid-cols-[2.5rem_minmax(0,1fr)] gap-3 pb-4 last:pb-0"
    >
      <!-- timeline line to the next step (between this icon and the next one) -->
      <span
        v-if="i < events.length - 1 || running"
        class="absolute -bottom-1 left-5 top-9 w-px -translate-x-1/2 bg-line"
        aria-hidden="true"
      />
      <!-- small muted agent icon on the line; the autonomy level is the badge next to it (no coloured node) -->
      <span class="grid h-10 w-10 place-items-center text-muted" aria-hidden="true">
        <AppIcon :name="isHandoff(e) ? 'messageSquare' : agentIcon(e.agent)" :size="18" />
      </span>
      <div class="grid min-w-0 gap-1 pt-0.5">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span class="flex min-w-0 flex-wrap items-center gap-1 text-label font-semibold text-muted">
            {{ t(e.agent) }}
            <template v-if="isHandoff(e)">
              <AppIcon name="arrowRight" :size="14" aria-hidden="true" />
              <span class="sr-only">{{ t("to") }}</span>
              {{ t(e.to!) }}
            </template>
          </span>
          <AutonomyBadge :level="e.autonomy" />
        </div>
        <p class="text-label leading-snug text-fg [overflow-wrap:anywhere]">
          {{ e.message }}
          <SourceTag :source="e.source" />
        </p>
      </div>
    </li>

    <!-- more is coming -->
    <li v-if="running" class="grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-3" aria-hidden="true">
      <span class="grid h-10 w-10 place-items-center"><ThinkingSpinner size="sm" /></span>
      <span class="text-caption text-muted">{{ t("Working…") }}</span>
    </li>
  </ol>
</template>

<style scoped>
.sync-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--c-line)) transparent;
}
</style>
