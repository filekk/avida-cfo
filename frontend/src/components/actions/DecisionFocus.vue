<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import FindingSplit from "@/components/findings/FindingSplit.vue";
import { describeFinding } from "@/components/findings/describe";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { t } from "@/i18n";
import ActionCard from "./ActionCard.vue";
import { CATEGORY_LABEL, STATUS, categoryOf, decisionState, type DecisionItem } from "./decision";

/**
 * Focus view: one decision fills the Action center. Everything about it – the email → contract → verdict flow,
 * the draft or offer and the buttons – plus "back to all actions" and previous / next to switch between decisions.
 */
const props = defineProps<{ item: DecisionItem; busy?: boolean; position: number; total: number }>();
const emit = defineEmits<{
  back: [];
  prev: [];
  next: [];
  decide: [id: string, approve: boolean, editedBody?: string];
}>();

const a = computed(() => props.item.action);
const f = computed(() => props.item.finding);
const state = computed(() => decisionState(props.item));
/** Backend action title when there is one; otherwise a title from the finding (price change / late payment). */
const title = computed(() => {
  if (a.value) return a.value.title;
  const party = describeFinding(f.value!).party;
  return f.value!.kind === "payment_delay"
    ? t("{supplier}: late payment", { supplier: party })
    : t("{supplier}: price change", { supplier: party });
});

const STEP =
  "grid h-10 w-10 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent";
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-line bg-surface" aria-labelledby="focus-title">
    <!-- toolbar: back · category · prev / next -->
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-input/40 px-3 py-2 sm:px-4">
      <button
        type="button"
        class="flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-semibold text-gold hover:bg-mist"
        @click="emit('back')"
      >
        <AppIcon name="arrowLeft" :size="18" />
        {{ t("All actions") }}
      </button>
      <span class="hidden text-label text-muted sm:block">{{ t(CATEGORY_LABEL[categoryOf(item)]) }}</span>
      <div class="flex items-center gap-1">
        <span class="px-1 text-label tabular-nums text-muted">{{ t("{position} of {total}", { position, total }) }}</span>
        <button type="button" :class="STEP" :disabled="position <= 1" :aria-label="t('Previous decision')" @click="emit('prev')">
          <AppIcon name="chevronLeft" :size="20" />
        </button>
        <button type="button" :class="STEP" :disabled="position >= total" :aria-label="t('Next decision')" @click="emit('next')">
          <AppIcon name="chevronRight" :size="20" />
        </button>
      </div>
    </div>

    <div class="grid gap-5 p-4 sm:p-5">
      <!-- title: max. two badges (status + autonomy) over the title; simulated / author / source as plain muted text -->
      <div class="grid gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <StatusPill :tone="STATUS[state].tone">{{ t(STATUS[state].label) }}</StatusPill>
          <AutonomyBadge v-if="a" :level="a.autonomy" />
        </div>
        <h2 id="focus-title" class="text-xl font-semibold leading-snug">{{ title }}</h2>
        <p v-if="a" class="flex flex-wrap items-center gap-x-2 gap-y-1 text-label text-muted">
          <AutonomyBadge level="simulated" plain />
          <span aria-hidden="true">·</span>
          <span>{{ t("by {agent}", { agent: t(a.agent) }) }}</span>
          <SourceTag :source="a.source" />
        </p>
      </div>

      <FindingSplit v-if="f" :finding="f" bare />

      <ActionCard
        v-if="a"
        :action="a"
        :busy="busy"
        embedded
        :compact="!!f"
        :class="f ? 'border-t border-line pt-5' : ''"
        @decide="(id, approve, body) => emit('decide', id, approve, body)"
      />
    </div>
  </section>
</template>
