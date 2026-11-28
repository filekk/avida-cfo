<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { storeToRefs } from "pinia";
import AppIcon from "@/components/ui/AppIcon.vue";
import { usePopover } from "@/composables/usePopover";
import { agentInfo, crewOf } from "@/constants/agents";
import { t, tn } from "@/i18n";
import { useDashboardStore } from "@/stores/dashboard";
import { fmtAgo, fmtDateTime } from "@/utils/format";
import SyncPanel from "./SyncPanel.vue";
import ThinkingSpinner from "./ThinkingSpinner.vue";
import type { SyncState } from "./sync";

/**
 * "Check my inbox" – the main action, in the top bar on every page (layout widget → may read the store).
 *   idle    sun box "Check my inbox" → click starts the check (explicit click only) and opens the progress pop-up
 *   running the box itself shows what is happening (a plain spinner + the current job) – also when the pop-up is
 *           hidden; clicking the box shows / hides the live progress
 *   done    "Inbox checked" + how many decisions wait; click → the result with the next useful step
 *   error   "Check failed"; click → what went wrong + Try again
 * The box width glides between states (measured), labels cross-fade in one cell – nothing jumps.
 * Below sm the box is a 40px icon button (the pop-up becomes a full-width sheet under the bar).
 */
const store = useDashboardStore();
const { trace, syncing, syncError, hasSynced, pendingActions, findings, checkedAt } = storeToRefs(store);

// --- "checked 5 minutes ago": a clock that ticks while the page is open (text gets coarser with age) ---------
const now = ref(Date.now());
let clock: ReturnType<typeof setInterval> | undefined;
const tick = () => (now.value = Date.now());
const ago = computed(() => (checkedAt.value ? fmtAgo(checkedAt.value, now.value) : ""));
watch(checkedAt, tick); // a fresh check says "just now" at once, not after the next tick

const state = computed<SyncState>(() =>
  syncing.value ? "running" : syncError.value ? "error" : hasSynced.value || trace.value.length ? "done" : "idle",
);
const crew = computed(() => crewOf(trace.value));
const activeAgent = computed(() => trace.value[trace.value.length - 1]?.agent ?? null);
const seen = computed(() => [...new Set(trace.value.map((e) => e.agent))]);
const working = computed(() => (trace.value.length ? t(agentInfo(activeAgent.value).working) : t("Starting…")));
const pending = computed(() => pendingActions.value.length);

const label = computed(
  () =>
    ({
      idle: t("Check my inbox"),
      running: working.value,
      done: t("Inbox checked"),
      error: t("Check failed"),
    })[state.value],
);
const ariaLabel = computed(() => {
  if (state.value === "running") return `${working.value} ${t("Step {n}", { n: Math.max(1, trace.value.length) })}`;
  const when = state.value === "done" && checkedAt.value ? ` (${t("last checked {when}", { when: fmtDateTime(checkedAt.value) })})` : "";
  if (state.value === "done" && pending.value) return `${label.value}${when}, ${tn(pending.value, "{n} to approve", "{n} to approve")}`;
  return label.value + when;
});

// --- pop-up ------------------------------------------------------------------------------------------
const { open, root, trigger, show, close, onTriggerClick, onFocusOut } = usePopover({ hover: false });
const panelId = `inbox-check-${useId()}`;

function start() {
  store.sync();
  show(true);
}
function onBoxClick(e: MouseEvent) {
  if (state.value === "idle") return start();
  onTriggerClick(e);
}

/** Phones: a full-width sheet under the bar (1rem gutters) instead of a pop-up hanging off the small box. */
const panelStyle = ref<Record<string, string>>({});
function place() {
  if (!root.value || window.innerWidth >= 640) {
    panelStyle.value = {};
    return;
  }
  const left = root.value.getBoundingClientRect().left;
  panelStyle.value = { left: `${16 - left}px`, right: "auto", width: `${window.innerWidth - 32}px`, maxWidth: "none" };
}
watch(open, (o) => {
  if (o) nextTick(place);
  window[o ? "addEventListener" : "removeEventListener"]("resize", place);
});

// --- finished while the pop-up was hidden → the box border turns green for a moment (no halo) ---------
const flash = ref(false);
let flashTimer: ReturnType<typeof setTimeout> | undefined;
watch(syncing, (now, was) => {
  if (!was || now || open.value) return;
  flash.value = true;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => (flash.value = false), 1800);
});

// --- box width follows its content smoothly -------------------------------------------------------------
const inner = ref<HTMLElement | null>(null);
const width = ref<number | null>(null);
let ro: ResizeObserver | null = null;
onMounted(() => {
  clock = setInterval(tick, 15_000);
  document.addEventListener("visibilitychange", tick);
  ro = new ResizeObserver(() => {
    if (inner.value) width.value = inner.value.offsetWidth + 2; // + 1px border on each side
  });
  if (inner.value) ro.observe(inner.value);
});
onBeforeUnmount(() => {
  clearInterval(clock);
  document.removeEventListener("visibilitychange", tick);
  ro?.disconnect();
  clearTimeout(flashTimer);
  window.removeEventListener("resize", place);
});

const BOX: Record<SyncState, string> = {
  idle: "border-sun bg-sun text-sun-on hover:border-sun-hover hover:bg-sun-hover",
  running: "border-line bg-surface text-fg hover:border-fg/40",
  done: "border-line bg-surface text-fg hover:border-fg/40",
  error: "border-negative/50 bg-negative-soft text-negative hover:border-negative",
};
</script>

<template>
  <div ref="root" class="relative" @focusout="onFocusOut">
    <button
      ref="trigger"
      type="button"
      :class="[
        'relative flex h-10 items-center overflow-hidden rounded-lg border text-label font-semibold',
        'transition-[width,background-color,border-color,color] duration-base active:scale-[0.98]',
        BOX[state],
        open && (state === 'running' || state === 'done') ? '!border-fg/40 !bg-mist' : '',
        open && state === 'error' ? '!border-negative' : '',
        flash ? '!border-positive' : '',
      ]"
      :style="width ? { width: `${width}px` } : undefined"
      :aria-label="ariaLabel"
      :title="ariaLabel"
      :aria-expanded="state === 'idle' ? undefined : open"
      :aria-controls="panelId"
      @click="onBoxClick"
    >
      <span ref="inner" class="flex shrink-0 items-center gap-2 whitespace-nowrap px-[7px] sm:px-3">
        <!-- icon: one cell, states cross-fade -->
        <TransitionGroup name="fade" tag="span" class="grid h-6 w-6 shrink-0 place-items-center [&>*]:col-start-1 [&>*]:row-start-1">
          <ThinkingSpinner v-if="state === 'running'" key="running" size="sm" />
          <AppIcon v-else-if="state === 'done'" key="done" name="checkCircle" :size="18" class="text-positive" />
          <AppIcon v-else-if="state === 'error'" key="error" name="alert" :size="18" />
          <AppIcon v-else key="idle" name="inbox" :size="18" />
        </TransitionGroup>
        <!-- label (sm+): one cell, old and new text cross-fade while the box width glides -->
        <!-- done: a quiet second line "5 minutes ago" under the label (ticks while the page is open) -->
        <TransitionGroup name="fade" tag="span" class="hidden sm:grid [&>*]:col-start-1 [&>*]:row-start-1" aria-hidden="true">
          <span :key="label" class="grid text-left leading-[1.15]">
            <span :class="state === 'idle' ? 'font-semibold' : ''">{{ label }}</span>
            <!-- reserved in "done" (no jump when the time arrives from the history a moment later) -->
            <span
              v-if="state === 'done'"
              :class="['text-caption font-normal text-muted transition-opacity duration-base', ago ? 'opacity-100' : 'opacity-0']"
            >{{ ago || " " }}</span>
          </span>
        </TransitionGroup>
        <!-- decisions waiting (sm+) -->
        <Transition name="fade">
          <span
            v-if="state === 'done' && pending"
            class="hidden items-center rounded-md bg-sun px-2 py-0.5 text-caption font-semibold text-sun-on sm:inline-flex"
            aria-hidden="true"
          >
            <span class="md:hidden">{{ pending }}</span>
            <span class="hidden md:inline">{{ tn(pending, "{n} to approve", "{n} to approve") }}</span>
          </span>
        </Transition>
      </span>
    </button>

    <!-- phones: count badge on the icon button -->
    <Transition name="fade">
      <span
        v-if="state === 'done' && pending"
        class="pointer-events-none absolute -right-1.5 -top-1.5 grid h-5 min-w-5 place-items-center rounded-md bg-sun px-1 text-caption font-semibold leading-none text-sun-on ring-2 ring-bg sm:hidden"
        aria-hidden="true"
      >{{ pending }}</span>
    </Transition>

    <Transition
      enter-active-class="transition duration-base ease-out"
      leave-active-class="transition duration-fast ease-out"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <section
        v-show="open"
        :id="panelId"
        role="dialog"
        :aria-label="t('Inbox check')"
        class="absolute right-0 top-full z-30 mt-2 max-h-[calc(100dvh-6rem)] w-[26rem] max-w-[calc(100vw-2rem)] origin-top-right overflow-y-auto overscroll-contain rounded-xl border border-line bg-surface p-4 text-fg shadow-pop"
        :style="panelStyle"
      >
        <SyncPanel
          :state="state"
          :events="trace"
          :crew="crew"
          :active-agent="activeAgent"
          :seen="seen"
          :pending="pending"
          :findings-count="findings.length"
          :error="syncError"
          @hide="close(true)"
          @start="store.sync()"
          @reset="store.reset()"
          @review="close()"
          @dismiss="syncError = null"
        />
      </section>
    </Transition>
  </div>
</template>
