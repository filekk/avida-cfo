<script setup lang="ts">
import { computed, reactive } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import DecisionFocus from "@/components/actions/DecisionFocus.vue";
import DecisionTile from "@/components/actions/DecisionTile.vue";
import { buildItems, categoryOf, isOpenItem, type DecisionCategory, type DecisionItem } from "@/components/actions/decision";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { useDashboardStore } from "@/stores/dashboard";
import { eur } from "@/utils/format";

/**
 * Action center = a board of everything the owner can act on, in two columns:
 *   left  – based on your emails   ·   right – based on your forecast
 * each with Pending (open) and Resolved (toned down) parts of small tiles.
 * Click a tile → focus view: only that decision, full width, with back and previous / next.
 * The focused item lives in the URL (?item=<key>) so the browser's Back button returns to the board.
 * Old /findings links arrive as ?finding=<id> and open that item too.
 */
type PartKey = "pending" | "resolved";

const route = useRoute();
const router = useRouter();
const store = useDashboardStore();
const { actions, findings, loading, dashboard, deciding, error, kpis } = storeToRefs(store);

const items = computed(() => buildItems(actions.value, findings.value));
const inCategory = (c: DecisionCategory, open: boolean) =>
  items.value.filter((i) => categoryOf(i) === c && isOpenItem(i) === open);

const pendingCount = computed(() => items.value.filter(isOpenItem).length);
const approvedCount = computed(() => actions.value.filter((a) => a.status === "executed").length);

const partOpen = reactive<Record<DecisionCategory, Record<PartKey, boolean>>>({
  emails: { pending: true, resolved: false },
  forecast: { pending: true, resolved: false },
});

const COLUMNS = [
  {
    key: "emails" as const,
    icon: "mail" as const,
    title: "Based on your emails",
    hint: "Supplier price changes, checked against your contracts.",
    emptyPending: "No email needs your decision right now.",
  },
  {
    key: "forecast" as const,
    icon: "chart" as const,
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

/** Once the owner decides, go straight back to the board (the tile is now under Resolved). Stay on error. */
async function decide(id: string, approve: boolean, body?: string) {
  await store.decide(id, approve, body);
  if (!error.value) router.replace({ query: {} });
}
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Action center"
    description="Everything you can act on. Pick an item to see why Avida suggests it – then approve, edit or decline."
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="items.length">
    <BaseCard aria-label="Summary">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="approval" tone="warn" label="Waiting for you" :value="String(pendingCount)" />
        <StatTile icon="decisions" tone="info" label="Already approved" :value="String(approvedCount)" />
        <StatTile icon="piggyBank" tone="positive" label="Saved by Avida (12 months)" :value="eur(kpis?.saved_liquidity ?? 0)" />
      </div>
    </BaseCard>

    <Transition name="swap" mode="out-in">
      <!-- focus: one decision -->
      <DecisionFocus
        v-if="focused"
        :key="focused.key"
        :item="focused"
        :busy="!!focused.action && deciding.has(focused.action.id)"
        :position="position"
        :total="order.length"
        @back="back"
        @prev="step(-1)"
        @next="step(1)"
        @decide="decide"
      />

      <!--
        board: two equal columns. On lg each column is a subgrid over 3 shared rows (header / Pending / Resolved),
        so both parts start at the same height in both columns; long parts scroll inside.
      -->
      <div v-else class="grid gap-5 lg:grid-cols-2 lg:grid-rows-[auto_auto_auto] lg:gap-y-4">
        <section
          v-for="col in columns"
          :key="col.key"
          class="grid content-start gap-4 rounded-xl border border-line bg-surface p-4 shadow-card sm:p-5 lg:row-span-3 lg:grid-rows-subgrid"
          :aria-labelledby="`col-${col.key}`"
        >
          <header class="flex items-start gap-3">
            <span class="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-mist text-mist-fg" aria-hidden="true">
              <AppIcon :name="col.icon" :size="19" />
            </span>
            <div class="grid gap-0.5">
              <h2 :id="`col-${col.key}`" class="text-lg font-bold">{{ col.title }}</h2>
              <p class="text-sm text-muted">{{ col.hint }}</p>
            </div>
          </header>

          <div
            v-for="part in col.parts"
            :key="part.key"
            :class="[
              'grid content-start gap-2 transition-[opacity,filter]',
              part.key === 'resolved'
                ? 'opacity-60 saturate-50 hover:opacity-100 hover:saturate-100 has-[:focus-visible]:opacity-100 has-[:focus-visible]:saturate-100'
                : '',
            ]"
          >
            <h3>
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-input/60"
                :aria-expanded="partOpen[col.key][part.key]"
                :aria-controls="`part-${col.key}-${part.key}`"
                @click="partOpen[col.key][part.key] = !partOpen[col.key][part.key]"
              >
                <AppIcon
                  :name="part.key === 'pending' ? 'approval' : 'checkCircle'"
                  :size="16"
                  :class="part.key === 'pending' ? 'text-warn' : 'text-muted'"
                />
                <span class="eyebrow !text-fg">{{ part.title }}</span>
                <span
                  :class="[
                    'min-w-[1.4rem] rounded-full px-1.5 text-center text-[0.72rem] font-bold leading-5',
                    part.key === 'pending' && part.items.length ? 'bg-sun text-sun-on' : 'bg-input text-muted',
                  ]"
                >{{ part.items.length }}</span>
                <AppIcon
                  name="chevronDown"
                  :class="['ml-auto shrink-0 text-muted transition-transform duration-300', partOpen[col.key][part.key] ? 'rotate-180' : '']"
                />
              </button>
            </h3>

            <div
              :id="`part-${col.key}-${part.key}`"
              :class="[
                'grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none',
                partOpen[col.key][part.key] ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
              ]"
              :inert="!partOpen[col.key][part.key]"
            >
              <div class="min-h-0 overflow-hidden">
                <div
                  v-if="part.items.length"
                  class="scroll-part grid gap-3 p-1 lg:max-h-[30rem] lg:overflow-y-auto"
                >
                  <DecisionTile v-for="item in part.items" :key="item.key" :item="item" @open="openItem(item.key)" />
                </div>
                <p v-else class="rounded-lg border border-dashed border-line px-4 py-4 text-center text-sm text-muted">
                  {{ part.empty }}
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
    title="Nothing here yet"
    description="Let Avida check your inbox first. Everything it finds and suggests shows up here."
  >
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowRight">Go to overview</BaseButton>
  </EmptyState>
</template>

<style scoped>
/* Board ↔ focus: a short cross-fade. */
.swap-enter-active,
.swap-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.swap-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.swap-leave-to {
  opacity: 0;
}
/* Thin, theme-aware scrollbar for the scrollable parts. */
.scroll-part {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--c-line)) transparent;
}
@media (prefers-reduced-motion: reduce) {
  .swap-enter-active,
  .swap-leave-active {
    transition: none;
  }
}
</style>
