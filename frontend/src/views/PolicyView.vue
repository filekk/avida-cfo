<script setup lang="ts">
import { getPolicy } from "@/api";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useAsyncData } from "@/composables/useAsyncData";

/** The autonomy matrix (GET /api/policy) – "who may do what". Challenge requirement made visible. */
const { data: policy, loading, error, reload } = useAsyncData(getPolicy);
</script>

<template>
  <PageHeader
    eyebrow="You stay in control"
    title="What your agents may do"
    description="Agents can read and calculate on their own. Anything that leaves your company needs your click – and in this demo, it is only simulated."
  />

  <BaseCard title="The four levels">
    <AutonomyLegend detailed />
  </BaseCard>

  <AlertBanner v-if="error">
    {{ error }} <button type="button" class="ml-2 underline" @click="reload">Try again</button>
  </AlertBanner>
  <SkeletonBlock v-else-if="loading && !policy" height="h-64" />

  <BaseCard v-else-if="policy" title="Permissions per action" :padded="false">
    <div class="overflow-x-auto">
      <table class="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr class="text-left text-[0.72rem] uppercase tracking-wider text-muted">
            <th class="border-b border-line px-5 py-2.5 font-semibold">Action</th>
            <th class="border-b border-line px-5 py-2.5 font-semibold">Agent</th>
            <th class="border-b border-line px-5 py-2.5 font-semibold">Level</th>
            <th class="border-b border-line px-5 py-2.5 font-semibold">Execution</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in policy" :key="row.action" class="[&:not(:last-child)>td]:border-b [&>td]:border-line">
            <td class="px-5 py-3 font-medium">{{ row.action }}</td>
            <td class="px-5 py-3 text-muted">{{ row.agent }}</td>
            <td class="px-5 py-3"><AutonomyBadge :level="row.autonomy" /></td>
            <td class="px-5 py-3">
              <AutonomyBadge v-if="row.execution === 'simulated'" level="simulated" />
              <span v-else class="text-muted">–</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>
