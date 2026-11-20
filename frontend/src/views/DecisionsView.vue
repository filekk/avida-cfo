<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import ActionCard from "@/components/actions/ActionCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { useDashboardStore } from "@/stores/dashboard";
import { eur } from "@/utils/format";

/**
 * Every action proposed by the agents. Pending first; nothing happens without a click.
 * Declined actions disappear from this view right away. They stay in the audit log (History).
 */
const store = useDashboardStore();
const { actions, pendingActions, loading, dashboard, deciding, error, kpis } = storeToRefs(store);
const decided = computed(() => actions.value.filter((a) => a.status === "executed"));
const visible = computed(() => actions.value.filter((a) => a.status !== "rejected"));
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Your decisions"
    description="Edit, approve or decline. Everything runs in a safe simulation."
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="visible.length">
    <BaseCard aria-label="Summary">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="approval" tone="warn" label="Waiting for you" :value="String(pendingActions.length)" />
        <StatTile icon="decisions" tone="info" label="Already decided" :value="String(decided.length)" />
        <StatTile icon="piggyBank" tone="positive" label="Saved by Avida (12 months)" :value="eur(kpis?.saved_liquidity ?? 0)" />
      </div>
    </BaseCard>

    <TransitionGroup
      v-if="pendingActions.length"
      tag="section"
      name="decision"
      class="relative grid gap-4"
      aria-label="Waiting for you"
    >
      <ActionCard
        v-for="a in pendingActions"
        :key="a.id"
        :action="a"
        :busy="deciding.has(a.id)"
        @decide="(id, approve, body) => store.decide(id, approve, body)"
      />
    </TransitionGroup>

    <section v-if="decided.length" class="grid gap-4" aria-label="Already decided">
      <h2 class="eyebrow mt-2">Already decided</h2>
      <ActionCard v-for="a in decided" :key="a.id" :action="a" />
    </section>
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
/* A declined (or approved) card leaves the "Waiting for you" list with a short fade; the rest slide up. */
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
