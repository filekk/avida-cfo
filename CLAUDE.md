# Avida CFO — project memory

Collabothon 2026 · **Autonomous CFO (Red Hat challenge, business owner: Commerzbank)**.
An AI liquidity assistant for SME owners who run their own finances: it reads the inbox and bank data,
forecasts cash 90 days ahead, checks supplier price increases against contracts and proposes
**explainable** next steps. Nothing is executed without the owner's click, and every execution is simulated.

Full challenge summary: [.claude/context/challenge.md](.claude/context/challenge.md).

## Team & ownership

| Area | Owner | Paths |
|---|---|---|
| Front-end (Vue 3 + Tailwind) | 1 person | `frontend/` |
| Back-end, agents, LLM, deploy | 3 people | `backend/`, `deploy/`, `notebooks/`, `Dockerfile`, `.devfile.yaml` |
| API contract | shared | `docs/API.md` (source of truth) |

- Front-end work happens on the **`frontend`** branch. Don't edit `backend/`, `deploy/` or `docs/API.md`
  from front-end tasks. If the UI needs a contract change, write the proposal down and hand it to the back-end team.
- Back-end changes the contract → `docs/API.md` + `frontend/src/types/api.ts` must be updated together.
- Don't commit or push on your own. Prepare the changes + a commit message and leave the commit to the developer.

## Architecture

```
Vue 3 SPA (Vite, Tailwind, Pinia, vue-router) ──REST + SSE──► FastAPI (backend/app/main.py)
                                                              └─ orchestrator: Inbox → Contract → Liquidity agent
                                                                  └─ vLLM on OpenShift AI (Granite / Qwen, OpenAI-compatible API)
```

- **One container:** the Dockerfile builds `frontend/` (`npm run build` → `dist/`) and FastAPI serves it from
  the same origin. No CORS. Unknown paths fall back to `index.html`, so history-mode routing works.
- **The LLM never computes numbers.** Forecast and contract verdicts are deterministic. The LLM extracts,
  explains and drafts. Every LLM answer has a fallback (`source: "fallback"`), and the UI has to label it.
- State lives in memory on the backend (single replica). `POST /api/reset` before every demo run.

## Demo flow the UI must support

1. `GET /api/dashboard` → start screen (forecast only)
2. "Check my inbox" → `GET /api/sync` (SSE): live `trace` steps, each with its autonomy badge → `result` = new dashboard
3. Findings: split screen **email ↔ contract clause ↔ calculation** (CloudHost +15 % violates §5.2; PaperPro +3.5 % allowed)
4. Decisions: edit the draft email → **Approve** / **Not now** → simulated execution, "Saved by Avida" goes up
5. `/api/policy` (who may do what) and `/api/audit` (history)

## Non-negotiable UI rules (from the challenge + docs/API.md)

1. Never trigger an action without an explicit click (approve/reject only).
2. Always show the **autonomy badge** (Analysed by agent · Recommendation · Needs your approval · Simulated execution)
   next to agent steps and action cards.
3. Label `source: "fallback"` discreetly ("cached answer") so the UI is honest about the AI.
4. Format money on the client: `Intl.NumberFormat("de-DE", { currency: "EUR" })`. Dates arrive as ISO `YYYY-MM-DD`.
5. "Innovations for all generations": plain language, large touch targets, readable contrast (WCAG AA), works on mobile.
6. **No emoji anywhere in the UI.** Icons come only from Lucide (ISC) via `AppIcon`. Every asset has to be
   free/open-source with its licence listed in `frontend/THIRD_PARTY_LICENSES.md`. It's a competition entry, so nothing paid or unclear.
7. **Two languages (EN/DE).** Every UI string goes through `t()` from `frontend/src/i18n` with a German entry; the UI
   sends `?lang=` to the API (proposal for the backend: `frontend/CONTRACT_PROPOSALS.md`).

## Commands

```bash
# frontend (Node 20+; Vite proxies /api → VITE_API_TARGET, default http://localhost:8080)
cd frontend && npm install && npm run dev        # http://localhost:5173
npm run typecheck                                 # vue-tsc
npm run build                                     # typecheck + vite build → dist/

# backend offline (no model needed)
cd backend && pip install -r requirements-dev.txt   # runtime deps + pytest (the image installs requirements.txt only)
LLM_ENABLED=false uvicorn app.main:app --port 8080 --reload
pytest -q
```

Live backend on the cluster: see `docs/API.md` (Swagger at `/docs`). It is **shared**: `sync`, `approve`
and `reset` change the state for the whole team, so use a local backend for UI tests.

## Where to look

- Front-end conventions and structure: [frontend/CLAUDE.md](frontend/CLAUDE.md)
- Path-scoped rules (loaded automatically): `.claude/rules/` (API contract, design system, Vue conventions)
- Skills: `.claude/skills/` (`vue-component`, `vue-view`, `api-endpoint`, `frontend-verify`)
- UI/UX prototype (outside the repo): `../ProjektPrototyp/index.html` (the "Aurum" theme)
- Challenge PDFs (outside the repo): `../Materialy/`
