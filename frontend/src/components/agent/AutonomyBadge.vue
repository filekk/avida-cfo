<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { AUTONOMY } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { Autonomy } from "@/types/api";

/**
 * Challenge requirement: the autonomy level is ALWAYS visible next to agent steps and action cards.
 * Default: same size/shape as StatusPill – a flat 6px-radius rectangle (1px border on every level so the dashed
 * "simulated" one is not bigger).
 * `plain`: the same icon + label as muted text, no box – for the second level in a row that already has two badges
 * (e.g. "Simulated execution" next to status + "Needs your approval"). Max. 2 badges per row.
 */
withDefaults(defineProps<{ level: Autonomy; plain?: boolean }>(), { plain: false });
</script>

<template>
  <span
    :class="
      plain
        ? 'inline-flex w-fit items-center gap-1.5 whitespace-nowrap text-label text-muted'
        : [
            'inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-caption font-medium leading-snug',
            AUTONOMY[level].classes,
          ]
    "
    :title="t(AUTONOMY[level].description)"
  >
    <AppIcon :name="AUTONOMY[level].icon" :size="14" />
    {{ t(AUTONOMY[level].label) }}
  </span>
</template>
