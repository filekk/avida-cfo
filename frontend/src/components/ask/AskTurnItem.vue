<script setup lang="ts">
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { agentIcon } from "@/constants/agents";
import { t } from "@/i18n";
import type { AskTurn } from "@/stores/ask";

/**
 * One question + the agent's answer. The answer text comes from the backend in the UI language.
 * in_data = false → the question can't be answered from the company's data: shown as a calm info note.
 */
defineProps<{ turn: AskTurn }>();
</script>

<template>
  <li class="grid gap-3 animate-rise">
    <!-- the owner's question -->
    <p class="ml-auto max-w-[85%] rounded-lg bg-side px-4 py-2.5 leading-relaxed text-white">
      <span class="sr-only">{{ t("You asked:") }} </span>{{ turn.question }}
    </p>

    <!-- the answer: one plain bubble; the agent is named in its first line (small muted icon, no avatar tile) -->
    <div
      v-if="turn.answer"
      :class="[
        'grid max-w-[92%] gap-2 rounded-lg border px-4 py-3',
        turn.answer.in_data ? 'border-line bg-surface' : 'border-transparent bg-mist text-mist-fg',
      ]"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="flex items-center gap-1.5 text-sm font-semibold">
          <AppIcon :name="agentIcon(turn.answer.agent)" :size="16" class="shrink-0 opacity-70" />{{ t(turn.answer.agent) }}
        </span>
        <AutonomyBadge level="analyzed" />
        <SourceTag :source="turn.answer.source" :only-fallback="false" />
      </div>
      <p class="leading-relaxed">{{ turn.answer.answer }}</p>
    </div>

    <p v-else-if="turn.error" class="flex items-start gap-2 rounded-lg bg-negative-soft p-3 text-negative" role="alert">
      <AppIcon name="alert" :size="18" class="mt-0.5" /> {{ turn.error }}
    </p>

    <div v-else class="flex items-center gap-3 text-muted">
      <ThinkingSpinner size="sm" />
      <span role="status">{{ t("Your agents are looking at the numbers…") }}</span>
    </div>
  </li>
</template>
