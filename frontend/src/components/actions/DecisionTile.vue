<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { STATUS, decisionState, gist, iconOf, keyFigure, type DecisionItem } from "./decision";

/** Small tile in the Action center: the gist of one decision. Click → the focus view with everything. */
const props = defineProps<{ item: DecisionItem }>();
defineEmits<{ open: [] }>();

const state = computed(() => decisionState(props.item));
const g = computed(() => gist(props.item));
const fig = computed(() => keyFigure(props.item));
</script>

<template>
  <button
    type="button"
    :class="[
      'group grid w-full content-start gap-3 rounded-xl border bg-surface p-3.5 text-left shadow-card transition-[border-color,box-shadow,transform] hover:-translate-y-0.5 hover:shadow-float',
      state === 'pending' ? 'border-sun' : 'border-line hover:border-fg/30',
    ]"
    @click="$emit('open')"
  >
    <span class="flex items-start gap-3">
      <span
        :class="[
          'grid h-9 w-9 shrink-0 place-items-center rounded-lg',
          state === 'pending' ? 'bg-sun text-sun-on' : 'bg-input text-muted',
        ]"
        aria-hidden="true"
      >
        <AppIcon :name="iconOf(item)" :size="17" />
      </span>
      <span class="grid min-w-0 flex-1 gap-0.5">
        <span class="truncate font-bold leading-snug">{{ g.title }}</span>
        <span class="truncate text-[0.8rem] text-muted">{{ g.hint }}</span>
      </span>
      <AppIcon name="arrowRight" :size="16" class="mt-1 shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />
    </span>

    <span class="flex flex-wrap items-end justify-between gap-2">
      <StatusPill :tone="STATUS[state].tone">{{ STATUS[state].label }}</StatusPill>
      <span v-if="fig" class="grid justify-items-end leading-tight">
        <span class="text-[0.7rem] text-muted">{{ fig.label }}</span>
        <span :class="['font-display text-base font-extrabold tabular-nums', fig.tone]">{{ fig.value }}</span>
      </span>
    </span>
  </button>
</template>
