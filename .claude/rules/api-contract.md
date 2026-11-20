---
paths:
  - "frontend/src/api/**"
  - "frontend/src/types/**"
  - "frontend/src/stores/**"
  - "docs/API.md"
  - "backend/app/main.py"
---

# API contract (backend ↔ frontend)

**Source of truth:** `docs/API.md`. Implementation: `backend/app/main.py` (routes), `orchestrator.py`
(dashboard + SSE events), `state.py` (actions, policy, audit), `forecast.py` (Forecast, credit payload).
TypeScript mirror: `frontend/src/types/api.ts`. When these disagree, the backend code is what actually runs.
Point out the mismatch rather than papering over it.

## Endpoints

| Method | Path | Front-end function (`@/api`) | Returns |
|---|---|---|---|
| GET | `/api/health` | `getHealth()` | `{status:"ok"}` |
| GET | `/api/llm/health` | `getLlmHealth()` | `LlmHealth` (`ok`, `models?`, `reason?`) |
| GET | `/api/config` | `getConfig()` | `AppConfig` |
| GET | `/api/dashboard` | `getDashboard()` | `Dashboard` |
| GET | `/api/sync` (SSE) | `startSync({onTrace,onResult,onError})` | events `trace` → `result` \| `error` |
| POST | `/api/actions/{id}/approve` | `approveAction(id, editedBody?)` | `DecisionResponse` |
| POST | `/api/actions/{id}/reject` | `rejectAction(id)` | `DecisionResponse` |
| GET | `/api/policy` | `getPolicy()` | `PolicyRule[]` |
| GET | `/api/audit` | `getAudit()` | `AuditEntry[]` |
| POST | `/api/reset` | `resetDemo()` | start `Dashboard` (also removes uploaded contracts) |
| GET | `/api/ask/suggestions` | `getAskSuggestions()` | `AskSuggestions` (`note` only before sync) |
| POST | `/api/ask` | `askCfo(question)` | `AskAnswer` – chip instant (`rules`), typed 3–7 s (`llm`/`fallback`) |
| GET | `/api/contracts` | `getContracts()` | `ContractSummary[]` (`origin`: `index` \| `uploaded`) |
| POST | `/api/contracts/upload` | `uploadContract(file)` | `UploadResult`, 10–20 s; 422 `{detail}` if unreadable |
| DELETE | `/api/contracts/{id}` | `deleteContract(id)` | `ContractSummary[]`; 404 for index contracts |

## Gotchas

- Before the first sync, `scenarios` contains **only `current`**. `if_accepted` and `recommended` appear after sync.
- `contract.contract` is `null` and `checks` is `[]` when `verdict === "unclear"` (no contract found).
- `Action` is a discriminated union on `type`: `send_email` → `payload {to, body}`; `credit_application` →
  `CreditPayload`. Narrow with `action.type === "send_email"` before touching `payload.body`.
- `approve` body is `{"edited_body": string | null}`. Only `send_email` uses it. `reject` takes no body.
- Deciding an already-decided action returns it unchanged (idempotent). Unknown id → 404 `{detail}`.
- SSE: a server-side failure arrives as `event: error` **with** data. A dropped connection fires `error` **without**
  data. `api/sync.ts` handles both and closes the stream.
- `trace.source`: `llm` | `fallback` | `rules`. **Fallback must be labelled** in the UI (`SourceTag`).
- Numbers are raw EUR floats and dates are ISO strings. Format only via `utils/format.ts`.
- Ask: send a chip's `question` **unchanged** (that's how the backend knows to give the prepared answer). `lang`
  goes in the body (`askCfo` takes it from the UI locale). `in_data: false` = polite refusal → show the suggestions.
  Answers and suggestions are already in the UI language. Re-fetch suggestions after sync, reset and language switch.
- Contracts: an uploaded contract affects the **next** sync, not the current dashboard. Show `warnings` before the
  owner trusts it, and label `extracted_by: "cached answer"` like any fallback. After a sync with an uploaded
  contract, `finding.contract.contract.origin === "uploaded"`.
- `saved_liquidity` comes back on every decision. Update `kpis.saved_liquidity` from the response and don't recompute it.

## Changing the contract

1. Agree on it with the back-end team. They own `backend/` and `docs/API.md`.
2. Update `types/api.ts` → fix the compile errors → update the `api/*` function → store → UI.
3. Run `npm run build`. vue-tsc is the safety net.
