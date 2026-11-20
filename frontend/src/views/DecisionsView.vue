<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import DecisionRow from "@/components/actions/DecisionRow.vue";
import { buildItems, isOpenItem, type DecisionItem } from "@/components/actions/decision";
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
 * Action center, split by where a decision comes from:
 *   left  – based on your emails   (supplier price changes, replies)
 *   right – based on your forecast (credit facility)
 * Each column has two collapsible parts:
 *   Pending  – waiting for the owner (open by default)
 *   Resolved – already decided or nothing to do (toned down, still fully interactive)
 * Items are compact rows that expand in place with the full explanation and the buttons.
 * Old /findings links land here with ?finding=<id> and open that row.
 */
type ColumnKey = "emails" | "forecast";
type PartKey = "pending" | "resolved";

const route = useRoute();
const store = useDashboardStore();
const { actions, findings, loading, dashboard, deciding, error, kpis } = storeToRefs(store);

const items = computed(() => buildItems(actions.value, findings.value));
const columnOf = (i: DecisionItem): ColumnKey =>
  i.action && i.action.type !== "send_email" ? "forecast" : "emails";

const pendingCount = computed(() => items.value.filter(isOpenItem).length);
const approvedCount = computed(() => actions.value.filter((a) => a.status === "executed").length);

/** Which parts are unfolded, per column. */
const partOpen = reactive<Record<ColumnKey, Record<PartKey, boolean>>>({
  emails: { pending: true, resolved: false },
  forecast: { pending: true, resolved: false },
});
const openKey = ref<string | null>(null);
const toggleRow = (key: string) => (openKey.value = openKey.value === key ? null : key);

/** After a decision the row moves to "Resolved" – fold it so that part stays compact. */
async function decide(id: string, approve: boolean, body?: string) {
  await store.decide(id, approve, body);
  if (openKey.value === id) openKey.value = null;
}

// Deep link from the overview (/findings/:id → ?finding=:id): open that row and its part.
watch(
  [() => route.query.finding, items],
  ([id]) => {
    if (typeof id !== "string") return;
    const item = items.value.find((i) => i.finding?.id === id || i.key === id);
    if (!item) return;
    openKey.value = item.key;
    partOpen[columnOf(item)][isOpenItem(item) ? "pending" : "resolved"] = true;
  },
  { immediate: true },
);

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
  COLUMNS.map((c) => {
    const mine = items.value.filter((i) => columnOf(i) === c.key);
    return {
      ...c,
      parts: [
        { key: "pending" as const, title: "Pending", items: mine.filter(isOpenItem), empty: c.emptyPending },
        { key: "resolved" as const, title: "Resolved", items: mine.filter((i) => !isOpenItem(i)), empty: "Nothing resolved yet." },
      ],
    };
  }),
);
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Action center"
    description="Open an item to see why Avida suggests it. Edit, approve or decline – everything runs in a safe simulation."
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

    <!-- two equal columns: same top, same height -->
    <div class="grid gap-5 lg:grid-cols-2">
      <section
        v-for="col in columns"
        :key="col.key"
        class="grid content-start gap-4 rounded-xl border border-line bg-surface p-4 shadow-card sm:p-5"
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
            'grid gap-2 transition-[opacity,filter]',
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
              <TransitionGroup tag="div" name="decision" class="relative grid gap-3 p-px">
                <DecisionRow
                  v-for="item in part.items"
                  :key="item.key"
                  :item="item"
                  :open="openKey === item.key"
                  :busy="!!item.action && deciding.has(item.action.id)"
                  @toggle="toggleRow(item.key)"
                  @decide="decide"
                />
              </TransitionGroup>
              <p
                v-if="!part.items.length"
                class="rounded-lg border border-dashed border-line px-4 py-4 text-center text-sm text-muted"
              >
                {{ part.empty }}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
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
/* A decided row leaves "Pending" with a short fade; the rest slide up. */
.decision-leave-active {
  position: absolute;
  inset-inline: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.decision-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.decision-enter-active {
  transition: opacity 0.25s ease;
}
.decision-enter-from {
  opacity: 0;
}
.decision-move {
  transition: transform 0.25s ease;
}
@media (prefers-reduced-motion: reduce) {
  .decision-leave-active,
  .decision-enter-active,
  .decision-move {
    transition: none;
  }
}
</style>
