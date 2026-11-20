# Avida CFO

**Liquidity agent for small businesses** – Collabothon 2026, *Autonomous CFO (Red Hat Challenge)*.

Avida watches the owner's inbox and bank data, forecasts cash 90 days ahead, checks supplier price
increases against the contracts and proposes explainable next steps. Nothing is executed without the
owner's approval, and all execution is simulated.

## Demo flow

1. **Check my inbox** → three agents run, every step is streamed to the UI with its autonomy level.
2. **Inbox Agent** finds two price increases (CloudHost +15%, PaperPro +3.5%) and ignores a newsletter.
3. **Contract Agent** checks them against the contracts: CloudHost breaks the 24-month price guarantee (§5.2)
   and the 90-day notice period; PaperPro is within its 5% indexation cap → accept.
4. **Liquidity Agent** forecasts 90 days: in early February the balance falls below the 15 000 EUR cushion.
   - Recommendation 1: reject the CloudHost increase (draft email, saves 17 640 EUR / year).
   - Recommendation 2: 5 000 EUR overdraft as a bridge until the Bauer invoice is paid (10 000 EUR if the increase were accepted).
5. Owner reads the split screen (email ↔ contract quote ↔ calculation), edits the draft and presses **Approve**
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
                                         │         ├─ Inbox Agent     (LLM: structured extraction)
                                         │         ├─ Contract Agent  (rules decide, LLM explains + quotes)
                                         │         └─ Liquidity Agent (deterministic forecast, LLM drafts email)
                                         └──► vLLM on OpenShift AI (Qwen2.5-7B / Granite, OpenAI-compatible API)
Jupyter workbench: contract PDFs → clause extraction + benchmark → contracts_index.json
```

Design rules: **numbers are never computed by the LLM**; contract verdicts come from explicit rule checks;
every LLM output has a fallback so the demo survives a model outage (and the UI labels it).

## Repository

```
backend/
  app/
    main.py            FastAPI: /api/dashboard, /api/sync (SSE), /api/actions/{id}/approve|reject, /api/policy, /api/audit
    orchestrator.py    runs the 3 agents, emits trace events
    agents/            inbox.py · contract.py · liquidity.py
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
