# Avida CFO

**Liquidity agent for small businesses** – Collabothon 2026, *Autonomous CFO (Red Hat Challenge)*.

Avida watches the owner's inbox and bank data, forecasts cash 90 days ahead, checks supplier price
increases against the contracts and proposes explainable next steps. Nothing is executed without the
owner's approval, and all execution is simulated.

## Demo flow

1. **Check my inbox** → three collaborating agents run; every step and every hand-off between them is
   streamed to the UI with its autonomy level.
2. 📊 **Analyst Agent** reads the inbox: two price increases (CloudHost +15%, PaperPro +3.5%), one newsletter ignored
   → hands the price changes to the lawyer.
3. ⚖️ **Legal Agent** checks the contracts: CloudHost breaks the 24-month price guarantee (§5.2) and the 90-day
   notice period; PaperPro is within its 5% indexation cap → verdicts back to the analyst.
4. 📊 **Analyst Agent** forecasts 90 days in 3 scenarios: in early February the balance falls below the 15 000 EUR
   cushion → proposes a 5 000 EUR overdraft bridge (10 000 EUR if the increase were accepted) and writes a briefing.
5. ✉️ **Negotiator Agent** drafts the rejection to CloudHost from the lawyer's clause and the analyst's figures.
6. ⚖️ **Legal Agent** reviews the draft (clause cited, agreed price stated, no placeholders, no internal financials
   revealed); if it finds issues the Negotiator revises once (four-eyes principle).
7. Owner reads the split screen (email ↔ contract quote ↔ calculation), edits the draft and presses **Approve**
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
Jupyter workbench: contract PDFs → clause extraction + benchmark → contracts_index.json
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
notebooks/             contract_extraction.ipynb (OpenShift AI workbench)
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

To use the cluster model locally: `oc port-forward -n avida-models svc/qwen25-7b-instruct-predictor 8000:8080`
and set `LLM_BASE_URL=http://localhost:8000/v1`.

## Deploy to OpenShift AI

See [deploy/README.md](deploy/README.md).

## License

All rights reserved. © 2026 Avida CFO team.
