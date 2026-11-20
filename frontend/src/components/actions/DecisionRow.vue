<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import FindingSplit from "@/components/findings/FindingSplit.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
import StatusPill from "@/components/ui/StatusPill.vue";
import { RECOMMENDATION } from "@/constants/autonomy";
import { eur, pct } from "@/utils/format";
import ActionCard from "./ActionCard.vue";
import { decisionState, type DecisionItem } from "./decision";

/**
 * Compact row in the Action center: icon, short title, where it comes from, status, key number.
 * Click → it expands in place and shows everything: the email → contract → verdict flow (if any),
 * the draft / offer and the Approve / Not now buttons.
 */
const props = defineProps<{ item: DecisionItem; open: boolean; busy?: boolean }>();
const emit = defineEmits<{ toggle: []; decide: [id: string, approve: boolean, editedBody?: string] }>();

const a = computed(() => props.item.action);
const f = computed(() => props.item.finding);
const state = computed(() => decisionState(props.item));
const bodyId = computed(() => `decision-${props.item.key}`);

const title = computed(() => {
  if (a.value) return a.value.title;
  const ex = f.value!.extraction;
  return `${ex.supplier}: ${pct(ex.increase_pct)} – ${RECOMMENDATION[f.value!.recommendation]}`;
});

const source = computed(() =>
  a.value && a.value.type !== "send_email"
    ? "From your forecast"
    : `From an email · ${f.value?.extraction.supplier ?? (a.value?.type === "send_email" ? a.value.payload.to : "")}`,
);

const icon = computed<IconName>(() =>
  !a.value ? "inbox" : a.value.type === "send_email" ? "send" : "landmark",
);

const STATUS: Record<typeof state.value, { label: string; tone: "accent" | "warn" | "positive" | "neutral" | "info" }> = {
  pending: { label: "Waiting for you", tone: "accent" },
  review: { label: "Check it yourself", tone: "warn" },
  executed: { label: "Approved", tone: "positive" },
  rejected: { label: "Declined", tone: "neutral" },
  "no-action": { label: "No action needed", tone: "info" },
};

/** The one number worth seeing without opening the row. */
const keyFigure = computed(() => {
  if (a.value?.type === "credit_application") return { label: "Amount", value: eur(a.value.payload.amount), tone: "" };
  if (a.value && a.value.savings_12m > 0)
    return a.value.status === "rejected"
      ? { label: "Would have saved / year", value: eur(a.value.savings_12m), tone: "text-muted" }
      : { label: "You save / year", value: eur(a.value.savings_12m), tone: "text-positive" };
  if (f.value) return { label: "Extra / year", value: eur(f.value.impact.next_12_months), tone: "" };
  return null;
});
</script>

<template>
  <article
    :class="[
      'overflow-hidden rounded-xl border bg-surface transition-shadow',
      state === 'pending' ? 'border-sun' : 'border-line',
      open ? 'shadow-float' : 'shadow-card',
    ]"
  >
    <!-- the compact row -->
    <button
      type="button"
      class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-input/50 sm:gap-4 sm:px-5"
      :aria-expanded="open"
      :aria-controls="bodyId"
      @click="emit('toggle')"
    >
      <span
        :class="[
          'grid h-10 w-10 shrink-0 place-items-center rounded-lg',
          state === 'pending' ? 'bg-sun text-sun-on' : 'bg-input text-muted',
        ]"
        aria-hidden="true"
      >
        <AppIcon :name="icon" :size="18" />
      </span>

      <span class="grid min-w-0 flex-1 gap-1">
        <span class="line-clamp-2 font-semibold leading-snug">{{ title }}</span>
        <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8rem] text-muted">
          <StatusPill :tone="STATUS[state].tone">{{ STATUS[state].label }}</StatusPill>
          <span class="truncate">{{ source }}</span>
        </span>
      </span>

      <span v-if="keyFigure" class="hidden shrink-0 justify-items-end leading-tight sm:grid">
        <span class="text-[0.75rem] text-muted">{{ keyFigure.label }}</span>
        <span :class="['font-display text-lg font-extrabold tabular-nums', keyFigure.tone]">{{ keyFigure.value }}</span>
      </span>

      <AppIcon name="chevronDown" :class="['shrink-0 text-muted transition-transform duration-300', open ? 'rotate-180' : '']" />
    </button>

    <!-- the full content: animates open with the grid-rows 0fr → 1fr trick -->
    <div
      :id="bodyId"
      :class="['grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none', open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]']"
      :inert="!open"
    >
      <div class="min-h-0 overflow-hidden">
        <div class="grid gap-5 border-t border-line px-4 py-4 sm:px-5">
          <div v-if="a" class="flex flex-wrap items-center gap-2">
            <AutonomyBadge :level="a.autonomy" />
            <AutonomyBadge level="simulated" />
            <span class="text-[0.8rem] text-muted">by {{ a.agent }}</span>
            <SourceTag :source="a.source" />
          </div>

          <FindingSplit v-if="f" :finding="f" bare />

          <ActionCard
            v-if="a"
            :action="a"
            :busy="busy"
            embedded
            :compact="!!f"
            @decide="(id, approve, body) => emit('decide', id, approve, body)"
          />
        </div>
      </div>
    </div>
  </article>
</template>
