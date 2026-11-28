<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import type { IconName } from "@/components/ui/icons";
import type { Tone } from "@/components/ui/tones";
import { agentInfo } from "@/constants/agents";
import { t, tn } from "@/i18n";

/**
 * Compact "who works on it" strip for the inbox-check pop-up: the agents of the current crew + You.
 * Live: the agent at work is sun-coloured (static, no pulsing), agents that already spoke get a green check.
 * Works for today's sequential crew and for the upcoming crew whose agents take turns (status comes from
 * "has spoken" + "speaks now", not from a fixed order).
 */
const props = withDefaults(
  defineProps<{
    crew: string[];
    state: "idle" | "running" | "done" | "error";
    activeAgent?: string | null;
    seen?: string[];
    pending?: number;
  }>(),
  { activeAgent: null, seen: () => [], pending: 0 },
);

type StepStatus = "todo" | "active" | "done";
interface Step { key: string; label: string; icon: IconName; status: StepStatus }

const steps = computed<Step[]>(() => {
  const status = (name: string): StepStatus => {
    if (props.state === "done") return "done";
    if (props.state === "running" && name === props.activeAgent) return "active";
    return props.seen.includes(name) ? "done" : "todo";
  };
  const you: StepStatus = props.state !== "done" ? "todo" : props.pending > 0 ? "active" : "done";
  return [
    ...props.crew.map((name) => ({ key: name, label: agentInfo(name).short, icon: agentInfo(name).icon, status: status(name) })),
    { key: "you", label: "You", icon: "user" as const, status: you },
  ];
});

const TONE: Record<StepStatus, Tone> = { todo: "neutral", active: "accent", done: "positive" };
const STATUS_TEXT: Record<StepStatus, string> = { todo: "not started", active: "in progress", done: "done" };
</script>

<template>
  <ol class="grid" :style="{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }">
    <li v-for="(s, i) in steps" :key="s.key" class="relative grid content-start justify-items-center gap-1.5 text-center">
      <!-- connector: from 4px right of this 40px tile to 4px before the next one -->
      <span
        v-if="i < steps.length - 1"
        :class="[
          'absolute left-[calc(50%+1.5rem)] right-[calc(1.5rem-50%)] top-[calc(1.25rem-1px)] h-0.5 rounded-full transition-colors duration-slow',
          s.status === 'done' ? 'bg-positive' : 'bg-line',
        ]"
        aria-hidden="true"
      />
      <IconTile
        size="sm"
        round
        :tone="TONE[s.status]"
        :class="['relative transition-[background-color,color,box-shadow] duration-base', s.status === 'active' ? 'ring-4 ring-sun/25' : '']"
      >
        <AppIcon :name="s.icon" :size="18" />
        <span
          :class="[
            'absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-positive text-surface ring-2 ring-surface transition-[opacity,transform] duration-base',
            s.status === 'done' ? 'scale-100 opacity-100' : 'scale-50 opacity-0',
          ]"
        >
          <AppIcon name="check" :size="12" />
        </span>
      </IconTile>
      <!-- hyphens + anywhere-wrap: long German words ("Posteingang") break instead of overlapping at large text sizes -->
      <span
        :class="[
          'max-w-full px-0.5 text-caption font-semibold leading-tight hyphens-auto [overflow-wrap:anywhere]',
          s.status === 'todo' ? 'text-muted' : 'text-fg',
        ]"
      >
        {{ t(s.label) }}
        <span v-if="s.key === 'you' && state === 'done' && pending > 0" class="block font-normal text-muted">
          {{ tn(pending, "{n} to approve", "{n} to approve") }}
        </span>
      </span>
      <span class="sr-only">({{ t(STATUS_TEXT[s.status]) }})</span>
    </li>
  </ol>
</template>
