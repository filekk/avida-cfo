<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import ActionCard from "@/components/actions/ActionCard.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useDashboardStore } from "@/stores/dashboard";

/** Every action proposed by the agents. Pending first; nothing happens without a click. */
const store = useDashboardStore();
const { actions, pendingActions, loading, dashboard, deciding, error } = storeToRefs(store);
const decided = computed(() => actions.value.filter((a) => a.status !== "pending"));
</script>

<template>
  <PageHeader
    eyebrow="Needs your approval"
    title="Your decisions"
    description="Avida prepared these steps. You can edit the email before sending. Every execution is simulated – nothing leaves the system."
  />

  <AlertBanner v-if="error" dismissible @dismiss="error = null">{{ error }}</AlertBanner>
  <SkeletonBlock v-if="!dashboard && loading" height="h-64" />

  <template v-else-if="actions.length">
    <section v-if="pendingActions.length" class="grid gap-4" aria-label="Waiting for you">
      <ActionCard
        v-for="a in pendingActions"
        :key="a.id"
        :action="a"
        :busy="deciding.has(a.id)"
        @decide="(id, approve, body) => store.decide(id, approve, body)"
      />
    </section>

    <section v-if="decided.length" class="grid gap-4" aria-label="Already decided">
      <h2 class="eyebrow mt-2">Already decided</h2>
      <ActionCard v-for="a in decided" :key="a.id" :action="a" />
    </section>
  </template>

  <EmptyState
    v-else
    icon="decisions"
    title="No decisions waiting"
    description="When Avida finds something that needs your OK, it will appear here."
  >
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowRight">Go to overview</BaseButton>
  </EmptyState>
</template>
