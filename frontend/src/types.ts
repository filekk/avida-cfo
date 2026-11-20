export type Autonomy = "analyzed" | "recommendation" | "approval" | "simulated";

export interface TraceEvent {
  type: "trace";
  agent: string;
  autonomy: Autonomy;
  message: string;
  source?: "llm" | "fallback" | "rules";
  to?: string;
  kind?: "handoff";
}

export interface Forecast {
  min_balance: number;
  min_date: string;
  buffer: number;
  first_breach_date: string | null;
  days_safe: number;
  horizon_days: number;
  end_balance: number;
  series: { date: string; balance: number }[];
}

export interface Clause {
  id: string;
  page: number;
  title: string;
  text: string;
}

export interface Finding {
  id: string;
  email: { from: string; from_name: string; subject: string; received: string; body: string };
  extraction: {
    supplier: string;
    old_monthly: number;
    new_monthly: number;
    increase_pct: number;
    effective_date: string;
    summary: string;
  };
  contract: {
    verdict: "violates" | "allowed" | "unclear";
    explanation_simple: string;
    clause_id: string;
    quote: string;
    clause?: Clause;
    contract?: { title: string; file: string };
    checks: { check: string; passed: boolean; detail: string; clause_id: string }[];
  };
  impact: { monthly: number; in_horizon: number; next_12_months: number; calculation: string };
  recommendation: "reject" | "accept" | "review";
  action_id?: string;
}

export interface Action {
  id: string;
  type: "send_email" | "credit_application";
  title: string;
  why: string;
  agent: string;
  status: "pending" | "executed" | "rejected";
  autonomy: Autonomy;
  execution: string;
  savings_12m: number;
  source?: string;
  result?: string;
  payload: Record<string, any>;
}

export interface Dashboard {
  company: { name: string; owner: string; currency: string };
  today: string;
  headline: string;
  kpis: {
    balance_today: number;
    days_safe: number;
    min_balance: number;
    min_date: string;
    safety_buffer: number;
    saved_liquidity: number;
  };
  scenarios: { current: Forecast; if_accepted?: Forecast; recommended?: Forecast };
  findings: Finding[];
  actions: Action[];
}
