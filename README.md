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
    main.py            FastAPI: /api/dashboard, /api/sync (SSE), /api/actions/{id}/approve|reject, /api/policy, /api/audit
    orchestrator.py    coordinates the 3 agents and their hand-offs, emits trace events
    agents/            analyst.py · legal.py · negotiator.py
    forecast.py        deterministic cash forecast + credit sizing
    llm.py             OpenAI-compatible client for vLLM (+ fallback)
    fallback.py        canned answers for offline demo
    state.py           actions, approvals, audit log, autonomy policy
    config.py          env-based settings
  data/                mock bank data, inbox, contracts, contract index
  tests/               end-to-end test of the happy path (offline)
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
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
LLM_ENABLED=false uvicorn app.main:app --port 8080 --reload
pytest -q

# frontend (proxies /api to :8080)
cd frontend && npm install && npm run dev            # http://localhost:5173
```

To use the cluster model locally: `oc port-forward -n avida-models deploy/granite-8b-predictor 8001:8080`
and set `LLM_BASE_URL=http://localhost:8001/v1`.

## Deploy to OpenShift AI

See [deploy/README.md](deploy/README.md).

## License

All rights reserved. © 2026 Avida CFO team.
