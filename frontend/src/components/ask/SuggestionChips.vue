<script setup lang="ts">
import AppIcon from "@/components/ui/AppIcon.vue";
import { agentIcon } from "@/constants/agents";
import { t } from "@/i18n";
import type { AskSuggestion } from "@/types/api";

/**
 * Clickable questions from the backend (already in the UI language). Emits the question text UNCHANGED –
 * that is how the backend recognises a chip and answers instantly with a prepared answer.
 */
defineProps<{ suggestions: AskSuggestion[]; disabled?: boolean }>();
const emit = defineEmits<{ pick: [question: string] }>();
</script>

<template>
  <ul class="flex flex-wrap gap-2" :aria-label="t('Suggested questions')">
    <li v-for="s in suggestions" :key="s.id" class="animate-rise">
      <button
        type="button"
        :disabled="disabled"
        class="flex min-h-10 items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-left text-sm font-semibold hover:border-fg/40 hover:shadow-lift disabled:opacity-60"
        @click="emit('pick', s.question)"
      >
        <AppIcon :name="agentIcon(s.agent)" :size="16" class="text-muted" />
        <span>{{ s.question }}</span>
        <span class="sr-only">({{ t(s.agent) }})</span>
      </button>
    </li>
  </ul>
</template>
