<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { IconName } from "@/components/ui/icons";
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

const TILE: Record<StepStatus, string> = {
  todo: "bg-mist text-mist-fg",
  active: "bg-sun text-sun-on ring-4 ring-sun/25",
  done: "bg-positive-soft text-positive",
};
const STATUS_TEXT: Record<StepStatus, string> = { todo: "not started", active: "in progress", done: "done" };
</script>

<template>
  <ol class="grid grid-cols-2 gap-x-3 gap-y-5 sm:grid-cols-4">
    <li v-for="(s, i) in steps" :key="s.key" class="relative grid justify-items-center gap-1.5 text-center">
      <!-- connector to the next step (one row only from sm up) -->
      <span
        v-if="i < steps.length - 1"
        :class="[
          'absolute left-[calc(50%_+_2.1rem)] right-[calc(2.1rem_-_50%_-_0.75rem)] top-6 hidden h-0.5 rounded-full sm:block',
          s.status === 'done' ? 'bg-positive' : 'bg-line',
        ]"
        aria-hidden="true"
      />
      <span :class="['relative grid h-12 w-12 place-items-center rounded-2xl transition-colors', TILE[s.status]]">
        <AppIcon :name="s.icon" :size="22" :class="s.status === 'active' && state === 'running' ? 'animate-pulse' : ''" />
        <span
          v-if="s.status === 'done'"
          class="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full bg-positive text-surface ring-2 ring-surface"
          aria-hidden="true"
        >
          <AppIcon name="check" :size="12" />
        </span>
      </span>
      <span class="mt-1 text-sm font-bold">{{ s.name }}</span>
      <span class="text-[0.8rem] leading-snug text-muted">{{ s.task }}</span>
      <span class="sr-only">({{ STATUS_TEXT[s.status] }})</span>
    </li>
  </ol>
</template>
