<script setup lang="ts">
import { getPolicy } from "@/api";
import AutonomyLegend from "@/components/agent/AutonomyLegend.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import { agentIcon } from "@/constants/agents";
import { AUTONOMY, AUTONOMY_ORDER } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { Autonomy, PolicyRule } from "@/types/api";

/**
 * The autonomy matrix (GET /api/policy) – "who may do what", drawn as action × level with marks instead of text.
 * The action names come from the backend and stay as delivered; agent names and levels are translated.
 */
const { data: policy, loading, error, reload } = useAsyncData(getPolicy);

const applies = (row: PolicyRule, level: Autonomy) =>
  level === "simulated" ? row.execution === "simulated" : row.autonomy === level;
</script>

<template>
  <PageHeader
    :title="t('What your agents may do')"
    :description="t('Reading and calculating: on their own. Anything that leaves your company: only after your click.')"
  />

  <BaseCard :title="t('The four levels')">
    <AutonomyLegend detailed />
  </BaseCard>

  <AlertBanner v-if="error">
    {{ error }} <button type="button" class="ml-2 underline" @click="reload">{{ t("Try again") }}</button>
  </AlertBanner>
  <SkeletonBlock v-else-if="loading && !policy" height="h-64" />

  <BaseCard v-else-if="policy" :title="t('Who may do what')" :padded="false">
    <!-- relative: keeps the absolutely-positioned sr-only labels inside the scroll box (else they widen the page) -->
    <div class="relative overflow-x-auto">
      <table class="w-full min-w-[680px] border-collapse">
        <thead>
          <tr>
            <th class="border-b border-line px-5 py-3 text-left align-bottom text-caption font-semibold text-muted">
              {{ t("Action") }}
            </th>
            <th v-for="l in AUTONOMY_ORDER" :key="l" class="w-[8rem] border-b border-line px-2 py-3 align-top font-semibold">
              <span class="grid justify-items-center gap-1.5">
                <AppIcon :name="AUTONOMY[l].icon" :size="18" class="text-muted" />
                <span class="text-caption leading-tight text-muted">{{ t(AUTONOMY[l].label) }}</span>
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
                <AppIcon :name="agentIcon(row.agent)" :size="18" class="shrink-0 text-muted" />
                <span class="grid gap-0.5 leading-tight">
                  <b class="font-semibold">{{ row.action }}</b>
                  <span class="text-label text-muted">{{ t(row.agent) }}</span>
                </span>
              </span>
            </td>
            <td v-for="l in AUTONOMY_ORDER" :key="l" class="px-2 py-3.5 text-center">
              <!-- plain check = "applies" (the column header names the level); a faint dot = "does not apply" -->
              <span v-if="applies(row, l)" class="inline-grid h-8 w-8 place-items-center text-fg">
                <AppIcon name="check" :size="18" /><span class="sr-only">{{ t(AUTONOMY[l].label) }}</span>
              </span>
              <span v-else class="inline-block h-2 w-2 rounded-full bg-muted/40" aria-hidden="true" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>
