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

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` |
| GET | `/api/llm/health` | `{"ok":true,"models":["granite-8b"],...}` – show a small "AI online" indicator |
| GET | `/api/config` | model name, forecast days, demo "today" |
| GET | `/api/dashboard` | `Dashboard` (below) |
| GET | `/api/sync` | **Server-Sent Events** stream, ~20–40 s |
| POST | `/api/actions/{id}/approve` | body `{"edited_body": "<email text>" \| null}` → `{"action": Action, "saved_liquidity": number}` |
| POST | `/api/actions/{id}/reject` | no body → `{"action": Action, "saved_liquidity": number}` |
| GET | `/api/ask/suggestions?lang=en\|de` | clickable questions for the current situation (see "Ask your CFO") |
| POST | `/api/ask` | body `{"question": "…", "lang": "en"\|"de"}` → answer from the right agent (chip: instant, typed: 3–7 s) |
| GET | `/api/contracts` | `[ContractSummary]` – the Legal Agent's contracts (`origin`: `index` = prepared in Jupyter, `uploaded` = read live by the model) |
| POST | `/api/contracts/upload` | multipart `file` (PDF / .md / .txt, max 5 MB) → `UploadResult`, **10–20 s** (model reads it); 422 with `detail` if unreadable |
| DELETE | `/api/contracts/{id}` | removes an uploaded contract (`U-001`…), returns the new list; 404 for index contracts |
| GET | `/api/policy` | `[{action, agent, autonomy, execution}]` – the autonomy matrix |
| GET | `/api/audit` | `[{time, event, ...}]` – what happened, in order |
| POST | `/api/reset` | clears findings/actions, returns the start `Dashboard` |

## SSE `/api/sync`

```js
const es = new EventSource("/api/sync");
es.addEventListener("trace",  e => addStep(JSON.parse(e.data)));
es.addEventListener("result", e => { setDashboard(JSON.parse(e.data).dashboard); es.close(); });
es.addEventListener("error",  e => { showError(e.data ? JSON.parse(e.data).message : "Connection lost"); es.close(); });
```

`trace` event:
```json
{ "type": "trace", "agent": "Legal Agent", "autonomy": "recommendation",
  "message": "CloudHost GmbH: increase is NOT allowed by the contract (§5.2).", "source": "llm" }
```

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
  "series": [ { "date": "2026-11-20", "balance": 79000 }, … 90 items ],   // one point per day → line chart
  "largest_outflows": [ { "date", "amount", "label", "category", "counterparty" } ] }
```

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
  "agent": "Negotiator Agent", "autonomy": "approval", "execution": "simulated",
  "status": "pending",                          // pending | executed | rejected
  "savings_12m": 17640,                         // 0 for payment reminders / requests for details
  "finding_id": "mail-001",                     // send_email only: which Finding this email answers
  "payload": { "to": "billing@cloudhost.example", "body": "Subject: …\n\nDear …" },   // editable textarea
  "reviewed_by": "Legal Agent",                 // send_email only
  "review": { "approved": true, "issues": [], "rounds": 1 },   // "✔ Checked by the Legal Agent" badge; rounds 2 = was revised
  "result": "Email to … sent (simulated – nothing left the system)."                  // after approve
}
```
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

## Rules for the UI

1. Never trigger an action without an explicit click – approve/reject only.
2. Always show the autonomy badge next to agent steps and action cards.
3. Show `source: "fallback"` discreetly ("cached answer") – honesty about the AI.
4. Amounts are EUR numbers; format on the client (`Intl.NumberFormat("de-DE", {style:"currency",currency:"EUR"})`).
5. Dates are ISO `YYYY-MM-DD`.

## Deployment of the frontend

The production image builds `frontend/` with `npm install && npm run build` and serves `frontend/dist`
from FastAPI (same origin → no CORS, no extra route). Keep: `frontend/package.json` with a `build`
script that outputs to `dist/`, assets under `dist/assets/`. Any framework works.
