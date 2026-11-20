<script setup lang="ts">
import AutonomyBadge from "@/components/agent/AutonomyBadge.vue";
import SourceTag from "@/components/agent/SourceTag.vue";
import ThinkingSpinner from "@/components/sync/ThinkingSpinner.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
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
    <p class="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-side px-4 py-2.5 leading-relaxed text-white">
      <span class="sr-only">{{ t("You asked:") }} </span>{{ turn.question }}
    </p>

    <!-- the answer -->
    <div v-if="turn.answer" class="grid max-w-[92%] grid-cols-[auto_minmax(0,1fr)] gap-3">
      <IconTile :icon="agentIcon(turn.answer.agent)" tone="info" size="sm" />
      <div
        :class="[
          'grid gap-2 rounded-2xl rounded-tl-md border px-4 py-3',
          turn.answer.in_data ? 'border-line bg-surface' : 'border-transparent bg-mist text-mist-fg',
        ]"
      >
        <div class="flex flex-wrap items-center gap-2">
          <b class="text-sm">{{ t(turn.answer.agent) }}</b>
          <AutonomyBadge level="analyzed" />
          <SourceTag :source="turn.answer.source" :only-fallback="false" />
        </div>
        <p class="leading-relaxed">{{ turn.answer.answer }}</p>
      </div>
    </div>

    <p v-else-if="turn.error" class="flex items-start gap-2 rounded-lg bg-negative-soft p-3 text-negative" role="alert">
      <AppIcon name="alert" :size="18" class="mt-0.5" /> {{ turn.error }}
    </p>

    <div v-else class="flex items-center gap-3 text-muted">
      <ThinkingSpinner icon="sparkles" size="sm" />
      <span role="status">{{ t("Your agents are looking at the numbers…") }}</span>
    </div>
  </li>
</template>
