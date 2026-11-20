<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import FindingCard from "@/components/findings/FindingCard.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatTile from "@/components/ui/StatTile.vue";
import { useDashboardStore } from "@/stores/dashboard";
import { eur } from "@/utils/format";

/** All detected price changes, each checked against its contract. Summary tiles first, then one card each. */
const store = useDashboardStore();
const { findings, loading, dashboard } = storeToRefs(store);

const notAllowed = computed(() => findings.value.filter((f) => f.contract.verdict === "violates"));
const avoidable = computed(() => notAllowed.value.reduce((sum, f) => sum + f.impact.next_12_months, 0));
</script>

<template>
  <PageHeader eyebrow="Inbox Agent + Contract Agent" title="Price changes in your inbox" description="Each one checked against your contract." />

  <SkeletonBlock v-if="!dashboard && loading" height="h-40" />

  <template v-else-if="findings.length">
    <BaseCard aria-label="Summary">
      <div class="grid gap-4 sm:grid-cols-3">
        <StatTile icon="inbox" tone="info" label="Price changes found" :value="String(findings.length)" />
        <StatTile icon="xCircle" tone="negative" label="Not allowed by contract" :value="String(notAllowed.length)" />
        <StatTile icon="piggyBank" tone="positive" label="You can avoid (12 months)" :value="eur(avoidable)" />
      </div>
    </BaseCard>
    <div class="grid gap-3">
      <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
    </div>
  </template>

  <EmptyState
    v-else
    icon="inbox"
    title="Nothing found yet"
    description="Start an inbox check on the overview."
  >
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowRight">Go to overview</BaseButton>
  </EmptyState>
</template>
