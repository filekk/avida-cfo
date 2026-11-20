<script setup lang="ts">
import { getPolicy } from "@/api";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import IconTile from "@/components/ui/IconTile.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { TONE_SOFT } from "@/components/ui/tones";
import { useAsyncData } from "@/composables/useAsyncData";
import { agentIcon } from "@/constants/agents";
import { AUTONOMY, AUTONOMY_ORDER } from "@/constants/autonomy";
import type { Autonomy, PolicyRule } from "@/types/api";

/** The autonomy matrix (GET /api/policy) – "who may do what", drawn as action × level with marks instead of text. */
const { data: policy, loading, error, reload } = useAsyncData(getPolicy);

const applies = (row: PolicyRule, level: Autonomy) =>
  level === "simulated" ? row.execution === "simulated" : row.autonomy === level;
</script>

<template>
  <PageHeader
    eyebrow="You stay in control"
    title="What your agents may do"
    description="Reading and calculating: on their own. Anything that leaves your company: only after your click."
  />

  <BaseCard title="The four levels">
    <AutonomyLegend detailed />
  </BaseCard>

  <AlertBanner v-if="error">
    {{ error }} <button type="button" class="ml-2 underline" @click="reload">Try again</button>
  </AlertBanner>
  <SkeletonBlock v-else-if="loading && !policy" height="h-64" />

  <BaseCard v-else-if="policy" title="Who may do what" :padded="false" class="animate-rise">
    <!-- relative: keeps the absolutely-positioned sr-only labels inside the scroll box (else they widen the page) -->
    <div class="relative overflow-x-auto">
      <table class="w-full min-w-[680px] border-collapse">
        <thead>
          <tr>
            <th class="border-b border-line px-5 py-3 text-left align-bottom text-caption font-semibold uppercase tracking-eyebrow text-muted">
              Action
            </th>
            <th v-for="l in AUTONOMY_ORDER" :key="l" class="w-[8rem] border-b border-line px-2 py-3 align-top font-semibold">
              <span class="grid justify-items-center gap-2">
                <IconTile :icon="AUTONOMY[l].icon" :tone="AUTONOMY[l].tone" size="sm" :class="AUTONOMY[l].tile" />
                <span class="text-caption leading-tight text-muted">{{ AUTONOMY[l].label }}</span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in policy"
            :key="row.action"
            class="transition-colors duration-fast hover:bg-input/60 [&:not(:last-child)>td]:border-b [&>td]:border-line"
          >
            <td class="px-5 py-3.5">
              <span class="flex items-center gap-3">
                <IconTile :icon="agentIcon(row.agent)" tone="neutral" size="sm" />
                <span class="grid gap-0.5 leading-tight">
                  <b class="font-semibold">{{ row.action }}</b>
                  <span class="text-label text-muted">{{ row.agent }}</span>
                </span>
              </span>
            </td>
            <td v-for="l in AUTONOMY_ORDER" :key="l" class="px-2 py-3.5 text-center">
              <span
                v-if="applies(row, l)"
                :class="['inline-grid h-8 w-8 place-items-center rounded-full', TONE_SOFT[AUTONOMY[l].tone], AUTONOMY[l].tile]"
              >
                <AppIcon name="check" :size="16" /><span class="sr-only">{{ AUTONOMY[l].label }}</span>
              </span>
              <span v-else class="inline-block h-2 w-2 rounded-full bg-muted/40" aria-hidden="true" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>
