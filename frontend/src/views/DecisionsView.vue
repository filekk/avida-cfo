<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import DecisionFocus from "@/components/actions/DecisionFocus.vue";
import DecisionTile from "@/components/actions/DecisionTile.vue";
import {
  buildItems,
  categoryOf,
  isOpenItem,
  type DecisionCategory,
  type DecisionItem,
  type DraftCheck,
  type RewriteHint,
  type RewrittenDraft,
} from "@/components/actions/decision";
import AskContext from "@/components/ask/AskContext.vue";
import { contextualSuggestions } from "@/components/ask/contextual";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { t } from "@/i18n";
import { useAskStore, type ProblemRef } from "@/stores/ask";
import { useDashboardStore } from "@/stores/dashboard";

/**
 * Action center = a board of everything the owner can act on, in two columns:
 *   left  – based on your emails   ·   right – based on your forecast
 * each with Pending (open) and Resolved (greyed out until hovered) parts of small tiles.
 * Click a tile → focus view: only that decision, full width, with back and previous / next.
 * The focused item lives in the URL (?item=<key>) so the browser's Back button returns to the board.
 * Old /findings links arrive as ?finding=<id> and open that item too.
 * Inside the focus view the owner gets help for THAT decision: a contextual, full-width "Ask your CFO" bar under the explanation
 * (chips fitted to the case) and "AV Rewrite" next to the decision buttons (rewrites the draft along a short wish).
 * There is no general "Ask your CFO" card on this page any more – the general chat is the overview's floating bubble.
 */
type PartKey = "pending" | "resolved";

const route = useRoute();
const router = useRouter();
const store = useDashboardStore();
const { actions, findings, loading, dashboard, deciding, error } = storeToRefs(store);

const items = computed(() => buildItems(actions.value, findings.value));
const inCategory = (c: DecisionCategory, open: boolean) =>
  items.value.filter((i) => categoryOf(i) === c && isOpenItem(i) === open);

const pendingCount = computed(() => items.value.filter(isOpenItem).length);
const approvedCount = computed(() => actions.value.filter((a) => a.status === "executed").length);

const partOpen = reactive<Record<DecisionCategory, Record<PartKey, boolean>>>({
  emails: { pending: true, resolved: false },
  forecast: { pending: true, resolved: false },
});

/** English source text – translated in the template. */
const COLUMNS = [
  {
    key: "emails" as const,
    title: "Based on your emails",
    hint: "Price changes and late payments, checked against your contracts.",
    emptyPending: "No email needs your decision right now.",
  },
  {
    key: "forecast" as const,
    title: "Based on your forecast",
    hint: "Steps that keep your balance above your safety cushion.",
    emptyPending: "Your forecast needs no action right now.",
  },
];

const columns = computed(() =>
  COLUMNS.map((c) => ({
    ...c,
    parts: [
      { key: "pending" as const, title: "Pending", items: inCategory(c.key, true), empty: c.emptyPending },
      { key: "resolved" as const, title: "Resolved", items: inCategory(c.key, false), empty: "Nothing resolved yet." },
    ],
  })),
);

// --- focus view ------------------------------------------------------------------------------------
/** Order used by previous / next: everything pending first, then everything resolved. */
const order = computed<DecisionItem[]>(() => [
  ...inCategory("emails", true),
  ...inCategory("forecast", true),
  ...inCategory("emails", false),
  ...inCategory("forecast", false),
]);
/** ?item=<key>, or the legacy ?finding=<id> coming from /findings/:id links on the overview. */
const focusKey = computed(() => {
  const { item, finding } = route.query;
  if (typeof item === "string") return item;
  if (typeof finding === "string") return items.value.find((i) => i.finding?.id === finding)?.key ?? null;
  return null;
});
const focused = computed(() => items.value.find((i) => i.key === focusKey.value) ?? null);
const position = computed(() => order.value.findIndex((i) => i.key === focusKey.value) + 1);

const openItem = (key: string) => router.push({ query: { item: key } });
const back = () => router.push({ query: {} });
const step = (d: number) => {
  const next = order.value[position.value - 1 + d];
  if (next) router.replace({ query: { item: next.key } });
};

// --- contextual "Ask your CFO" (focus view) -------------------------------------------------------
const ask = useAskStore();
/** The problem on the backend: the action, or – for findings with nothing to approve – the finding. */
const problemRef = (item: DecisionItem): ProblemRef =>
  item.action ? { action_id: item.action.id } : item.finding ? { finding_id: item.finding.id } : {};
/** Chips from GET /context for this problem; until they arrive (or if they fail) our own case questions. */
const askSuggestions = computed(() => {
  const f = focused.value;
  if (!f) return [];
  return ask.contextSuggestions[f.key] ?? contextualSuggestions(f, ask.suggestions);
});
const askTurns = computed(() => ask.turns.filter((x) => x.context === focused.value?.key));
onMounted(() => {
  if (!ask.suggestions.length && !ask.loadingSuggestions) ask.loadSuggestions();
});
/** Chip → sent unchanged (instant prepared answer). Typed → the model, with the problem and the turns so far. */
const askAbout = (q: string) => focused.value && ask.ask(q, { context: focused.value.key, ...problemRef(focused.value) });

// --- AV Rewrite + checking the draft (focus view) ------------------------------------------------
/** One decision is in focus at a time → one state, reset when the focus changes. */
const rewriteState = reactive<{
  busy: boolean;
  error: string | null;
  result: RewrittenDraft | null;
  hints: RewriteHint[] | null;
  placeholder: string | null;
  check: DraftCheck | null;
}>({ busy: false, error: null, result: null, hints: null, placeholder: null, check: null });
let rewriteRun = 0;
let reviewTimer: ReturnType<typeof setTimeout> | undefined;
let reviewAbort: AbortController | null = null;

watch(
  [focusKey, () => focused.value?.action?.status],
  async ([key]) => {
    rewriteRun++; // a late answer for the previous decision is ignored
    clearTimeout(reviewTimer);
    reviewAbort?.abort();
    Object.assign(rewriteState, { busy: false, error: null, result: null, hints: null, placeholder: null, check: null });
    const item = focused.value;
    if (!key || !item) return;
    // chips for "Ask your CFO" (once per problem and language)
    if (!ask.contextSuggestions[item.key]) ask.loadContext(item.key, problemRef(item));
    // chips for AV Rewrite (only drafts that still wait for the owner)
    const a = item.action;
    if (a?.type === "send_email" && a.status === "pending") {
      const run = rewriteRun;
      const h = await store.redraftHints(a.id);
      if (h && run === rewriteRun) Object.assign(rewriteState, { hints: h.hints, placeholder: h.placeholder });
    }
  },
  { immediate: true },
);

async function rewrite(id: string, body: string, instruction: string) {
  const run = ++rewriteRun;
  clearTimeout(reviewTimer);
  Object.assign(rewriteState, { busy: true, error: null });
  try {
    const r = await store.redraft(id, body, instruction);
    if (run !== rewriteRun) return;
    rewriteState.result = {
      body: r.body,
      source: r.source,
      n: (rewriteState.result?.n ?? 0) + 1,
      attempt: r.attempt,
      changed: r.changed,
      note: r.note,
    };
    if (r.changed) rewriteState.check = { ...r.review, origin: "rewrite" };
  } catch (e) {
    if (run === rewriteRun) rewriteState.error = e instanceof Error ? e.message : t("Something went wrong.");
  } finally {
    if (run === rewriteRun) rewriteState.busy = false;
  }
}

/** Owner edits the draft → instant rule check (POST /review), 600 ms after the last key press. */
function onEdit(id: string, body: string) {
  clearTimeout(reviewTimer);
  reviewTimer = setTimeout(async () => {
    reviewAbort?.abort();
    reviewAbort = new AbortController();
    const key = focusKey.value;
    const r = await store.review(id, body, reviewAbort.signal);
    if (r && key === focusKey.value) rewriteState.check = { approved: r.approved, issues: r.issues, origin: "typing" };
  }, 600);
}
onBeforeUnmount(() => {
  clearTimeout(reviewTimer);
  reviewAbort?.abort();
});

/** Once the owner decides, go straight back to the board (the tile is now under Resolved). Stay on error. */
async function decide(id: string, approve: boolean, body?: string) {
  await store.decide(id, approve, body);
  if (!error.value) router.replace({ query: {} });
}
</script>

<template>
  <PageHeader
    :title="t('Action center')"
    :description="t('Everything you can act on. Pick an item to see why Avida suggests it – then approve, edit or decline.')"
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="items.length">
    <BaseCard :aria-label="t('Summary')">
      <!-- "Saved by Avida" is not repeated here: it lives in the navigation (sidebar card) on every page -->
      <div class="grid gap-4 sm:grid-cols-2">
        <StatTile icon="approval" tone="warn" :label="t('Waiting for you')" :value="String(pendingCount)" />
        <StatTile icon="decisions" tone="info" :label="t('Already approved')" :value="String(approvedCount)" />
      </div>
    </BaseCard>

    <!-- board ↔ focus: the shared "rise" transition (fade out, soft rise in) -->
    <Transition name="rise" mode="out-in">
      <!-- focus: one decision -->
      <DecisionFocus
        v-if="focused"
        :key="focused.key"
        :item="focused"
        :busy="!!focused.action && deciding.has(focused.action.id)"
        :position="position"
        :total="order.length"
        :rewriting="rewriteState.busy"
        :rewrite-error="rewriteState.error"
        :rewritten="rewriteState.result"
        :rewrite-hints="rewriteState.hints"
        :rewrite-placeholder="rewriteState.placeholder"
        :check="rewriteState.check"
        @back="back"
        @prev="step(-1)"
        @next="step(1)"
        @decide="decide"
        @rewrite="rewrite"
        @edit="onEdit"
      >
        <template #ask>
          <AskContext
            :key="focused.key"
            :suggestions="askSuggestions"
            :turns="askTurns"
            :asking="ask.asking"
            @pick="askAbout"
            @ask="askAbout"
            @clear="ask.clear(focused.key)"
          />
        </template>
      </DecisionFocus>

      <!--
        board: two equal columns. On lg each column is a subgrid over 3 shared rows (header / Pending / Resolved),
        so both parts start at the same height in both columns; long parts scroll inside.
      -->
      <div v-else class="grid gap-5 lg:grid-cols-2 lg:grid-rows-[auto_auto_auto] lg:gap-y-4">
        <section
          v-for="col in columns"
          :key="col.key"
          class="grid content-start gap-4 rounded-xl border border-line bg-surface p-4 sm:p-5 lg:row-span-3 lg:grid-rows-subgrid"
          :aria-labelledby="`col-${col.key}`"
        >
          <header class="grid gap-0.5">
            <h2 :id="`col-${col.key}`" class="text-lg font-semibold">{{ t(col.title) }}</h2>
            <p class="text-label text-muted">{{ t(col.hint) }}</p>
          </header>

          <div v-for="part in col.parts" :key="part.key" class="grid content-start gap-2">
            <h3>
              <button
                type="button"
                :class="[
                  'group/part flex min-h-10 w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors duration-fast hover:bg-input/60',
                  part.key === 'resolved' ? 'text-muted hover:text-fg' : '',
                ]"
                :aria-expanded="partOpen[col.key][part.key]"
                :aria-controls="`part-${col.key}-${part.key}`"
                @click="partOpen[col.key][part.key] = !partOpen[col.key][part.key]"
              >
                <AppIcon
                  :name="part.key === 'pending' ? 'approval' : 'checkCircle'"
                  :size="18"
                  :class="part.key === 'pending' ? 'text-warn' : 'text-muted'"
                />
                <span :class="['eyebrow', part.key === 'resolved' ? '!text-muted group-hover/part:!text-fg' : '!text-fg']">{{ t(part.title) }}</span>
                <span
                  :class="[
                    'min-w-[1.75rem] rounded-md px-2 py-0.5 text-center text-caption font-semibold leading-tight transition-colors duration-base',
                    part.key === 'pending' && part.items.length ? 'bg-sun text-sun-on' : 'bg-input text-muted',
                  ]"
                >{{ part.items.length }}</span>
                <AppIcon
                  name="chevronDown"
                  :size="18"
                  :class="['ml-auto shrink-0 text-muted transition-transform duration-base', partOpen[col.key][part.key] ? 'rotate-180' : '']"
                />
              </button>
            </h3>

            <!-- open/close: grid-rows 0fr ↔ 1fr animates the real height (no max-height guessing) -->
            <div
              :id="`part-${col.key}-${part.key}`"
              :class="[
                'grid transition-[grid-template-rows] duration-base',
                partOpen[col.key][part.key] ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
              ]"
              :inert="!partOpen[col.key][part.key]"
            >
              <div class="min-h-0 overflow-hidden">
                <div v-if="part.items.length" class="scroll-part grid gap-3 p-1 lg:max-h-[30rem] lg:overflow-y-auto">
                  <DecisionTile v-for="item in part.items" :key="item.key" :item="item" @open="openItem(item.key)" />
                </div>
                <p v-else class="rounded-lg border border-dashed border-line px-4 py-4 text-center text-label text-muted">
                  {{ t(part.empty) }}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </Transition>
  </template>

  <EmptyState
    v-else
    icon="decisions"
    :title="t('Nothing here yet')"
    :description="t('Use “{button}” at the top. Everything Avida finds and suggests shows up here.', { button: t('Check my inbox') })"
  >
    <BaseButton :to="{ name: 'dashboard' }" variant="secondary" icon="arrowRight">{{ t("Go to overview") }}</BaseButton>
  </EmptyState>
</template>

<style scoped>
/* Thin, theme-aware scrollbar for the scrollable parts. */
.scroll-part {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--c-line)) transparent;
}
</style>
