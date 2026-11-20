<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import StatusPill from "@/components/ui/StatusPill.vue";
import { t } from "@/i18n";
import { STATUS, decisionState, gist, iconOf, isOpenItem, keyFigure, type DecisionItem } from "./decision";

/**
 * Small tile in the Action center: the gist of one decision. Click → the focus view with everything.
 * Pending = sun border; resolved = toned down by background and shadow (never by opacity, so text keeps ≥ 4.5:1).
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
      'group grid w-full content-start gap-3 rounded-xl border p-3.5 text-left',
      'transition-[border-color,box-shadow,transform,background-color] duration-base hover:-translate-y-0.5 hover:shadow-lift',
      state === 'pending'
        ? 'border-sun bg-surface shadow-card'
        : open
          ? 'border-line bg-surface shadow-card hover:border-fg/30'
          : 'border-line bg-input/60 hover:border-fg/30 hover:bg-surface',
    ]"
    @click="$emit('open')"
  >
    <span class="flex items-start gap-3">
      <IconTile :icon="iconOf(item)" :tone="state === 'pending' ? 'accent' : 'neutral'" size="sm" class="transition-colors duration-base" />
      <span class="grid min-w-0 flex-1 gap-0.5">
        <span class="truncate font-bold leading-snug">{{ g.title }}</span>
        <span class="truncate text-label text-muted">{{ g.hint }}</span>
      </span>
      <AppIcon name="arrowRight" :size="18" class="mt-1 shrink-0 text-muted transition-transform duration-base group-hover:translate-x-1" />
    </span>

    <span class="flex flex-wrap items-end justify-between gap-2">
      <StatusPill :tone="STATUS[state].tone">{{ t(STATUS[state].label) }}</StatusPill>
      <span v-if="fig" class="grid justify-items-end gap-0.5 leading-tight">
        <span class="text-caption text-muted">{{ fig.label }}</span>
        <span :class="['font-display text-base font-extrabold tabular-nums', fig.tone]">{{ fig.value }}</span>
      </span>
    </span>
  </button>
</template>
