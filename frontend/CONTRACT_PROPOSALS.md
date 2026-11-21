# API contract proposals from the front-end

For the back-end team. `docs/API.md` is still the source of truth: nothing here is part of the contract until
you agree and update `docs/API.md`. The front-end is already prepared for each item and keeps working without it.

---

## 1. `lang` on every endpoint (EN / DE)

> **Status 2026-11-21: implemented by the back-end** (branch `backend/frontend-support`). See `docs/API.md` → Languages
> and `docs/FRONTEND_HANDOFF.md`. Difference from the proposal: model-written texts exist only in the sync's
> language (`Dashboard.sync_lang`); the other language gets the rule-based text.

**Why:** the UI now has an English/German switch, and every UI label is translated. Texts the backend writes
still arrive in English in German mode: the headline, agent step messages, action `title`/`why`/`result`,
`explanation_simple`, check `detail`, `calculation`, the backend-dev `analysis.summary` and `key_points`.
On `backend-dev`, `/api/ask*` already takes `lang=en|de`. This proposal extends the same parameter to the rest of the API.

**What the front-end sends today:** `?lang=en` or `?lang=de` on **every** request (`api/http.ts → apiUrl`),
including the SSE stream `/api/sync?lang=de`. FastAPI ignores unknown query parameters, so this is harmless now.
After a language switch the front-end calls `GET /api/dashboard` again.

**Proposal:**

| Item | Proposal |
|---|---|
| Parameter | `lang` = `en` \| `de`, default `en`; `422` for other values (same as `/api/ask`) |
| Endpoints | `GET /api/dashboard`, `GET /api/sync` (SSE), `POST /api/reset`, `POST /api/actions/{id}/approve` / `reject`, `GET /api/policy`, `GET /api/audit` |
| Texts in `lang` | `headline`, trace `message`, action `title` / `why` / `result`, `contract.explanation_simple`, `checks[].check` / `detail`, `impact.calculation`, `analysis.summary` / `key_points`, policy `action` |
| Echo | add `"lang": "de"` to the `Dashboard` response. The front-end uses it to decide whether to show the backend's headline or build its own (see below) |
| **Not** in `lang` | **draft emails** (`payload.body`). They go to the supplier or customer, so write them in the recipient's language, not the owner's UI language. Original email bodies and contract quotes stay verbatim |

**Front-end behaviour until then:**
- **Headline:** when `Dashboard.lang` (default `en`) differs from the UI language, the front-end builds the headline
  itself from the same forecast fields `liquidity.headline()` uses (`first_breach_date`, `days_safe`,
  `horizon_days`, `min_balance`, `buffer`). That is formatting only; no number is computed. It also covers the
  overdrawn wording from `backend-dev` (`min_balance < 0`). Code: `src/components/dashboard/headline.ts`.
- **Everything else** from the list above is shown in English as delivered.
- **Agent names** are translated in the UI (e.g. "Legal Agent" → "Rechts-Agent"), so keep sending them in
  English as stable identifiers.

**Typed field (already in `src/types/api.ts`):** `Dashboard.lang?: "en" | "de"`.

---

## 2. Spending by category for the payments donut (optional)

> **Status 2026-11-21: implemented.** `Forecast.outflows_by_category` / `inflows_by_category` (whole horizon) and
> `Forecast.events` (every payment) to cut any period on the client.

**Why:** the "Biggest payments ahead" donut can only show `largest_outflows`, which is the top 5 single
payments (`liquidity.py`: `[:5]`). A real "where does my money go" donut needs totals per category over the
forecast window.

**Proposal:** add to `Forecast`:
```jsonc
"outflows_by_category": [ { "category": "payroll", "total": -138000, "count": 3 }, … ]  // whole horizon, negative = outflow
```
If you can, also give per-day category totals so the UI can cut them to the chosen period (week / month).
A cheaper option is `outflows_by_category_30d` / `_90d` buckets.

---

## 3. Notes on `backend-dev` (already handled in the front-end)

- The new agent names `Analyst Agent`, `Legal Agent` and `Negotiator Agent` are supported next to the
  current names (icon, task, German name).
- Hand-off trace events (`to` + `kind: "handoff"`) are typed as optional fields and shown as "A → B".
- Still to do on the front-end once `backend-dev` is merged:
  - `Finding.kind = "payment_delay"`, `figures_stated: false`, `Action.review` ("Checked by the Legal Agent");
  - `Dashboard.analysis` (briefing, `risk_level`);
  - "Ask your CFO" (`/api/ask`, `/api/ask/suggestions`);
  - contract upload.
