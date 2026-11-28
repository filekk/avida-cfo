import type { Action, Dashboard, Scenarios } from "@/types/api";

/**
 * "Saved by Avida" maths for the overview (KPI card, sidebar chart, the loss strip under the forecast).
 * The UI never invents money: everything comes from the backend's deterministic numbers –
 *   - `savings_12m` per action and `kpis.saved_liquidity` (12-month figures, the official total),
 *   - `savings_events` per action: dated savings inside the forecast horizon (a rejected increase each month, a price
 *     kept after asking, overdraft interest no longer needed). Each approval adds its own → the 90-day amount grows
 *     with every OK, not only with the decision that changes the forecast lines,
 *   - the two forecast scenarios: `recommended` (follow Avida) vs `if_accepted` (accept every price increase =
 *     "without Avida"). Their gap on a given day = money Avida keeps for you up to that day (fallback without events).
 */

/** Money-saving actions (an overdraft or a reminder saves nothing directly). */
const moneyActions = (actions: Action[]) => actions.filter((a) => a.savings_12m > 0);
const sum = (actions: Action[]) => actions.reduce((s, a) => s + a.savings_12m, 0);

/** 12-month savings still waiting for the owner's click. */
export const pendingSavings12m = (actions: Action[]) => sum(moneyActions(actions).filter((a) => a.status === "pending"));

/** Money you would NOT have without Avida by day `i` (index into the forecast series, 0 = today). ≥ 0. */
export function gapAt(s: Scenarios, i: number): number {
  const withAvida = s.recommended?.series[i]?.balance;
  const without = s.if_accepted?.series[i]?.balance;
  return withAvida == null || without == null ? 0 : Math.max(0, withAvida - without);
}

/**
 * What to say next to a "Saved by Avida" amount for `days` from today. RULE: every number in the same card is for
 * the SAME period as the amount – never a yearly figure next to a 90-day amount.
 *   waiting  – something in this period waits for the owner's OK (`amount` = for this period, may be 0 when the
 *              saving only starts later → `from`)
 *   approved – saved in this period
 *   later    – approved, but it only starts after this period (`from`)
 *   none     – the inbox was checked, nothing to save · unchecked – no inbox check yet
 */
export type SavingsStatus =
  | { kind: "waiting"; amount: number; from: string | null }
  | { kind: "approved"; amount: number }
  | { kind: "later"; from: string | null }
  | { kind: "none" | "unchecked" };

export function savingsStatus(d: Dashboard, days: number): SavingsStatus {
  const { saved, waiting } = savingsForPeriod(d, days);
  const from = firstSavingDate(d.scenarios);
  if (pendingSavings12m(d.actions) > 0) return { kind: "waiting", amount: waiting, from };
  if (saved > 0.5) return { kind: "approved", amount: saved };
  if (d.kpis.saved_liquidity > 0) return { kind: "later", from };
  return { kind: d.scenarios.recommended ? "none" : "unchecked" };
}

/** First day on which following Avida makes a difference (ISO) – "savings start on 5 Jan". null = never. */
/** ISO date `days` after `iso` (UTC, no time zone drift). */
function addDays(iso: string, days: number): string {
  const t = new Date(`${iso}T00:00:00Z`);
  t.setUTCDate(t.getUTCDate() + days);
  return t.toISOString().slice(0, 10);
}

export function firstSavingDate(s: Scenarios): string | null {
  const series = s.recommended?.series ?? [];
  const i = series.findIndex((_, k) => gapAt(s, k) > 0.5);
  return i < 0 ? null : series[i].date;
}

/**
 * Savings for the chart period (`days` from today):
 *   - 12 months → the backend's totals as they are;
 *   - shorter → the forecast gap at the end of the period, split between "approved" and "waiting"
 *     in the same ratio as the 12-month figures (so the KPI matches what the chart shows).
 */
export function savingsForPeriod(d: Dashboard, days: number): { saved: number; waiting: number } {
  const saved12 = d.kpis.saved_liquidity;
  const waiting12 = pendingSavings12m(d.actions);
  const potential = sum(moneyActions(d.actions));
  if (days >= 365 || potential <= 0) return { saved: saved12, waiting: waiting12 };
  if (d.actions.some((a) => a.savings_events?.length)) {
    const end = addDays(d.today, days);
    const within = (a: Action) => (a.savings_events ?? []).filter((e) => e.date < end).reduce((s, e) => s + e.amount, 0);
    const of = (status: Action["status"]) => d.actions.filter((a) => a.status === status).reduce((s, a) => s + within(a), 0);
    return { saved: of("executed"), waiting: of("pending") };
  }
  const gap = gapAt(d.scenarios, days - 1);
  return { saved: (gap * saved12) / potential, waiting: (gap * waiting12) / potential };
}
