<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import ActionCard from "@/components/actions/ActionCard.vue";
import FindingSplit from "@/components/findings/FindingSplit.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useDashboardStore } from "@/stores/dashboard";

/** Split screen for one finding + the related action (approve right here, with full context). */
const props = defineProps<{ id: string }>();

const store = useDashboardStore();
const { loading, dashboard, deciding } = storeToRefs(store);
const finding = computed(() => store.findingById(props.id));
const action = computed(() => (finding.value?.action_id ? store.actionById(finding.value.action_id) : undefined));
</script>

<template>
  <RouterLink :to="{ name: 'findings' }" class="flex w-fit items-center gap-1.5 text-sm font-semibold text-gold hover:underline">
    <AppIcon name="arrowLeft" /> All findings
  </RouterLink>

  <SkeletonBlock v-if="!dashboard && loading" height="h-96" />

  <template v-else-if="finding">
    <FindingSplit :finding="finding" />
    <ActionCard
      v-if="action"
      :action="action"
      :busy="deciding.has(action.id)"
      compact
      @decide="(id, approve, body) => store.decide(id, approve, body)"
    />
  </template>

  <EmptyState
    v-else
    icon="inbox"
    title="This finding is not available"
    description="Findings live only for the current session. Run a new inbox check from the overview."
  />
</template>
