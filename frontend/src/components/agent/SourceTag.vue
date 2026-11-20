<script setup lang="ts">
import { SOURCE_LABEL } from "@/constants/autonomy";
import type { AnswerSource } from "@/types/api";

/** UI rule #3: be honest about the AI – show "cached answer" discreetly when the model was unavailable. */
const props = withDefaults(defineProps<{ source?: AnswerSource; onlyFallback?: boolean }>(), { onlyFallback: true });
</script>

<template>
  <span
    v-if="props.source && (!props.onlyFallback || props.source === 'fallback')"
    class="text-xs italic text-muted"
    :title="props.source === 'fallback' ? 'The AI model was unavailable – this is a prepared answer.' : undefined"
  >
    ({{ SOURCE_LABEL[props.source] }})
  </span>
</template>
