<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import ActionCard from "@/components/actions/ActionCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { useDashboardStore } from "@/stores/dashboard";
import type { Action } from "@/types/api";
import { eur } from "@/utils/format";

/**
 * Action center: every action proposed by the agents, split by where it comes from.
 *   left  – decisions based on emails (replies to suppliers)
 *   right – decisions based on the forecast (credit facility)
 * Pending first in each column; nothing happens without a click.
 * Declined actions disappear right away. They stay in the audit log (History).
 */
const store = useDashboardStore();
const { actions, pendingActions, loading, dashboard, deciding, error, kpis } = storeToRefs(store);

const visible = computed(() => actions.value.filter((a) => a.status !== "rejected"));
const decided = computed(() => actions.value.filter((a) => a.status === "executed"));
const pendingFirst = (list: Action[]) =>
  [...list].sort((a, b) => Number(b.status === "pending") - Number(a.status === "pending"));

const fromEmails = computed(() => pendingFirst(visible.value.filter((a) => a.type === "send_email")));
const fromForecast = computed(() => pendingFirst(visible.value.filter((a) => a.type !== "send_email")));

const columns = computed(() => [
  {
    key: "emails",
    icon: "mail" as const,
    title: "Based on your emails",
    hint: "Replies to suppliers whose price changes Avida checked against your contracts.",
    empty: "No email needs a reply right now.",
    items: fromEmails.value,
  },
  {
    key: "forecast",
    icon: "chart" as const,
    title: "Based on your forecast",
    hint: "Steps that keep your balance above your safety cushion.",
    empty: "Your forecast needs no action right now.",
    items: fromForecast.value,
  },
]);
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Action center"
    description="Edit, approve or decline. Everything runs in a safe simulation."
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="visible.length">
    <BaseCard aria-label="Summary">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="approval" tone="warn" label="Waiting for you" :value="String(pendingActions.length)" />
        <StatTile icon="decisions" tone="info" label="Already approved" :value="String(decided.length)" />
        <StatTile icon="piggyBank" tone="positive" label="Saved by Avida (12 months)" :value="eur(kpis?.saved_liquidity ?? 0)" />
      </div>
    </BaseCard>

    <div class="grid items-start gap-5 lg:grid-cols-2">
      <section v-for="col in columns" :key="col.key" class="grid gap-4" :aria-labelledby="`col-${col.key}`">
        <header class="flex items-start gap-3">
          <span class="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-mist text-mist-fg" aria-hidden="true">
            <AppIcon :name="col.icon" :size="18" />
          </span>
          <div class="grid gap-0.5">
            <h2 :id="`col-${col.key}`" class="text-base font-bold">{{ col.title }}</h2>
            <p class="text-sm text-muted">{{ col.hint }}</p>
          </div>
        </header>

        <TransitionGroup tag="div" name="decision" class="relative grid gap-4">
          <ActionCard
            v-for="a in col.items"
            :key="a.id"
            :action="a"
            :busy="deciding.has(a.id)"
            @decide="(id, approve, body) => store.decide(id, approve, body)"
          />
        </TransitionGroup>

        <p
          v-if="!col.items.length"
          class="rounded-xl border border-dashed border-line px-4 py-6 text-center text-sm text-muted"
        >
          {{ col.empty }}
        </p>
      </section>
    </div>
  </template>

  <EmptyState
    v-else
    icon="decisions"
    title="No decisions waiting"
    description="When Avida needs your OK, it shows up here."
  >
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowRight">Go to overview</BaseButton>
  </EmptyState>
</template>

<style scoped>
/* A declined card leaves its column with a short fade; the rest slide up. */
.decision-leave-active {
  position: absolute;
  inset-inline: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.decision-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.decision-move {
  transition: transform 0.25s ease;
}
@media (prefers-reduced-motion: reduce) {
  .decision-leave-active,
  .decision-move {
    transition: none;
  }
}
</style>
