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

export type FindingKind = "price_change" | "payment_delay";

export interface Finding {
  id: string;
  kind: FindingKind;
  email: { from: string; from_name: string; subject: string; received: string; body: string };
  extraction: {
    kind: FindingKind;
    party: string; // supplier or customer, canonical contract name
    summary: string;
    figures_stated: boolean; // false = the email gave no (verifiable) figures → nothing was calculated
    // price_change
    supplier?: string;
    old_monthly?: number;
    new_monthly?: number;
    increase_pct?: number;
    monthly_delta?: number;
    effective_date?: string;
    // payment_delay
    customer?: string;
    invoice?: string;
    amount?: number;
    due_date?: string;
    new_payment_date?: string;
    days_late?: number;
  };
  contract: {
    verdict: "violates" | "allowed" | "unclear";
    explanation_simple: string;
    clause_id: string;
    quote: string;
    clause?: Clause | null;
    contract?: { title: string; file: string } | null;
    checks: { check: string; passed: boolean; detail: string; clause_id: string }[];
  };
  impact: {
    monthly: number;
    in_horizon: number;
    next_12_months: number;
    calculation: string;
    // payment_delay
    days_late?: number;
    lowest_balance_effect?: number;
    min_balance_on_time?: number;
    min_balance_late?: number;
  };
  recommendation: "reject" | "accept" | "remind" | "review";
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
  finding_id?: string;
  reviewed_by?: string;
  review?: { approved: boolean; issues: string[]; rounds: number };
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
  agents?: { name: string; role: string; icon: string; does: string }[];
  analysis?: { summary: string; key_points: string[]; risk_level: "low" | "medium" | "high"; source?: string } | null;
  findings: Finding[];
  actions: Action[];
}
