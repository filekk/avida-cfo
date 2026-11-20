<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { AUTONOMY } from "@/constants/autonomy";
import type { Autonomy } from "@/types/api";

/** Challenge requirement: the autonomy level is ALWAYS visible next to agent steps and action cards. */
defineProps<{ level: Autonomy }>();
</script>

<template>
  <span
    :class="['inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[0.75rem] font-semibold', AUTONOMY[level].classes]"
    :title="AUTONOMY[level].description"
  >
    <AppIcon :name="AUTONOMY[level].icon" :size="13" />
    {{ AUTONOMY[level].label }}
  </span>
</template>
