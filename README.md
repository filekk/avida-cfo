# COLLABOTHON 2026 – Project Card

## Project Name *
Avida CFO

## One-Line Summary *
Avida is an AI CFO for small business owners: it reads emails and contracts, spots cash-flow risks early, and suggests ready-to-send solutions, while you make the final call.

## Technology Stack *
- **Languages:** Python, TypeScript/JavaScript
- **Frontend:** Vue 3, TypeScript, Vite, Pinia, Vue Router, Tailwind CSS
- **Backend:** FastAPI, Uvicorn, Pydantic, pypdf, OpenAI-compatible client, Server-Sent Events
- **AI & models:** IBM Granite 3.3 8B Instruct, served by vLLM (KServe) and llm-d behind a private inference gateway
- **Agents & orchestration:** multi-agent pipeline (Analyst, Legal, Negotiator), OGX, MCP server and MCP registry
- **Observability & evaluation:** MLflow (tracing and agent evaluation)
- **Platform:** Red Hat OpenShift, Red Hat OpenShift AI, OpenShift Dev Spaces with Continue (OSS AI code assistant), JupyterLab workbench, OpenShift BuildConfig with GitHub webhook
- **Data:** PostgreSQL (OGX)
- **Testing & tools:** pytest, httpx, Git/GitHub, oc CLI, Docker
- **Hardware:** 1x NVIDIA L4 GPU (24 GB), single OpenShift node (32 CPUs, ~121 GB RAM)

## Project Overview *

### The Problem
Small and medium business owners run their companies on gut feeling when it comes to cash. A late customer payment, a supplier price increase or a contract clause hidden in an email can push the company below zero weeks later, and nobody notices until it is too late. Large companies have a CFO, a lawyer and a controller watching this every day. A 40-person company cannot pay over €10,000 a month for that team, so the owner guesses. Liquidity problems are one of the most common reasons healthy SMEs fail, which makes this worth solving.

### Your Solution
Avida is an autonomous AI CFO that works on the owner's side. It reads the business inbox, understands what each email means for cash, checks it against the real contracts and projects the impact on the bank balance day by day. For every risk it prepares a concrete action, such as a payment reminder citing the contract clause or a counter-offer to a price increase. Three specialised agents work as a team: the Analyst runs the numbers, the Legal agent verifies every claim against the contract and refuses to invent anything, and the Negotiator drafts the reply. What makes Avida different is that it never decides for the owner. It shows facts, options and their impact, and the human approves with one click. Everything runs privately on Red Hat OpenShift, so sensitive financial data never leaves the cluster.

### The Working Prototype
Implemented and working today on OpenShift:
- **Inbox check:** one click runs the agents over the inbox and streams their steps live in the UI.
- **Cash-flow forecast:** a day-by-day liquidity forecast with a safety cushion, showing exactly when the company would go negative (e.g. −€27,882 on 3 February in the demo).
- **Action center:** for each finding, a drafted email grounded in a contract clause (e.g. "§7.1: invoices payable within 30 days"). The owner can edit, approve and send, or reject. The forecast and the "saved" counter update instantly.
- **Ask your CFO:** natural-language questions in English or German, answered by the right agent.
- **Contract library:** upload a PDF or text contract and Granite extracts the key terms live.
- **Policy and audit:** an autonomy matrix showing what each agent may do, and a full history of every decision.

### Behind the Build
The React/Vite frontend is built into the same image as the FastAPI backend and served from one origin. An OpenShift BuildConfig rebuilds the app on every push to `main`. The backend orchestrates the Analyst → Legal → Negotiator chain. Every model call goes to IBM Granite 3.3 8B Instruct on OpenShift AI, first through **llm-d** (distributed inference behind a private gateway) with automatic failover to the vLLM/KServe endpoint, and a deterministic fallback so the owner never sees an error. The agents are also exposed as an **MCP server** listed in an MCP registry, so **OGX** can orchestrate them as tools. **MLflow** traces every inbox check, agent step and model call (prompt, response, tokens, latency), and an evaluation script runs the real agent chain on test emails and scores the results. Contract extraction was prototyped and benchmarked in **Jupyter Notebooks on OpenShift AI**. Part of the backend code was written with **Continue**, an open-source AI code assistant, in **OpenShift Dev Spaces**, running on our own Granite model.

### Challenges and Discoveries
- **One GPU:** our sandbox has a single NVIDIA L4, so vLLM and llm-d could not run side by side. We learned to switch between serving stacks cleanly and built failover so the app keeps working either way.
- **Hallucinations in legal reasoning:** early versions sometimes cited clauses that did not exist. We grounded the Legal agent strictly in extracted contract text and made it refuse when evidence is missing.
- **Small model, structured output:** an 8B model needs tight prompts and validation. We added sanity checks (dates, percentages) and measured accuracy in Jupyter before moving it into the app.
- **Tooling surprises:** MLflow only lists runs in "Evaluation runs" when a dataset is registered, and llm-d needs cluster-level resources. Reading the platform docs closely saved us hours.
- **Team workflow:** working in parallel on frontend and backend over one weekend taught us to agree on a clear API contract first.

### Results and Next Steps
We built a working end-to-end product on enterprise infrastructure in one weekend. Avida reads emails, understands contracts, forecasts cash and drafts actions, all on a private Granite model. We validated it with an automated pytest suite and an MLflow evaluation that runs the real agents on demo emails, scoring **100%** on category, company, amounts, verdict, contract clause and email correctness. We are most proud of the moment the owner clicks "Approve and send" and the forecast moves out of the red.

Current limitations: the demo uses a simulated inbox and bank data, the evaluation set is small, and OGX orchestration is implemented in code but not yet the default path in production.

Next steps: connect real mailboxes and bank APIs (PSD2), grow the evaluation set with real anonymised cases, add guardrails and multi-tenant support, and turn on full MLflow tracing and OGX orchestration in production.

## Source Code Repository *
https://github.com/filekk/avida-cfo

## APP Website
https://avida-cfo-avida-cfo.apps.ocp.8c6kp.sandbox2571.opentlc.com/
