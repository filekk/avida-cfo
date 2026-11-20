<script setup lang="ts">
import { getAudit } from "@/api";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import type { AuditEntry } from "@/types/api";
import { fmtDateTime } from "@/utils/format";

/** Audit log (GET /api/audit) – everything that happened, in order. */
const { data: audit, loading, error, reload } = useAsyncData(getAudit);

const EVENT: Record<string, { label: string; tone: "positive" | "negative" | "info" | "neutral" }> = {
  sync_started: { label: "Check started", tone: "info" },
  sync_finished: { label: "Check finished", tone: "info" },
  approved: { label: "Approved", tone: "positive" },
  rejected: { label: "Declined", tone: "neutral" },
};
const eventMeta = (e: AuditEntry) => EVENT[e.event] ?? { label: e.event, tone: "neutral" as const };

function describe(e: AuditEntry): string {
  if (e.event === "sync_finished") return `${e.findings ?? 0} findings, ${e.actions ?? 0} proposed actions`;
  if (e.event === "approved") return `${e.title ?? ""} – ${e.result ?? ""}`;
  if (e.event === "rejected") return String(e.title ?? "");
  return "";
}
</script>

<template>
  <PageHeader eyebrow="Audit log" title="What happened" description="Every check and every decision, in order.">
    <BaseButton variant="secondary" icon="refresh" :loading="loading" @click="reload">Refresh</BaseButton>
  </PageHeader>

  <AlertBanner v-if="error">{{ error }}</AlertBanner>
  <SkeletonBlock v-else-if="loading && !audit" height="h-48" />

  <BaseCard v-else-if="audit?.length" :padded="false">
    <ol>
      <li
        v-for="(e, i) in [...audit].reverse()"
        :key="i"
        class="grid gap-1 border-b border-line px-5 py-3 last:border-b-0 sm:grid-cols-[11rem_9rem_1fr] sm:items-center sm:gap-4"
      >
        <span class="text-sm tabular-nums text-muted">{{ fmtDateTime(e.time) }}</span>
        <StatusPill :tone="eventMeta(e).tone">{{ eventMeta(e).label }}</StatusPill>
        <span>{{ describe(e) }}</span>
      </li>
    </ol>
  </BaseCard>

  <EmptyState v-else icon="history" title="Nothing has happened yet" description="Run an inbox check on the overview page." />
</template>
