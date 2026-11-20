<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import IconTile from "@/components/ui/IconTile.vue";
import type { IconName } from "@/components/ui/icons";
import type { Tone } from "@/components/ui/tones";
import { AGENTS, AGENT_ORDER } from "@/constants/agents";
import type { AgentName } from "@/types/api";

/**
 * "How it works" diagram: Inbox → Contract → Liquidity → You. Replaces the explanatory paragraph and
 * doubles as a live progress indicator while /api/sync is streaming (the active agent is highlighted).
 */
const props = withDefaults(
  defineProps<{ state: "idle" | "running" | "done"; activeAgent?: AgentName | null; pending?: number }>(),
  { activeAgent: null, pending: 0 },
);

type StepStatus = "todo" | "active" | "done";
interface Step { key: string; name: string; task: string; icon: IconName; status: StepStatus }

const steps = computed<Step[]>(() => {
  const activeIdx = props.activeAgent ? AGENT_ORDER.indexOf(props.activeAgent) : 0;
  const agentStatus = (i: number): StepStatus => {
    if (props.state === "done") return "done";
    if (props.state === "running") return i < activeIdx ? "done" : i === activeIdx ? "active" : "todo";
    return "todo";
  };
  const youStatus: StepStatus = props.state !== "done" ? "todo" : props.pending > 0 ? "active" : "done";
  return [
    ...AGENT_ORDER.map((name, i) => ({ key: name, name, task: AGENTS[name].task, icon: AGENTS[name].icon, status: agentStatus(i) })),
    { key: "you", name: "You", task: props.pending > 0 ? `${props.pending} to approve` : "Approve or decline", icon: "user" as const, status: youStatus },
  ];
});

const TONE: Record<StepStatus, Tone> = { todo: "info", active: "accent", done: "positive" };
const STATUS_TEXT: Record<StepStatus, string> = { todo: "not started", active: "in progress", done: "done" };
</script>

<template>
  <ol class="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-4">
    <li v-for="(s, i) in steps" :key="s.key" class="relative grid justify-items-center gap-1 text-center">
      <!-- connector to the next step (one row only from sm up): from 0.5rem right of this 56px tile to 0.5rem before the next -->
      <span
        v-if="i < steps.length - 1"
        :class="[
          'absolute left-[calc(50%_+_2.25rem)] right-[calc(1.5rem_-_50%)] top-[calc(1.75rem_-_1px)] hidden h-0.5 rounded-full transition-colors duration-slow sm:block',
          s.status === 'done' ? 'bg-positive' : 'bg-line',
        ]"
        aria-hidden="true"
      />
      <IconTile
        size="lg"
        :tone="TONE[s.status]"
        :class="['relative transition-[background-color,color,box-shadow] duration-base', s.status === 'active' ? 'ring-4 ring-sun/25' : '']"
      >
        <AppIcon :name="s.icon" :size="26" :class="s.status === 'active' && state === 'running' ? 'animate-pulse' : ''" />
        <Transition name="fade">
          <span
            v-if="s.status === 'done'"
            class="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full bg-positive text-surface ring-2 ring-surface"
          >
            <AppIcon name="check" :size="14" />
          </span>
        </Transition>
      </IconTile>
      <span class="mt-1.5 text-base font-bold leading-tight">{{ s.name }}</span>
      <span class="text-label leading-snug text-muted">{{ s.task }}</span>
      <span class="sr-only">({{ STATUS_TEXT[s.status] }})</span>
    </li>
  </ol>
</template>
