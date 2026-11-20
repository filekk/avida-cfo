<script setup lang="ts">
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseCard from "@/components/ui/BaseCard.vue";
import { t } from "@/i18n";
import type { AskSuggestion } from "@/types/api";
import SuggestionChips from "./SuggestionChips.vue";

/** Overview entry to "Ask your CFO": the top suggestions as chips; the parent asks and opens the Ask page. */
defineProps<{ suggestions: AskSuggestion[]; note?: string | null }>();
const emit = defineEmits<{ pick: [question: string] }>();
</script>

<template>
  <BaseCard :title="t('Ask your CFO')" :eyebrow="t('Questions?')">
    <div class="grid gap-4">
      <p class="text-sm text-muted">{{ note ?? t("Your agents answer from your own numbers – instantly for these questions:") }}</p>
      <SuggestionChips :suggestions="suggestions" @pick="(q) => emit('pick', q)" />
      <BaseButton variant="secondary" size="sm" icon="ask" :to="{ name: 'ask' }" class="w-fit">{{ t("Ask your own question") }}</BaseButton>
    </div>
  </BaseCard>
</template>
