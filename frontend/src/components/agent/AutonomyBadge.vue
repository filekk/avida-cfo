<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import AppTooltip from "@/components/ui/AppTooltip.vue";
import { AUTONOMY } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { Autonomy } from "@/types/api";

/**
 * Challenge requirement: the autonomy level is ALWAYS visible next to agent steps and action cards.
 * Default: same size/shape as StatusPill – a flat 6px-radius rectangle (1px border on every level so the dashed
 * "simulated" one is not bigger).
 * `plain`: the same icon + label as muted text, no box – for the second level in a row that already has two badges
 * (e.g. "Simulated execution" next to status + "Needs your approval"). Max. 2 badges per row.
 * Every badge explains itself: hover or keyboard focus shows a tooltip with what this level means (this replaced the
 * separate "four levels" legend on the Agent permissions page). Hover signal: help cursor + a darker border / text.
 */
withDefaults(defineProps<{ level: Autonomy; plain?: boolean }>(), { plain: false });
</script>

<template>
  <AppTooltip :title="t(AUTONOMY[level].label)" :text="t(AUTONOMY[level].tooltip)">
    <span
      :class="
        plain
          ? 'inline-flex w-fit items-center gap-1.5 whitespace-nowrap text-label text-muted decoration-dotted underline-offset-4 transition-colors duration-fast hover:text-fg hover:underline'
          : [
              'inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-caption font-medium leading-snug transition-colors duration-fast hover:border-fg/40',
              AUTONOMY[level].classes,
            ]
      "
    >
      <AppIcon :name="AUTONOMY[level].icon" :size="14" />
      {{ t(AUTONOMY[level].label) }}
    </span>
  </AppTooltip>
</template>
