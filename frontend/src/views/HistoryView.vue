<script setup lang="ts">
import { computed } from "vue";
import { getAudit } from "@/api";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import type { IconName } from "@/components/ui/icons";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue";
import type { Tone } from "@/components/ui/tones";
import { useAsyncData } from "@/composables/useAsyncData";
import { t, tn } from "@/i18n";
import type { AuditEntry } from "@/types/api";
import { eur, fmtDate, fmtDateTime } from "@/utils/format";

/**
 * Audit log (GET /api/audit) – everything that happened, newest first, as a timeline.
 * Event names are translated; the details (titles, results, questions, replies) come from the backend as delivered.
 * Every event the backend writes has a label below; anything unknown (a newer backend) is left out rather than
 * shown as a raw id like "redraft_proposed".
 */
const { data: audit, loading, error, reload } = useAsyncData(getAudit);

/** English labels – translated where shown. */
const EVENT: Record<string, { label: string; icon: IconName; tone: Tone }> = {
  sync_started: { label: "Check started", icon: "inbox", tone: "info" },
  sync_finished: { label: "Check finished", icon: "checkCircle", tone: "info" },
  approved: { label: "Approved", icon: "check", tone: "positive" },
  rejected: { label: "Declined", icon: "xCircle", tone: "neutral" },
  reply_received: { label: "Reply received (simulated)", icon: "mail", tone: "info" },
  plan_updated: { label: "Plan updated", icon: "chart", tone: "info" },
  question: { label: "Question asked", icon: "ask", tone: "neutral" },
  redraft_proposed: { label: "Draft rewritten", icon: "pencil", tone: "neutral" },
  redraft_refused: { label: "Rewrite refused", icon: "alert", tone: "neutral" },
  contract_uploaded: { label: "Contract uploaded", icon: "upload", tone: "neutral" },
};
const entries = computed(() => (audit.value ? [...audit.value].reverse().filter((e) => e.event in EVENT) : []));
const eventMeta = (e: AuditEntry) => EVENT[e.event];

const text = (v: unknown) => (typeof v === "string" ? v.trim() : "");
/** The parts that exist, joined – never a dangling " – " when one is missing. */
const join = (...parts: unknown[]) => parts.map(text).filter(Boolean).join(" – ");

function describe(e: AuditEntry): string {
  switch (e.event) {
    case "sync_finished": {
      const f = Number(e.findings ?? 0);
      const a = Number(e.actions ?? 0);
      return `${tn(f, "{n} finding", "{n} findings")}, ${tn(a, "{n} proposed action", "{n} proposed actions")}`;
    }
    case "approved":
      return join(e.title, e.result);
    case "rejected":
      return join(e.title);
    case "reply_received":
      return join(e.partner, e.summary);
    case "plan_updated":
      return typeof e.min_balance === "number"
        ? t("Lowest balance {amount} on {date}", { amount: eur(e.min_balance), date: fmtDate(text(e.min_date)) })
        : "";
    case "question":
      return join(e.question);
    case "redraft_proposed":
    case "redraft_refused":
      return join(e.instruction);
    case "contract_uploaded":
      return join(e.party, e.file);
    default:
      return "";
  }
}
</script>

<template>
  <PageHeader :title="t('What happened')" :description="t('Every check and decision, newest first.')">
    <BaseButton variant="secondary" icon="refresh" :loading="loading" @click="reload">{{ t("Refresh") }}</BaseButton>
  </PageHeader>

  <AlertBanner v-if="error">{{ error }}</AlertBanner>
  <SkeletonBlock v-else-if="loading && !audit" height="h-48" />

  <BaseCard v-else-if="entries.length">
    <ol class="grid">
      <li
        v-for="(e, i) in entries"
        :key="`${e.time}-${e.event}-${entries.length - i}`"
        class="relative grid grid-cols-[2.5rem_1fr] gap-3 pb-6 last:pb-0"
      >
        <span
          v-if="i < entries.length - 1"
          class="absolute -bottom-1 left-5 top-9 w-px -translate-x-1/2 bg-line"
          aria-hidden="true"
        />
        <!-- small icon on the line, no coloured node; only "approved" is green (the check tells it apart without colour too) -->
        <span
          :class="['grid h-10 w-10 place-items-center', eventMeta(e).tone === 'positive' ? 'text-positive' : 'text-muted']"
          aria-hidden="true"
        >
          <AppIcon :name="eventMeta(e).icon" :size="18" />
        </span>
        <div class="grid gap-1 pt-1.5">
          <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <b class="font-semibold">{{ t(eventMeta(e).label) }}</b>
            <span class="flex items-center gap-1.5 text-label tabular-nums text-muted">
              <AppIcon name="clock" :size="14" /> {{ fmtDateTime(e.time) }}
            </span>
          </div>
          <span v-if="describe(e)" class="text-sm leading-snug text-muted">{{ describe(e) }}</span>
        </div>
      </li>
    </ol>
  </BaseCard>

  <EmptyState
    v-else
    icon="history"
    :title="t('Nothing has happened yet')"
    :description="t('Use “{button}” at the top of the page.', { button: t('Check my inbox') })"
  />
</template>
