<script setup lang="ts">
import { computed } from "vue";
import { getAudit } from "@/api";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import IconTile from "@/components/ui/IconTile.vue";
import type { IconName } from "@/components/ui/icons";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import type { Tone } from "@/components/ui/tones";
import { useAsyncData } from "@/composables/useAsyncData";
import type { AuditEntry } from "@/types/api";
import { fmtDateTime } from "@/utils/format";

/** Audit log (GET /api/audit) – everything that happened, newest first, as a timeline. */
const { data: audit, loading, error, reload } = useAsyncData(getAudit);
const entries = computed(() => (audit.value ? [...audit.value].reverse() : []));

const EVENT: Record<string, { label: string; icon: IconName; tone: Tone }> = {
  sync_started: { label: "Check started", icon: "inbox", tone: "info" },
  sync_finished: { label: "Check finished", icon: "checkCircle", tone: "info" },
  approved: { label: "Approved", icon: "check", tone: "positive" },
  rejected: { label: "Declined", icon: "xCircle", tone: "neutral" },
};
const eventMeta = (e: AuditEntry) => EVENT[e.event] ?? { label: e.event, icon: "history" as const, tone: "neutral" as const };

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
      <li
        v-for="(e, i) in entries"
        :key="`${e.time}-${e.event}-${i}`"
        class="relative grid grid-cols-[2.5rem_1fr] gap-3 pb-6 animate-rise last:pb-0"
      >
        <span
          v-if="i < entries.length - 1"
          class="absolute bottom-0 left-5 top-11 w-px -translate-x-1/2 bg-line"
          aria-hidden="true"
        />
        <IconTile :icon="eventMeta(e).icon" :tone="eventMeta(e).tone" size="sm" round />
        <div class="grid gap-1 pt-1.5">
          <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <b class="font-semibold">{{ eventMeta(e).label }}</b>
            <span class="flex items-center gap-1.5 text-label tabular-nums text-muted">
              <AppIcon name="clock" :size="14" /> {{ fmtDateTime(e.time) }}
            </span>
          </div>
          <span v-if="describe(e)" class="text-sm leading-snug text-muted">{{ describe(e) }}</span>
        </div>
      </li>
    </ol>
  </BaseCard>

  <EmptyState v-else icon="history" title="Nothing has happened yet" description="Run an inbox check on the overview." />
</template>
