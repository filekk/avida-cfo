# Avida CFO

**Liquidity agent for small businesses** – Collabothon 2026, *Autonomous CFO (Red Hat Challenge)*.

Avida watches the owner's inbox and bank data, forecasts cash 90 days ahead, checks supplier price
increases against the contracts and proposes explainable next steps. Nothing is executed without the
owner's approval, and all execution is simulated.

## Demo flow

1. **Check my inbox** → three collaborating agents run; every step and every hand-off between them is
   streamed to the UI with its autonomy level.
2. 📊 **Analyst Agent** reads 6 emails (English and German): CloudHost +15%, PaperPro +3.5%, Stahlhandel Nord +6%
   (German), the key customer Bauer announces paying a 38 000 EUR invoice 30 days late (SAP migration),
   IT-Service Kraus announces "moderate" increases **without figures** (Avida doesn't guess), one newsletter ignored.
   Every extracted amount is checked against the email text.
3. ⚖️ **Legal Agent** checks the contracts: CloudHost breaks the price guarantee (§5.2) and the notice period;
   PaperPro and Stahlhandel are within their caps; Bauer's contract fixes 30-day payment terms (§7.1) and forbids
   one-sided changes (§7.2); Kraus cannot be checked (no figures, no contract) → verdicts back to the analyst.
4. 📊 **Analyst Agent** forecasts 90 days in 3 scenarios, planning prudently with Bauer's late payment: the account
   would be 27 882 EUR overdrawn on 3 Feb and **payroll on 28 Jan would not be covered** → proposes a 45 000 EUR
   overdraft for 14 days (max. 164 EUR interest) and writes a briefing.
5. ✉️ **Negotiator Agent** drafts three emails in parallel: rejection to CloudHost, a friendly payment reminder to
   Bauer, a request for exact prices to Kraus.
6. ⚖️ **Legal Agent** reviews every draft (clause cited, figures stated, no placeholders, no internal financials
   revealed – also in German); if it finds issues the Negotiator revises once (four-eyes principle).
7. Owner reads the split screen (email ↔ contract quote ↔ calculation), edits the drafts and presses **Approve**
   → simulated execution, "Saved by Avida" counter goes up.

| Level | Examples |
|---|---|
| 🔍 Analysed by agent | read inbox, check contracts, forecast |
| 💡 Recommendation | reject / accept a price change |
| ✋ Needs your approval | send email, apply for credit |
| 🧪 Simulated execution | every executed action |

## Architecture

```
Vue 3 (Vite, Tailwind) ──SSE/REST──► FastAPI ──► orchestrator
                                         │         ├─ Analyst Agent    (LLM extraction + deterministic forecast + LLM briefing)
                                         │         ├─ Legal Agent      (rules decide, LLM explains; reviews drafts)
                                         │         └─ Negotiator Agent (LLM drafts / revises the supplier email)
                                         └──► vLLM on OpenShift AI (Granite 3.3 8B, FP8, OpenAI-compatible API)
Contract upload (PDF/.md) → extraction.py (Granite, guided JSON, verbatim-quote guard) → Legal Agent knowledge base
Jupyter workbench: imports the same extraction.py → benchmark vs. hand-labelled contracts_index.json
```

Design rules: **numbers are never computed by the LLM**; contract verdicts come from explicit rule checks;
every LLM output has a fallback so the demo survives a model outage (and the UI labels it).

## Repository

```
backend/
  app/
    main.py            FastAPI routes (docs/API.md) + serves the built front-end
    orchestrator.py    coordinates the 3 agents and their hand-offs, emits trace events, re-plans after decisions
    agents/            analyst.py · legal.py · negotiator.py
    decision.py        decision support per action card + the owner's draft tools (review, AV Rewrite)
    ask.py             "Ask your CFO" (routing, facts per agent, guarded answers, problem chat)
    contract_library.py / extraction.py   contract upload → live extraction (shared with the notebook)
    forecast.py        deterministic cash forecast + credit sizing
    llm.py             OpenAI-compatible client for vLLM (failover, circuit breaker, fallback)
    fallback.py        canned answers for offline demo
    texts.py           every owner-facing text in EN / DE + localize()
    tracing.py         optional MLflow tracing of the agents
    state.py           actions, approvals, audit log, autonomy policy
    data.py            loads the mock data sources
    config.py          env-based settings (see "Configuration" below)
  data/                mock bank data, inbox, contracts, contract index
  eval/                MLflow GenAI evaluation of the agents
  tests/               offline tests (pipeline, decisions, contracts, failover, tracing, audit fixes)
frontend/              Vue 3 app (served by FastAPI in production)
notebooks/             contract_extraction.ipynb – benchmark of backend/app/extraction.py (OpenShift AI workbench)
deploy/                ConfigMap, Deployment/Service/Route, step-by-step guide
Dockerfile             one image: builds frontend, runs backend on :8080
.devfile.yaml          OpenShift Dev Spaces workspace
```

## Run locally

```bash
# backend (works without a model: LLM_ENABLED=false uses fallback answers)
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt                 # runtime deps + pytest (the image installs requirements.txt only)
LLM_ENABLED=false uvicorn app.main:app --port 8080 --reload
pytest -q

# frontend (proxies /api to :8080)
cd frontend && npm install && npm run dev            # http://localhost:5173
```

To use the cluster model locally: `oc port-forward -n avida-models deploy/granite-8b-predictor 8001:8080`
and set `LLM_BASE_URL=http://localhost:8001/v1`.

## Configuration

Everything comes from environment variables (on OpenShift: `deploy/configmap.yaml`). Defaults in brackets.

| Variable | What it does |
|---|---|
| `LLM_ENABLED` [`true`] | `false` = never call a model, every answer is the canned one (labelled "cached answer") |
| `LLM_BASE_URL` [`http://localhost:8000/v1`] · `LLM_MODEL` [`granite-8b`] · `LLM_API_KEY` [`EMPTY`] | primary OpenAI-compatible endpoint |
| `LLM_FALLBACK_BASE_URL` · `LLM_FALLBACK_MODEL` · `LLM_FALLBACK_CA_FILE` [empty] | optional second endpoint, tried when the primary fails (empty = no failover) |
| `LLM_TIMEOUT_S` [`60`] · `LLM_FAILOVER_COOLDOWN_S` [`30`] · `LLM_BREAKER_S` [`45`] | per-call timeout · skip the failed primary for · canned answers after all endpoints failed for |
| `DEMO_FALLBACK` [`true`] | use canned answers instead of failing when the model is down or answers garbage |
| `FORECAST_DAYS` [`90`] · `DEMO_TODAY` [`2026-11-20`] · `TRACE_DELAY_S` [`0.4`] | forecast horizon · fixed "today" (empty = real date) · pause between trace steps |
| `CORS_ORIGINS` [`http://localhost:5173,http://127.0.0.1:5173`] | browser origins allowed cross-origin (prod is same-origin; empty = no CORS) |
| `DATA_DIR` [`backend/data`] · `STATIC_DIR` [`backend/static`] | mock data · built front-end |
| `MLFLOW_TRACKING_URI` [empty] · `MLFLOW_EXPERIMENT_NAME` [`avida-cfo-agents`] | optional MLflow tracing (empty = off) |

The SSE stream of an inbox check can be silent for one failed-over model call (2 × `LLM_TIMEOUT_S`), so the
OpenShift route timeout (`haproxy.router.openshift.io/timeout`, 180 s) must stay above that.

## Deploy to OpenShift AI

See [deploy/README.md](deploy/README.md).

## License

All rights reserved. © 2026 Avida CFO team.
