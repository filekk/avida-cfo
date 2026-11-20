<script setup lang="ts">
import AppIcon from "./AppIcon.vue";

withDefaults(defineProps<{ tone?: "error" | "info" | "warn"; dismissible?: boolean }>(), { tone: "error" });
defineEmits<{ dismiss: [] }>();

const TONES = {
  error: "bg-negative-soft text-negative",
  warn: "bg-warn-soft text-warn",
  info: "bg-mist text-mist-fg",
};
</script>

<template>
  <div
    :role="tone === 'error' ? 'alert' : 'status'"
    :class="['flex items-start gap-3 rounded-xl px-4 py-3.5 font-medium animate-rise', TONES[tone]]"
  >
    <AppIcon name="alert" :size="20" class="mt-0.5" />
    <div class="flex-1"><slot /></div>
    <button
      v-if="dismissible"
      type="button"
      class="flex items-center gap-1 rounded-md px-1.5 text-label font-semibold underline-offset-4 hover:underline"
      @click="$emit('dismiss')"
    >
      <AppIcon name="x" :size="16" /> Close
    </button>
  </div>
</template>
