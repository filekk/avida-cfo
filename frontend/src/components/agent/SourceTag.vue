<script setup lang="ts">
import { SOURCE_LABEL } from "@/constants/autonomy";
import { t } from "@/i18n";
import type { AnswerSource } from "@/types/api";

/** UI rule #3: be honest about the AI – show "cached answer" discreetly when the model was unavailable. */
const props = withDefaults(defineProps<{ source?: AnswerSource; onlyFallback?: boolean }>(), { onlyFallback: true });
</script>

<template>
  <span
    v-if="props.source && (!props.onlyFallback || props.source === 'fallback')"
    class="whitespace-nowrap text-caption italic text-muted"
    :title="props.source === 'fallback' ? t('The AI model was unavailable – this is a prepared answer.') : undefined"
  >
    ({{ t(SOURCE_LABEL[props.source]) }})
  </span>
</template>
