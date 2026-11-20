<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { AUTONOMY } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { Autonomy } from "@/types/api";

/**
 * Challenge requirement: the autonomy level is ALWAYS visible next to agent steps and action cards.
 * Same size/shape as StatusPill (1px border on every level so the dashed "simulated" one is not bigger).
 */
defineProps<{ level: Autonomy }>();
</script>

<template>
  <span
    :class="[
      'inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-caption font-semibold leading-tight',
      AUTONOMY[level].classes,
    ]"
    :title="t(AUTONOMY[level].description)"
  >
    <AppIcon :name="AUTONOMY[level].icon" :size="14" />
    {{ t(AUTONOMY[level].label) }}
  </span>
</template>
