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
  <div :role="tone === 'error' ? 'alert' : 'status'" :class="['flex items-start gap-3 rounded-xl px-4 py-3 font-medium', TONES[tone]]">
    <AppIcon name="alert" :size="18" class="mt-0.5" />
    <div class="flex-1"><slot /></div>
    <button v-if="dismissible" type="button" class="text-sm font-semibold underline" @click="$emit('dismiss')">Close</button>
  </div>
</template>
