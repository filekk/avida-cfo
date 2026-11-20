<script setup lang="ts">
import { computed } from "vue";
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import FindingSplit from "@/components/findings/FindingSplit.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import ActionCard from "./ActionCard.vue";
import { CATEGORY_LABEL, STATUS, categoryOf, decisionState, iconOf, type DecisionItem } from "./decision";

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
const title = computed(() => a.value?.title ?? `${f.value!.extraction.supplier}: price change`);
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-line bg-surface shadow-card" aria-labelledby="focus-title">
    <!-- toolbar: back · category · prev / next -->
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-input/40 px-3 py-2 sm:px-4">
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-semibold text-gold hover:bg-mist"
        @click="emit('back')"
      >
        <AppIcon name="arrowLeft" /> All actions
      </button>
      <span class="hidden text-[0.8rem] text-muted sm:block">{{ CATEGORY_LABEL[categoryOf(item)] }}</span>
      <div class="flex items-center gap-1">
        <span class="px-1 text-[0.8rem] tabular-nums text-muted">{{ position }} of {{ total }}</span>
        <button
          type="button"
          class="grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg disabled:opacity-40"
          :disabled="position <= 1"
          aria-label="Previous decision"
          @click="emit('prev')"
        >
          <AppIcon name="arrowLeft" />
        </button>
        <button
          type="button"
          class="grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-mist hover:text-fg disabled:opacity-40"
          :disabled="position >= total"
          aria-label="Next decision"
          @click="emit('next')"
        >
          <AppIcon name="arrowRight" />
        </button>
      </div>
    </div>

    <div class="grid gap-5 p-4 sm:p-5">
      <!-- title -->
      <div class="flex items-start gap-4">
        <span
          :class="[
            'grid h-12 w-12 shrink-0 place-items-center rounded-xl',
            state === 'pending' ? 'bg-sun text-sun-on' : 'bg-input text-muted',
          ]"
          aria-hidden="true"
        >
          <AppIcon :name="iconOf(item)" :size="22" />
        </span>
        <div class="grid min-w-0 flex-1 gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <StatusPill :tone="STATUS[state].tone">{{ STATUS[state].label }}</StatusPill>
            <template v-if="a">
              <AutonomyBadge :level="a.autonomy" />
              <AutonomyBadge level="simulated" />
              <span class="text-[0.8rem] text-muted">by {{ a.agent }}</span>
              <SourceTag :source="a.source" />
            </template>
          </div>
          <h2 id="focus-title" class="text-xl font-bold leading-snug">{{ title }}</h2>
        </div>
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
