<script setup lang="ts">
import { computed } from "vue";
import AgentPipeline from "@/components/agent/AgentPipeline.vue";
import AgentTrace from "@/components/agent/AgentTrace.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import IconTile from "@/components/ui/IconTile.vue";
import { agentInfo } from "@/constants/agents";
import { t, tn } from "@/i18n";
import type { TraceEvent } from "@/types/api";
import ShimmerText from "./ShimmerText.vue";
import ThinkingSpinner from "./ThinkingSpinner.vue";
import { errorText, type SyncState } from "./sync";

/**
 * Content of the inbox-check pop-up: what is happening now (spinner + current job), who works on it (pipeline),
 * every step (timeline), and – once done – what came out of it with the next useful click.
 * Presentational: the parent (InboxCheck) owns the store and the open/close state.
 */
const props = defineProps<{
  state: SyncState;
  events: TraceEvent[];
  crew: string[];
  activeAgent: string | null;
  seen: string[];
  pending: number;
  findingsCount: number;
  error: string | null;
}>();
const emit = defineEmits<{ hide: []; start: []; reset: []; review: []; dismiss: [] }>();

/** Buttons in the narrow pop-up may wrap their label (German / large text) instead of overflowing. */
const WRAP = "w-full min-w-0 !whitespace-normal text-center";
const BUTTON_ROW = "grid grid-cols-[repeat(auto-fit,minmax(min(100%,9rem),1fr))] gap-2";

const working = computed(() => (props.events.length ? t(agentInfo(props.activeAgent).working) : t("Starting…")));

const title = computed(
  () =>
    ({
      idle: t("Let Avida check your inbox"),
      running: t("Checking your inbox"),
      done: t("Inbox checked"),
      error: t("Check failed"),
    })[props.state],
);
</script>

<template>
  <div class="grid gap-4">
    <!-- now: spinner / result icon + title + current job · hide -->
    <div class="flex items-start gap-3">
      <div class="grid h-12 w-12 shrink-0 place-items-center [&>*]:col-start-1 [&>*]:row-start-1">
        <Transition name="fade">
          <ThinkingSpinner v-if="state === 'running'" key="running" :icon="agentInfo(activeAgent).icon" />
          <IconTile v-else-if="state === 'done'" key="done" icon="checkCircle" tone="positive" round />
          <IconTile v-else-if="state === 'error'" key="error" icon="alert" tone="negative" round />
          <IconTile v-else key="idle" icon="inbox" tone="info" round />
        </Transition>
      </div>
      <div class="grid min-w-0 flex-1 gap-0.5 pt-0.5">
        <h2 class="text-base font-bold leading-snug">{{ title }}</h2>
        <p v-if="state === 'running'" class="text-label font-medium" aria-live="polite">
          <ShimmerText>{{ working }}</ShimmerText>
          <span class="whitespace-nowrap text-muted"> · {{ t("Step {n}", { n: Math.max(1, events.length) }) }}</span>
        </p>
        <p v-else-if="state === 'done'" class="text-label text-muted">
          {{ events.length ? tn(events.length, "{n} step, all done", "{n} steps, all done") : t("Your last check is done.") }}
        </p>
        <p v-else-if="state === 'error'" class="text-label text-negative [overflow-wrap:anywhere]">{{ errorText(error) }}</p>
        <p v-else class="text-label text-muted">
          {{ t("Avida reads your new emails, checks them against your contracts and updates your forecast.") }}
        </p>
      </div>
      <button
        type="button"
        class="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg"
        :aria-label="t('Hide')"
        :title="t('Hide')"
        @click="emit('hide')"
      >
        <AppIcon name="minimize" :size="18" />
      </button>
    </div>

    <!-- who works on it -->
    <div class="rounded-xl bg-input/70 px-2 py-3">
      <AgentPipeline :crew="crew" :state="state" :active-agent="activeAgent" :seen="seen" :pending="pending" />
    </div>

    <!-- every step -->
    <section v-if="events.length" class="grid gap-2" :aria-label="t('What your assistant did')">
      <h3 class="eyebrow">{{ t("What your assistant did") }}</h3>
      <AgentTrace :events="events" :running="state === 'running'" />
    </section>
    <p v-else-if="state === 'done'" class="rounded-lg bg-input px-3 py-2.5 text-label text-muted">
      {{ t("Run a new check to see every step again.") }}
    </p>

    <!-- result + the next useful click -->
    <Transition name="rise">
      <div v-if="state === 'done'" class="grid gap-3 border-t border-line pt-4">
        <!-- auto-fit with a rem minimum: side by side normally, stacked at large text sizes -->
        <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,9.5rem),1fr))] gap-2">
          <div class="flex min-w-0 items-center gap-2.5 rounded-xl bg-input px-3 py-2.5">
            <IconTile icon="inbox" tone="info" size="sm" />
            <span class="grid min-w-0 leading-tight">
              <b class="font-display text-lg tabular-nums">{{ findingsCount }}</b>
              <span class="text-caption text-muted hyphens-auto">{{ tn(findingsCount, "thing found", "things found") }}</span>
            </span>
          </div>
          <div class="flex min-w-0 items-center gap-2.5 rounded-xl bg-input px-3 py-2.5">
            <IconTile icon="approval" :tone="pending ? 'accent' : 'positive'" size="sm" />
            <span class="grid min-w-0 leading-tight">
              <b class="font-display text-lg tabular-nums">{{ pending }}</b>
              <span class="text-caption text-muted hyphens-auto">{{ tn(pending, "waits for you", "wait for you") }}</span>
            </span>
          </div>
        </div>
        <BaseButton
          :to="{ name: 'decisions' }"
          :variant="pending ? 'primary' : 'secondary'"
          icon="arrowRight"
          :class="WRAP"
          @click="emit('review')"
        >
          {{ pending ? t("Review decisions") : t("Open Action center") }}
        </BaseButton>
        <div :class="BUTTON_ROW">
          <BaseButton variant="secondary" size="sm" icon="refresh" :class="WRAP" @click="emit('start')">{{ t("Check again") }}</BaseButton>
          <BaseButton variant="ghost" size="sm" icon="reset" :class="WRAP" @click="emit('reset')">{{ t("Start over") }}</BaseButton>
        </div>
      </div>
    </Transition>

    <!-- failed: say so plainly + retry -->
    <div v-if="state === 'error'" :class="BUTTON_ROW">
      <BaseButton icon="refresh" size="sm" :class="WRAP" @click="emit('start')">{{ t("Try again") }}</BaseButton>
      <BaseButton variant="ghost" size="sm" :class="WRAP" @click="emit('dismiss')">{{ t("Dismiss") }}</BaseButton>
    </div>

    <!-- not started yet (e.g. after "Start over") -->
    <BaseButton v-if="state === 'idle'" icon="inbox" :class="WRAP" @click="emit('start')">{{ t("Check my inbox") }}</BaseButton>

    <p class="flex items-center gap-2 border-t border-line pt-3 text-caption text-muted">
      <AppIcon name="shield" :size="16" class="shrink-0 text-positive" /> {{ t("Nothing is sent without your OK.") }}
    </p>
  </div>
</template>
