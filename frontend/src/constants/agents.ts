import type { IconName } from "@/components/ui/icons";
import type { AgentName } from "@/types/api";

/** The three agents in pipeline order, each with its icon and a 3-word job description. */
export const AGENTS: Record<AgentName, { icon: IconName; task: string }> = {
  "Inbox Agent": { icon: "mail", task: "Reads your emails" },
  "Contract Agent": { icon: "scale", task: "Checks your contracts" },
  "Liquidity Agent": { icon: "chart", task: "Updates your forecast" },
};

export const AGENT_ORDER: AgentName[] = ["Inbox Agent", "Contract Agent", "Liquidity Agent"];

/** Unknown agent names from the backend fall back to a neutral AI icon. */
export const agentIcon = (name: string): IconName => AGENTS[name as AgentName]?.icon ?? "sparkles";
