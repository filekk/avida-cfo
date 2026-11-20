import type { IconName } from "@/components/ui/icons";
import type { AgentName } from "@/types/api";

/** The three agents in pipeline order, each with its icon and a 3-word job description. */
export const AGENTS: Record<AgentName, { icon: IconName; task: string }> = {
  "Analyst Agent": { icon: "chart", task: "Reads emails, forecasts cash" },
  "Legal Agent": { icon: "scale", task: "Checks your contracts" },
  "Negotiator Agent": { icon: "mail", task: "Drafts your replies" },
};

export const AGENT_ORDER: AgentName[] = ["Analyst Agent", "Legal Agent", "Negotiator Agent"];

/** Unknown agent names from the backend fall back to a neutral AI icon. */
export const agentIcon = (name: string): IconName => AGENTS[name as AgentName]?.icon ?? "sparkles";
