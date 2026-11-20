/**
 * Types mirroring the backend ↔ frontend contract.
 * Source of truth: docs/API.md + backend/app (orchestrator.py, state.py, forecast.py, agents/*).
 * When the backend changes a field, update it HERE first – the compiler will show every place to fix.
 */

export type IsoDate = string; // "YYYY-MM-DD"
export type IsoDateTime = string; // "2026-11-20T10:00:00+00:00"

// ---- Autonomy (required by the challenge: must be visible in the UI) --------------------------
export type Autonomy = "analyzed" | "recommendation" | "approval" | "simulated";
export type AgentName = "Analyst Agent" | "Legal Agent" | "Negotiator Agent";
/** llm = answered by the model · fallback = cached answer (model down) · rules = deterministic */
export type AnswerSource = "llm" | "fallback" | "rules";

// ---- SSE /api/sync ------------------------------------------------------------------------------
export interface TraceEvent {
  type: "trace";
  agent: AgentName;
  autonomy: Autonomy;
  message: string;
  source?: AnswerSource;
  email_id?: string;
  /** Handoff: the step is a message from `agent` to `to` (shown as "A → B"). */
  to?: string;
  kind?: "handoff" | (string & {});
}
export interface SyncResultEvent {
  type: "result";
  dashboard: Dashboard;
}
export interface SyncErrorEvent {
  type: "error";
  message: string;
}

// ---- Forecast -----------------------------------------------------------------------------------
export interface SeriesPoint {
  date: IsoDate;
  balance: number;
}
export interface Outflow {
  date: IsoDate;
  amount: number;
  label: string;
  category: string;
  counterparty: string;
}
export interface Forecast {
  start_balance: number;
  end_balance: number;
  min_balance: number;
  min_date: IsoDate;
  buffer: number;
  first_breach_date: IsoDate | null;
  last_breach_date: IsoDate | null;
  days_safe: number;
  horizon_days: number;
  series: SeriesPoint[];
  largest_outflows: Outflow[];
}
/** Before the first sync only `current` exists. */
export interface Scenarios {
  current: Forecast;
  if_accepted?: Forecast;
  recommended?: Forecast;
}

// ---- Findings (one per detected price change → split screen) ---------------------------------
export interface Email {
  id?: string;
  from: string;
  from_name: string;
  subject: string;
  received: IsoDate;
  body: string;
}
export type FindingKind = "price_change" | "payment_delay";
export interface Extraction {
  kind: FindingKind;
  /** Supplier or customer, canonical contract name. */
  party: string;
  summary: string;
  /** false = the email gave no (verifiable) figures → nothing was calculated. */
  figures_stated: boolean;
  // price_change
  supplier?: string;
  old_monthly?: number;
  new_monthly?: number;
  increase_pct?: number;
  monthly_delta?: number;
  effective_date?: IsoDate;
  // payment_delay
  customer?: string;
  invoice?: string;
  amount?: number;
  due_date?: IsoDate;
  new_payment_date?: IsoDate;
  days_late?: number;
}
export type Verdict = "violates" | "allowed" | "unclear";
export interface Clause {
  id: string;
  page: number;
  title: string;
  text: string;
}
/** index = prepared offline (Jupyter / hand-labelled) · uploaded = the owner uploaded it, Granite read it live. */
export type ContractOrigin = "index" | "uploaded";
export interface ContractRef {
  id?: string;
  supplier?: string;
  /** customer contracts (late payments) have `customer` instead of `supplier` */
  customer?: string;
  title: string;
  file: string;
  start_date?: IsoDate;
  fixed_price_until?: IsoDate;
  payment_terms_days?: number;
  /** only set for uploaded contracts – show "terms extracted by the model" next to the verdict */
  origin?: ContractOrigin;
  extracted_by?: string;
}
export interface ContractCheck {
  check: string;
  passed: boolean;
  detail: string;
  clause_id: string;
}
export interface ContractResult {
  verdict: Verdict;
  explanation_simple: string;
  clause_id?: string;
  quote?: string;
  clause?: Clause | null;
  contract: ContractRef | null; // null when verdict = "unclear" (no contract found)
  checks: ContractCheck[];
}
export interface Impact {
  monthly: number;
  in_horizon: number;
  next_12_months: number;
  payments_in_horizon?: number;
  calculation: string; // shown behind "Show calculation"
  // payment_delay
  days_late?: number;
  lowest_balance_effect?: number;
  min_balance_on_time?: number;
  min_date_on_time?: IsoDate;
  min_balance_late?: number;
  min_date_late?: IsoDate;
}
export type Recommendation = "reject" | "accept" | "remind" | "review";
export interface Finding {
  id: string;
  kind: FindingKind;
  email: Email;
  extraction: Extraction;
  contract: ContractResult;
  impact: Impact;
  recommendation: Recommendation;
  action_id?: string; // only when there is something to approve
}

// ---- Actions (Approve / Not now) ----------------------------------------------------------------
export type ActionStatus = "pending" | "executed" | "rejected";
export type ActionType = "send_email" | "credit_application";

export interface EmailPayload {
  to: string;
  body: string; // editable before approval
}
export interface CreditPayload {
  product: string;
  bank: string;
  amount: number;
  gap: number;
  from: IsoDate;
  until: IsoDate;
  days_needed: number;
  indicative_rate_pct: number;
  max_interest_cost: number;
  calculation: string;
  note: string;
}
interface ActionBase {
  id: string;
  title: string;
  why: string;
  agent: AgentName;
  autonomy: Autonomy; // always "approval" today
  execution: "simulated";
  status: ActionStatus;
  savings_12m: number;
  source?: AnswerSource;
  result?: string; // after approve
  finding_id?: string;
  reviewed_by?: string;
  review?: { approved: boolean; issues: string[]; rounds: number };
  created?: IsoDateTime;
  decided?: IsoDateTime;
}
export type SendEmailAction = ActionBase & { type: "send_email"; payload: EmailPayload };
export type CreditAction = ActionBase & { type: "credit_application"; payload: CreditPayload };
export type Action = SendEmailAction | CreditAction;

// ---- Dashboard ----------------------------------------------------------------------------------
export interface Company {
  name: string;
  owner: string;
  currency: string;
}
export interface Kpis {
  balance_today: number;
  days_safe: number;
  min_balance: number;
  min_date: IsoDate;
  safety_buffer: number;
  saved_liquidity: number; // grows after approvals
}
export interface Dashboard {
  company: Company;
  today: IsoDate;
  headline: string;
  kpis: Kpis;
  scenarios: Scenarios;
  agents?: { name: string; role: string; icon: string; does: string }[];
  analysis?: { summary: string; key_points: string[]; risk_level: "low" | "medium" | "high"; source?: AnswerSource } | null;
  findings: Finding[];
  actions: Action[];
  /** PROPOSED (frontend/CONTRACT_PROPOSALS.md): language the backend wrote its texts in, echoing `?lang=`. */
  lang?: "en" | "de";
}

// ---- Misc endpoints -----------------------------------------------------------------------------
export interface DecisionResponse {
  action: Action;
  saved_liquidity: number;
}
export interface PolicyRule {
  action: string;
  agent: AgentName;
  autonomy: Autonomy;
  execution: "simulated" | "-";
}
export interface AuditEntry {
  time: IsoDateTime;
  event: "sync_started" | "sync_finished" | "approved" | "rejected" | (string & {});
  [detail: string]: unknown;
}
export interface AppConfig {
  model: string;
  llm_enabled: boolean;
  demo_fallback: boolean;
  forecast_days: number;
  today: IsoDate;
}
// ---- Ask your CFO (GET /api/ask/suggestions, POST /api/ask) -------------------------------------
export type Lang = "en" | "de";
export interface AskSuggestion {
  /** stable id: overdraft | on_time | reject | no_figures | safe | big_payments */
  id: string;
  /** already in the requested language – send it back UNCHANGED when the chip is clicked */
  question: string;
  agent: AgentName;
}
export interface AskSuggestions {
  lang: Lang;
  /** only before the first sync ("more precise questions after the inbox check"), else null */
  note: string | null;
  suggestions: AskSuggestion[];
}
export interface AskAnswer extends Omit<AskSuggestions, "lang"> {
  question: string;
  lang: Lang;
  /** who answered → show that agent's icon/name next to the answer */
  agent: AgentName;
  answer: string;
  /** rules = clicked chip (prepared, instant) · llm = typed question · fallback = "cached answer" (label it!) */
  source: AnswerSource;
  /** false = not answerable from company data → `answer` is a polite refusal; show the suggestions under it */
  in_data: boolean;
}

// ---- Contracts (GET /api/contracts, POST /api/contracts/upload, DELETE /api/contracts/{id}) ------
export interface ContractSummary {
  id: string;
  supplier?: string;
  customer?: string;
  title: string;
  file: string;
  start_date?: IsoDate | null;
  origin: ContractOrigin;
  /** uploaded only: "granite-8b (live)" or "cached answer" (model was down) */
  extracted_by?: string;
  /** uploaded only: things the owner should double-check (dropped quotes, unreadable dates…) */
  warnings?: string[];
  /** number of clauses the Legal Agent can quote */
  clauses: number;
}
export interface UploadedContract {
  id: string;
  supplier?: string;
  customer?: string;
  aliases?: string[];
  title: string;
  file: string;
  start_date: IsoDate | null;
  // supplier contracts
  monthly_fee?: number | null;
  fixed_price_until?: IsoDate | null;
  price_change_notice_days?: number | null;
  max_annual_increase_pct?: number | null;
  // customer contracts
  payment_terms_days?: number | null;
  changes_require_written_agreement?: boolean | null;
  clauses: Clause[];
  origin: "uploaded";
  extracted_by: string;
  warnings: string[];
}
export interface UploadResult {
  contract: UploadedContract;
  /** llm = read live by Granite · fallback = model down, known demo contract served from cache */
  source: AnswerSource;
  seconds: number;
  pages: number;
}

export interface LlmHealth {
  ok: boolean;
  base_url?: string;
  models?: string[];
  reason?: string;
}
