# Avida CFO – API contract (backend ↔ frontend)

Live backend (real Granite model on OpenShift AI):
`https://avida-cfo-avida-cfo.apps.ocp.8c6kp.sandbox2571.opentlc.com`

Interactive docs (try every endpoint in the browser): **`/docs`** · machine-readable: `/openapi.json`

> Developing the frontend locally? Don't run the backend – proxy `/api` to the cluster.
> Vite: `server: { proxy: { "/api": { target: "<live URL>", changeOrigin: true, secure: false } } }`

## Flow the UI has to support

```
GET /api/dashboard          → render start screen (forecast, no findings yet)
GET /api/sync  (SSE)        → show agent steps live ("trace" events) … final "result" = new dashboard
POST /api/actions/{id}/approve | reject   → owner decides, UI updates action + "saved" counter
GET /api/policy, /api/audit → "who may do what" page, history page
POST /api/reset             → back to start (use before every demo run)
```

## Endpoints

Every endpoint marked **`?lang`** takes `lang=en|de` (default `en`, `422` otherwise) – see [Languages](#languages).

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` |
| GET | `/api/llm/health` | `{"ok":true,"models":["granite-8b"],...}` – show a small "AI online" indicator |
| GET | `/api/config` | model name, forecast days, demo "today" |
| GET | `/api/tracing/health` | diagnostics only (not for the UI): is MLflow tracing of the agents on? `{"enabled":true,"experiment":"avida-cfo-agents",...}` |
| GET | `/api/dashboard` **`?lang`** | `Dashboard` (below) |
| GET | `/api/sync` **`?lang`** | **Server-Sent Events** stream, ~20–40 s: `phase` → `trace` … → `result` |
| GET | `/api/sync/trace` | `{lang, events: [...]}` – replay of the last sync's `phase` / `trace` events (empty after reset) |
| POST | `/api/actions/{id}/approve` **`?lang`** | body `{"edited_body": "<email text>" \| null}` → `{"action": Action, "saved_liquidity": number, "saved_liquidity_previous": number}` |
| POST | `/api/actions/{id}/reject` **`?lang`** | no body → same as approve |
| GET | `/api/actions/{id}/context` **`?lang`** | `ProblemContext` – one problem view: action (with `decision`), its finding, chat suggestions |
| GET | `/api/findings/{id}/context` **`?lang`** | `ProblemContext` for a finding (also findings without an action, e.g. an allowed increase) |
| POST | `/api/actions/{id}/review` | body `{"body": "…", "lang"}` → `DraftReview` – **instant** rule check of the owner's edited draft (no model) |
| POST | `/api/actions/{id}/redraft` | Rewrite button: body `{"instruction"?: "make it softer", "body"?: "…", "lang"}` → `RedraftProposal`, 3–8 s. Empty instruction = "write it again". **Proposal only** – nothing changes until approve |
| GET | `/api/actions/{id}/redraft/hints` | `?lang` → `RedraftHints` (chips + placeholder for the Rewrite button) |
| GET | `/api/ask/suggestions?lang=en\|de[&action_id=\|&finding_id=]` | clickable questions; with an id: decision helpers for that one problem |
| POST | `/api/ask` | body `{"question", "lang", "action_id"?, "finding_id"?, "history"?}` → answer from the right agent (chip: instant, typed: 3–7 s) |
| GET | `/api/contracts?q=&origin=&party_type=&sort=` | `[ContractSummary]` – files page: filter + sort on the server (see Contracts) |
| GET | `/api/contracts/{id}` | `ContractDetail` – extracted terms, all clauses, file metadata, where it was used |
| GET | `/api/contracts/{id}/file[?download=true]` | the original document (inline preview or download) |
| POST | `/api/contracts/upload` | multipart `file` (PDF / .md / .txt, max 5 MB) → `UploadResult`, **10–20 s** (model reads it); 422 with `detail` if unreadable |
| DELETE | `/api/contracts/{id}` | removes an uploaded contract (`U-001`…), returns the new list; 404 for index contracts |
| GET | `/api/policy` **`?lang`** | `[{action, agent, autonomy, execution}]` – the autonomy matrix |
| GET | `/api/audit` | `[{time, event, ...}]` – what happened, in order |
| POST | `/api/reset` **`?lang`** | clears findings/actions/audit/trace **and uploaded contracts**, returns the start `Dashboard` |

## Languages

`?lang=de` returns every text the backend writes in German: `headline`, trace messages, phase labels, action
`title` / `why` / `why_short` / `result`, `decision` labels and summaries, `explanation_simple`, check `check` /
`detail`, `impact.calculation`, credit `calculation` / `note`, `analysis.summary` / `key_points`, policy `action`,
agent `role` / `does`, draft-review issues.

- **One sync, both languages.** Rule-based texts exist in both languages; switching language only needs
  `GET /api/dashboard?lang=…` – nothing re-runs.
- **Model texts exist in one language** – the `lang` of the sync (`Dashboard.sync_lang`). In the other language
  those fields (`explanation_simple`, `analysis.summary`) hold the rule-based text and their `source` is `"rules"`.
- **Trace messages** are written in the sync's `lang` only (they are live). Start the sync with the UI language.
- **Never translated:** draft emails (`payload.body` – they go to the partner), original emails, contract quotes,
  cash-flow labels from the bank data (e.g. "Payroll (12 employees)"), and the model's own review remarks.
- `Dashboard.lang` echoes the requested language.

## SSE `/api/sync`

```js
const es = new EventSource("/api/sync?lang=de");
es.addEventListener("phase",  e => setProgress(JSON.parse(e.data)));   // optional – progress bar
es.addEventListener("trace",  e => addStep(JSON.parse(e.data)));
es.addEventListener("result", e => { setDashboard(JSON.parse(e.data).dashboard); es.close(); });
es.addEventListener("error",  e => { showError(e.data ? JSON.parse(e.data).message : "Connection lost"); es.close(); });
```

`phase` event (6 stages, each `start` then `done`, always in this order):
```json
{ "type": "phase", "id": 1, "ts": "2026-11-21T10:10:09.913+00:00", "elapsed_ms": 0,
  "phase": "inbox", "status": "start", "index": 1, "total": 6, "label": "Reading the inbox" }
```
`phase`: `inbox` → `legal` → `forecast` → `negotiation` → `approval` → `briefing`.

`trace` event:
```json
{ "type": "trace", "id": 12, "ts": "2026-11-21T10:10:11.402+00:00", "elapsed_ms": 1489, "phase": "legal",
  "agent": "Legal Agent", "autonomy": "recommendation",
  "message": "CloudHost GmbH: the increase is NOT allowed by the contract (§5.2).", "source": "llm",
  "finding_id": "mail-001", "partner": "CloudHost GmbH" }
```
- `id`: 1, 2, 3 … in stream order (shared with `phase` events) · `ts` / `elapsed_ms`: when it happened (animation timing).
- `finding_id` + `partner` (optional): the step is about one email. During `negotiation` the negotiations of
  different partners run **in parallel** and interleave – group by `finding_id` to show one thread per partner.
- `action_id` (only on the "Waiting for your approval" steps): the action card this step created.
- `email_id` (inbox steps): the email that was read.

Handoff between agents (show as an arrow / chat bubble from one agent to another):
```json
{ "type": "trace", "agent": "Legal Agent", "to": "Negotiator Agent", "kind": "handoff", "autonomy": "analyzed",
  "message": "Use §5.2 – Prices are fixed until 31 Aug 2027, but the increase starts on 01 Jan 2027." }
```

- `agent`: `Analyst Agent` | `Legal Agent` | `Negotiator Agent` (details in `Dashboard.agents`)
- `to` + `kind: "handoff"` (optional): the step is a message from `agent` to `to`.

### The three agents and how they collaborate

| Agent | Role | Does |
|---|---|---|
| 📊 Analyst Agent | numbers | reads the inbox (EN + DE), forecasts 90 days in 3 scenarios, sizes the credit line, writes the briefing |
| ⚖️ Legal Agent | lawyer | checks each change against the supplier / customer contract; **reviews every draft email** before the owner sees it |
| ✉️ Negotiator Agent | writer | drafts replies from the lawyer's clause + the analyst's figures; revises once if the lawyer finds issues |

The demo inbox (6 emails) produces every kind of finding:

| Email | Kind | Verdict → recommendation | Negotiator writes |
|---|---|---|---|
| CloudHost +15% (breaks price guarantee) | `price_change` | `violates` → `reject` | rejection |
| PaperPro +3.5% (within cap) | `price_change` | `allowed` → `accept` | – |
| Bauer pays invoice 30 days late (SAP migration) | `payment_delay` | `violates` → `remind` | friendly payment reminder |
| Stahlhandel Nord +6% (**German email**) | `price_change` | `allowed` → `accept` | – |
| IT-Service Kraus "prices go up", **no figures** | `price_change`, `figures_stated: false` | `unclear` → `review` | asks for the exact prices |
| IHK newsletter | – (ignored) | – | – |

Typical sequence of trace events:
```
Analyst  reads 6 emails → 4 price changes, 1 late payment, 1 ignored ("no figures – I won't guess")
Analyst  → Legal       "Please check 5 change(s) …"
Legal    verdicts (one line per change)
Legal    → Analyst     "Verdicts: …"
Analyst  forecast, lowest balance
── negotiations run IN PARALLEL, events of different partners interleave (each message names the partner) ──
Analyst  → Negotiator  figures            Legal → Negotiator  clause + violations
Negotiator "Draft to X written."          Negotiator → Legal "Please review my draft to X …"
Legal    approved   (or: Legal → Negotiator "found issues…", Negotiator revised, Legal approved)
──
Negotiator ✋ waiting for approval (one per email)    Analyst ✋ waiting for approval (overdraft)
Analyst  briefing ready
```
A second `GET /api/sync` while one is running gets an `error` event ("already running") – disable the button while syncing.
- `autonomy` (**must be visible in the UI – required by the challenge**):

| value | label for the UI | meaning |
|---|---|---|
| `analyzed` | 🔍 Analysed by agent | agent did it on its own |
| `recommendation` | 💡 Recommendation | agent suggests, owner decides |
| `approval` | ✋ Needs your approval | nothing happens without a click |
| `simulated` | 🧪 Simulated execution | executed, but nothing leaves the system |

- `source` (optional): `llm` = answered by the model, `fallback` = cached answer (model unavailable), `rules` = deterministic.

## `Dashboard`

```jsonc
{
  "company": { "name": "Müller Feinmechanik GmbH", "owner": "Petra Müller", "currency": "EUR" },
  "today": "2026-11-20",
  "headline": "You're safe for the next 63 days. From 22 January your balance falls below your safety cushion, and on 03 February your account would be 27,882 EUR overdrawn.",
  "kpis": {                                            // before sync: days_safe 73, min_balance 11000
    "balance_today": 93000, "days_safe": 63,
    "min_balance": -27882, "min_date": "2027-02-03",   // can be NEGATIVE (= overdrawn) → show in red
    "safety_buffer": 15000, "saved_liquidity": 0        // grows after approvals
  },
  "kpis_previous": { …same keys… },                   // KPIs of the start screen before this sync → animate from → to;
                                                       // null before the first sync
  "lang": "en",                                        // echo of ?lang
  "sync_lang": "en",                                   // language the model wrote in during the last sync; null before sync
  "agents": [ { "name": "Analyst Agent", "role": "Analyst", "icon": "📊", "does": "…" }, … ],   // for an "our team" panel
  "analysis": {                                        // Analyst's briefing; null before sync
    "summary": "…max 3 short sentences written by the model (checked: only numbers from key_points)…",
    "key_points": [ "Bauer Maschinenbau AG wants to pay 38,000 EUR 30 days late (2027-02-04 instead of 2027-01-05). …",
                    "If you follow the advice, your lowest balance is -27,882 EUR on 2027-02-03 – your account would be overdrawn …",
                    "Payroll (12 employees): 46,000 EUR on 2027-01-28 would not be covered without an overdraft.",
                    "Rejecting the CloudHost GmbH increase keeps 17,640 EUR per year in your company.", … ],  // exact, computed
    "risk_level": "high",                              // low | medium | high → colour
    "source": "llm"
  },
  "scenarios": {                                       // before sync only "current" exists
    "current":     Forecast,                           // no price changes
    "if_accepted": Forecast,                           // owner accepts every increase
    "recommended": Forecast                            // owner follows Avida
  },
  "findings": [Finding],
  "actions":  [Action]
}
```

`Forecast`
```jsonc
{ "start_balance": 93000, "end_balance": 92916, "min_balance": 10958, "min_date": "2027-02-03",
  "buffer": 15000, "first_breach_date": "2027-02-01", "last_breach_date": "2027-02-04",
  "days_safe": 73, "horizon_days": 90,
  "series": [ { "date": "2026-11-20", "balance": 79000, "inflow": 0, "outflow": -14000 }, … 90 items ],
                                                         // one point per day → line chart; inflow/outflow → bars
  "events": [ { "date", "amount", "label", "category", "counterparty" } ],   // EVERY payment in the horizon
                                                         // → chart annotations ("why does it drop here?"), own filters
  "outflows_by_category": [ { "category": "payroll", "total": -156000, "count": 4 }, … ],  // biggest first, negative
  "inflows_by_category":  [ { "category": "revenue", "total": 300000, "count": 10 }, … ],
  "largest_outflows": [ { "date", "amount", "label", "category", "counterparty" } ] }    // top 5 single payments
```
Categories: `revenue`, `payroll`, `supplier`, `rent`, `loan`, `tax`, `other` (from the bank data – translate in the UI).

`Finding` (one per detected price change or late payment – the split screen)
```jsonc
{
  "id": "mail-001",
  "kind": "price_change",                                                    // price_change | payment_delay
  "email": { "from", "from_name", "subject", "received", "body" },          // LEFT side (body may be German)
  "extraction": { "kind": "price_change", "party": "CloudHost GmbH", "supplier": "CloudHost GmbH",
                  "figures_stated": true,      // false → email had no verifiable figures, nothing calculated
                  "old_monthly": 9800, "new_monthly": 11270,
                  "increase_pct": 15.0, "monthly_delta": 1470, "effective_date": "2027-01-01",
                  "summary": "CloudHost raises hosting by 15% from 1 Jan 2027." },
  "contract": {                                                              // RIGHT side
    "verdict": "violates",            // violates | allowed | unclear
    "explanation_simple": "…plain-language explanation…",
    "clause_id": "§5.2", "quote": "The fees under §5.1 are fixed for 24 months …",
    "clause": { "id": "§5.2", "page": 3, "title": "Price guarantee", "text": "…" },
    "contract": { "title": "Master Services Agreement – Business ERP Hosting", "file": "contracts/cloudhost_msa.md", … },
    "source": "llm",                  // who wrote explanation_simple (rules in the other language, see Languages)
    "checks": [ { "check": "Price guarantee period", "passed": false, "detail": "Prices are fixed until 31 Aug 2027, but …", "clause_id": "§5.2" },
                { "check": "Notice period",          "passed": false, "detail": "42 days' notice given, 90 days required.", "clause_id": "§5.3" } ]
  },
  "impact": { "monthly": 1470, "in_horizon": 2940, "next_12_months": 17640,
              "calculation": "11,270.00 − 9,800.00 = 1,470.00 EUR/month × 12 = 17,640.00 EUR/year" },  // "Show calculation"
  "recommendation": "reject",         // reject | accept | remind (late payment) | review (cannot check)
  "action_id": "act-1"                // only when there is something to approve
}
```

`Finding` with `kind: "payment_delay"` – same shape, different `extraction` / `impact`:
```jsonc
{ "id": "mail-004", "kind": "payment_delay",
  "extraction": { "kind": "payment_delay", "party": "Bauer Maschinenbau AG", "customer": "Bauer Maschinenbau AG",
                  "figures_stated": true, "invoice": "RE-2026-1187", "amount": 38000,
                  "due_date": "2027-01-05", "new_payment_date": "2027-02-04", "days_late": 30, "summary": "…" },
  "contract": { "verdict": "violates", "clause_id": "§7.1", "contract": { "title": "Framework Agreement – Precision Parts (customer contract)", … },
                "checks": [ { "check": "Agreed payment date", "passed": false, … }, { "check": "Change of payment date", "passed": false, … } ], … },
  "impact": { "monthly": 0, "in_horizon": 0, "next_12_months": 0,          // costs nothing – it moves cash
              "days_late": 30, "min_balance_on_time": 10118, "min_balance_late": -27882,
              "lowest_balance_effect": 38000,                              // "your lowest balance is 38,000 EUR lower"
              "calculation": "EUR 38,000.00 arrives 30 days later (05 Jan 2027 → 04 Feb 2027). …" },
  "recommendation": "remind", "action_id": "act-2" }
```
When `figures_stated` is `false` (IT-Service Kraus): `verdict: "unclear"`, `checks: []`, `contract: null`,
`impact.calculation: "The email gives no figures – nothing to calculate yet."` → show "no figures given – Avida asks".

`Action` (cards with Approve / Not now)
```jsonc
{
  "id": "act-1", "type": "send_email",          // send_email | credit_application
  "title": "Reject the 15% price increase from CloudHost GmbH",
  "why": "…one-paragraph reason…",
  "why_short": "The contract does not allow it. Saves 17,640 EUR over 12 months.",   // one line for compact cards
  "partner": "CloudHost GmbH",                  // send_email only
  "decision": Decision,                         // what changes if you approve vs. "Not now" (below)
  "agent": "Negotiator Agent", "autonomy": "approval", "execution": "simulated",
  "status": "pending",                          // pending | executed | rejected
  "savings_12m": 17640,                         // 0 for payment reminders / requests for details
  "finding_id": "mail-001",                     // send_email only: which Finding this email answers
  "payload": { "to": "billing@cloudhost.example", "body": "Subject: …\n\nDear …" },   // editable textarea
  "reviewed_by": "Legal Agent",                 // send_email only
  "review": { "approved": true, "issues": [], "rounds": 1 },   // "✔ Checked by the Legal Agent" badge; rounds 2 = was revised
  "result": "Email to … sent (simulated – nothing left the system).",                 // after approve
  "edited_by_owner": true                       // after approve, only if the owner changed the draft
}
```

`Decision` – decision support for an action card. Deterministic: the forecast is re-run with / without the change.
```jsonc
{ "recommended": "approve",                     // approve | not_now
  "certainty": "high",                          // high | medium (medium = depends on the partner, e.g. a customer may still pay late)
  "deadline": "2027-01-01",                     // decide before … (null if none)
  "deadline_reason": "The new price would be invoiced from this date.",
  "options": [
    { "choice": "approve", "label": "Send the rejection",
      "summary": "CloudHost GmbH is told that §5.2 excludes the increase. You keep paying 9,800 EUR per month; …",
      "effects": { "min_balance": -27882, "min_date": "2027-02-03", "cost_12m": 0, "cost_in_horizon": 0 } },
    { "choice": "not_now", "label": "Not now",
      "summary": "Without an objection CloudHost GmbH will likely invoice 11,270 EUR from 01 Jan 2027: …",
      "effects": { "min_balance": -29352, "min_date": "2027-02-03", "cost_12m": 17640, "cost_in_horizon": 2940 } } ] }
```
`effects` keys (all optional, numbers in EUR / ISO dates): `min_balance`, `min_date`, `cost_12m`, `cost_in_horizon`,
`credit_line`, `max_interest`. Request for details (no figures) has no `effects`.
For `credit_application` (agent `Analyst Agent`) the payload is:
```jsonc
{ "product": "Business overdraft facility (Kontokorrentkredit)", "bank": "Commerzbank (simulated offer)",
  "amount": 45000, "gap": 42882, "from": "2027-01-22", "until": "2027-02-04", "days_needed": 14,
  "indicative_rate_pct": 9.5, "max_interest_cost": 163.97,
  "calculation": "Lowest balance -27,882 EUR on … → gap 42,882 EUR, rounded up to 45,000 EUR. …", "note": "…" }
```

## Contracts: upload → live extraction → Legal Agent

The owner uploads a contract; Granite extracts the terms the Legal Agent's rules need (guided JSON on vLLM),
the backend checks them (dates parse, the monthly fee must appear in the document, every clause quote must exist
word for word – otherwise dropped and listed in `warnings`) and adds the contract to the knowledge base.
An upload for the same party replaces the earlier upload and takes precedence over the index entry.
Uploads live in memory: `POST /api/reset` (and a pod restart) removes them.
On the next `/api/sync` the Legal Agent uses it; its trace line ends with *"(contract you uploaded, terms
extracted by the model)"* and `finding.contract.contract.origin == "uploaded"`.

```jsonc
// POST /api/contracts/upload  → UploadResult
{ "source": "llm", "seconds": 14.0, "pages": 4,
  "contract": { "id": "U-001", "supplier": "Stahlhandel Nord GmbH",          // or "customer": "…"
    "title": "Rahmenliefervertrag – Stahl und Aluminium", "file": "uploads/stahlhandel.pdf", "start_date": "2025-01-01",
    "monthly_fee": 14000, "fixed_price_until": null, "price_change_notice_days": 42, "max_annual_increase_pct": 8.0,
    // customer contracts instead: "payment_terms_days": 30, "changes_require_written_agreement": true
    "clauses": [{ "id": "§6.1", "page": 4, "title": "Material price adjustment", "text": "The Supplier may adjust …" }],
    "origin": "uploaded", "extracted_by": "granite-8b (live)", "warnings": [] } }
```
```jsonc
// GET /api/contracts  → [ContractSummary]   (default order: uploads newest first, then the index)
[ { "id": "U-001", "supplier": "CloudHost GmbH", "title": "…", "file": "uploads/cloudhost_msa.md",
    "start_date": "2025-09-01", "origin": "uploaded", "extracted_by": "granite-8b (live)", "warnings": [],
    "party": "CloudHost GmbH", "party_type": "supplier",         // supplier | customer
    "file_name": "cloudhost_msa.md", "file_type": "md",          // md | txt | pdf
    "size_bytes": 1385, "pages": 7,
    "uploaded_at": "2026-11-21T10:10:09+00:00",                  // null for the prepared index
    "extraction_seconds": 14.0, "source": "llm",                 // llm | fallback (uploads) · rules (index)
    "warnings_count": 0,
    "clauses": 4,                                                // number of clauses, not the clauses themselves
    "used_in_last_sync": true, "used_by_findings": ["mail-001"] },
  { "id": "C-004", "customer": "Bauer Maschinenbau AG", "title": "…", "file": "contracts/customers/bauer_framework.md",
    "start_date": "2025-03-01", "origin": "index", "party_type": "customer", "uploaded_at": null, … } ]
```
Query parameters (all optional, combine freely):

| Param | Values |
|---|---|
| `q` | text in party, title or file name (case-insensitive, max 100 chars) |
| `origin` | `index` \| `uploaded` |
| `party_type` | `supplier` \| `customer` |
| `sort` | `uploaded_at`, `party`, `title`, `start_date`, `size_bytes`, `pages`; prefix `-` = descending. Empty values (e.g. `uploaded_at` of the index) always go last |

The list is small – filtering on the client is fine too; the parameters exist so bookmarks / URLs can carry them.

`GET /api/contracts/{id}` → `ContractDetail`: everything in `ContractSummary`, plus the extracted terms
(`monthly_fee`, `fixed_price_until`, `price_change_notice_days`, `max_annual_increase_pct` / `payment_terms_days`,
`changes_require_written_agreement`), `aliases`, `clauses` as **full list** and `clause_count`.

`GET /api/contracts/{id}/file` → the original document (`text/markdown`, `text/plain` or `application/pdf`),
`Content-Disposition: inline`; `?download=true` → `attachment`. Uploaded files live in memory: gone after reset.
The same extraction code (`backend/app/extraction.py`) is benchmarked in `notebooks/contract_extraction.ipynb`.

## Ask your CFO

The owner asks in plain language; the backend routes the question to the right agent (numbers → Analyst,
contracts → Legal, emails → Negotiator), which answers **only from the numbers already computed**. Every number in
the answer is checked; if the model is down or invents something, a prepared answer is used (`source: "fallback"`).
`lang` = the language selected on the site; suggestions **and** answers come in that language.

```
GET /api/ask/suggestions?lang=de
```
```jsonc
{ "lang": "de",
  "note": "Nach dem Abgleich Ihres Posteingangs erscheinen genauere Fragen.",   // only before sync, else null
  "suggestions": [ { "id": "overdraft", "question": "Warum brauche ich einen Kontokorrentkredit?", "agent": "Analyst Agent" }, … ] }
```
Before sync: `safe`, `big_payments`. After sync (up to 4, fixed order): `overdraft`, `on_time` (late customer),
`reject` (Legal), `no_figures` (Negotiator), then `safe`, `big_payments`. Re-fetch after every sync, reset and language switch.

```
POST /api/ask   {"question": "Warum brauche ich einen Kontokorrentkredit?", "lang": "de"}
```
```jsonc
{ "question": "…", "lang": "de",
  "agent": "Analyst Agent",          // who answered → show the agent's icon/name next to the answer
  "answer": "Zwischen dem 22.01.2027 und …",
  "source": "llm",                   // rules = clicked suggestion (prepared answer, instant)
                                     // llm = typed question answered by the model; fallback → "cached answer"
  "in_data": true,                   // false = question not answerable from company data → polite refusal text;
                                     //         show the suggestions below it
  "note": null, "suggestions": [ … ] // same as GET /api/ask/suggestions – handy for follow-up chips
}
```
- Send the suggestion's `question` text unchanged when a chip is clicked – the backend recognises it and returns the
  prepared, always-correct answer **instantly** (`source: "rules"`). Typed questions go to the model.
- `422` if `lang` is not `en`/`de` or the question is empty / longer than 500 characters.
- Typed questions take 3–7 s → show a "thinking…" state; one request at a time is enough.

### Problem chat (one action card / finding)

Add `action_id` **or** `finding_id` to talk about one problem. The answer then uses only that problem's facts
(email, contract clause and checks, calculation, the draft, the `decision` options) and the suggestions become
decision helpers:

```
GET /api/ask/suggestions?lang=en&action_id=act-1
```
```jsonc
{ "lang": "en", "note": null, "action_id": "act-1", "finding_id": "mail-001",
  "suggestions": [ { "id": "why",      "question": "Why can I reject the CloudHost GmbH increase?", "agent": "Legal Agent" },
                   { "id": "cost",     "question": "What does it cost me if I accept?",            "agent": "Analyst Agent" },
                   { "id": "not_now",  "question": "What happens if I do nothing?",                "agent": "Analyst Agent" },
                   { "id": "deadline", "question": "By when should I decide?",                     "agent": "Analyst Agent" } ] }
```
Suggestion ids per problem (max 4): reject → `why`, `cost`, `not_now`, `deadline` · late payment → `why`, `on_time`,
`tone`, `not_now` · no figures → `why`, `email`, `not_now`, `deadline` · overdraft → `why`, `cost`, `not_now`, `deadline` ·
allowed increase (finding without action) → `why`, `cost`, `negotiate`. `not_now` / `deadline` disappear once the action is decided.

```
POST /api/ask  {"question": "And what would I pay then?", "lang": "en", "action_id": "act-1",
                "history": [ {"role": "owner", "text": "Should I reject it?"}, {"role": "agent", "text": "Yes – §5.2 …"} ]}
```
- `history`: the last turns of **this** conversation, oldest first, max 6 (the model sees the last 4). Only for
  follow-ups – the backend keeps no chat state. `role`: `owner` | `agent`.
- The response has the same shape as before plus `action_id` / `finding_id`; `suggestions` are the scoped ones.
- Chips are instant (`source: "rules"`); typed questions use the model with the same number guard and fallback.
- `404` for an unknown `action_id` / `finding_id` (e.g. after a reset – re-fetch the dashboard).
- Answers are not streamed on purpose: every number is checked **before** the owner sees it. Show a "thinking…"
  state with the routed agent instead.

`GET /api/actions/{id}/context` (and `/api/findings/{id}/context`) → `ProblemContext` – one request for a
problem view:
```jsonc
{ "lang": "en", "action": Action | null, "finding": Finding | null, "suggestions": { …same as above… } }
```

## Owner tools on a draft email

```
POST /api/actions/act-1/review   {"body": "<text in the editor>", "lang": "de"}     → instant, no model
```
```jsonc
{ "action_id": "act-1", "approved": false, "source": "rules",
  "issues": [ "Die E-Mail verweist nicht auf §5.2 des Vertrags.", "Die E-Mail verrät interne Finanzinformationen." ] }
```
Same rules the Legal Agent applies to the Negotiator: clause cited, agreed price / invoice amount stated, no
`[placeholder]`, no internal finance (liquidity, overdraft …). Call it while the owner edits (debounced) and show the
issues next to the editor – approving is still allowed, it is the owner's decision.

```
POST /api/actions/act-1/redraft   {"instruction": "Make it softer", "body": "<optional: text in the editor>", "lang": "en"}
```
```jsonc
{ "action_id": "act-1", "attempt": 1,          // 1, 2, 3 … per action ("Version 2")
  "instruction": "Make it softer",             // what the Negotiator was asked (default text when no hint)
  "body": "Subject: …", "changed": true, "source": "llm",
  "note": null,                                // model down → "…the draft is unchanged.", source "fallback", changed false
  "review": { "approved": true, "issues": [], "source": "llm" } }   // Legal Agent's review of the proposal
```
- This is the back-end of the **Rewrite button** ("write the email again, with a hint from the owner").
- `instruction` is **optional**: empty / omitted = "write it again" (a fresh version with the same facts).
  Max 300 characters. The email keeps its language unless the owner asks for another one.
- Iterate: send the text currently in the editor as `body`, so the next rewrite builds on the last proposal.
- Safety net: a rewrite that loses the clause / amount (or adds a placeholder or internal finance) gets one fix
  round; if it is still broken, the editor's text comes back unchanged (`changed: false`, `source: "fallback"`,
  `note` says why). Chatty preambles ("Sure! Here is …") and ``` fences are stripped.
- **A proposal only**: the action is not changed and nothing is sent. Put `body` into the editor; the owner approves
  with `edited_body` as usual (`Action.edited_by_owner` becomes `true`). Every proposal is logged in `/api/audit`
  (`redraft_proposed`).
- 3–8 s with the model. `409` for an action that is already decided or is not an email (overdraft). `404` unknown id.
- **Illegal / deceptive requests** ("scam them for 1 million dollars", fraud, fake claims, blackmail, bribery …) →
  `422 {detail}` with a localized message ("The AI can't help with that …"); the draft is not touched. A rules screen
  (EN + DE) refuses clear cases instantly without the model; the Negotiator answers `REFUSED` for the rest. Both are
  logged in `/api/audit` as `redraft_refused`. The UI shows `detail` next to the rewrite field.

```
GET /api/actions/act-1/redraft/hints?lang=de     → chips for the Rewrite button
```
```jsonc
{ "action_id": "act-1", "placeholder": "z. B. „Erwähne, dass wir seit 5 Jahren Kunde sind“",
  "hints": [ { "id": "softer",  "label": "Freundlicher", "instruction": "Make the tone friendlier and warmer; …" },
             { "id": "firmer",  "label": "Bestimmter",   "instruction": "…" },
             { "id": "shorter", "label": "Kürzer",       "instruction": "…" },
             { "id": "formal",  "label": "Förmlicher",   "instruction": "…" },
             { "id": "german",  "label": "Auf Deutsch",  "instruction": "…" },
             { "id": "english", "label": "Auf Englisch", "instruction": "…" } ] }
```
Send a chip's `instruction` unchanged as the redraft `instruction` (or let the owner type their own hint). Same
`404` / `409` as redraft.

## Errors and demo safety nets

- SSE `error` event: `message` is plain, localized text for the owner (show it as is). `code: "sync_running"` = another
  window is already checking the inbox (wait and retry); `detail` carries the technical reason for other failures.
- `POST /api/ask`: `history` is never rejected – only the last 6 turns are used, each clipped to 2000 characters.
- `approve` with a blank `edited_body` keeps the reviewed draft (a cleared editor never sends an empty email).
- Model down / timing out on every endpoint → the backend answers from canned data for `LLM_BREAKER_S` seconds
  (default 45) instead of waiting for each call's timeout; those answers are `source: "fallback"` as usual.
- A demo email the model reads differently from the checked reading (wrong kind, missed figures) uses the checked
  reading (`source: "fallback"`). A negotiated draft that still breaks a hard rule after two rounds is replaced by
  the checked template (`source: "fallback"`).

## Rules for the UI

1. Never trigger an action without an explicit click – approve/reject only.
2. Always show the autonomy badge next to agent steps and action cards.
3. Show `source: "fallback"` discreetly ("cached answer") – honesty about the AI.
4. Amounts are EUR numbers; format on the client (`Intl.NumberFormat("de-DE", {style:"currency",currency:"EUR"})`).
5. Dates are ISO `YYYY-MM-DD`; timestamps (`ts`, `uploaded_at`, `created`, `decided`) are ISO date-times in UTC.
6. Send `?lang=` with the UI language (dashboard, sync, decisions, policy, reset) – see [Languages](#languages).

## Deployment of the frontend

The production image builds `frontend/` with `npm install && npm run build` and serves `frontend/dist`
from FastAPI (same origin → no CORS, no extra route). Keep: `frontend/package.json` with a `build`
script that outputs to `dist/`, assets under `dist/assets/`. Any framework works.
