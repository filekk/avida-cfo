import type { Action, Finding } from "@/types/api";

/**
 * One row in the Action center. Either an action to approve (optionally explained by the finding it came from),
 * or a finding with nothing to approve (e.g. a price change that is within the contract).
 */
export interface DecisionItem {
  key: string;
  action?: Action;
  finding?: Finding;
}

export type DecisionState = "pending" | "review" | "executed" | "rejected" | "no-action";

export function decisionState(item: DecisionItem): DecisionState {
  if (item.action) return item.action.status;
  return item.finding?.recommendation === "review" ? "review" : "no-action";
}

/** Waiting for the owner: an action to approve, or a finding the owner should check themselves. */
export const isOpenItem = (item: DecisionItem) => {
  const s = decisionState(item);
  return s === "pending" || s === "review";
};

/** Build the rows: every action (with its finding, if any) + every finding without an action. */
export function buildItems(actions: Action[], findings: Finding[]): DecisionItem[] {
  const fromActions = actions.map((a) => ({
    key: a.id,
    action: a,
    finding: findings.find((f) => f.action_id === a.id),
  }));
  const infoOnly = findings.filter((f) => !f.action_id).map((f) => ({ key: f.id, finding: f }));
  return [...fromActions, ...infoOnly];
}
