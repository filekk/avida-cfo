<script setup lang="ts">
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { t } from "@/i18n";
import type { Dashboard } from "@/types/api";

/**
 * The Analyst's briefing after an inbox check: a short summary (written by the model, every number checked)
 * and the key points (deterministic). Texts come from the backend and are shown as delivered.
 */
defineProps<{ analysis: NonNullable<Dashboard["analysis"]> }>();

const RISK = {
  low: { label: "Low risk", tone: "positive" },
  medium: { label: "Medium risk", tone: "warn" },
  high: { label: "High risk", tone: "negative" },
} as const;
</script>

<template>
  <BaseCard :title="t('Analyst briefing')" :eyebrow="t('Analyst Agent')">
    <template #actions>
      <StatusPill :tone="RISK[analysis.risk_level].tone">{{ t(RISK[analysis.risk_level].label) }}</StatusPill>
    </template>
    <div class="grid gap-4">
      <p class="flex flex-wrap items-center gap-2">
        <AutonomyBadge level="analyzed" />
        <SourceTag :source="analysis.source" />
      </p>
      <p class="text-lg font-semibold leading-relaxed">{{ analysis.summary }}</p>
      <ul class="grid gap-2.5">
        <li v-for="p in analysis.key_points" :key="p" class="grid grid-cols-[auto_1fr] gap-2.5 text-sm leading-relaxed">
          <AppIcon name="chevronRight" :size="18" class="mt-0.5 text-muted" />
          <span>{{ p }}</span>
        </li>
      </ul>
    </div>
  </BaseCard>
</template>
