<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";

/**
 * "Please double-check" box for a contract the model read: what it could not confirm in the document
 * (dropped quotes, unreadable dates…). The warnings come from the backend and are shown as delivered.
 */
defineProps<{ warnings: string[] }>();
</script>

<template>
  <div class="grid gap-1.5 rounded-lg bg-warn-soft p-3 text-label text-warn">
    <p class="flex items-center gap-2 font-semibold">
      <AppIcon name="alert" :size="16" />
      {{ t("Please double-check") }}
    </p>
    <ul class="grid gap-1 pl-6">
      <li v-for="w in warnings" :key="w" class="list-disc break-words">{{ w }}</li>
    </ul>
  </div>
</template>
