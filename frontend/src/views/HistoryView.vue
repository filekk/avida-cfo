<script setup lang="ts">
import { computed } from "vue";
import { getAudit } from "@/api";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import { useAsyncData } from "@/composables/useAsyncData";
import type { AuditEntry } from "@/types/api";
import { fmtDateTime } from "@/utils/format";

/** Audit log (GET /api/audit) – everything that happened, newest first, as a timeline. */
const { data: audit, loading, error, reload } = useAsyncData(getAudit);
const entries = computed(() => (audit.value ? [...audit.value].reverse() : []));

const EVENT: Record<string, { label: string; icon: IconName; node: string }> = {
  sync_started: { label: "Check started", icon: "inbox", node: "bg-mist text-mist-fg" },
  sync_finished: { label: "Check finished", icon: "checkCircle", node: "bg-mist text-mist-fg" },
  approved: { label: "Approved", icon: "check", node: "bg-positive-soft text-positive" },
  rejected: { label: "Declined", icon: "xCircle", node: "bg-input text-muted" },
};
const eventMeta = (e: AuditEntry) => EVENT[e.event] ?? { label: e.event, icon: "history" as const, node: "bg-input text-muted" };

function describe(e: AuditEntry): string {
  if (e.event === "sync_finished") return `${e.findings ?? 0} findings, ${e.actions ?? 0} proposed actions`;
  if (e.event === "approved") return `${e.title ?? ""} – ${e.result ?? ""}`;
  if (e.event === "rejected") return String(e.title ?? "");
  return "";
}
</script>

<template>
  <PageHeader eyebrow="Audit log" title="What happened" description="Every check and decision, newest first.">
    <BaseButton variant="secondary" icon="refresh" :loading="loading" @click="reload">Refresh</BaseButton>
  </PageHeader>

  <AlertBanner v-if="error">{{ error }}</AlertBanner>
  <SkeletonBlock v-else-if="loading && !audit" height="h-48" />

  <BaseCard v-else-if="entries.length">
    <ol class="grid">
      <li v-for="(e, i) in entries" :key="i" class="relative grid grid-cols-[2.25rem_1fr] gap-3 pb-5 last:pb-0">
        <span
          v-if="i < entries.length - 1"
          class="absolute bottom-0 left-[1.125rem] top-10 w-px -translate-x-1/2 bg-line"
          aria-hidden="true"
        />
        <span :class="['grid h-9 w-9 place-items-center rounded-full', eventMeta(e).node]" aria-hidden="true">
          <AppIcon :name="eventMeta(e).icon" />
        </span>
        <div class="grid gap-0.5 pt-1.5">
          <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
            <b class="font-semibold">{{ eventMeta(e).label }}</b>
            <span class="flex items-center gap-1 text-[0.8rem] tabular-nums text-muted">
              <AppIcon name="clock" :size="12" /> {{ fmtDateTime(e.time) }}
            </span>
          </div>
          <span v-if="describe(e)" class="text-sm text-muted">{{ describe(e) }}</span>
        </div>
      </li>
    </ol>
  </BaseCard>

  <EmptyState v-else icon="history" title="Nothing has happened yet" description="Run an inbox check on the overview." />
</template>
