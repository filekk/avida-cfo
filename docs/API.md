# Avida CFO – API contract (backend ↔ frontend)

Live backend (real Granite model on OpenShift AI):
`https://avida-cfo-avida-cfo.apps.ocp.8c6kp.sandbox2571.opentlc.com`

Interactivee docs (try every endpoint in the browser): **`/docs`** · machine-readable: `/openapi.json`

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
{ "type": "trace", "agent": "Contract Agent", "autonomy": "recommendation",
  "message": "CloudHost GmbH: increase is NOT allowed by the contract (§5.2).", "source": "llm" }
```

- `agent`: `Inbox Agent` | `Contract Agent` | `Liquidity Agent`
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
  "headline": "You're safe for the next 73 days. Around 01 February your balance drops to 10,958 EUR – below your safety cushion of 15,000 EUR.",
  "kpis": {
    "balance_today": 93000, "days_safe": 73,
    "min_balance": 10958, "min_date": "2027-02-03",
    "safety_buffer": 15000, "saved_liquidity": 0        // grows after approvals
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

`Finding` (one per detected price change – the split screen)
```jsonc
{
  "id": "mail-001",
  "email": { "from", "from_name", "subject", "received", "body" },          // LEFT side
  "extraction": { "supplier": "CloudHost GmbH", "old_monthly": 9800, "new_monthly": 11270,
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
  "recommendation": "reject",         // reject | accept | review
  "action_id": "act-1"                // only when there is something to approve
}
```

`Action` (cards with Approve / Not now)
```jsonc
{
  "id": "act-1", "type": "send_email",          // send_email | credit_application
  "title": "Reject the 15% price increase from CloudHost GmbH",
  "why": "…one-paragraph reason…",
  "agent": "Liquidity Agent", "autonomy": "approval", "execution": "simulated",
  "status": "pending",                          // pending | executed | rejected
  "savings_12m": 17640,
  "payload": { "to": "billing@cloudhost.example", "body": "Subject: …\n\nDear …" },   // editable textarea
  "result": "Email to … sent (simulated – nothing left the system)."                  // after approve
}
```
For `credit_application` the payload is:
```jsonc
{ "product": "Business overdraft facility (Kontokorrentkredit)", "bank": "Commerzbank (simulated offer)",
  "amount": 5000, "gap": 4042, "from": "2027-02-01", "until": "2027-02-04", "days_needed": 4,
  "indicative_rate_pct": 9.5, "max_interest_cost": 5.21,
  "calculation": "Lowest balance 10,958 EUR on … → gap 4,042 EUR, rounded up to 5,000 EUR. …", "note": "…" }
```

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
