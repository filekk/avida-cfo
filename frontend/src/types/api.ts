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
export type SyncPhase = "inbox" | "legal" | "forecast" | "negotiation" | "approval" | "briefing";
/** Fields every `phase` / `trace` event carries (stamped by the backend). */
interface StampedEvent {
  /** 1, 2, 3 … in stream order (shared by phase + trace events) */
  id: number;
  ts: IsoDateTime;
  /** ms since the sync started → animation timing */
  elapsed_ms: number;
  /** stage the event belongs to */
  phase: SyncPhase;
}
/** Progress: each of the 6 stages sends `start` then `done`, always in the order of SyncPhase. */
export interface PhaseEvent extends StampedEvent {
  type: "phase";
  status: "start" | "done";
  /** 1-based position of `phase`, `total` = 6 */
  index: number;
  total: number;
  /** already in the sync's language */
  label: string;
}
export interface TraceEvent extends StampedEvent {
  type: "trace";
  agent: AgentName;
  autonomy: Autonomy;
  /** in the sync's language (`/api/sync?lang=`) */
  message: string;
  source?: AnswerSource;
  email_id?: string;
  /** Handoff: the step is a message from `agent` to `to` (shown as "A → B"). */
  to?: AgentName;
  kind?: "handoff" | (string & {});
  /** The step is about one email – group parallel negotiations by this (one thread per partner). */
  finding_id?: string;
  partner?: string;
  /** Only on "Waiting for your approval" steps: the action card that was created. */
  action_id?: string;
}
export interface SyncResultEvent {
  type: "result";
  dashboard: Dashboard;
}
export interface SyncErrorEvent {
  type: "error";
  /** plain, localized words for the owner – show as delivered */
  message: string;
  /** "sync_running" = a check is already running (maybe in another window) – wait and try again */
  code?: "sync_running";
  /** error type only (e.g. "RuntimeError"), for diagnostics – the details stay in the server log */
  detail?: string;
}
/** GET /api/sync/trace – replay of the last sync (empty after reset). */
export interface SyncTrace {
  lang: Lang | null;
  events: (PhaseEvent | TraceEvent)[];
}

// ---- Forecast -----------------------------------------------------------------------------------
export interface SeriesPoint {
  date: IsoDate;
  balance: number;
  /** sum of incoming payments that day (≥ 0) */
  inflow: number;
  /** sum of outgoing payments that day (≤ 0) */
  outflow: number;
}
/** revenue | payroll | supplier | rent | loan | tax | other (from the bank data – translate in the UI) */
export type CashCategory = "revenue" | "payroll" | "supplier" | "rent" | "loan" | "tax" | "other" | (string & {});
export interface CategoryTotal {
  category: CashCategory;
  /** whole horizon; negative for outflows */
  total: number;
  count: number;
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
  /** every dated payment in the horizon (inflows positive, outflows negative) → chart annotations, own filters */
  events: Outflow[];
  /** biggest first */
  outflows_by_category: CategoryTotal[];
  inflows_by_category: CategoryTotal[];
  /** top 5 single payments */
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
  /** who wrote explanation_simple: the model in the sync language, `rules` in the other language */
  source?: AnswerSource;
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
/** What changes if the owner approves vs. says "Not now" – deterministic (forecast re-run). */
export interface DecisionEffects {
  min_balance?: number;
  min_date?: IsoDate;
  cost_12m?: number;
  cost_in_horizon?: number;
  credit_line?: number;
  max_interest?: number;
}
export interface DecisionOption {
  choice: "approve" | "not_now";
  label: string;
  summary: string;
  effects: DecisionEffects;
}
export interface Decision {
  recommended: "approve" | "not_now";
  /** medium = the outcome depends on the partner (e.g. a customer may still pay late) */
  certainty: "high" | "medium";
  deadline: IsoDate | null;
  deadline_reason: string | null;
  options: DecisionOption[];
}
interface ActionBase {
  id: string;
  title: string;
  why: string;
  /** one line for compact cards */
  why_short: string;
  decision: Decision;
  agent: AgentName;
  autonomy: Autonomy; // always "approval" today
  execution: "simulated";
  status: ActionStatus;
  savings_12m: number;
  /** dated savings inside the forecast horizon (EUR > 0); approved ones add up to "Saved by Avida" per period */
  savings_events?: { date: IsoDate; amount: number }[];
  source?: AnswerSource;
  result?: string; // after approve
  finding_id?: string;
  /** send_email only: supplier / customer name */
  partner?: string;
  reviewed_by?: string;
  review?: { approved: boolean; issues: string[]; rounds: number };
  /** after approve: the owner changed the draft before sending */
  edited_by_owner?: boolean;
  /** send_email, after approve: the partner's SIMULATED reply (demo data); its summary is also in `result` */
  reply?: { from: string; from_name: string; subject: string; received: IsoDate; body: string; simulated: true };
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
  /** KPIs of the start screen before the last sync → animate numbers from → to. null before the first sync. */
  kpis_previous: Kpis | null;
  /** language the model wrote in during the last sync (other language = rule-based texts); null before sync */
  sync_lang: Lang | null;
  scenarios: Scenarios;
  /** `role` / `does` in the requested language; `name` stays English (stable id). `icon` is a Lucide icon name
   *  (`chart` / `scale` / `mail`); the UI uses its own map in constants/agents.ts. */
  agents?: { name: AgentName; role: string; icon: string; does: string }[];
  analysis?: { summary: string; key_points: string[]; risk_level: "low" | "medium" | "high"; source?: AnswerSource } | null;
  findings: Finding[];
  actions: Action[];
  /** echo of `?lang=` – every backend text in this response is in this language (see docs/API.md → Languages) */
  lang: Lang;
}

// ---- Misc endpoints -----------------------------------------------------------------------------
export interface DecisionResponse {
  action: Action;
  saved_liquidity: number;
  /** counter before this decision → animate from → to */
  saved_liquidity_previous: number;
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
  /** stable id. General: overdraft | on_time | reject | no_figures | safe | big_payments.
   *  Problem chat: why | cost | on_time | tone | email | negotiate | not_now | deadline */
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
  /** problem chat only: the problem these suggestions are about */
  action_id?: string | null;
  finding_id?: string | null;
}
/** One turn of a problem chat, sent back as `history` (oldest first, max 6). */
export interface ChatTurn {
  role: "owner" | "agent";
  text: string;
}
/** POST /api/ask body */
export interface AskRequest {
  question: string;
  lang: Lang;
  action_id?: string;
  finding_id?: string;
  history?: ChatTurn[];
}
/** GET /api/actions/{id}/context, GET /api/findings/{id}/context */
export interface ProblemContext {
  lang: Lang;
  action: Action | null;
  finding: Finding | null;
  suggestions: AskSuggestions;
}
/** POST /api/actions/{id}/review – instant rule check of the owner's edited draft */
export interface DraftReview {
  action_id: string;
  approved: boolean;
  issues: string[];
  source: "rules";
}
/** POST /api/actions/{id}/redraft – a PROPOSAL; nothing changes until the owner approves with edited_body */
export interface RedraftRequest {
  /** the owner's hint; "" or omitted = "write it again" (fresh version, same facts) */
  instruction?: string;
  /** text currently in the editor (default: the agent's draft) – send it to rewrite iteratively */
  body?: string;
  lang?: Lang;
}
/** GET /api/actions/{id}/redraft/hints – chips for the Rewrite button */
export interface RedraftHint {
  id: "softer" | "firmer" | "shorter" | "formal" | "german" | "english";
  /** in the UI language */
  label: string;
  /** send unchanged as RedraftRequest.instruction */
  instruction: string;
}
export interface RedraftHints {
  action_id: string;
  /** example text for the hint input */
  placeholder: string;
  hints: RedraftHint[];
}
export interface RedraftProposal {
  action_id: string;
  /** 1, 2, 3 … per action – for "Version 2" */
  attempt: number;
  /** what the Negotiator was asked (the default text when no hint was given) */
  instruction: string;
  body: string;
  changed: boolean;
  source: AnswerSource;
  /** set when the model was unavailable ("the draft is unchanged") */
  note: string | null;
  review: { approved: boolean; issues: string[]; source: AnswerSource };
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
  party: string;
  party_type: "supplier" | "customer";
  file_name: string;
  file_type: "md" | "txt" | "pdf" | (string & {});
  size_bytes: number | null;
  pages: number | null;
  /** null for the notebook-prepared index */
  uploaded_at: IsoDateTime | null;
  extraction_seconds: number | null;
  /** llm | fallback for uploads, rules for the prepared index */
  source: AnswerSource;
  warnings_count: number;
  used_in_last_sync: boolean;
  used_by_findings: string[];
}
/** GET /api/contracts query parameters */
export type ContractSort =
  | "uploaded_at" | "party" | "title" | "start_date" | "size_bytes" | "pages"
  | "-uploaded_at" | "-party" | "-title" | "-start_date" | "-size_bytes" | "-pages";
export interface ContractQuery {
  q?: string;
  origin?: ContractOrigin;
  party_type?: "supplier" | "customer";
  sort?: ContractSort;
}
/** GET /api/contracts/{id} */
export interface ContractDetail extends Omit<ContractSummary, "clauses"> {
  aliases?: string[];
  monthly_fee?: number | null;
  fixed_price_until?: IsoDate | null;
  price_change_notice_days?: number | null;
  max_annual_increase_pct?: number | null;
  payment_terms_days?: number | null;
  changes_require_written_agreement?: boolean | null;
  clauses: Clause[];
  clause_count: number;
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
  uploaded_at: IsoDateTime;
  size_bytes: number;
  pages: number;
  extraction_seconds: number;
  source: AnswerSource;
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
