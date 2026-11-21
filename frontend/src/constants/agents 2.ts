import type { IconName } from "@/components/ui/icons";
import type { TraceEvent } from "@/types/api";

/**
 * Every agent the backend can report: icon, a one-word name for the pipeline, a short job and the
 * "what it is doing right now" line shown in the top-bar inbox box. English only – translate where shown
 * (`t(agentInfo(name).working)`), never here at module level.
 *
 * Two crews exist:
 *   current backend          Analyst · Legal · Negotiator (they hand work to each other: trace `to` + `kind: "handoff"`)
 *   older backend            Inbox → Contract → Liquidity (kept so an older deployment still renders)
 * Unknown names fall back to a neutral AI entry, so a new agent never breaks the UI.
 */
export interface AgentInfo {
  icon: IconName;
  short: string;
  task: string;
  working: string;
}

export const AGENTS: Record<string, AgentInfo> = {
  "Analyst Agent": { icon: "chart", short: "Analyst", task: "Reads emails, forecasts cash", working: "Reading emails and forecasting…" },
  "Legal Agent": { icon: "scale", short: "Legal", task: "Checks your contracts", working: "Checking your contracts…" },
  "Negotiator Agent": { icon: "mail", short: "Negotiator", task: "Drafts your replies", working: "Drafting your replies…" },
  "Inbox Agent": { icon: "inbox", short: "Inbox", task: "Reads your emails", working: "Reading your emails…" },
  "Contract Agent": { icon: "scale", short: "Contract", task: "Checks your contracts", working: "Checking your contracts…" },
  "Liquidity Agent": { icon: "chart", short: "Liquidity", task: "Updates your forecast", working: "Updating your forecast…" },
};

const FALLBACK: AgentInfo = { icon: "sparkles", short: "Agent", task: "", working: "Working…" };

export const NEW_CREW = ["Analyst Agent", "Legal Agent", "Negotiator Agent"];
export const LEGACY_CREW = ["Inbox Agent", "Contract Agent", "Liquidity Agent"];
/** The pipeline order of the current backend. */
export const AGENT_ORDER = NEW_CREW;

export const agentInfo = (name: string | null | undefined): AgentInfo => (name ? AGENTS[name] : undefined) ?? FALLBACK;
/** Unknown agent names from the backend fall back to a neutral AI icon. */
export const agentIcon = (name: string): IconName => agentInfo(name).icon;

/** A trace step that is a message from one agent to another. */
export const isHandoff = (e: TraceEvent) => e.kind === "handoff" && !!e.to;

/**
 * Which crew is at work: the older one only if one of its names shows up, otherwise the current one.
 * Agents the UI doesn't know yet are appended, so they still get a step in the pipeline.
 */
export function crewOf(events: TraceEvent[]): string[] {
  const names = events.flatMap((e) => (e.to ? [e.agent, e.to] : [e.agent]));
  const base = names.some((n) => LEGACY_CREW.includes(n)) ? LEGACY_CREW : NEW_CREW;
  return [...base, ...[...new Set(names)].filter((n) => !base.includes(n))];
}
