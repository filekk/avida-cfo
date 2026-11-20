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
 * One TransitionGroup → a decided card glides down to "Already decided" instead of jumping there.
 */
const store = useDashboardStore();
const { actions, pendingActions, loading, dashboard, deciding, error, kpis } = storeToRefs(store);
const decided = computed(() => actions.value.filter((a) => a.status !== "pending"));
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Your decisions"
    description="Edit, approve or decline. Everything runs in a safe simulation."
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="actions.length">
    <BaseCard aria-label="Summary">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="approval" tone="warn" label="Waiting for you" :value="String(pendingActions.length)" />
        <StatTile icon="decisions" tone="info" label="Already decided" :value="String(decided.length)" />
        <StatTile icon="piggyBank" tone="positive" label="Saved by Avida (12 months)" :value="eur(kpis?.saved_liquidity ?? 0)" />
      </div>
    </BaseCard>

    <TransitionGroup
      tag="div"
      class="grid gap-4"
      move-class="transition-transform duration-slow"
      enter-active-class="transition-[opacity,transform] duration-base"
      enter-from-class="opacity-0 translate-y-2"
    >
      <h2 v-if="pendingActions.length" key="h-pending" class="sr-only">Waiting for you</h2>
      <ActionCard
        v-for="a in pendingActions"
        :key="a.id"
        :action="a"
        :busy="deciding.has(a.id)"
        @decide="(id, approve, body) => store.decide(id, approve, body)"
      />
      <h2 v-if="decided.length" key="h-decided" class="eyebrow mt-2">Already decided</h2>
      <ActionCard v-for="a in decided" :key="a.id" :action="a" />
    </TransitionGroup>
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
