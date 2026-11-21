import type { Action, Dashboard, Scenarios } from "@/types/api";

/**
 * "Saved by Avida" maths for the overview (KPI card, sidebar chart, the loss strip under the forecast).
 * The UI never invents money: everything comes from the backend's deterministic numbers –
 *   - `savings_12m` per action and `kpis.saved_liquidity` (12-month figures, the official total),
 *   - the two forecast scenarios: `recommended` (follow Avida) vs `if_accepted` (accept every price increase =
 *     "without Avida"). Their gap on a given day = money Avida keeps for you up to that day.
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
  const gap = gapAt(d.scenarios, days - 1);
  return { saved: (gap * saved12) / potential, waiting: (gap * waiting12) / potential };
}

/**
 * Sidebar chart: the 12-month total builds up month by month (a monthly price difference comes in evenly).
 * Returns, for each of the 12 months after `startIso`'s month, its first day (ISO) and the amount saved by its end.
 */
export function monthlyBuildUp(total12m: number, startIso: string): { month: string; value: number }[] {
  const [y, m] = startIso.slice(0, 7).split("-").map(Number);
  return Array.from({ length: 12 }, (_, k) => {
    const d = new Date(y, m + k, 1); // m is 1-based → m + k = next month + k
    const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    return { month, value: (total12m * (k + 1)) / 12 };
  });
}
