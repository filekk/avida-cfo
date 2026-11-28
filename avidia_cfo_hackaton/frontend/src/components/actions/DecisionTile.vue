<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { t } from "@/i18n";
import { STATUS, decisionState, gist, isOpenItem, keyFigure, type DecisionItem } from "./decision";

/**
 * Small tile in the Action center: the gist of one decision. Click → the focus view with everything.
 * Open = white tile. Resolved = greyed out until hovered: muted background and text, status + figure without colour
 * (grayscale filter – never opacity on text, so it keeps ≥ 4.5:1); hover/focus brings back the full tile.
 * Hover = border + background colour only – the tile never lifts or casts a shadow. The status label says "waiting",
 * so the sun stays free for the one main button of the screen. No icon tile: the column already says what kind
 * of item it is, and the title says which one.
 */
const props = defineProps<{ item: DecisionItem }>();
defineEmits<{ open: [] }>();

const state = computed(() => decisionState(props.item));
const open = computed(() => isOpenItem(props.item));
const g = computed(() => gist(props.item));
const fig = computed(() => keyFigure(props.item));
</script>

<template>
  <button
    type="button"
    :class="[
      'group grid w-full content-start gap-3 rounded-xl border border-line p-3.5 text-left',
      'transition-colors duration-fast hover:border-fg/30',
      open
        ? 'bg-surface hover:bg-input/40'
        : 'bg-input/60 text-muted hover:bg-surface hover:text-fg focus-visible:bg-surface focus-visible:text-fg',
    ]"
    @click="$emit('open')"
  >
    <span class="flex items-start gap-3">
      <span class="grid min-w-0 flex-1 gap-0.5">
        <span class="truncate font-semibold leading-snug">{{ g.title }}</span>
        <span class="truncate text-label text-muted">{{ g.hint }}</span>
      </span>
      <AppIcon name="arrowRight" :size="18" class="mt-1 shrink-0 text-muted transition-colors duration-fast group-hover:text-fg" />
    </span>

    <span
      :class="[
        'flex flex-wrap items-end justify-between gap-2',
        open ? '' : 'grayscale transition-[filter] duration-fast group-hover:grayscale-0 group-focus-visible:grayscale-0',
      ]"
    >
      <StatusPill :tone="STATUS[state].tone">{{ t(STATUS[state].label) }}</StatusPill>
      <span v-if="fig" class="grid justify-items-end gap-0.5 leading-tight">
        <span class="text-caption text-muted">{{ fig.label }}</span>
        <span :class="['font-display text-base font-semibold tracking-tight tabular-nums', fig.tone]">{{ fig.value }}</span>
      </span>
    </span>
  </button>
</template>
