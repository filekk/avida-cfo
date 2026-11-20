<script setup lang="ts">
import { storeToRefs } from "pinia";
import FindingCard from "@/components/findings/FindingCard.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useDashboardStore } from "@/stores/dashboard";

/** All detected price changes, each checked against its contract. */
const store = useDashboardStore();
const { findings, loading, dashboard } = storeToRefs(store);
</script>

<template>
  <PageHeader
    eyebrow="Inbox Agent + Contract Agent"
    title="Price changes in your inbox"
    description="Each change is compared with your contract. Open one to see the email, the contract clause and the calculation side by side."
  />

  <SkeletonBlock v-if="!dashboard && loading" height="h-40" />

  <div v-else-if="findings.length" class="grid gap-3">
    <FindingCard v-for="f in findings" :key="f.id" :finding="f" />
  </div>

  <EmptyState
    v-else
    icon="inbox"
    title="Nothing found yet"
    description="Avida hasn't checked your inbox in this session. Start a check on the overview page."
  >
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowRight">Go to overview</BaseButton>
  </EmptyState>
</template>
